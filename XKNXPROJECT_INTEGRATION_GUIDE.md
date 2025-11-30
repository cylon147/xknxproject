# xknxproject Integration Guide for Matterbridge

## Overview

**xknxproject** is a Python library that extracts and parses KNX project files (.knxproj) from ETS (Engineering Tool Software) versions 4, 5, and 6. This guide explains how to use xknxproject to extract device information, communication objects, and group addresses for integration into Matterbridge projects.

## Installation

```bash
pip install xknxproject
```

**Dependencies:**
- Python >= 3.9
- pyzipper >= 0.3.6
- striprtf >= 0.0.26

## Basic Usage

```python
from xknxproject import XKNXProj
from xknxproject.models import KNXProject

# Initialize parser
knxproj = XKNXProj(
    path="path/to/project.knxproj",
    password="password",  # Optional: only if project is password protected
    language="de-DE",      # Optional: language code (de-DE, en-US, etc.)
)

# Parse the project
project: KNXProject = knxproj.parse()
```

## Data Structure Overview

The parsed `KNXProject` is a TypedDict containing the following main sections:

```python
{
    "info": ProjectInfo,                    # Project metadata
    "devices": dict[str, Device],            # All devices in the project
    "communication_objects": dict[str, CommunicationObject],  # All communication objects
    "group_addresses": dict[str, GroupAddress],  # All group addresses
    "topology": dict[str, Area],             # Topology (areas, lines)
    "locations": dict[str, Space],            # Room/location information
    "group_ranges": dict[str, GroupRange],    # Group address ranges
    "functions": dict[str, Function],         # Functions assigned to rooms
}
```

## Core Data Models

### 1. Device

A device represents a physical KNX device in the installation.

```python
Device = {
    "name": str,                    # Custom name (can be empty)
    "hardware_name": str,           # Hardware product name
    "order_number": str,             # Product order number
    "description": str,              # Device description
    "manufacturer_name": str,       # Manufacturer name
    "individual_address": str,       # Individual address (e.g., "1.1.5")
    "application": str | None,       # Application program reference
    "project_uid": int | None,       # Project unique identifier
    "communication_object_ids": list[str],  # List of communication object IDs
    "channels": dict[str, Channel], # Channels (if any)
}
```

**Key Field:** `communication_object_ids` - This is the link to communication objects.

**Example:**
```python
device = {
    "name": "D1-G1, Tunable Light 1",
    "hardware_name": "DALI Control 2x64",
    "individual_address": "1.1.5",
    "communication_object_ids": [
        "1.1.5/O-40_R-1433",
        "1.1.5/O-41_R-1434",
        "1.1.5/O-70_R-1505"
    ]
}
```

### 2. CommunicationObject

A communication object represents a data point on a device that can communicate via group addresses.

```python
CommunicationObject = {
    "name": str,                    # Object name (e.g., "D1-G1, Switching, Tunable Light 1")
    "number": int,                   # Object number (e.g., 40, 41, 71)
    "text": str,                     # Object text description
    "function_text": str,            # Function description (e.g., "ON/OFF", "Dimming relative")
    "description": str,              # Additional description
    "device_address": str,           # ⭐ Links back to device (e.g., "1.1.5")
    "device_application": str | None, # Application program reference
    "module": ModuleInstanceInfos | None,  # Module information (if applicable)
    "channel": str | None,           # Channel identifier (if applicable)
    "dpts": list[DPTType],          # Data Point Types
    "object_size": str,              # Size (e.g., "1 Bit", "4 bit", "1 byte", "2 bytes")
    "group_address_links": list[str], # ⭐ List of group address strings (e.g., ["6/0/1"])
    "flags": Flags,                  # Communication flags
}
```

**Key Fields:**
- `device_address`: Links the communication object to its device
- `group_address_links`: List of group addresses this object is linked to

**Example:**
```python
com_obj = {
    "name": "D1-G1, Switching, Tunable Light 1",
    "number": 71,
    "function_text": "ON/OFF",
    "device_address": "1.1.5",  # Links to device with individual_address "1.1.5"
    "group_address_links": ["6/0/1"],  # This object is linked to group address "6/0/1"
    "object_size": "1 bit",
    "flags": {
        "read": False,
        "write": True,
        "communication": True,
        "transmit": False,
        "update": False,
        "read_on_init": False
    }
}
```

### 3. GroupAddress

