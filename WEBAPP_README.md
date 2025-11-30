# KNX Project Parser Web Application

A simple web interface for uploading and parsing KNX project files (.knxproj).

## Features

- Upload .knxproj files (password protected or not)
- Parse and display KNX devices
- Show communication objects for each device
- Display associated group addresses with DPT types
- Modern, responsive web interface

## Installation

1. Make sure you have the virtual environment activated:
   ```bash
   .\venv\Scripts\Activate.ps1  # Windows PowerShell
   ```

2. Install web dependencies (if not already installed):
   ```bash
   pip install -r requirements_web.txt
   ```

## Running the Application

Start the Flask server:
```bash
python app.py
```

The web application will be available at:
- **URL**: http://localhost:5000
- **Host**: 0.0.0.0 (accessible from network)
- **Port**: 5000

## Usage

1. Open your web browser and navigate to http://localhost:5000
2. Click "Choose File" and select a .knxproj file
3. (Optional) Enter password if the file is password protected
4. (Optional) Select a language preference
5. Click "Upload and Parse"
6. View the results showing:
   - Project information
   - All devices with their individual addresses
   - Communication objects for each device
   - Group addresses linked to each communication object

## Project Structure

- `app.py` - Flask web application
- `templates/index.html` - Web interface HTML/CSS/JavaScript
- `requirements_web.txt` - Web application dependencies

## Notes

- Maximum file size: 50MB
- Files are temporarily stored during parsing and automatically deleted
- The application supports ETS 4, 5, and 6 project files

