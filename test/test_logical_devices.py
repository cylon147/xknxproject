"""Tests for logical device exports."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from test import STUBS_PATH
from xknxproject.logical_devices import build_logical_device_view, export_logical_devices


@pytest.fixture()
def stub_project() -> dict:
    return json.loads((STUBS_PATH / "xknx_test_project.json").read_text(encoding="utf-8"))


def test_build_logical_device_view_collects_group_addresses(stub_project: dict) -> None:
    logical_devices = build_logical_device_view(stub_project)

    device = next(
        entry
        for entry in logical_devices
        if entry["individual_address"] == "1.1.5"
    )
    assert device["name"] == stub_project["devices"]["1.1.5"]["name"]

    group_address = next(
        ga for ga in device["group_addresses"] if ga["address"] == "1/0/5"
    )
    assert group_address["name"] == stub_project["group_addresses"]["1/0/5"]["name"]
    assert group_address["dpt"] == {"main": 1, "sub": None}

    communication_object_names = {
        link["name"] for link in group_address["communication_objects"]
    }
    assert "Ausgang B" in communication_object_names


def test_export_logical_devices_writes_expected_file(
    stub_project: dict, tmp_path: Path
) -> None:
    input_path = tmp_path / "project.json"
    input_path.write_text(json.dumps(stub_project), encoding="utf-8")

    output_path = tmp_path / "logical_devices.json"
    written_path = export_logical_devices(input_path=input_path, output_path=output_path)

    assert written_path == output_path
    payload = json.loads(output_path.read_text(encoding="utf-8"))

    device = next(
        entry
        for entry in payload["devices"]
        if entry["individual_address"] == "1.1.7"
    )
    assert any(
        link["channel_name"]
        for group in device["group_addresses"]
        for link in group["communication_objects"]
    )