A group address represents a shared communication address that multiple devices can use.

```python
GroupAddress = {
    "name": str,                    # Group address name
    "identifier": str,              # Internal identifier
    "raw_address": int,             # Raw numeric address
    "address": str,                  # ⭐ Address string (e.g., "6/0/1", "1/0/5")
    "project_uid": int | None,       # Project unique identifier
    "dpt": DPTType | None,          # Data Point Type
    "data_secure": bool,            # Whether data is encrypted
    "communication_object_ids": list[str],  # ⭐ Communication objects using this GA
    "description": str,              # Description
    "comment": str,                  # Comment
}
```

**Key Field:** `address` - The group address string used for matching.

**Example:**
```python
group_address = {
    "name": "Switch Tunable Light 1",
    "address": "6/0/1",  # The group address string
    "dpt": {"main": 1, "sub": None},  # DPT-1
    "communication_object_ids": ["1.1.5/O-40_R-1433"]  # Objects using this GA
}
```

### 4. Flags

Communication flags indicate the capabilities of a communication object.

```python
Flags = {
    "read": bool,           # Can read from this object
    "write": bool,          # Can write to this object
    "communication": bool,   # Object is enabled for communication
    "transmit": bool,       # Object transmits
    "update": bool,         # Object updates
    "read_on_init": bool,   # Read on initialization
}
```

## How Devices Link to Group Addresses

### The Relationship Chain

```
Device (individual_address: "1.1.5")
  ↓ has communication_object_ids: ["1.1.5/O-40_R-1433", "1.1.5/O-41_R-1434", ...]
    ↓
CommunicationObject (device_address: "1.1.5", group_address_links: ["6/0/1"])
  ↓ has group_address_links: ["6/0/1", "6/2/1", ...]
    ↓
GroupAddress (address: "6/0/1")
```

### Step-by-Step: Finding Group Addresses for a Device

**Method 1: Device → Communication Objects → Group Addresses (Recommended)**

```python
def get_device_group_addresses(project: KNXProject, device_id: str) -> list[dict]:
    """
    Get all group addresses for a specific device.
    
    Args:
        project: Parsed KNXProject
        device_id: Device identifier
        
    Returns:
        List of group address information dictionaries
    """
    device = project["devices"][device_id]
    device_address = device["individual_address"]
    group_addresses = []
    
    # Step 1: Get all communication objects for this device
    for com_obj_id in device["communication_object_ids"]:
        if com_obj_id not in project["communication_objects"]:
            continue
            
        com_obj = project["communication_objects"][com_obj_id]
        
        # Step 2: Verify this communication object belongs to this device
        if com_obj["device_address"] != device_address:
            # Safety check: skip if mismatch (shouldn't happen)
            continue
        
        # Step 3: Get group addresses linked to this communication object
        for ga_address_str in com_obj["group_address_links"]:
            # Step 4: Find the full group address information
            if ga_address_str in project["group_addresses"]:
                ga = project["group_addresses"][ga_address_str]
                group_addresses.append({
                    "address": ga["address"],
                    "name": ga["name"],
                    "dpt": ga["dpt"],
                    "communication_object": {
                        "id": com_obj_id,
                        "number": com_obj["number"],
                        "name": com_obj["name"],
                        "function": com_obj["function_text"],
                    }
                })
    
    return group_addresses
```

**Method 2: Group Address → Communication Objects → Device (Reverse Lookup)**

```python
def get_devices_for_group_address(project: KNXProject, ga_address: str) -> list[str]:
    """
    Find all devices that use a specific group address.
    
    Args:
        project: Parsed KNXProject
        ga_address: Group address string (e.g., "6/0/1")
        
    Returns:
        List of device IDs using this group address
    """
    if ga_address not in project["group_addresses"]:
        return []
    
    ga = project["group_addresses"][ga_address]
    device_ids = set()
    
    # Get all communication objects using this group address
    for com_obj_id in ga["communication_object_ids"]:
        if com_obj_id not in project["communication_objects"]:
            continue
            
        com_obj = project["communication_objects"][com_obj_id]
        device_address = com_obj["device_address"]
        
        # Find device with matching individual_address
        for device_id, device in project["devices"].items():
            if device["individual_address"] == device_address:
                device_ids.add(device_id)
                break
    
    return list(device_ids)
```

## Complete Example: Extracting Device Information

