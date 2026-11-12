"""A file that takes a device over from ZHA's own quirk where that quirk shows less (the manifest's
over_zha): offered in the change list with what each side shows, recorded with the names it takes
over, handed back to ZHA's quirk once the state ships no file under its name, whatever the reason
(every device on those names, also those paired since). The guard lets the take-over filter stand
only in a file whose entry says so."""

from __future__ import annotations

import copy
import errno
import os
from pathlib import Path
from unittest.mock import patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from .conftest import (
    MANIFEST,
    REPOS,
    Zha,
    apply_list,
    continue_fix,
    issue_of,
    listed,
    offered,
    our_issues,
    quirk_text,
    setup_entry,
    start_fix,
    take_over_filter,
    write_repo,
)
from .integration import const, content, files, guard, text
from .integration import plan as plans
from .test_content import NOTHING, apply_and_reload

STORAGE_KEY = const.STORAGE_KEY
IEEE = "00:11:22:33:44:55:66:0b"
IEEE_OTHER = "00:11:22:33:44:55:66:0c"
IEEE_SECOND = "00:11:22:33:44:55:66:0d"
IEEE_REPAIRED = "00:11:22:33:44:55:66:0e"
# What ZHA reports for the device: on its own quirk, on ours.
ZHAS = "zhaquirks.sonoff.trvzb:(SONOFF / TRV-ZBT)"
OURS = "z2m_sonoff_trv_zbt:(None / TRV-ZBT)"
OVER_ZHA = {"adds": ["Screen direction", "Low battery valve state"], "zha_only": ["Boost mode", "Timer mode"]}
TRV = {
    "file": "quirks/z2m_sonoff_trv_zbt.py",
    # As the manifest holds it: z2m's model-only name and the shipped name it takes over.
    "fingerprints": [[None, "TRV-ZBT"], ["SONOFF", "TRV-ZBT"]],
    "claimed_elsewhere": [],
    "vendor": "SONOFF",
    "model": "TRV-ZBT",
    "description": "Zigbee thermostatic radiator valve",
    "status": "verified",
    "path": "zcl",
    "over_zha": OVER_ZHA,
}
FILE = "z2m_sonoff_trv_zbt.py"
# The next state ships no file under the name: upstream caught up (no entry), or no file can be built
# any more (the entry stays without a file). Either way ZHA's
# quirk takes the device back.
NOT_BUILT = {**{key: value for key, value in TRV.items() if key not in ("file", "over_zha")}, "file": None, "not_built": "endpoint unclear"}
DROPS = [
    pytest.param({"acme_c": MANIFEST["acme_c"]}, id="no_entry"),
    pytest.param({"acme_c": MANIFEST["acme_c"], "sonoff_trv_zbt": NOT_BUILT}, id="not_built"),
]


def ship(repo_dir: Path, manifest: dict, version: int = 1) -> str:
    """The working tree with these entries as the next content tag."""
    write_repo(repo_dir, manifest, version)
    return REPOS[repo_dir].publish()


def changes_text(flow: dict) -> list[str]:
    return flow["description_placeholders"]["changes"].splitlines()


def names_in_record(hass_storage, path: str) -> dict:
    return hass_storage[STORAGE_KEY]["data"]["installed"][path]["names"]


