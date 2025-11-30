"""Flask web application for parsing KNX project files."""

import json
import os
import tempfile
from datetime import datetime
from pathlib import Path

from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename

from xknxproject import XKNXProj

# Get project root directory (where app.py is located)
PROJECT_ROOT = Path(__file__).parent.absolute()

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50MB max file size
app.config["UPLOAD_FOLDER"] = tempfile.gettempdir()

ALLOWED_EXTENSIONS = {"knxproj"}


def allowed_file(filename: str) -> bool:
    """Check if file extension is allowed."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/")
def index():
    """Render the main page."""
    return render_template("index.html")


@app.route("/list-json-files", methods=["GET"])
def list_json_files():
    """List all JSON files in the project root."""
    json_files = []
    try:
        for file in PROJECT_ROOT.glob("*.json"):
            # Skip test files
            if not file.name.startswith("test_"):
                json_files.append({
                    "name": file.name,
                    "path": str(file),
                    "size": file.stat().st_size,
                    "modified": datetime.fromtimestamp(file.stat().st_mtime).isoformat(),
                })
        json_files.sort(key=lambda x: x["modified"], reverse=True)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
    return jsonify({
        "project_root": str(PROJECT_ROOT),
        "files": json_files,
        "count": len(json_files),
    })


@app.route("/view-json/<filename>", methods=["GET"])
def view_json_file(filename: str):
    """View a specific JSON file."""
    # Security: only allow filenames that exist and are in project root
    json_filepath = PROJECT_ROOT / filename
    if not json_filepath.exists() or not str(json_filepath).startswith(str(PROJECT_ROOT)):
        return jsonify({"error": "File not found"}), 404
    
    try:
        with open(json_filepath, "r", encoding="utf-8") as f:
            json_data = json.load(f)
        return jsonify(json_data)
    except Exception as e:
        return jsonify({"error": f"Error reading file: {str(e)}"}), 500


@app.route("/upload", methods=["POST"])
def upload_file():
    """Handle file upload and parsing."""
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    password = request.form.get("password", "").strip() or None
    language = request.form.get("language", "").strip() or None

    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": "Invalid file type. Please upload a .knxproj file"}), 400

    # Save uploaded file temporarily
    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    
    try:
        file.save(filepath)

        # Parse the KNX project
        knxproj = XKNXProj(
            path=filepath,
            password=password,
            language=language,
        )
        project = knxproj.parse()

        # Build structured JSON with devices and their group addresses (like ETS6 view)
        structured_devices = []
        for device_id, device in project["devices"].items():
            device_group_objects = []
            
            # Process each communication object for this device
            for com_obj_id in device["communication_object_ids"]:
                if com_obj_id not in project["communication_objects"]:
                    continue
                    
                com_obj = project["communication_objects"][com_obj_id]
                
                # Verify this communication object belongs to this device
                if com_obj["device_address"] != device["individual_address"]:
                    continue
                
                # Get full group address details for each linked group address
                group_addresses_full = []
                for ga_address in com_obj["group_address_links"]:
                    if ga_address in project["group_addresses"]:
                        ga = project["group_addresses"][ga_address]
                        group_addresses_full.append({
                            "address": ga["address"],
                            "name": ga.get("name", ""),
                            "dpt": ga.get("dpt"),
                            "description": ga.get("description", ""),
                            "comment": ga.get("comment", ""),
                        })
                
                # Build flags (C, R, W, T, U)
                flags = {
                    "C": com_obj["flags"]["communication"],
                    "R": com_obj["flags"]["read"],
                    "W": com_obj["flags"]["write"],
                    "T": com_obj["flags"].get("transmit", False),
                    "U": com_obj["flags"].get("update", False),
                }
                
                # Get DPT type description
                dpt_type = None
                if com_obj.get("dpts") and len(com_obj["dpts"]) > 0:
                    dpt = com_obj["dpts"][0]
                    dpt_type = f"{dpt['main']}.{dpt['sub']}" if dpt.get('sub') else str(dpt['main'])
                
                # Create group object entry (like ETS6 table row)
                group_object = {
                    "number": com_obj["number"],
                    "name": com_obj.get("name") or com_obj.get("text") or f"Object {com_obj['number']}",
                    "object_function": com_obj.get("function_text") or com_obj.get("text") or "",
                    "linked_with": com_obj.get("description") or com_obj.get("function_text") or com_obj.get("text") or "",
                    "group_addresses": group_addresses_full,  # Full group address details
                    "length": com_obj.get("object_size", ""),
                    "flags": flags,
                    "dpt": dpt_type,
                    "communication_object_id": com_obj_id,
                }
                device_group_objects.append(group_object)
            
            # Sort by communication object number
            device_group_objects.sort(key=lambda x: x["number"])
            
            # Create device entry with all its group objects
            device_entry = {
                "device_id": device_id,
                "name": device.get("name") or device.get("hardware_name") or "Unnamed Device",
                "hardware_name": device.get("hardware_name", ""),
                "individual_address": device["individual_address"],
                "manufacturer": device.get("manufacturer_name", ""),
                "description": device.get("description", ""),
                "group_objects": device_group_objects,  # All group objects with group addresses
                "total_group_objects": len(device_group_objects),
            }
            structured_devices.append(device_entry)
        
        # Sort devices by individual address
        structured_devices.sort(key=lambda x: x["individual_address"])
        
        # Create the structured JSON output
        structured_output = {
            "project_info": project["info"],
            "devices": structured_devices,
            "total_devices": len(structured_devices),
            "total_group_addresses": len(project["group_addresses"]),
        }
        
        # Save JSON files to project root
        # Generate filename based on original filename and timestamp
        base_name = Path(filename).stem  # Get filename without extension
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save structured JSON (with devices and group addresses)
        structured_json_filename = f"{base_name}_{timestamp}.json"
        structured_json_filepath = PROJECT_ROOT / structured_json_filename
        
        # Save raw JSON (complete parsed project)
        raw_json_filename = f"{base_name}_{timestamp}_raw.json"
        raw_json_filepath = PROJECT_ROOT / raw_json_filename
        
        json_filename = None
        raw_json_filename_saved = None
        
        try:
            # Save structured JSON
            with open(structured_json_filepath, "w", encoding="utf-8") as json_file:
                json.dump(structured_output, json_file, indent=2, ensure_ascii=False)
            # Verify file was created
            if not structured_json_filepath.exists():
                raise IOError(f"Failed to create structured JSON file at {structured_json_filepath}")
            json_filename = structured_json_filename
        except Exception as json_error:
            # Log error but don't fail the request
            print(f"Error saving structured JSON file: {json_error}")
        
        try:
            # Save raw JSON (complete parsed project)
            with open(raw_json_filepath, "w", encoding="utf-8") as json_file:
                json.dump(project, json_file, indent=2, ensure_ascii=False)
            # Verify file was created
            if not raw_json_filepath.exists():
                raise IOError(f"Failed to create raw JSON file at {raw_json_filepath}")
            raw_json_filename_saved = raw_json_filename
        except Exception as json_error:
            # Log error but don't fail the request
            print(f"Error saving raw JSON file: {json_error}")
        
        # Clean up temporary file
        os.remove(filepath)

        # Use the structured output for the web display as well
        # Convert structured devices to display format (for backward compatibility with frontend)
        devices_data = []
        for device_entry in structured_devices:
            device_info = {
                "id": device_entry["device_id"],
                "name": device_entry["name"],
                "hardware_name": device_entry["hardware_name"],
                "individual_address": device_entry["individual_address"],
                "manufacturer": device_entry["manufacturer"],
                "description": device_entry["description"],
                "group_objects": [],
            }
            
            # Convert group objects to display format
            for go in device_entry["group_objects"]:
                # Format group addresses as comma-separated string for display
                ga_addresses_str = ", ".join([ga["address"] for ga in go["group_addresses"]]) if go["group_addresses"] else ""
                
                # Format flags as string
                flags_list = []
                if go["flags"]["C"]:
                    flags_list.append("C")
                if go["flags"]["R"]:
                    flags_list.append("R")
                if go["flags"]["W"]:
                    flags_list.append("W")
                if go["flags"]["T"]:
                    flags_list.append("T")
                if go["flags"]["U"]:
                    flags_list.append("U")
                flags_str = " ".join(flags_list) if flags_list else "-"
                
                obj_info = {
                    "com_obj_id": go["communication_object_id"],
                    "number": go["number"],
                    "name": go["name"],
                    "object_function": go["object_function"],
                    "linked_with": go["linked_with"],
                    "group_addresses": ga_addresses_str,
                    "length": go["length"],
                    "flags": flags_str,
                    "dpt": go["dpt"],
                }
                device_info["group_objects"].append(obj_info)
            
            devices_data.append(device_info)

        response_data = {
            "success": True,
            "project_info": structured_output["project_info"],
            "devices": devices_data,
            "total_devices": structured_output["total_devices"],
            "total_group_addresses": structured_output["total_group_addresses"],
            "full_json": structured_output,  # Include the structured JSON output
        }
        
        if json_filename:
            response_data["json_file_saved"] = json_filename
            response_data["json_file_path"] = str(structured_json_filepath)
        
        if raw_json_filename_saved:
            response_data["raw_json_file_saved"] = raw_json_filename_saved
            response_data["raw_json_file_path"] = str(raw_json_filepath)
        
        return jsonify(response_data)

    except Exception as e:
        # Clean up file if it still exists
        if os.path.exists(filepath):
            os.remove(filepath)
        return jsonify({"error": f"Error parsing file: {str(e)}"}), 500


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)