```python
from xknxproject import XKNXProj
from xknxproject.models import KNXProject

def extract_device_info(knxproj_path: str, password: str = None) -> list[dict]:
    """
    Extract all devices with their communication objects and group addresses.
    
    Returns a list of devices, each containing:
    - Device information
    - List of communication objects
    - List of group addresses
    """
    # Parse the project
    knxproj = XKNXProj(path=knxproj_path, password=password)
    project = knxproj.parse()
    
    devices_info = []
    
    # Iterate through all devices
    for device_id, device in project["devices"].items():
        device_info = {
            "device_id": device_id,
            "name": device["name"],
            "hardware_name": device["hardware_name"],
            "individual_address": device["individual_address"],
            "manufacturer": device["manufacturer_name"],
            "description": device["description"],
            "communication_objects": [],
            "group_addresses": set(),  # Use set to avoid duplicates
        }
        
        # Get communication objects for this device
        for com_obj_id in device["communication_object_ids"]:
            if com_obj_id not in project["communication_objects"]:
                continue
                
            com_obj = project["communication_objects"][com_obj_id]
            
            # Verify ownership
            if com_obj["device_address"] != device["individual_address"]:
                continue
            
            # Build communication object info
            com_obj_info = {
                "id": com_obj_id,
                "number": com_obj["number"],
                "name": com_obj["name"],
                "function": com_obj["function_text"],
                "description": com_obj["description"],
                "object_size": com_obj["object_size"],
                "dpt": com_obj["dpts"],
                "flags": {
                    "read": com_obj["flags"]["read"],
                    "write": com_obj["flags"]["write"],
                    "communication": com_obj["flags"]["communication"],
                },
                "group_addresses": [],
            }
            
            # Get group addresses for this communication object
            for ga_address_str in com_obj["group_address_links"]:
                if ga_address_str in project["group_addresses"]:
                    ga = project["group_addresses"][ga_address_str]
                    com_obj_info["group_addresses"].append({
                        "address": ga["address"],
                        "name": ga["name"],
                        "dpt": ga["dpt"],
                        "description": ga["description"],
                    })
                    device_info["group_addresses"].add(ga["address"])
            
            device_info["communication_objects"].append(com_obj_info)
        
        # Convert set to sorted list
        device_info["group_addresses"] = sorted(list(device_info["group_addresses"]))
        devices_info.append(device_info)
    
    return devices_info

# Usage
devices = extract_device_info("project.knxproj")
for device in devices:
    print(f"Device: {device['name']} ({device['individual_address']})")
    print(f"  Group Addresses: {device['group_addresses']}")
    print(f"  Communication Objects: {len(device['communication_objects'])}")
```

## ETS6-Style Table Format

To display devices in a table format similar to ETS6's "Group Objects" view:

```python
def get_device_group_objects_table(project: KNXProject, device_id: str) -> list[dict]:
    """
    Get communication objects for a device in table format (like ETS6).
    Each row represents one communication object.
    """
    device = project["devices"][device_id]
    rows = []
    
    for com_obj_id in device["communication_object_ids"]:
        if com_obj_id not in project["communication_objects"]:
            continue
            
        com_obj = project["communication_objects"][com_obj_id]
        
        # Verify ownership
        if com_obj["device_address"] != device["individual_address"]:
            continue
        
        # Get group addresses (comma-separated)
        group_addresses = ", ".join(com_obj["group_address_links"])
        
        # Build flags string (C, R, W format)
        flags = []
        if com_obj["flags"]["communication"]:
            flags.append("C")
        if com_obj["flags"]["read"]:
            flags.append("R")
        if com_obj["flags"]["write"]:
            flags.append("W")
        flags_str = " ".join(flags) if flags else "-"
        
        rows.append({
            "number": com_obj["number"],                    # Column: Number
            "name": com_obj["name"],                        # Column: Name
            "object_function": com_obj["function_text"],     # Column: Object Function
            "linked_with": com_obj["description"],          # Column: Linked with
            "group_addresses": group_addresses,              # Column: Group Addresses
            "length": com_obj["object_size"],               # Column: Length
            "flags": flags_str,                             # Column: C, R, W
        })
    
    # Sort by communication object number
    rows.sort(key=lambda x: x["number"])
    return rows
```

## Important Notes

### 1. Communication Object ID Format

Communication object IDs follow the pattern: `{device_address}/{reference_id}`