@pytest.mark.parametrize("next_state", DROPS)
async def test_a_file_takes_a_device_over_from_zhas_quirk_and_hands_it_back(hass: HomeAssistant, zha: Zha, repo_dir: Path, quirks_dir: Path, hass_storage, next_state: dict):
    write_repo(repo_dir, {"sonoff_trv_zbt": TRV})
    zha.add_device(IEEE, "SONOFF", "TRV-ZBT", "Valve")
    zha.apply_quirks({IEEE: ZHAS})
    entry = await setup_entry(hass, repo_dir)
    assert offered(hass) == [FILE]

    flow = await start_fix(hass, issue_of(hass, "changes"))
    assert changes_text(flow) == [
        f"- **Install** `{FILE}` (SONOFF TRV-ZBT: Zigbee thermostatic radiator valve) for Valve. Status: verified on a device.",
        "    - replaces ZHA's own quirk on Valve, which shows less. Adds: Screen direction, Low battery valve state. Only in ZHA's quirk: Boost mode, Timer mode",
        "    - to keep ZHA's quirk, leave Valve out in the xquirks options",
    ]
    flow = await continue_fix(hass, flow, {"next_step_id": "apply"})
    assert flow["type"] is FlowResultType.ABORT and flow["reason"] == "done", flow
    path = str(quirks_dir / FILE)
    assert (quirks_dir / FILE).read_bytes() == quirk_text("sonoff_trv_zbt", 1, TRV)
    # The record keeps the exact names the version takes over, not the devices of this list.
    assert names_in_record(hass_storage, path)["takes_over"] == [["SONOFF", "TRV-ZBT"]]
    assert "took_over" not in hass_storage[STORAGE_KEY]["data"]["installed"][path]

    # ZHA reloads and applies the file: nothing more to do.
    zha.reload({IEEE: OURS})
    await entry.runtime_data.async_refresh()
    assert our_issues(hass) == {}

    # A new revision that still takes it over: the update keeps the names.
    ship(repo_dir, {"sonoff_trv_zbt": TRV}, 2)
    await entry.runtime_data.async_check()
    assert listed(hass) == {**NOTHING, "update": [FILE]}
    flow = await start_fix(hass, issue_of(hass, "changes"))
    # The device runs the file already: no take-over line.
    assert not [line for line in changes_text(flow) if "ZHA's own quirk" in line or "keep ZHA's quirk" in line]
    await apply_and_reload(hass, zha, {IEEE: OURS})
    assert names_in_record(hass_storage, path)["takes_over"] == [["SONOFF", "TRV-ZBT"]]
    assert our_issues(hass) == {}

    # Upstream catches up, or no file can be built any more: the state ships no file
    # under its name, ZHA's quirk takes the device back.
    ship(repo_dir, next_state)
    await entry.runtime_data.async_check()
    assert listed(hass) == {**NOTHING, "remove": [FILE]}
    flow = await start_fix(hass, issue_of(hass, "changes"))
    # No file under the name in the state: the label is the file name, as plain text.
    assert changes_text(flow) == [rf"- **Remove** `{FILE}` (z2m\_sonoff\_trv\_zbt.py): ZHA can handle this device by itself now, xquirks is no longer needed for it."]
    flow = await continue_fix(hass, flow, {"next_step_id": "apply"})
    assert flow["reason"] == "done", flow
    assert not (quirks_dir / FILE).exists() and path not in hass_storage[STORAGE_KEY]["data"]["installed"]
    zha.reload({IEEE: ZHAS})
    await entry.runtime_data.async_refresh()
    assert our_issues(hass) == {}


# Entities that read an attribute, as the manifest holds them: [cluster, attribute id, platform, unique id, name].
OURS_IDS = [[0xFC11, 0x6011, "number", "-1-temperature_trigger", "Temperature accuracy"], [0xFC11, 0x600E, "select", "-1-sensor_select", "Temperature *sensor*"],
            [0xFC11, 0x0000, "switch", "-1-child_lock", "Child lock"]]
ZHA_IDS = [[0xFC11, 0x6011, "number", "-1-temperature_control_accuracy", "Temperature control accuracy"], [0xFC11, 0x600E, "switch", "-1-sensor_select", "External sensor"],
           [0xFC11, 0x0000, "switch", "-1-child_lock", "Child lock"]]


