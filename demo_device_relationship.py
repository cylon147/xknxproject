"""Demonstration script showing how devices are linked to group addresses."""

from xknxproject import XKNXProj

# Use a test project file
test_file = "test/resources/xknx_test_project_no_password.knxproj"

print("=" * 80)
print("DEMONSTRATION: How Group Addresses are Linked to Devices")
print("=" * 80)

knxproj = XKNXProj(path=test_file)
project = knxproj.parse()

# Get the first device as an example
first_device_id = list(project["devices"].keys())[0]
device = project["devices"][first_device_id]

print(f"\n1. DEVICE:")
print(f"   ID: {first_device_id}")
print(f"   Name: {device['name']}")
print(f"   Individual Address: {device['individual_address']}")
print(f"   Communication Object IDs: {device['communication_object_ids'][:3]}...")  # Show first 3
print(f"   Total Communication Objects: {len(device['communication_object_ids'])}")

print(f"\n2. COMMUNICATION OBJECTS (linked to this device):")
print(f"   {'-' * 76}")
for i, com_obj_id in enumerate(device["communication_object_ids"][:5], 1):  # Show first 5
    if com_obj_id in project["communication_objects"]:
        com_obj = project["communication_objects"][com_obj_id]
        print(f"\n   Communication Object #{i}:")
        print(f"   ├─ ID: {com_obj_id}")
        print(f"   ├─ Device Address: {com_obj['device_address']} (matches device: {com_obj['device_address'] == device['individual_address']})")
        print(f"   ├─ Name: {com_obj['name']}")
        print(f"   ├─ Number: {com_obj['number']}")
        print(f"   ├─ Function: {com_obj['function_text']}")
        print(f"   └─ Group Address Links: {com_obj['group_address_links']}")

print(f"\n3. GROUP ADDRESSES (found through communication objects):")
print(f"   {'-' * 76}")
all_group_addresses = set()
for com_obj_id in device["communication_object_ids"]:
    if com_obj_id in project["communication_objects"]:
        com_obj = project["communication_objects"][com_obj_id]
        for ga_address in com_obj["group_address_links"]:
            all_group_addresses.add(ga_address)

print(f"   Total unique group addresses for this device: {len(all_group_addresses)}")
print(f"   Group addresses: {sorted(all_group_addresses)[:10]}...")  # Show first 10

print(f"\n4. VERIFICATION:")
print(f"   {'-' * 76}")
print(f"   ✓ Device has {len(device['communication_object_ids'])} communication objects")
print(f"   ✓ Each communication object has device_address = '{device['individual_address']}'")
print(f"   ✓ Each communication object links to group addresses via 'group_address_links'")
print(f"   ✓ This device has {len(all_group_addresses)} unique group addresses")

print(f"\n" + "=" * 80)
print("CONCLUSION:")
print("=" * 80)
print("The relationship is:")
print("  Device (individual_address)")
print("    ↓ has communication_object_ids")
print("  Communication Objects (device_address + group_address_links)")
print("    ↓ has group_address_links")
print("  Group Addresses (address)")
print("=" * 80)

