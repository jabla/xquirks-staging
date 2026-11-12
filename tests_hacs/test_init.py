"""Setup, refresh triggers, the devices the change list is made for and diagnostics."""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.util import dt as dt_util
from pytest_homeassistant.common import MockConfigEntry, async_fire_time_changed

from .integration import const, diagnostics

REFRESH_COOLDOWN = const.REFRESH_COOLDOWN

from .conftest import NO_QUIRK, REPOS, Zha, apply_list, continue_fix, issue_of, listed, offered, our_issues, quirk_revision, setup_entry, start_fix, write_repo

IEEE_A = "00:11:22:33:44:55:66:01"
IEEE_B = "00:11:22:33:44:55:66:02"
NOTHING = {"remove": [], "update": [], "install": []}
ALSO_LAMP_PLUG = "    - also applies to Lamp plug, which you left out: ZHA applies a file to every device it lists"


async def wait_for_refresh(hass: HomeAssistant) -> None:
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=REFRESH_COOLDOWN + 1))
    await hass.async_block_till_done(wait_background_tasks=True)


async def leave_out(hass: HomeAssistant, entry: MockConfigEntry, device_id: str, how: str, *, out: bool = True) -> None:
    """Leave the device out (out=False: take it back in): disabled in Home Assistant or excluded in the options."""
    if how == "disabled":
        dr.async_get(hass).async_update_device(device_id, disabled_by=dr.DeviceEntryDisabler.USER if out else None)
        await wait_for_refresh(hass)
    else:
        hass.config_entries.async_update_entry(entry, options={const.CONF_EXCLUDED: [device_id] if out else []})
        await hass.async_block_till_done(wait_background_tasks=True)


async def test_new_device_brings_a_list_after_the_cooldown(hass: HomeAssistant, zha: Zha, repo_dir: Path):
    await setup_entry(hass, repo_dir)
    assert our_issues(hass) == {}
    zha.add_device(IEEE_A, "_TZE200_aaaa", "TS0601")
    await hass.async_block_till_done(wait_background_tasks=True)
    assert our_issues(hass) == {}
    await wait_for_refresh(hass)
    assert issue_of(hass, "changes").translation_placeholders == {"count": "1"}
    assert offered(hass) == ["z2m_tuya_a.py"]


async def test_devices_of_other_integrations_do_not_count(hass: HomeAssistant, zha: Zha, repo_dir: Path):
    other = MockConfigEntry(domain="mqtt")
    other.add_to_hass(hass)
    dr.async_get(hass).async_get_or_create(config_entry_id=other.entry_id, identifiers={("mqtt", "x")}, manufacturer="_TZE200_aaaa", model="TS0601")
    await setup_entry(hass, repo_dir)
    assert our_issues(hass) == {}


async def test_service_device_says_what_the_integration_does(hass: HomeAssistant, zha: Zha, repo_dir: Path):
    entry = await setup_entry(hass, repo_dir)
    device = dr.async_get(hass).async_get_device_by_identifier((const.DOMAIN, entry.entry_id), entry.entry_id)
    assert device.entry_type is dr.DeviceEntryType.SERVICE
    assert device.model == "Extra quirks for ZHA"


async def test_zha_reload_refreshes_what_zha_applies(hass: HomeAssistant, zha: Zha, repo_dir: Path):
    zha.add_device(IEEE_A, "_TZE200_aaaa", "TS0601")
    entry = await setup_entry(hass, repo_dir)
    issue_of(hass, "changes")
    # ZHA (re)loads and applies a quirk it ships to the device: the list goes.
    zha.apply_quirks({IEEE_A: "zhaquirks.tuya.ts0601_radar:TuyaRadar"})
    async_dispatcher_send(hass, "config_entry_changed", "updated", zha.entry)
    await wait_for_refresh(hass)
    assert our_issues(hass) == {}
    assert entry.runtime_data.devices[next(iter(entry.runtime_data.devices))].quirk == "zhaquirks.tuya.ts0601_radar"


async def test_the_list_waits_for_zha_to_load_a_change(hass: HomeAssistant, zha: Zha, repo_dir: Path):
    """Until ZHA loaded the folder after a change, what it reports is older than the folder: no list
    comes before it did."""
    zha.add_device(IEEE_A, "_TZE200_aaaa", "TS0601")
    entry = await setup_entry(hass, repo_dir)
    await apply_list(hass)
    zha.add_device(IEEE_B, "Anyone", "B-1")
    await wait_for_refresh(hass)
    assert our_issues(hass) == {}
    assert entry.runtime_data.summary()["change_list"]["held"] == "pending"
    # ZHA loaded the folder: the list for the new device comes.
    zha.reload({IEEE_A: "z2m_tuya_a:TuyaA"})
    await wait_for_refresh(hass)
    assert listed(hass) == {**NOTHING, "install": ["z2m_acme_b.py"]}
    assert entry.runtime_data.summary()["change_list"]["held"] is None