async def test_the_change_list_names_the_entities_that_get_another_id(hass: HomeAssistant, zha: Zha, repo_dir: Path, quirks_dir: Path, hass_storage):
    """An entity both quirks read from the same attribute under another platform or unique id is a new
    entity in Home Assistant. Before the take-over the line names ZHA's entities (the user has them);
    the record keeps the file's; before the hand-back the line names those of the version written."""
    write_repo(repo_dir, {"sonoff_trv_zbt": {**TRV, "swap": {"ours": OURS_IDS, "zha": ZHA_IDS}}})
    zha.add_device(IEEE, "SONOFF", "TRV-ZBT", "Valve")
    zha.apply_quirks({IEEE: ZHAS})
    entry = await setup_entry(hass, repo_dir)
    lines = changes_text(await start_fix(hass, issue_of(hass, "changes")))
    assert lines[1:] == [
        "    - replaces ZHA's own quirk on Valve, which shows less. Adds: Screen direction, Low battery valve state. Only in ZHA's quirk: Boost mode, Timer mode",
        "    - new IDs in Home Assistant for Temperature control accuracy, External sensor: automations that use them need updating",
        "    - to keep ZHA's quirk, leave Valve out in the xquirks options",
    ]
    await apply_and_reload(hass, zha, {IEEE: OURS})
    assert names_in_record(hass_storage, str(quirks_dir / FILE))["swap"] == OURS_IDS
    # The newer file has other names by now; the hand-back compares the version written.
    newer = [[0xFC11, 0x6011, "number", "-1-temperature_control_accuracy", "Temperature control accuracy"]]
    handed_back = {key: value for key, value in NOT_BUILT.items() if key != "not_built"}
    handed_back |= {"status": "upstream", "fingerprints": [["SONOFF", "TRV-ZBT"]], "swap": {"ours": newer, "zha": ZHA_IDS}}
    ship(repo_dir, {"acme_c": MANIFEST["acme_c"], "sonoff_trv_zbt": handed_back}, 2)
    await entry.runtime_data.async_check()
    assert listed(hass) == {**NOTHING, "remove": [FILE]}
    assert changes_text(await start_fix(hass, issue_of(hass, "changes"))) == [
        HANDED_BACK, r"    - new IDs in Home Assistant for Temperature accuracy, Temperature \*sensor\*: automations that use them need updating"]


async def test_a_version_that_takes_nothing_over_clears_the_record(hass: HomeAssistant, zha: Zha, repo_dir: Path, quirks_dir: Path, hass_storage):
    """ZHA dropped its quirk: the next state ships the file without over_zha, the device keeps it.
    Its record then names nothing taken over (a later drop of the file must not leave the device
    without any quirk)."""
    write_repo(repo_dir, {"sonoff_trv_zbt": TRV})
    zha.add_device(IEEE, "SONOFF", "TRV-ZBT", "Valve")
    zha.apply_quirks({IEEE: ZHAS})
    entry = await setup_entry(hass, repo_dir)
    await apply_and_reload(hass, zha, {IEEE: OURS})
    path = str(quirks_dir / FILE)
    assert names_in_record(hass_storage, path)["takes_over"]

    plain = {key: value for key, value in TRV.items() if key != "over_zha"}
    ship(repo_dir, {"sonoff_trv_zbt": plain}, 2)
    await entry.runtime_data.async_check()
    assert listed(hass) == {**NOTHING, "update": [FILE]}
    await apply_and_reload(hass, zha, {IEEE: OURS})
    assert "takes_over" not in names_in_record(hass_storage, path)
    # Dropped from the state now, the file stays: the device had no quirk of ZHA to go back to.
    ship(repo_dir, {"acme_c": MANIFEST["acme_c"]})
    await entry.runtime_data.async_check()
    assert listed(hass) == NOTHING and (quirks_dir / FILE).exists()


