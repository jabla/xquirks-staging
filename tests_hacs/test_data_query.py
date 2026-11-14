"""The Tuya data query after ZHA loaded a file the change list installed or updated.

A Tuya device sends its datapoints by itself only when it joins: the settings of a quirk installed
later stay unknown until the device is asked. Each device that runs the file, is not left out and
that ZHA reports available gets one query.
"""

from __future__ import annotations

import logging
import subprocess
import sys
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.util import dt as dt_util
from homeassistant.util.async_ import run_callback_threadsafe
from pytest_homeassistant.common import async_fire_time_changed
from zigpy.exceptions import DeliveryError

from . import integration
from .conftest import NO_QUIRK, REPOS, TuyaCluster, Zha, apply_list, continue_fix, issue_of, listed, manager_of, setup_entry, start_fix, write_repo
from .integration import PACKAGE, ROOT, const, diagnostics
from .test_content import restart_with

IEEE_A = "00:11:22:33:44:55:66:01"
IEEE_B = "00:11:22:33:44:55:66:02"
NOTHING = {"remove": [], "update": [], "install": []}
FROZEN = Path(__file__).resolve().parent / "fixtures"
# What one data query is: the command without payload, no reply awaited.
QUERY = (const.TUYA_QUERY_DATA, (), {"expect_reply": False})
TUYA_A = "z2m_tuya_a:TuyaA"


async def settle(hass: HomeAssistant) -> None:
    """The refresh after the cooldown has run, the queries it sent too."""
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=const.REFRESH_COOLDOWN + 1))
    await hass.async_block_till_done(wait_background_tasks=True)


def tuya_device(zha: Zha, ieee: str = IEEE_A, name: str = "Radar", **cluster) -> TuyaCluster:
    """A device z2m_tuya_a.py is for, with a Tuya MCU cluster: the cluster."""
    zha.tuya[ieee] = TuyaCluster(**cluster)
    zha.add_device(ieee, "_TZE200_aaaa", "TS0601", name)
    return zha.tuya[ieee]


def queries(hass: HomeAssistant) -> dict[str, list[str]]:
    """The data queries as the diagnostics list them: file -> what became of each device."""
    return {name: record["devices"] for name, record in manager_of(hass).summary()["tuya_data_queries"].items()}


async def test_the_device_is_asked_once_zha_loaded_its_new_file(hass: HomeAssistant, zha: Zha, repo_dir: Path):
    cluster = tuya_device(zha)
    entry = await setup_entry(hass, repo_dir)
    await apply_list(hass)
    # ZHA has not loaded the file yet: its quirk is not applied, nothing is asked.
    await settle(hass)
    assert cluster.sent == []
    zha.reload({IEEE_A: TUYA_A})
    await settle(hass)
    assert cluster.sent == [QUERY]
    result = await diagnostics.async_get_config_entry_diagnostics(hass, entry)
    assert [record["devices"] for record in result["tuya_data_queries"].values()] == [["_TZE200_aaaa TS0601: sent"]]
    assert list(result["tuya_data_queries"]) == ["z2m_tuya_a.py"] and "Radar" not in str(result["tuya_data_queries"])
    # Once: neither a refresh nor the next reload of ZHA asks again.
    await entry.runtime_data.async_refresh()
    zha.reload()
    await settle(hass)
    assert cluster.sent == [QUERY]


async def test_an_update_asks_again_a_removal_does_not(hass: HomeAssistant, zha: Zha, repo_dir: Path):
    cluster = tuya_device(zha)
    entry = await setup_entry(hass, repo_dir)
    await apply_list(hass)
    zha.reload({IEEE_A: TUYA_A})
    await settle(hass)
    write_repo(repo_dir, version=2)
    REPOS[repo_dir].publish()
    await entry.runtime_data.async_check()
    assert listed(hass) == {**NOTHING, "update": ["z2m_tuya_a.py"]}
    await apply_list(hass)
    zha.reload()
    await settle(hass)
    assert cluster.sent == [QUERY, QUERY]
    # Left out, the device loses the file: nothing is asked after that reload.
    hass.config_entries.async_update_entry(entry, options={const.CONF_EXCLUDED: [next(iter(entry.runtime_data.devices))]})
    await hass.async_block_till_done(wait_background_tasks=True)
    assert listed(hass) == {**NOTHING, "remove": ["z2m_tuya_a.py"]}
    await apply_list(hass)
    zha.reload({IEEE_A: NO_QUIRK})
    await settle(hass)
    assert cluster.sent == [QUERY, QUERY]


async def test_a_file_for_another_kind_of_device_asks_nothing(hass: HomeAssistant, zha: Zha, repo_dir: Path):
    """Only a file the manifest marks as Tuya ("path": "tuya") brings a query, even to a device with a
    Tuya cluster."""
    zha.tuya[IEEE_B] = cluster = TuyaCluster()
    zha.add_device(IEEE_B, "Anyone", "B-1")
    await setup_entry(hass, repo_dir)
    assert listed(hass) == {**NOTHING, "install": ["z2m_acme_b.py"]}
    await apply_list(hass)
    zha.reload({IEEE_B: "z2m_acme_b:AcmeB"})
    await settle(hass)
    assert cluster.sent == [] and queries(hass) == {}