- Example: `"1.1.5/O-40_R-1433"`
  - Device address: `"1.1.5"`
  - Reference ID: `"O-40_R-1433"`

This format allows you to extract the device address from the ID if needed.

### 2. Verification is Critical

Always verify that `com_obj["device_address"] == device["individual_address"]` before using group addresses. This ensures:
- The communication object belongs to the device
- No data corruption or parsing errors
- Correct device-to-group-address mapping

### 3. Multiple Group Addresses

A single communication object can link to multiple group addresses:
```python
com_obj["group_address_links"] = ["6/0/1", "6/0/2", "6/0/3"]
```

### 4. Empty Group Addresses

Some communication objects may not have group addresses:
```python
com_obj["group_address_links"] = []  # Empty list
```

### 5. Group Address Lookup

Group addresses are stored in the dictionary keyed by their address string:
```python
ga = project["group_addresses"]["6/0/1"]  # Direct lookup
```

## Error Handling

```python
from xknxproject import XKNXProj
from xknxproject.exceptions import XKNXProjectException

try:
    knxproj = XKNXProj(path="project.knxproj", password="wrong_password")
    project = knxproj.parse()
except XKNXProjectException as e:
    print(f"Error parsing project: {e}")
except FileNotFoundError:
    print("Project file not found")
except Exception as e:
    print(f"Unexpected error: {e}")
```

## Performance Considerations

- **Parsing Time**: A medium-sized project takes ~1.5 seconds. Large projects may take >3 seconds.
- **Memory**: The entire project is loaded into memory as dictionaries.
- **Caching**: Consider caching parsed results if you need to query multiple times.

## Integration with Matterbridge

### Recommended Approach

1. **Parse Once**: Parse the .knxproj file once at startup or when the file changes.
2. **Store in Memory**: Keep the parsed `KNXProject` in memory for fast queries.
3. **Query Functions**: Create helper functions to query devices, group addresses, etc.
4. **Update on File Change**: Re-parse when the .knxproj file is updated.

### Example Integration Structure

```python
class KNXProjectManager:
    def __init__(self, knxproj_path: str, password: str = None):
        self.path = knxproj_path
        self.password = password
        self.project = None
        self._load_project()
    
    def _load_project(self):
        """Load and parse the KNX project."""
        knxproj = XKNXProj(path=self.path, password=self.password)
        self.project = knxproj.parse()
    
    def get_device(self, device_id: str) -> dict:
        """Get device information."""
        return self.project["devices"].get(device_id)
    
    def get_device_group_addresses(self, device_id: str) -> list[str]:
        """Get all group addresses for a device."""
        # Implementation from earlier examples
        pass
    
    def find_device_by_address(self, individual_address: str) -> str | None:
        """Find device ID by individual address."""
        for device_id, device in self.project["devices"].items():
            if device["individual_address"] == individual_address:
                return device_id
        return None
```

## Troubleshooting

### Issue: Communication objects not found

**Symptom:** `com_obj_id` not in `project["communication_objects"]`

**Solution:** Check if the communication object ID format matches. The ID should be `"{device_address}/{ref_id}"`.

### Issue: Group addresses not matching

**Symptom:** Group address string not found in `project["group_addresses"]`

**Solution:** Verify the group address format. It should match exactly (e.g., `"6/0/1"` not `"6.0.1"`).

### Issue: Device address mismatch

**Symptom:** `com_obj["device_address"] != device["individual_address"]`

**Solution:** This shouldn't happen in valid projects. Check for:
- Corrupted project file
- Parsing errors
- Project file version compatibility

## Additional Resources

- **xknxproject GitHub**: https://github.com/XKNX/xknxproject
- **Type Definitions**: See `xknxproject/models/knxproject.py` for complete type definitions
- **Test Examples**: See `test/resources/stubs/` for example JSON outputs

## Summary

**Key Takeaways:**

1. **Device → Communication Objects → Group Addresses** is the relationship chain
2. **Always verify** `device_address` matches `individual_address`
3. **Communication object IDs** include the device address in their format
4. **Group addresses** are stored keyed by their address string
5. **One communication object** = one row in ETS6-style table
6. **Multiple group addresses** can link to one communication object

This structure allows you to:
- Find all group addresses for a device
- Find all devices using a group address
- Display devices in ETS6-style table format
- Build device-to-group-address mappings for Matterbridge integration