async def test_no_take_over_for_a_device_left_out_or_of_another_manufacturer(hass: HomeAssistant, zha: Zha, repo_dir: Path, quirks_dir: Path):
    write_repo(repo_dir, {"sonoff_trv_zbt": TRV})
    device_id = zha.add_device(IEEE, "SONOFF", "TRV-ZBT", "Valve")
    # Another manufacturer the model-only name claims, on a quirk ZHA ships for it.
    zha.add_device(IEEE_OTHER, "Other", "TRV-ZBT", "Other valve")
    zha.apply_quirks({IEEE: ZHAS, IEEE_OTHER: "zhaquirks.other.trv:(Other / TRV-ZBT)"})
    await setup_entry(hass, repo_dir, {const.CONF_EXCLUDED: [device_id]})
    assert listed(hass) == NOTHING and list(quirks_dir.iterdir()) == []


HANDED_BACK = rf"- **Remove** `{FILE}` (z2m\_sonoff\_trv\_zbt.py): ZHA can handle this device by itself now, xquirks is no longer needed for it."


async def drop_the_file(hass: HomeAssistant, entry, repo_dir: Path, next_state: dict) -> list[str]:
    """The next state ships no file under the take-over file's name: the change list's lines."""
    ship(repo_dir, next_state, 3)
    await entry.runtime_data.async_check()
    assert listed(hass) == {**NOTHING, "remove": [FILE]}
    return changes_text(await start_fix(hass, issue_of(hass, "changes")))


@pytest.mark.parametrize("next_state", DROPS)
async def test_devices_paired_or_re_paired_since_go_back_to_zhas_quirk_too(hass: HomeAssistant, zha: Zha, repo_dir: Path, quirks_dir: Path, next_state: dict):
    """The record keeps the names the version takes over, not the devices of the install: a second
    valve paired since and the first one re-paired under a new id run the file too (its filter keeps
    it for the exact name). Once the state drops the file, ZHA's quirk takes all of them back."""
    write_repo(repo_dir, {"sonoff_trv_zbt": TRV})
    first = zha.add_device(IEEE, "SONOFF", "TRV-ZBT", "Valve")
    zha.apply_quirks({IEEE: ZHAS})
    entry = await setup_entry(hass, repo_dir)
    await apply_and_reload(hass, zha, {IEEE: OURS})
    zha.remove_device(first)
    zha.add_device(IEEE_REPAIRED, "SONOFF", "TRV-ZBT", "Valve")
    zha.add_device(IEEE_SECOND, "SONOFF", "TRV-ZBT", "Second valve")
    zha.reload({IEEE_REPAIRED: OURS, IEEE_SECOND: OURS})
    await entry.runtime_data.async_refresh()
    assert our_issues(hass) == {}
    # No device listed as left without a quirk: ZHA's quirk takes them back.
    assert await drop_the_file(hass, entry, repo_dir, next_state) == [HANDED_BACK]


@pytest.mark.parametrize("next_state", DROPS)
async def test_a_device_left_out_at_the_install_and_back_since_goes_back_too(hass: HomeAssistant, zha: Zha, repo_dir: Path, quirks_dir: Path, next_state: dict):
    write_repo(repo_dir, {"sonoff_trv_zbt": TRV})
    zha.add_device(IEEE, "SONOFF", "TRV-ZBT", "Valve")
    second = zha.add_device(IEEE_SECOND, "SONOFF", "TRV-ZBT", "Second valve")
    zha.apply_quirks({IEEE: ZHAS, IEEE_SECOND: ZHAS})
    entry = await setup_entry(hass, repo_dir, {const.CONF_EXCLUDED: [second]})
    assert listed(hass) == {**NOTHING, "install": [FILE]}
    # ZHA applies the file to every device with the name: the left-out valve gets it too.
    await apply_and_reload(hass, zha, {IEEE: OURS, IEEE_SECOND: OURS})
    hass.config_entries.async_update_entry(entry, options={const.CONF_EXCLUDED: []})
    await hass.async_block_till_done()
    await entry.runtime_data.async_refresh()
    assert our_issues(hass) == {}
    assert await drop_the_file(hass, entry, repo_dir, next_state) == [HANDED_BACK]


