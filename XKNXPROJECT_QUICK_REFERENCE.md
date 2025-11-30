# xknxproject Quick Reference Guide

## Installation
```bash
pip install xknxproject
```

## Basic Usage
```python
from xknxproject import XKNXProj

knxproj = XKNXProj(path="project.knxproj", password=None, language=None)
project = knxproj.parse()
```

## Data Structure

```python
project = {
    "devices": dict[str, Device],              # All devices
    "communication_objects": dict[str, CommunicationObject],  # All communication objects
    "group_addresses": dict[str, GroupAddress], # All group addresses
    "info": ProjectInfo,                       # Project metadata
    # ... other fields
}
```

## Key Relationships

### Device → Communication Objects → Group Addresses

```python
# 1. Get device
device = project["devices"]["device_id"]
device_address = device["individual_address"]  # e.g., "1.1.5"

# 2. Get communication objects for device
for com_obj_id in device["communication_object_ids"]:
    com_obj = project["communication_objects"][com_obj_id]
    
    # 3. Verify ownership
    assert com_obj["device_address"] == device_address
    
    # 4. Get group addresses
    for ga_address in com_obj["group_address_links"]:
        ga = project["group_addresses"][ga_address]
        # Use group address information
```

## Common Queries

### Get all group addresses for a device
```python
def get_device_gas(project, device_id):
    device = project["devices"][device_id]
    gas = []
    for com_obj_id in device["communication_object_ids"]:
        com_obj = project["communication_objects"][com_obj_id]
        if com_obj["device_address"] == device["individual_address"]:
            gas.extend(com_obj["group_address_links"])
    return list(set(gas))  # Remove duplicates
```

### Get all devices using a group address
```python
def get_devices_for_ga(project, ga_address):
    ga = project["group_addresses"][ga_address]
    devices = set()
    for com_obj_id in ga["communication_object_ids"]:
        com_obj = project["communication_objects"][com_obj_id]
        device_address = com_obj["device_address"]
        for device_id, device in project["devices"].items():
            if device["individual_address"] == device_address:
                devices.add(device_id)
    return list(devices)
```

### Get ETS6-style table for device
```python
def get_device_table(project, device_id):
    device = project["devices"][device_id]
    rows = []
    for com_obj_id in device["communication_object_ids"]:
        com_obj = project["communication_objects"][com_obj_id]
        if com_obj["device_address"] != device["individual_address"]:
            continue
        rows.append({
            "number": com_obj["number"],
            "name": com_obj["name"],
            "function": com_obj["function_text"],
            "group_addresses": ", ".join(com_obj["group_address_links"]),
            "length": com_obj["object_size"],
            "flags": " ".join([
                "C" if com_obj["flags"]["communication"] else "",
                "R" if com_obj["flags"]["read"] else "",
                "W" if com_obj["flags"]["write"] else "",
            ]).strip() or "-"
        })
    return sorted(rows, key=lambda x: x["number"])
```

## Field Reference

### Device
- `individual_address`: str (e.g., "1.1.5")
- `name`: str
- `hardware_name`: str
- `communication_object_ids`: list[str]

### CommunicationObject
- `device_address`: str (links to device)
- `number`: int
- `name`: str
- `function_text`: str
- `group_address_links`: list[str] (e.g., ["6/0/1"])
- `object_size`: str (e.g., "1 bit")
- `flags`: Flags dict

### GroupAddress
- `address`: str (e.g., "6/0/1")
- `name`: str
- `dpt`: DPTType | None
- `communication_object_ids`: list[str]

## Important Notes

1. **Always verify**: `com_obj["device_address"] == device["individual_address"]`
2. **Communication object ID format**: `"{device_address}/{ref_id}"` (e.g., "1.1.5/O-40_R-1433")
3. **Group addresses are keyed by address string**: `project["group_addresses"]["6/0/1"]`
4. **One communication object can have multiple group addresses**: `group_address_links: ["6/0/1", "6/0/2"]`
5. **Some communication objects may have no group addresses**: `group_address_links: []`

## Error Handling
```python
from xknxproject.exceptions import XKNXProjectException

try:
    project = XKNXProj(path="file.knxproj").parse()
except XKNXProjectException as e:
    # Handle parsing error
    pass
```