async def test_a_withdrawn_revision_in_use_is_noticed_while_the_list_waits(hass: HomeAssistant, zha: Zha, repo_dir: Path):
    """The notice of a withdrawn revision in use is kept current during a hold: it does not wait for ZHA."""
    zha.add_device(IEEE_A, "_TZE200_aaaa", "TS0601")
    entry = await setup_entry(hass, repo_dir)
    await apply_list(hass)
    (repo_dir / "data").mkdir(exist_ok=True)
    (repo_dir / "data" / "withdrawn.toml").write_text(f'[[withdrawn]]\nfile = "z2m_tuya_a.py"\nrevision = "{quirk_revision("tuya_a")}"\nreason = "Drives the valve fully open."\n')
    REPOS[repo_dir].publish()
    await entry.runtime_data.async_check()
    assert [i.translation_key for i in our_issues(hass).values()] == ["withdrawn_installed"]
    assert entry.runtime_data.summary()["change_list"]["held"] == "pending"
    # Once ZHA loaded the folder the list takes the file out.
    zha.reload({IEEE_A: "z2m_tuya_a:TuyaA"})
    await wait_for_refresh(hass)
    assert listed(hass) == {**NOTHING, "remove": ["z2m_tuya_a.py"]}


async def test_devices_are_matched_by_their_zigpy_names(hass: HomeAssistant, zha: Zha, repo_dir: Path, quirks_dir: Path):
    """A quirk's friendly name changes the manufacturer and model in the device registry only: quirks
    match on those of the zigpy device, so does the change list."""
    device_id = zha.add_device(IEEE_A, "_TZE200_aaaa", "TS0601", "Radar")
    entry = await setup_entry(hass, repo_dir)
    await apply_list(hass)
    # ZHA applies the file: the device registry shows its friendly name from now on.
    zha.zigpy[IEEE_A] = ("_TZE200_aaaa", "TS0601")
    dr.async_get(hass).async_update_device(device_id, manufacturer="Tuya", model="Presence radar")
    zha.reload({IEEE_A: "z2m_tuya_a:TuyaA"})
    await wait_for_refresh(hass)
    # Still the file's device: no removal.
    assert our_issues(hass) == {}
    assert entry.runtime_data.summary()["installed"][str(quirks_dir / "z2m_tuya_a.py")]["claims"] == ["_TZE200_aaaa TS0601"]
    # A newer version is an update for it.
    write_repo(repo_dir, version=2)
    REPOS[repo_dir].publish()
    await entry.runtime_data.async_check()
    assert listed(hass) == {**NOTHING, "update": ["z2m_tuya_a.py"]}


@pytest.mark.parametrize("how", ["disabled", "excluded"])
async def test_a_device_left_out_keeps_nothing(hass: HomeAssistant, zha: Zha, repo_dir: Path, quirks_dir: Path, how: str):
    """A file only a left-out device runs goes; taken back in, the device gets it again in a new list."""
    device_id = zha.add_device(IEEE_A, "_TZE200_aaaa", "TS0601", "Radar")
    entry = await setup_entry(hass, repo_dir)
    await apply_list(hass)
    zha.reload({IEEE_A: "z2m_tuya_a:TuyaA"})
    await leave_out(hass, entry, device_id, how)
    assert listed(hass) == {**NOTHING, "remove": ["z2m_tuya_a.py"]}
    flow = await start_fix(hass, issue_of(hass, "changes"))
    assert "- **Remove** `z2m_tuya_a.py` (Tuya A): the devices that used it are left out" in flow["description_placeholders"]["changes"]
    flow = await continue_fix(hass, flow, {"next_step_id": "apply"})
    assert flow["reason"] == "done", flow
    assert list(quirks_dir.iterdir()) == []
    # Left out, the device gets nothing new.
    zha.reload({IEEE_A: NO_QUIRK})
    await entry.runtime_data.async_refresh()
    assert our_issues(hass) == {}
    await leave_out(hass, entry, device_id, how, out=False)
    assert offered(hass) == ["z2m_tuya_a.py"]