async def test_a_failed_list_puts_a_take_over_update_back_with_its_record(hass: HomeAssistant, zha: Zha, repo_dir: Path, quirks_dir: Path, hass_storage):
    """A later step of the list fails: the update of the take-over file is undone, its bytes and its
    record (with the names it takes over) as before the list."""
    write_repo(repo_dir, {"sonoff_trv_zbt": TRV})
    zha.add_device(IEEE, "SONOFF", "TRV-ZBT", "Valve")
    zha.apply_quirks({IEEE: ZHAS})
    entry = await setup_entry(hass, repo_dir)
    await apply_and_reload(hass, zha, {IEEE: OURS})
    zha.add_device(IEEE_OTHER, "Anyone", "B-1")
    ship(repo_dir, {"sonoff_trv_zbt": TRV, "acme_b": MANIFEST["acme_b"]}, 2)
    await entry.runtime_data.async_check()
    assert listed(hass) == {**NOTHING, "update": [FILE], "install": ["z2m_acme_b.py"]}
    before = {item.name: item.read_bytes() for item in quirks_dir.iterdir()}
    stored = copy.deepcopy(hass_storage[STORAGE_KEY]["data"])
    write_new = files.write_new

    def full_disk(path: str, data: bytes) -> None:
        if os.path.basename(path) == "z2m_acme_b.py":
            raise OSError(errno.ENOSPC, "No space left on device")
        write_new(path, data)

    with patch.object(files, "write_new", full_disk):
        flow = await apply_list(hass, expect=("failed",))
    assert flow["description_placeholders"]["failed"] == "`z2m_acme_b.py`: No space left on device"
    assert {item.name: item.read_bytes() for item in quirks_dir.iterdir()} == before
    assert before[FILE] == quirk_text("sonoff_trv_zbt", 1, TRV)
    assert hass_storage[STORAGE_KEY]["data"] == entry.runtime_data.data == stored
    assert names_in_record(hass_storage, str(quirks_dir / FILE))["takes_over"] == [["SONOFF", "TRV-ZBT"]]


@pytest.mark.parametrize(
    ("over_zha", "variant", "problem"),
    [
        (False, True, "takes devices over from ZHA's own quirk, which its manifest entry does not say"),
        (True, False, "its manifest entry says it takes devices over from ZHA's own quirk, its filter does not"),
    ],
)
async def test_the_take_over_filter_stands_exactly_where_the_entry_says_so(hass: HomeAssistant, zha: Zha, repo_dir: Path, quirks_dir: Path, over_zha, variant, problem):
    entry_ = TRV if over_zha else {key: value for key, value in TRV.items() if key != "over_zha"}
    write_repo(repo_dir, {"sonoff_trv_zbt": entry_})
    data = quirk_text("sonoff_trv_zbt", 1, TRV if variant else {})
    (repo_dir / "quirks" / FILE).write_bytes(data)
    zha.add_device(IEEE, "Anyone", "TRV-ZBT", "Valve")
    entry = await setup_entry(hass, repo_dir)
    assert offered(hass) == [] and list(quirks_dir.iterdir()) == []
    assert issue_of(hass, "refused", FILE)
    assert problem in entry.runtime_data.summary()["refused_by_the_guard"][FILE]["problems"][0]


@pytest.mark.parametrize(
    "over_zha",
    [
        "Screen direction",
        {"adds": ["Screen direction"]},
        {"adds": ["Screen direction"], "zha_only": [], "more": []},
        {"adds": "Screen direction", "zha_only": []},
        {"adds": [1], "zha_only": []},
    ],
)
def test_over_zha_in_another_shape_is_refused(over_zha):
    entry = {**TRV, "over_zha": over_zha}
    # The guard has no entry to compare the file with; the content check takes no such state.
    assert guard.Targets.of(entry) is None
    with pytest.raises(content.BadContent, match="over_zha missing or malformed"):
        content.check_entry("sonoff_trv_zbt", entry)