@pytest.mark.parametrize("how", ["disabled", "excluded"])
async def test_a_left_out_device_is_not_asked(hass: HomeAssistant, zha: Zha, repo_dir: Path, how: str):
    """ZHA applies the file to a left-out device as well (another device needs it): only the other one is asked."""
    left_out_cluster = tuya_device(zha, IEEE_A, "Left out")
    other_cluster = tuya_device(zha, IEEE_B, "Other")
    left_out = next(device.id for device in dr.async_entries_for_config_entry(dr.async_get(hass), zha.entry.entry_id) if device.name == "Left out")
    if how == "disabled":
        dr.async_get(hass).async_update_device(left_out, disabled_by=dr.DeviceEntryDisabler.USER)
    await setup_entry(hass, repo_dir, {const.CONF_EXCLUDED: [left_out]} if how == "excluded" else None)
    await apply_list(hass)
    zha.reload({IEEE_A: TUYA_A, IEEE_B: TUYA_A})
    await settle(hass)
    assert left_out_cluster.sent == [] and other_cluster.sent == [QUERY]
    assert queries(hass) == {"z2m_tuya_a.py": ["_TZE200_aaaa TS0601: sent"]}


async def test_a_device_on_another_quirk_is_not_asked(hass: HomeAssistant, zha: Zha, repo_dir: Path):
    cluster = tuya_device(zha)
    await setup_entry(hass, repo_dir)
    await apply_list(hass)
    # ZHA applies a quirk it ships, not the file.
    zha.reload({IEEE_A: "zhaquirks.tuya.ts0601_radar:TuyaRadar"})
    await settle(hass)
    assert cluster.sent == [] and queries(hass) == {}


async def test_an_unavailable_device_is_not_asked(hass: HomeAssistant, zha: Zha, repo_dir: Path):
    cluster = tuya_device(zha)
    zha.unavailable.add(IEEE_A)
    await setup_entry(hass, repo_dir)
    await apply_list(hass)
    zha.reload({IEEE_A: TUYA_A})
    await settle(hass)
    assert cluster.sent == []
    assert queries(hass) == {"z2m_tuya_a.py": ["_TZE200_aaaa TS0601: skipped, ZHA reports it unavailable"]}


async def test_a_quirk_without_the_query_is_not_asked(hass: HomeAssistant, zha: Zha, repo_dir: Path):
    """A Tuya cluster that defines no data query (not one of zhaquirks' Tuya MCU clusters) gets no command."""
    cluster = tuya_device(zha, commands={})
    await setup_entry(hass, repo_dir)
    await apply_list(hass)
    zha.reload({IEEE_A: TUYA_A})
    await settle(hass)
    assert cluster.sent == []
    assert queries(hass) == {"z2m_tuya_a.py": ["_TZE200_aaaa TS0601: skipped, its quirk has no Tuya data query"]}


async def test_a_query_that_fails_is_not_repeated_and_logs_no_warning(hass: HomeAssistant, zha: Zha, repo_dir: Path, caplog: pytest.LogCaptureFixture):
    """A sleepy battery device may miss the query: best effort, no retry of ours, nothing above debug."""
    failing = tuya_device(zha, IEEE_A, error=DeliveryError("MAC transaction expired"))
    answering = tuya_device(zha, IEEE_B, "Plug")
    entry = await setup_entry(hass, repo_dir)
    await apply_list(hass)
    caplog.clear()
    with caplog.at_level(logging.DEBUG):
        zha.reload({IEEE_A: TUYA_A, IEEE_B: TUYA_A})
        await settle(hass)
    # The next device is asked all the same.
    assert failing.sent == [QUERY] and answering.sent == [QUERY]
    assert sorted(queries(hass)["z2m_tuya_a.py"]) == ["_TZE200_aaaa TS0601: not delivered (MAC transaction expired)", "_TZE200_aaaa TS0601: sent"]
    ours = [record for record in caplog.records if record.name.startswith(PACKAGE)]
    assert any("not delivered" in record.getMessage() for record in ours)
    assert all(record.levelno <= logging.DEBUG for record in ours), [record.getMessage() for record in ours if record.levelno > logging.DEBUG]
    await entry.runtime_data.async_refresh()
    zha.reload()
    await settle(hass)
    assert failing.sent == [QUERY]


async def test_a_file_loaded_at_the_start_of_home_assistant_is_asked_for(hass: HomeAssistant, zha: Zha, repo_dir: Path):
    """ZHA was not reloaded after the change (the user restarted Home Assistant instead): ZHA loaded the
    file at the start, its devices are asked then."""
    cluster = tuya_device(zha)
    entry = await setup_entry(hass, repo_dir)
    await apply_list(hass)
    assert entry.runtime_data.summary()["pending_zha_reload"] == ["z2m_tuya_a.py: installed"]
    # Home Assistant restarts before the reload: ZHA loads the folder at its start.
    zha.apply_quirks({IEEE_A: TUYA_A})
    await restart_with(hass, entry, repo_dir)
    await settle(hass)
    assert entry.runtime_data.summary()["pending_zha_reload"] == []
    assert cluster.sent == [QUERY]