async def test_a_file_another_device_needs_names_the_left_out_devices_it_applies_to(hass: HomeAssistant, zha: Zha, repo_dir: Path):
    """A shared file cannot be left out for one device: it comes for another device that needs it.
    The list says that ZHA applies it to the left-out device as well."""
    left_out = zha.add_device(IEEE_A, "Acme", "B-1", "Lamp plug")
    entry = await setup_entry(hass, repo_dir, {const.CONF_EXCLUDED: [left_out]})
    # Nothing just for a device left out.
    assert our_issues(hass) == {}
    assert (await diagnostics.async_get_config_entry_diagnostics(hass, entry))["devices_left_alone"] == 1
    zha.add_device(IEEE_B, "Anyone", "B-1", "Plug")
    await wait_for_refresh(hass)
    flow = await start_fix(hass, issue_of(hass, "changes"))
    lines = flow["description_placeholders"]["changes"].splitlines()
    assert lines[0].startswith("- **Install** `z2m_acme_b.py` (Acme B-1) for Plug.")
    assert lines[1] == ALSO_LAMP_PLUG
    flow = await continue_fix(hass, flow, {"next_step_id": "apply"})
    assert flow["reason"] == "done", flow
    # Its update says the same.
    zha.reload({IEEE_A: "z2m_acme_b:AcmeB", IEEE_B: "z2m_acme_b:AcmeB"})
    write_repo(repo_dir, version=2)
    REPOS[repo_dir].publish()
    await entry.runtime_data.async_check()
    assert listed(hass) == {**NOTHING, "update": ["z2m_acme_b.py"]}
    lines = (await entry.runtime_data.async_change_text()).splitlines()
    assert lines[0].startswith("- **Update** `z2m_acme_b.py` (Acme B-1) for Plug.") and ALSO_LAMP_PLUG in lines


async def test_diagnostics_list_installed_files(hass: HomeAssistant, zha: Zha, repo_dir: Path, quirks_dir: Path):
    zha.add_device(IEEE_A, "_TZE200_aaaa", "TS0601", "Radar")
    entry = await setup_entry(hass, repo_dir)
    manager = entry.runtime_data
    result = await diagnostics.async_get_config_entry_diagnostics(hass, entry)
    assert result["change_list"] == {"held": None, "id": manager.plan.key, "remove": {}, "update": [], "install": ["z2m_tuya_a.py"]}
    assert result["target"] == ["z2m_tuya_a.py"] and result["devices_left_alone"] == 0
    await apply_list(hass)
    zha.apply_quirks({IEEE_A: "z2m_tuya_a:TuyaA"})
    await manager.async_refresh()
    result = await diagnostics.async_get_config_entry_diagnostics(hass, entry)
    path = str(quirks_dir / "z2m_tuya_a.py")
    assert result["folder"] == str(quirks_dir)
    assert result["content"]["in_use"] == "content-1"
    assert result["content"]["state"]["files"] == 3
    assert result["installed"][path]["state"] == "installed"
    assert result["installed"][path]["claims"] == result["installed"][path]["active_for"] == ["_TZE200_aaaa TS0601"]
    assert result["installed"][path]["revision"] == result["installed"][path]["offered_revision"] == quirk_revision("tuya_a")
    assert "Radar" not in str(result)
    assert result["zha_quirks_known"] is True and result["zha"] == "loaded"
    # ZHA has not loaded the folder since: the change waits, so does the list.
    assert result["pending_zha_reload"] == ["z2m_tuya_a.py: installed"]
    assert result["change_list"]["held"] == "pending" and result["change_list"]["id"] is None


async def test_diagnostics_of_a_file_changed_by_hand(hass: HomeAssistant, zha: Zha, repo_dir: Path, quirks_dir: Path):
    zha.add_device(IEEE_A, "_TZE200_aaaa", "TS0601")
    entry = await setup_entry(hass, repo_dir)
    await apply_list(hass)
    (quirks_dir / "z2m_tuya_a.py").write_text("# tuned by the user\n")
    await entry.runtime_data.async_refresh()
    result = await diagnostics.async_get_config_entry_diagnostics(hass, entry)
    installed = result["installed"][str(quirks_dir / "z2m_tuya_a.py")]
    # The revision written, which the file on disk no longer has.
    assert installed["revision"] == installed["offered_revision"] == quirk_revision("tuya_a")
    assert installed["unchanged_on_disk"] is False
    assert installed["state"] == "changed by you, left alone"
