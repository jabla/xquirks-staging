"""A device whose endpoints do not fit a file: no install for it, a notice with a report link."""

from __future__ import annotations

import json
from datetime import timedelta
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.util import dt as dt_util
from pytest_homeassistant.common import async_fire_time_changed

from .conftest import MANIFEST, Zha, issue_of, issues_of, manager_of, offered, setup_entry, write_repo
from .integration import const, manager

IEEE = "00:11:22:33:44:55:66:21"
# acme_c puts its manufacturer cluster on endpoint 1.
ENDPOINTS = {"1": [0xFC00]}


def signature(*endpoints: tuple[int, list[int]]) -> dict:
    """zigpy's original signature with these endpoints and input clusters."""
    return {"endpoints": {ep: {"profile_id": 260, "device_type": 81, "input_clusters": clusters, "output_clusters": [0x0019]} for ep, clusters in endpoints}}


def manifest() -> dict:
    return {**MANIFEST, "acme_c": {**MANIFEST["acme_c"], "endpoints": ENDPOINTS}}


async def test_a_device_that_does_not_fit_gets_a_report_link(hass: HomeAssistant, zha: Zha, repo_dir: Path):
    write_repo(repo_dir, manifest())
    zha.signatures[IEEE] = signature((1, [0x0000]), (2, [0x0000, 0xFC00]))
    zha.add_device(IEEE, "Acme", "C-1", name="Hallway sensor")
    await setup_entry(hass, repo_dir, publish=True)
    assert offered(hass) == []
    issue = issue_of(hass, "misfit")
    placeholders = issue.translation_placeholders
    assert placeholders["file"] == "z2m_acme_c.py"
    assert "Hallway sensor (Acme C-1): the first endpoint with cluster 0xFC00 is 2, not 1." in placeholders["devices"]
    link = placeholders["devices"].split("[Report this device](", 1)[1].rstrip(")")
    parts = urlsplit(link)
    assert f"{parts.scheme}://{parts.netloc}{parts.path}" == f"https://github.com/{const.REPOSITORY}/issues/new"
    query = {key: values[0] for key, values in parse_qs(parts.query).items()}
    assert query["template"] == "device-layout.yml"
    assert '"model":"C-1"' in query["signature"] and '"0xfc00"' in query["signature"]
    assert not any("Hallway" in value for value in query.values())
    # Diagnostics name the device by manufacturer and model only.
    summary = manager_of(hass).summary()
    assert summary["devices_that_do_not_fit"] == {"z2m_acme_c.py": ["Acme C-1: the first endpoint with cluster 0xFC00 is 2, not 1"]}


async def test_a_device_that_fits_gets_the_file(hass: HomeAssistant, zha: Zha, repo_dir: Path):
    write_repo(repo_dir, manifest())
    zha.signatures[IEEE] = signature((1, [0x0000, 0xFC00]))
    zha.add_device(IEEE, "Acme", "C-1")
    await setup_entry(hass, repo_dir, publish=True)
    assert offered(hass) == ["z2m_acme_c.py"]
    assert issues_of(hass, "misfit") == []


async def test_a_device_without_a_readable_signature_counts_as_fitting(hass: HomeAssistant, zha: Zha, repo_dir: Path):
    write_repo(repo_dir, manifest())
    zha.signatures[IEEE] = {"endpoints": {1: {"profile_id": "x"}}}
    zha.add_device(IEEE, "Acme", "C-1")
    await setup_entry(hass, repo_dir, publish=True)
    assert offered(hass) == ["z2m_acme_c.py"]
    assert manager._signature(type("D", (), {"device": type("Z", (), {"original_signature": None})()})()) is None


async def test_an_endpoint_without_a_known_profile_keeps_the_layout(hass: HomeAssistant, zha: Zha, repo_dir: Path):
    """zigpy keeps profile_id or device_type None for an endpoint whose descriptor never came: the fit
    reads only endpoints and input clusters, so the device still gets the notice, not the file."""
    write_repo(repo_dir, manifest())
    zha.signatures[IEEE] = {"endpoints": {1: {"profile_id": None, "device_type": None, "input_clusters": [0x0000], "output_clusters": []},
                                          2: {"profile_id": 260, "device_type": 81, "input_clusters": [0xFC00], "output_clusters": []}}}
    zha.add_device(IEEE, "Acme", "C-1")
    await setup_entry(hass, repo_dir, publish=True)
    assert offered(hass) == []
    devices = issue_of(hass, "misfit").translation_placeholders["devices"]
    query = {key: values[0] for key, values in parse_qs(urlsplit(devices.split("[Report this device](", 1)[1].rstrip(")")).query).items()}
    assert '"1":{"profile_id":null,"device_type":null,"input_clusters":["0x0000"]' in query["signature"]
    # The report keeps the endpoint with its profile null, as the weekly search takes it.
    reported = json.loads(query["signature"])
    assert (reported["manufacturer"], reported["model"]) == ("Acme", "C-1")
    assert reported["endpoints"]["1"] == {"profile_id": None, "device_type": None, "input_clusters": ["0x0000"], "output_clusters": []}
    assert reported["endpoints"]["2"]["profile_id"] == "0x0104"


async def test_new_firmware_reads_the_layout_again(hass: HomeAssistant, zha: Zha, repo_dir: Path):
    """After a firmware update ZHA may know other endpoints of the device: the registry's sw_version
    changes, the change list is made again with the layout ZHA reports now."""
    write_repo(repo_dir, manifest())
    zha.signatures[IEEE] = signature((1, [0x0000]), (2, [0xFC00]))
    device_id = zha.add_device(IEEE, "Acme", "C-1")
    await setup_entry(hass, repo_dir, publish=True)
    assert offered(hass) == [] and issues_of(hass, "misfit")
    zha.signatures[IEEE] = signature((1, [0x0000, 0xFC00]))
    zha.apply_quirks({})
    dr.async_get(hass).async_update_device(device_id, sw_version="2.0")
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=const.REFRESH_COOLDOWN + 1))
    await hass.async_block_till_done(wait_background_tasks=True)
    assert offered(hass) == ["z2m_acme_c.py"] and issues_of(hass, "misfit") == []