@pytest.mark.parametrize(
    "swap",
    [
        [],
        {"ours": []},
        {"ours": [], "zha": [], "more": []},
        {"ours": [[0xFC11, 1, "switch", "-1-x"]], "zha": []},
        {"ours": [[0xFC11, "1", "switch", "-1-x", "X"]], "zha": []},
        {"ours": [[True, 1, "switch", "-1-x", "X"]], "zha": []},
        {"ours": [], "zha": [[0xFC11, 1, "switch", "", "X"]]},
    ],
)
def test_swap_in_another_shape_is_refused(swap):
    with pytest.raises(content.BadContent, match="swap missing or malformed"):
        content.check_entry("sonoff_trv_zbt", {**TRV, "swap": swap})
    # Also on an entry without a file.
    with pytest.raises(content.BadContent, match="swap missing or malformed"):
        content.check_entry("sonoff_trv_zbt", {"file": None, "fingerprints": [], "status": "upstream", "swap": swap})


def test_the_entry_shapes_the_build_writes_pass():
    for entry in (TRV, {**TRV, "over_zha": {"adds": [], "zha_only": []}}, {key: value for key, value in TRV.items() if key != "over_zha"}):
        content.check_entry("sonoff_trv_zbt", entry)
        targets = guard.Targets.of(entry)
        assert targets is not None and targets.takes_over is ("over_zha" in entry)
    # The verdicts are cached per targets: a take-over entry and a plain one never share a key.
    assert guard.Targets.of(TRV).key != guard.Targets.of({key: value for key, value in TRV.items() if key != "over_zha"}).key


def test_the_take_over_filter_is_fixed_code_of_this_release():
    shipped = guard.Guard.load()
    source = f'"""Quirk.\n"""\nFINGERPRINTS = [(None, "TRV-ZBT"), ("SONOFF", "TRV-ZBT")]\n{take_over_filter()}'
    assert shipped.problems(source.encode(), guard.Targets.of(TRV)) == ()
    assert shipped.problems(source.encode(), guard.Targets.of({key: value for key, value in TRV.items() if key != "over_zha"})) != ()


def test_the_change_list_caps_long_lists_and_keeps_names_plain():
    names = [f"Setting *{n}*" for n in range(14)]
    install = plans.Install(FILE, "a" * 64, ("d1", "d2"), took_over=("d1",))
    devices = {"d1": plans.Device("SONOFF", "TRV-ZBT", "Valve [hall]", "zhaquirks.sonoff.trvzb"), "d2": plans.Device("Other", "TRV-ZBT", "Spare", "")}
    found = {**TRV, "over_zha": {"adds": names, "zha_only": []}}
    lines = text.change_list(plans.Plan(install=[install]), devices, lambda name: "SONOFF TRV-ZBT", {}, {}, lambda name: found).splitlines()
    shown = ", ".join(rf"Setting \*{n}\*" for n in range(10))
    assert lines[1] == rf"    - replaces ZHA's own quirk on Valve \[hall\], which shows less. Adds: {shown} and 4 more"
    assert lines[2] == r"    - to keep ZHA's quirk, leave Valve \[hall\] out in the xquirks options"
    # Without devices taken over (or an entry without over_zha) no such line.
    plain = plans.Install(FILE, "a" * 64, ("d2",))
    assert text.change_list(plans.Plan(install=[plain]), devices, lambda name: "SONOFF TRV-ZBT", {}, {}, lambda name: found).splitlines()[1:] == []


def test_every_removal_reason_has_its_text():
    # WITHDRAWN brings the withdrawal's own reason.
    for reason in (plans.MOVED, plans.HANDED_BACK, plans.SHIPPED, plans.LEFT_OUT, plans.UNUSED, plans.OUTSIDE):
        assert reason in text.REMOVALS