async def test_a_file_written_while_zha_sets_up_is_asked_for_after_the_next_load(hass: HomeAssistant, zha: Zha, repo_dir: Path):
    """The query follows the load of ZHA that has the change: not one whose setup started before the write."""
    cluster = tuya_device(zha)
    entry = await setup_entry(hass, repo_dir)
    flow = await start_fix(hass, issue_of(hass, "changes"))
    write_new = integration.files.write_new

    def setup_then_write(path, data):
        # A reload of ZHA started elsewhere: its setup loaded the folder before the file is there.
        run_callback_threadsafe(hass.loop, zha.start_reload).result()
        run_callback_threadsafe(hass.loop, zha.begin_setup).result()
        return write_new(path, data)

    with patch.object(integration.files, "write_new", setup_then_write):
        flow = await continue_fix(hass, flow, {"next_step_id": "apply"})
    assert flow["reason"] == "done_zha_not_loaded", flow
    # That setup ends (the stand-in reports the quirk all the same).
    zha.apply_quirks({IEEE_A: TUYA_A})
    zha.finish_reload()
    await settle(hass)
    assert entry.runtime_data.summary()["pending_zha_reload"] == ["z2m_tuya_a.py: installed"]
    assert cluster.sent == []
    zha.reload()
    await settle(hass)
    assert cluster.sent == [QUERY]


def test_the_query_reaches_the_tuya_cluster_of_a_real_quirk(tmp_path: Path):
    """No stand-in: a frozen Tuya file applied to a zigpy device as ZHA applies it. query_cluster finds
    the quirk's Tuya MCU cluster on endpoint 1, the query is the ZCL command 0x03 without payload to
    cluster 0xEF00, with no reply awaited. A device without the quirk has no such cluster."""
    script = f"""
import asyncio, pathlib, sys, warnings
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
warnings.simplefilter("ignore")
sys.path.insert(0, {str(ROOT)!r})
import zhaquirks
import zigpy.device, zigpy.types as t
from zha.quirks import DEVICE_REGISTRY

folder = pathlib.Path(sys.argv[1])
zhaquirks.setup(str(folder))
# Imported once the quirks are: Home Assistant imported first breaks the schemas of a radio library.
from {PACKAGE} import const, manager

def joined():
    device = zigpy.device.Device(MagicMock(), t.EUI64.convert("00:11:22:33:44:55:66:77"), 0x1234)
    endpoint = device.add_endpoint(1)
    endpoint.profile_id, endpoint.device_type = 260, 0x0051
    for cluster_id in (0x0000, 0x0004, 0x0005, 0xEF00):
        endpoint.add_input_cluster(cluster_id)
    for cluster_id in (0x000A, 0x0019):
        endpoint.add_output_cluster(cluster_id)
    device.manufacturer, device.model = "_TZE284_2fnssffc", "TS0601"
    return device

print("raw", manager.query_cluster(SimpleNamespace(device=joined())))
quirked = DEVICE_REGISTRY.resolve(joined())
cluster = manager.query_cluster(SimpleNamespace(device=quirked))
print("found", cluster is quirked.endpoints[1].in_clusters[0xEF00], type(cluster).__mro__[1].__name__)
quirked.request = AsyncMock()
asyncio.run(cluster.command(const.TUYA_QUERY_DATA, expect_reply=False))
call = quirked.request.call_args.kwargs
print("sent", hex(call["cluster"]), call["dst_ep"], call["data"][:1].hex(), call["data"][2:].hex(), call["expect_reply"])
"""
    (tmp_path / "custom").mkdir()
    (tmp_path / "custom" / "z2m_moes_zm6lt1.py").write_bytes((FROZEN / "z2m_moes_zm6lt1.py.txt").read_bytes())
    out = subprocess.run([sys.executable, "-I", "-c", script, str(tmp_path / "custom")], capture_output=True, text=True, timeout=300, check=False)
    # Frame control 0x01: a cluster command from client to server; after the sequence number only the command.
    assert out.stdout.strip().splitlines()[-3:] == ["raw None", "found True TuyaMCUCluster", "sent 0xef00 1 01 03 False"], out.stdout[-500:] + out.stderr[-2000:]


def test_zha_initialized_its_devices_when_its_entry_is_loaded():
    """The query goes out when the integration sees ZHA's entry loaded: by then ZHA's setup has
    applied the quirks and set up the devices and their entities. Availability is a property of
    ZHA's device."""
    import inspect

    from homeassistant.components import zha
    from zha.zigbee.device import Device

    setup = inspect.getsource(zha.async_setup_entry)
    assert setup.index("await zha_gateway.async_initialize()") < setup.index("await ha_zha_data.gateway_proxy.async_initialize_devices_and_entities()")
    assert setup.index("async_initialize_devices_and_entities()") < setup.index("await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)")
    assert isinstance(inspect.getattr_static(Device, "available"), property)
