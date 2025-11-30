# How Group Addresses are Linked to Devices in xknxproject

## The Relationship Chain

xknxproject uses a **two-way relationship** to link devices, communication objects, and group addresses:

### 1. Device Structure
```json
{
  "devices": {
    "device_id_123": {
      "individual_address": "1.1.5",
      "name": "D1-G1, Tunable Light 1",
      "communication_object_ids": [
        "1.1.5/O-40_R-1433",
        "1.1.5/O-41_R-1434",
        "1.1.5/O-70_R-1505"
      ]
    }
  }
}
```

### 2. Communication Object Structure
```json
{
  "communication_objects": {
    "1.1.5/O-40_R-1433": {
      "device_address": "1.1.5",  // ← Links back to device
      "name": "D1-G1, Switching, Tunable Light 1",
      "number": 40,
      "function_text": "ON/OFF",
      "group_address_links": ["6/0/1"],  // ← Links to group addresses
      "object_size": "1 bit",
      "flags": { "read": false, "write": true, "communication": true }
    },
    "1.1.5/O-41_R-1434": {
      "device_address": "1.1.5",  // ← Same device
      "name": "D1-G1, Dimming, Tunable Light 1",
      "number": 41,
      "function_text": "Dimming relative",
      "group_address_links": ["6/2/1"],  // ← Different group address
      "object_size": "4 bit"
    }
  }
}
```

### 3. Group Address Structure
```json
{
  "group_addresses": {
    "6/0/1": {
      "address": "6/0/1",
      "name": "Switch Tunable Light 1",
      "communication_object_ids": ["1.1.5/O-40_R-1433"]  // ← Links back to communication objects
    }
  }
}
```

## How We Find Group Addresses for a Device

### Method 1: Device → Communication Objects → Group Addresses (What we use)

1. **Start with Device**: Get device's `communication_object_ids`
   ```python
   device = project["devices"]["device_id_123"]
   com_obj_ids = device["communication_object_ids"]
   # Result: ["1.1.5/O-40_R-1433", "1.1.5/O-41_R-1434", ...]
   ```

2. **Get Communication Objects**: Look up each communication object
   ```python
   for com_obj_id in com_obj_ids:
       com_obj = project["communication_objects"][com_obj_id]
       # Verify it belongs to this device
       assert com_obj["device_address"] == device["individual_address"]
   ```

3. **Get Group Addresses**: Extract group addresses from each communication object
   ```python
   for com_obj_id in com_obj_ids:
       com_obj = project["communication_objects"][com_obj_id]
       group_addresses = com_obj["group_address_links"]
       # Result: ["6/0/1"], ["6/2/1"], etc.
   ```

### Method 2: Group Address → Communication Objects → Device (Reverse lookup)

You can also go backwards:
1. Start with a group address
2. Get its `communication_object_ids`
3. For each communication object, check its `device_address`
4. Find the device with matching `individual_address`

## Verification

The communication object ID format is: `{device_address}/{com_object_ref_id}`
- Example: `"1.1.5/O-40_R-1433"` means:
  - Device address: `"1.1.5"`
  - Communication object reference: `"O-40_R-1433"`

This ensures:
- ✅ Each communication object knows which device it belongs to (`device_address`)
- ✅ Each device knows which communication objects it has (`communication_object_ids`)
- ✅ Each communication object knows which group addresses it's linked to (`group_address_links`)

## Current Implementation

Our `app.py` correctly uses Method 1:
1. Iterates through each device
2. Gets the device's `communication_object_ids`
3. For each communication object ID, looks it up in `communication_objects`
4. Extracts `group_address_links` from each communication object
5. Displays all communication objects with their group addresses in a table

This matches the ETS6 format where each communication object is a row showing its associated group addresses.

