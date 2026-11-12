"""The report link of a device a file does not fit: what it carries, how the form renders it (the
weekly search reads the signature's json block)."""

from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import yaml

from . import integration

text = integration.text
Device = integration.plan.Device

SIGNATURE = {
    3: {"profile_id": 260, "device_type": 257, "input_clusters": [0x0000, 0x0006, 0x0008, 0x0301], "output_clusters": [0x0019]},
    37: {"profile_id": 260, "device_type": 2080, "input_clusters": [0x0000, 0x0406, 0xFF19], "output_clusters": []},
    242: {"profile_id": 0xA1E0, "device_type": 97, "input_clusters": [], "output_clusters": [0x0021]},
}
DEVICE = Device("Schneider Electric", "NHMOTION/UNIDIM/1", "Upstairs hallway", "", False, ((3, frozenset({0x0301})), (37, frozenset({0x0406}))))
ENTRY = {"revision": "f5ce7e94"}
FORM = integration.ROOT / ".github" / "ISSUE_TEMPLATE" / text.REPORT_FORM


def report(device: Device = DEVICE, signature: dict = SIGNATURE) -> tuple[str, dict[str, str]]:
    url = text.report_url(ENTRY, "z2m_schneider_electric_nhmotion_unidim_1.py", device, signature, "it has no endpoint 1", "2026.11.1")
    parts = urlsplit(url)
    return f"{parts.scheme}://{parts.netloc}{parts.path}", {key: values[0] for key, values in parse_qs(parts.query).items()}


def rendered(fields: dict[str, str]) -> str:
    """The issue text GitHub builds from the form: a heading per field, a json block for the signature."""
    form = yaml.safe_load(FORM.read_text())
    parts = []
    for field in form["body"]:
        if field["type"] == "markdown":
            continue
        value = fields.get(field["id"], "")
        if field["attributes"].get("render"):
            value = f"```{field['attributes']['render']}\n{value}\n```"
        parts.append(f"### {field['attributes']['label']}\n\n{value}")
    return "\n\n".join(parts)


def test_the_link_opens_the_device_layout_form_in_this_repository():
    base, fields = report()
    assert base == f"https://github.com/{integration.const.REPOSITORY}/issues/new"
    assert fields["template"] == text.REPORT_FORM and FORM.is_file()
    assert fields["title"] == "Device layout: Schneider Electric NHMOTION/UNIDIM/1"
    assert fields["file"] == "z2m_schneider_electric_nhmotion_unidim_1.py (revision f5ce7e94)"
    assert fields["reason"] == "it has no endpoint 1" and fields["ha"] == "2026.11.1"


def test_every_field_of_the_link_is_a_field_of_the_form():
    _base, fields = report()
    ids = {field["id"] for field in yaml.safe_load(FORM.read_text())["body"] if "id" in field}
    assert set(fields) - {"template", "title"} <= ids


def test_the_report_names_nothing_of_the_home():
    _base, fields = report()
    assert not any("Upstairs" in value or "hallway" in value for value in fields.values())


def test_the_form_renders_the_signature_as_a_json_block():
    """The issue text holds the link's signature as one json block: the weekly search reads the
    device's endpoints and clusters from it."""
    _base, fields = report()
    assert f"```json\n{fields['signature']}\n```" in rendered(fields)
    signature = json.loads(fields["signature"])
    assert (signature["manufacturer"], signature["model"], signature["class"]) == ("Schneider Electric", "NHMOTION/UNIDIM/1", "zigpy.device.Device")
    assert signature["endpoints"] == {
        "3": {"profile_id": "0x0104", "device_type": "0x0101", "input_clusters": ["0x0000", "0x0006", "0x0008", "0x0301"], "output_clusters": ["0x0019"]},
        "37": {"profile_id": "0x0104", "device_type": "0x0820", "input_clusters": ["0x0000", "0x0406", "0xff19"], "output_clusters": []},
        "242": {"profile_id": "0xa1e0", "device_type": "0x0061", "input_clusters": [], "output_clusters": ["0x0021"]},
    }


def test_a_large_device_leaves_out_its_output_clusters_then_its_signature():
    big = {ep: {"profile_id": 260, "device_type": 81, "input_clusters": list(range(0x0000, 0x001E)), "output_clusters": list(range(0x0100, 0x011E))}
           for ep in range(1, 7)}
    url, fields = report(signature=big)
    assert len(text.report_url(ENTRY, "z2m_x.py", DEVICE, big, "why", "2026.11.1")) <= text.REPORT_LIMIT
    assert '"output_clusters":[]' in fields["signature"]
    # Every endpoint keeps its input clusters: what the fit needs.
    endpoints = json.loads(fields["signature"])["endpoints"]
    assert {ep: item["input_clusters"] for ep, item in endpoints.items()} == {str(ep): [f"0x{c:04x}" for c in range(0x0000, 0x001E)] for ep in range(1, 7)}
    huge = {ep: {"profile_id": 260, "device_type": 81, "input_clusters": list(range(0x0000, 0x0080)), "output_clusters": []} for ep in range(1, 41)}
    url = text.report_url(ENTRY, "z2m_x.py", DEVICE, huge, "why", "2026.11.1")
    assert len(url) <= text.REPORT_LIMIT
    assert {key: values[0] for key, values in parse_qs(urlsplit(url).query).items()}["signature"] == text.REPORT_TOO_LONG


def test_the_misfit_list_links_each_device_and_escapes_names():
    misfit = integration.plan.Misfit("z2m_x.py", (("d1", "it has no endpoint 1"),))
    devices = {"d1": Device("Acme", "X-1", "Kitchen *lamp*", "", False, None)}
    listed = text.misfit_list(misfit, devices, {"d1": "https://github.com/x/y/issues/new?title=a"})
    assert listed == "- Kitchen \\*lamp\\* (Acme X-1): it has no endpoint 1. [Report this device](https://github.com/x/y/issues/new?title=a)"
    assert text.misfit_list(misfit, devices, {}) == "- Kitchen \\*lamp\\* (Acme X-1): it has no endpoint 1."


def test_the_link_stays_one_markdown_link():
    url = text.report_url(ENTRY, "z2m_x.py", Device("A (b)", "M) [x]", "n", "", False, None), SIGNATURE, "why", "2026.11.1")
    assert not set(url) & set("()[] \n"), url


def test_the_form_file_is_where_the_link_points():
    assert Path(FORM).name == text.REPORT_FORM
