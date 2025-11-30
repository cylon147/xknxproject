"""Utilities for aggregating logical devices with their group addresses."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import TypedDict

from xknxproject.models import CommunicationObject, Device, DPTType, GroupAddress, KNXProject


class CommunicationObjectLink(TypedDict):
    """A simplified representation of a communication object for export."""

    id: str
    name: str
    number: int
    text: str
    function_text: str
    description: str
    channel: str | None
    channel_name: str | None


class LogicalDeviceGroupAddress(TypedDict):
    """Group address paired with the communication objects on a logical device."""

    address: str
    name: str
    project_uid: int | None
    dpt: DPTType | None
    data_secure: bool
    description: str
    comment: str
    communication_objects: list[CommunicationObjectLink]


class LogicalDeviceSummary(TypedDict):
    """Logical device paired with all linked group addresses."""

    individual_address: str
    name: str
    hardware_name: str
    manufacturer_name: str
    order_number: str
    application: str | None
    group_addresses: list[LogicalDeviceGroupAddress]


def build_logical_device_view(project: KNXProject) -> list[LogicalDeviceSummary]:
    """Return a list of logical devices with their linked group addresses."""

    communication_objects = project["communication_objects"]
    group_addresses = project["group_addresses"]

    logical_devices: list[LogicalDeviceSummary] = []
    for individual_address, device in sorted(
        project["devices"].items(), key=lambda item: _individual_address_sort_key(item[0])
    ):
        grouped_addresses = _collect_group_addresses(
            device=device,
            communication_objects=communication_objects,
            group_addresses=group_addresses,
        )
        logical_devices.append(
            LogicalDeviceSummary(
                individual_address=individual_address,
                name=device["name"],
                hardware_name=device["hardware_name"],
                manufacturer_name=device["manufacturer_name"],
                order_number=device["order_number"],
                application=device["application"],
                group_addresses=grouped_addresses,
            )
        )

    return logical_devices


def export_logical_devices(input_path: Path, output_path: Path | None = None) -> Path:
    """Generate a logical device export JSON file from a KNX project JSON dump."""

    project: KNXProject = json.loads(input_path.read_text(encoding="utf-8"))
    payload = _build_payload(project)

    final_output = output_path or input_path.with_name(
        f"{input_path.stem}_logical_devices.json"
    )
    final_output.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return final_output


def export_logical_devices_from_knxproj(
    input_path: Path,
    output_path: Path | None = None,
    *,
    password: str | None = None,
    language: str | None = None,
) -> Path:
    """Generate a logical device export JSON file directly from a .knxproj archive."""

    from xknxproject.xknxproj import XKNXProj

    project = XKNXProj(path=input_path, password=password, language=language).parse()
    payload = _build_payload(project)

    final_output = output_path or input_path.with_name(
        f"{input_path.stem}_logical_devices.json"
    )
    final_output.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return final_output


def _collect_group_addresses(
    *,
    device: Device,
    communication_objects: dict[str, CommunicationObject],
    group_addresses: dict[str, GroupAddress],
) -> list[LogicalDeviceGroupAddress]:
    device_comm_object_ids = _gather_comm_object_ids(device)
    grouped_addresses: dict[str, LogicalDeviceGroupAddress] = {}
    processed_links: set[tuple[str, str]] = set()

    for comm_object_id in device_comm_object_ids:
        if (comm_object := communication_objects.get(comm_object_id)) is None:
            continue

        channel_name = _channel_name(device, comm_object.get("channel"))
        for group_address in comm_object["group_address_links"]:
            if (group_address, comm_object_id) in processed_links:
                continue
            processed_links.add((group_address, comm_object_id))

            group_entry = grouped_addresses.setdefault(
                group_address,
                _build_group_address_entry(
                    group_address=group_address,
                    group_address_data=group_addresses.get(group_address),
                ),
            )
            group_entry["communication_objects"].append(
                _summarize_comm_object(
                    comm_object_id=comm_object_id,
                    comm_object=comm_object,
                    channel_name=channel_name,
                )
            )

    sorted_groups = _sort_group_addresses(grouped_addresses, group_addresses)
    for group in sorted_groups:
        group["communication_objects"].sort(key=lambda co: (co["number"], co["id"]))
    return sorted_groups


def _build_payload(project: KNXProject) -> dict:
    logical_devices = build_logical_device_view(project)
    return {
        "project": project.get("info", {}),
        "devices": logical_devices,
    }


def _gather_comm_object_ids(device: Device) -> set[str]:
    comm_object_ids = set(device["communication_object_ids"])
    for channel in device["channels"].values():
        comm_object_ids.update(channel["communication_object_ids"])
    return comm_object_ids


def _channel_name(device: Device, channel_id: str | None) -> str | None:
    if channel_id is None:
        return None
    if channel := device["channels"].get(channel_id):
        return channel["name"]
    return None


def _build_group_address_entry(
    *, group_address: str, group_address_data: GroupAddress | None
) -> LogicalDeviceGroupAddress:
    if group_address_data is not None:
        return LogicalDeviceGroupAddress(
            address=group_address_data["address"],
            name=group_address_data["name"],
            project_uid=group_address_data["project_uid"],
            dpt=group_address_data["dpt"],
            data_secure=group_address_data["data_secure"],
            description=group_address_data["description"],
            comment=group_address_data["comment"],
            communication_objects=[],
        )

    return LogicalDeviceGroupAddress(
        address=group_address,
        name="",
        project_uid=None,
        dpt=None,
        data_secure=False,
        description="",
        comment="",
        communication_objects=[],
    )


def _summarize_comm_object(
    *,
    comm_object_id: str,
    comm_object: CommunicationObject,
    channel_name: str | None,
) -> CommunicationObjectLink:
    return CommunicationObjectLink(
        id=comm_object_id,
        name=comm_object["name"],
        number=comm_object["number"],
        text=comm_object["text"],
        function_text=comm_object["function_text"],
        description=comm_object["description"],
        channel=comm_object.get("channel"),
        channel_name=channel_name,
    )


def _sort_group_addresses(
    grouped_addresses: dict[str, LogicalDeviceGroupAddress],
    group_addresses: dict[str, GroupAddress],
) -> list[LogicalDeviceGroupAddress]:
    def sort_key(entry: LogicalDeviceGroupAddress) -> int | str:
        if (group_address := group_addresses.get(entry["address"])) is not None:
            return group_address["raw_address"]
        return entry["address"]

    return sorted(grouped_addresses.values(), key=sort_key)


def _individual_address_sort_key(individual_address: str) -> tuple[int, int, int]:
    try:
        return tuple(int(part) for part in individual_address.split("."))  # type: ignore[return-value]
    except ValueError:
        return (0, 0, 0)


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint to export logical devices with their group addresses."""

    parser = argparse.ArgumentParser(
        description=(
            "Create a JSON export grouping logical devices with their linked group addresses"
        )
    )
    parser.add_argument(
        "input",
        type=Path,
        help="Path to the KNX project JSON file (exported by xknxproject)",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Optional output path. Defaults to <input>_logical_devices.json",
    )
    args = parser.parse_args(argv)

    output_path = export_logical_devices(args.input, args.output)
    print(f"Logical device export written to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
