"""Edge cases of the change list: slow ZHA, dialogs that go stale, failed steps and their undo,
unreadable files and folders, records a crash left behind."""

from __future__ import annotations

import asyncio
import copy
import errno
import logging
import os
import subprocess
import sys
import threading
import uuid
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import issue_registry as ir
from homeassistant.util import dt as dt_util
from pytest_homeassistant.common import MockConfigEntry, async_fire_time_changed

from . import integration
from .conftest import (
    MANIFEST,
    REPOS,
    Repo,
    Zha,
    apply_list,
    content_json,
    continue_fix,
    issue_of,
    issues_of,
    listed,
    offered,
    our_issues,
    published,
    quirk_revision,
    quirk_text,
    setup_entry,
    start_fix,
    tag_files,
    write_repo,
)
from .integration import DOMAIN, const, content, files, manager

IEEE_A = "00:11:22:33:44:55:66:01"
IEEE_B = "00:11:22:33:44:55:66:02"
IEEE_C = "00:11:22:33:44:55:66:03"
# Frozen copies of generated quirks (fixtures/README.md).
FROZEN = Path(__file__).resolve().parent / "fixtures"
STORAGE_KEY = const.STORAGE_KEY
NOTHING = {"remove": [], "update": [], "install": []}
# The names the manifest holds for z2m_tuya_a.py: a record keeps those of the version written.
TUYA_A_NAMES = {"fingerprints": [["_TZE200_aaaa", "TS0601"]], "claimed_elsewhere": []}
# A file of the collection as content tags hold it (the docstring tells its revision).
GENERATED = (
    b'"""Tuya A: a device.\n\nGenerated from the Zigbee2MQTT definition (zigbee-herdsman-converters 1.0.0).\n'
    b"Data: zigbee-herdsman-converters, MIT, Copyright (c) 2018 Koen Kanters.\nStatus: generated, not verified on hardware.\n"
    b'Revision: 0badc0de\n"""\n# linked\n'
)


async def wait_for_refresh(hass: HomeAssistant) -> None:
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=const.REFRESH_COOLDOWN + 1))
    await hass.async_block_till_done(wait_background_tasks=True)


def folder_of(quirks_dir: Path) -> dict[str, bytes]:
    return {path.name: path.read_bytes() for path in quirks_dir.iterdir()}


async def three_kinds(hass: HomeAssistant, zha: Zha, repo_dir: Path) -> MockConfigEntry:
    """A list with one change of each kind: z2m_acme_c.py goes (its device is gone), z2m_tuya_a.py
    is updated to version 2, z2m_acme_b.py comes for a new device."""
    zha.add_device(IEEE_A, "_TZE200_aaaa", "TS0601")
    dev_c = zha.add_device(IEEE_C, "Acme", "C-1")
    entry = await setup_entry(hass, repo_dir)
    await apply_list(hass)
    zha.reload({IEEE_A: "z2m_tuya_a:TuyaA", IEEE_C: "z2m_acme_c:AcmeC"})
    zha.remove_device(dev_c)
    zha.add_device(IEEE_B, "Anyone", "B-1")
    write_repo(repo_dir, version=2)
    REPOS[repo_dir].publish()
    await entry.runtime_data.async_check()
    assert listed(hass) == {"remove": ["z2m_acme_c.py"], "update": ["z2m_tuya_a.py"], "install": ["z2m_acme_b.py"]}
    return entry


async def test_slow_zha_reload_changes_no_list_and_keeps_the_ignore(hass: HomeAssistant, zha: Zha, repo_dir: Path):
    zha.add_device(IEEE_A, "_TZE200_aaaa", "TS0601")
    zha.add_device(IEEE_B, "Anyone", "B-1")
    zha.apply_quirks({IEEE_B: "zhaquirks.acme.b:ShippedB"})
    await setup_entry(hass, repo_dir)
    assert listed(hass) == {**NOTHING, "install": ["z2m_tuya_a.py"]}
    issue = issue_of(hass, "changes")
    ir.async_ignore_issue(hass, DOMAIN, issue.issue_id, True)
    # ZHA unloads; 10 s later it is still setting up: nothing changes.
    zha.start_reload()
    await wait_for_refresh(hass)
    assert our_issues(hass) == {}
    assert ir.async_get(hass).async_get_issue(DOMAIN, issue.issue_id).dismissed_version
    # Loaded again: the same list, still put aside; nothing for the device on a shipped quirk.
    zha.finish_reload()
    await wait_for_refresh(hass)
    assert our_issues(hass) == {}
    assert ir.async_get(hass).async_get_issue(DOMAIN, issue.issue_id).dismissed_version


async def test_zha_not_loaded_at_setup_lists_nothing_until_it_is(hass: HomeAssistant, zha: Zha, repo_dir: Path):
    zha.add_device(IEEE_A, "_TZE200_aaaa", "TS0601")
    zha.add_device(IEEE_B, "Anyone", "B-1")
    zha.apply_quirks({IEEE_B: "zhaquirks.acme.b:ShippedB"})
    zha.start_reload()
    entry = await setup_entry(hass, repo_dir)
    await entry.runtime_data.async_refresh()
    assert our_issues(hass) == {}
    assert entry.runtime_data.summary()["zha"] == "not loaded"
    zha.finish_reload()
    await wait_for_refresh(hass)
    assert offered(hass) == ["z2m_tuya_a.py"]


async def test_a_list_that_changed_while_its_dialog_was_open_changes_nothing(hass: HomeAssistant, zha: Zha, repo_dir: Path, quirks_dir: Path):
    dev_a = zha.add_device(IEEE_A, "_TZE200_aaaa", "TS0601")
    dev_b = zha.add_device(IEEE_B, "Anyone", "B-1")
    entry = await setup_entry(hass, repo_dir)
    await apply_list(hass)
    zha.reload({IEEE_A: "z2m_tuya_a:TuyaA", IEEE_B: "z2m_acme_b:AcmeB"})
    zha.remove_device(dev_a)
    await entry.runtime_data.async_refresh()
    assert listed(hass) == {**NOTHING, "remove": ["z2m_tuya_a.py"]}
    flow = await start_fix(hass, issue_of(hass, "changes"))
    # While the dialog is open the other device goes too: the dialog showed another list.
    zha.remove_device(dev_b)
    await entry.runtime_data.async_refresh()
    flow = await continue_fix(hass, flow, {"next_step_id": "apply"})
    assert flow["type"] is FlowResultType.ABORT and flow["reason"] == "stale", flow
    assert sorted(folder_of(quirks_dir)) == ["z2m_acme_b.py", "z2m_tuya_a.py"]
    assert zha.reloads == 1
    # The new list holds both removals: applied as one, ZHA reloads once.
    assert listed(hass) == {**NOTHING, "remove": ["z2m_acme_b.py", "z2m_tuya_a.py"]}
    await apply_list(hass)
    assert folder_of(quirks_dir) == {} and zha.reloads == 2


async def test_a_device_pairing_while_the_dialog_is_open_makes_a_new_list(hass: HomeAssistant, zha: Zha, repo_dir: Path, quirks_dir: Path):
    zha.add_device(IEEE_A, "_TZE200_aaaa", "TS0601")
    await setup_entry(hass, repo_dir)
    flow = await start_fix(hass, issue_of(hass, "changes"))
    zha.add_device(IEEE_B, "Anyone", "B-1")
    await wait_for_refresh(hass)
    flow = await continue_fix(hass, flow, {"next_step_id": "apply"})
    assert flow["type"] is FlowResultType.ABORT and flow["reason"] == "stale", flow
    # Nothing written: the new list brings both files.
    assert folder_of(quirks_dir) == {} and zha.reloads == 0
    assert offered(hass) == ["z2m_acme_b.py", "z2m_tuya_a.py"]
    await apply_list(hass)
    assert sorted(folder_of(quirks_dir)) == ["z2m_acme_b.py", "z2m_tuya_a.py"]


async def test_a_file_edited_while_the_dialog_is_open_is_left_alone(hass: HomeAssistant, zha: Zha, repo_dir: Path, quirks_dir: Path):
    zha.add_device(IEEE_A, "_TZE200_aaaa", "TS0601")
    entry = await setup_entry(hass, repo_dir)
    await apply_list(hass)
    zha.reload({IEEE_A: "z2m_tuya_a:TuyaA"})
    # The device's name moved to a file of its own: the old file goes in the list that brings the new one.
    manifest = {slug: e for slug, e in MANIFEST.items() if slug != "tuya_a"}
    manifest["tuya_a_aaaa"] = {**MANIFEST["tuya_a"], "file": "quirks/z2m_tuya_a_aaaa.py"}
    write_repo(repo_dir, manifest)
    REPOS[repo_dir].publish()
    await entry.runtime_data.async_check()
    assert listed(hass) == {"remove": ["z2m_tuya_a.py"], "update": [], "install": ["z2m_tuya_a_aaaa.py"]}
    flow = await start_fix(hass, issue_of(hass, "changes"))
    # The old file is edited while the dialog is open: it is the user's now.
    (quirks_dir / "z2m_tuya_a.py").write_text("# tuned meanwhile\n")
    flow = await continue_fix(hass, flow, {"next_step_id": "apply"})
    assert flow["type"] is FlowResultType.ABORT and flow["reason"] == "stale", flow
    assert folder_of(quirks_dir) == {"z2m_tuya_a.py": b"# tuned meanwhile\n"}
    assert zha.reloads == 1
    # The device runs the user's file from now on: the new file is not written next to it.
    assert sorted(i.translation_key for i in our_issues(hass).values()) == ["blocked", "changed"]


async def test_a_failed_step_undoes_the_steps_before_it(hass: HomeAssistant, zha: Zha, repo_dir: Path, quirks_dir: Path, hass_storage):
    entry = await three_kinds(hass, zha, repo_dir)
    before, stored, reloads = folder_of(quirks_dir), copy.deepcopy(hass_storage[STORAGE_KEY]["data"]), zha.reloads
    issue = issue_of(hass, "changes")
    delete, replace, write_new, calls = files.delete, files.replace, files.write_new, []

    def deleted(path: str, expected: str) -> bool:
        calls.append(("delete", os.path.basename(path)))
        return delete(path, expected)

    def replaced(path: str, data: bytes, expected: str) -> bool:
        calls.append(("replace", os.path.basename(path)))
        return replace(path, data, expected)

    def full_disk(path: str, data: bytes) -> None:
        calls.append(("write_new", os.path.basename(path)))
        if path.endswith("z2m_acme_b.py"):
            raise OSError(errno.ENOSPC, "No space left on device")
        write_new(path, data)

    with patch.object(files, "delete", deleted), patch.object(files, "replace", replaced), patch.object(files, "write_new", full_disk):
        flow = await apply_list(hass, expect=("failed",))
    # Removals, then updates, then installs: the install fails, the two steps before it are undone newest first.
    assert calls == [("delete", "z2m_acme_c.py"), ("replace", "z2m_tuya_a.py"), ("write_new", "z2m_acme_b.py"), ("replace", "z2m_tuya_a.py"), ("write_new", "z2m_acme_c.py")]
    assert flow["description_placeholders"]["failed"] == "`z2m_acme_b.py`: No space left on device"
    # The folder, the records and the pending changes as before; ZHA has nothing to load.
    assert folder_of(quirks_dir) == before
    assert hass_storage[STORAGE_KEY]["data"] == entry.runtime_data.data == stored
    assert zha.reloads == reloads
    # The list stays: once the cause is gone it applies.
    assert issue_of(hass, "changes").issue_id == issue.issue_id
    await apply_list(hass)
    assert folder_of(quirks_dir) == {"z2m_acme_b.py": quirk_text("acme_b", 2), "z2m_tuya_a.py": quirk_text("tuya_a", 2)}
    assert zha.reloads == reloads + 1


async def test_a_file_edited_during_the_apply_is_left_alone(hass: HomeAssistant, zha: Zha, repo_dir: Path, quirks_dir: Path, hass_storage):
    """The steps write only while a file has the sha256 the list was made for: an edit between the
    list and the write stops the apply, the steps done before it are undone."""
    entry = await three_kinds(hass, zha, repo_dir)
    before, stored = folder_of(quirks_dir), copy.deepcopy(hass_storage[STORAGE_KEY]["data"])
    path = quirks_dir / "z2m_tuya_a.py"
    replace = files.replace

    def edited_first(target: str, data: bytes, expected: str) -> bool:
        if target == str(path):
            path.write_text("# tuned at that very moment\n")
        return replace(target, data, expected)

    with patch.object(files, "replace", edited_first):
        flow = await apply_list(hass, expect=("failed",))
    assert flow["description_placeholders"]["failed"] == "`z2m_tuya_a.py`: changed since the list was made, left alone"
    # The removal before it is put back with its record; the edit stays.
    assert folder_of(quirks_dir) == {**before, "z2m_tuya_a.py": b"# tuned at that very moment\n"}
    assert entry.runtime_data.data["installed"] == stored["installed"]
    assert entry.runtime_data.data["pending"] == stored["pending"]
    assert issue_of(hass, "changed").translation_placeholders["file"] == "z2m_tuya_a.py"


async def test_a_failed_undo_says_what_is_left_and_reloads_zha(hass: HomeAssistant, zha: Zha, repo_dir: Path, quirks_dir: Path, hass_storage):
    entry = await three_kinds(hass, zha, repo_dir)
    stored, reloads = copy.deepcopy(hass_storage[STORAGE_KEY]["data"]), zha.reloads
    tuya_a = str(quirks_dir / "z2m_tuya_a.py")

    def full_disk(path: str, data: bytes) -> None:
        raise OSError(errno.ENOSPC, "No space left on device")

    # The install fails, so does writing back the file the removal deleted.
    with patch.object(files, "write_new", full_disk):
        flow = await apply_list(hass, expect=("failed_partly",))
    placeholders = flow["description_placeholders"]
    assert placeholders["failed"] == "`z2m_acme_b.py`: No space left on device"
    assert placeholders["left"] == "- `z2m_acme_c.py`: removed"
    # ZHA loads what is there: the update is undone, the removal stays.
    assert zha.reloads == reloads + 1
    assert folder_of(quirks_dir) == {"z2m_tuya_a.py": quirk_text("tuya_a", 1)}
    assert hass_storage[STORAGE_KEY]["data"]["installed"] == {tuya_a: stored["installed"][tuya_a]}
    assert entry.runtime_data.summary()["pending_zha_reload"] == ["z2m_acme_c.py: removed"]
    # Until ZHA loaded the folder the list is held: its dialog says why.
    flow = await start_fix(hass, issue_of(hass, "changes"))
    assert flow["type"] is FlowResultType.ABORT and flow["reason"] == "held_pending"
    # The next list starts from what is on disk.
    zha.reload({IEEE_A: "z2m_tuya_a:TuyaA"})
    await entry.runtime_data.async_refresh()
    assert listed(hass) == {"remove": [], "update": ["z2m_tuya_a.py"], "install": ["z2m_acme_b.py"]}


async def test_a_download_that_fails_before_the_writes_changes_nothing(hass: HomeAssistant, zha: Zha, repo_dir: Path, quirks_dir: Path, hass_storage):
    """Every file is read and every new version fetched and checked before the first write: a
    failure there writes nothing at all."""
    entry = await three_kinds(hass, zha, repo_dir)
    before, stored = folder_of(quirks_dir), copy.deepcopy(hass_storage[STORAGE_KEY]["data"])
    # The checked downloads are gone (the cache keeps eight files), the server fails on the install's file.
    entry.runtime_data._downloads.clear()
    repo = REPOS[repo_dir]
    repo.tags[max(repo.tags)]["quirks/z2m_acme_b.py"] = 500
    calls = []

    def logged(name: str):
        real = getattr(files, name)

        def call(path: str, *args):
            calls.append(name)
            return real(path, *args)

        return call

    with patch.object(files, "delete", logged("delete")), patch.object(files, "replace", logged("replace")), patch.object(files, "write_new", logged("write_new")):
        flow = await apply_list(hass, expect=("failed",))
    assert flow["description_placeholders"]["failed"].startswith("`z2m_acme_b.py`: cannot download it (")
    assert calls == []
    assert folder_of(quirks_dir) == before and hass_storage[STORAGE_KEY]["data"] == stored


async def test_each_record_is_saved_before_its_file_is_written(hass: HomeAssistant, zha: Zha, repo_dir: Path, quirks_dir: Path, hass_storage):
    """A crash between the two leaves a record naming the file on disk or, for an update, the version
    before it (previous): the plan settles either."""
    entry = await three_kinds(hass, zha, repo_dir)
    tuya_a = str(quirks_dir / "z2m_tuya_a.py")
    old = copy.deepcopy(entry.runtime_data.data["installed"][tuya_a])
    replace, write_new, seen = files.replace, files.write_new, {}

    def replaced(path: str, data: bytes, expected: str) -> bool:
        seen[os.path.basename(path)] = copy.deepcopy(hass_storage[STORAGE_KEY]["data"]["installed"].get(path))
        return replace(path, data, expected)

    def written(path: str, data: bytes) -> None:
        seen[os.path.basename(path)] = copy.deepcopy(hass_storage[STORAGE_KEY]["data"]["installed"].get(path))
        write_new(path, data)

    with patch.object(files, "replace", replaced), patch.object(files, "write_new", written):
        await apply_list(hass)
    new_a = {"sha256": content.sha256(quirk_text("tuya_a", 2)), "revision": quirk_revision("tuya_a", 2), "names": TUYA_A_NAMES}
    new_b = {"sha256": content.sha256(quirk_text("acme_b", 2)), "revision": quirk_revision("acme_b", 2), "names": {"fingerprints": [[None, "B-1"]], "claimed_elsewhere": [["Other", "B-1"]]}}
    assert seen == {"z2m_tuya_a.py": {**new_a, "previous": old}, "z2m_acme_b.py": new_b}
    # Written: no record keeps the version before.
    assert hass_storage[STORAGE_KEY]["data"]["installed"] == {tuya_a: new_a, str(quirks_dir / "z2m_acme_b.py"): new_b}


async def test_the_undo_puts_back_a_withdrawn_revision_it_removed(hass: HomeAssistant, zha: Zha, repo_dir: Path, quirks_dir: Path, hass_storage):
    """The undo writes back only bytes the same apply took away, without the checks of a new write:
    a withdrawn revision the list removed comes back as it was."""
    zha.add_device(IEEE_A, "_TZE200_aaaa", "TS0601")
    entry = await setup_entry(hass, repo_dir)
    await apply_list(hass)
    zha.reload({IEEE_A: "z2m_tuya_a:TuyaA"})
    zha.add_device(IEEE_B, "Anyone", "B-1")
    (repo_dir / "data").mkdir(exist_ok=True)
    (repo_dir / "data" / "withdrawn.toml").write_text(f'[[withdrawn]]\nfile = "z2m_tuya_a.py"\nrevision = "{quirk_revision("tuya_a")}"\nreason = "Drives the valve fully open."\n')
    REPOS[repo_dir].publish()
    await entry.runtime_data.async_check()
    assert listed(hass) == {"remove": ["z2m_tuya_a.py"], "update": [], "install": ["z2m_acme_b.py"]}
    before, stored = folder_of(quirks_dir), copy.deepcopy(hass_storage[STORAGE_KEY]["data"])
    write_new = files.write_new

    def full_disk(path: str, data: bytes) -> None:
        if path.endswith("z2m_acme_b.py"):
            raise OSError(errno.ENOSPC, "No space left on device")
        write_new(path, data)

    with patch.object(files, "write_new", full_disk):
        await apply_list(hass, expect=("failed",))
    assert folder_of(quirks_dir) == before and hass_storage[STORAGE_KEY]["data"] == stored
    # The notice of the withdrawn revision in use stays, so does the list that takes it out.
    assert issue_of(hass, "withdrawn_installed").translation_placeholders["file"] == "z2m_tuya_a.py"
    assert issue_of(hass, "changes").severity is ir.IssueSeverity.ERROR


async def test_a_record_without_names_is_dropped_and_its_file_is_the_users(hass: HomeAssistant, zha: Zha, repo_dir: Path, quirks_dir: Path, hass_storage):
    """Records from before the change list kept device lists instead of the names of the version
    written: they go when the data loads, the backups too. Their files belong to the user."""
    path = quirks_dir / "z2m_tuya_a.py"
    path.write_bytes(quirk_text("tuya_a"))
    record = {"sha256": content.sha256(quirk_text("tuya_a")), "revision": quirk_revision("tuya_a"), "devices": {"a-device-id": ["_TZE200_aaaa", "TS0601"]}}
    data = {"installed": {str(path): record}, "forgotten": {str(quirks_dir / "z2m_acme_b.py"): record}, "backups": {"z2m_tuya_a.py": {"revision": "0badc0de"}}, "pending": {"run": "an earlier run", "changes": []}}
    hass_storage[STORAGE_KEY] = {"version": const.STORAGE_VERSION, "minor_version": 1, "key": STORAGE_KEY, "data": data}
    zha.add_device(IEEE_A, "_TZE200_aaaa", "TS0601")
    zha.apply_quirks({IEEE_A: "z2m_tuya_a:TuyaA"})
    entry = await setup_entry(hass, repo_dir)
    assert entry.runtime_data.data["installed"] == entry.runtime_data.data["forgotten"] == {}
    assert "backups" not in entry.runtime_data.data
    assert entry.runtime_data.plan.users_files == ["z2m_tuya_a.py"]
    assert [i.translation_key for i in our_issues(hass).values()] == ["users_file"]
    assert path.read_bytes() == quirk_text("tuya_a")


@pytest.mark.parametrize(("on_disk", "update"), [(1, ["z2m_tuya_a.py"]), (2, [])])
async def test_a_record_a_crash_left_is_settled_to_the_file_on_disk(hass: HomeAssistant, zha: Zha, repo_dir: Path, quirks_dir: Path, hass_storage, on_disk: int, update: list[str]):
    """An update saves the new record, with the one before as previous, before it writes the file:
    after a crash in between the record settles to the version on disk, which stays ours."""
    path = quirks_dir / "z2m_tuya_a.py"
    path.write_bytes(quirk_text("tuya_a", on_disk))
    old, new = ({"sha256": content.sha256(quirk_text("tuya_a", v)), "revision": quirk_revision("tuya_a", v), "names": TUYA_A_NAMES} for v in (1, 2))
    data = {"installed": {str(path): {**new, "previous": old}}, "forgotten": {}, "pending": {"run": "a run before the crash", "changes": []}}
    hass_storage[STORAGE_KEY] = {"version": const.STORAGE_VERSION, "minor_version": 1, "key": STORAGE_KEY, "data": data}
    zha.add_device(IEEE_A, "_TZE200_aaaa", "TS0601")
    zha.apply_quirks({IEEE_A: "z2m_tuya_a:TuyaA"})
    entry = await setup_entry(hass, write_repo(repo_dir, version=2))
    assert hass_storage[STORAGE_KEY]["data"]["installed"] == {str(path): old if on_disk == 1 else new}
    assert entry.runtime_data.plan.ours == {"z2m_tuya_a.py"}
    # The version before: the update comes again. The version written: nothing left to do.
    assert listed(hass) == {**NOTHING, "update": update}
    assert issues_of(hass, "changed") == []
    if update:
        await apply_list(hass)
        assert path.read_bytes() == quirk_text("tuya_a", 2)
        assert hass_storage[STORAGE_KEY]["data"]["installed"] == {str(path): new}


async def test_a_failed_write_leaves_nothing_behind(tmp_path: Path):
    path = tmp_path / "z2m_tuya_a.py"
    with patch.object(files.os, "fsync", side_effect=OSError(errno.ENOSPC, "No space left on device")), pytest.raises(OSError):
        files.write_new(str(path), b"x" * 100_000)
    assert list(tmp_path.iterdir()) == []
    # Never over an existing file.
    path.write_text("# mine\n")
    with pytest.raises(FileExistsError):
        files.write_new(str(path), b"ours")
    assert path.read_text() == "# mine\n" and sorted(p.name for p in tmp_path.iterdir()) == ["z2m_tuya_a.py"]


async def test_without_hard_links_it_writes_exclusively(tmp_path: Path):
    path = tmp_path / "z2m_tuya_a.py"
    with patch.object(files.os, "link", side_effect=OSError(errno.EPERM, "Operation not permitted")):
        files.write_new(str(path), b"ours")
    assert path.read_bytes() == b"ours" and [p.name for p in tmp_path.iterdir()] == ["z2m_tuya_a.py"]


async def test_failed_install_keeps_the_list(hass: HomeAssistant, zha: Zha, repo_dir: Path, quirks_dir: Path):
    zha.add_device(IEEE_A, "_TZE200_aaaa", "TS0601")
    entry = await setup_entry(hass, repo_dir)
    with patch.object(files.os, "fsync", side_effect=OSError(errno.ENOSPC, "No space left on device")):
        flow = await apply_list(hass, expect=("failed",))
    assert "No space left" in flow["description_placeholders"]["failed"]
    assert list(quirks_dir.iterdir()) == [] and entry.runtime_data.data["installed"] == {}
    assert offered(hass) == ["z2m_tuya_a.py"] and zha.reloads == 0


@pytest.mark.skipif(os.geteuid() == 0, reason="root reads mode-000 files")
async def test_an_unreadable_installed_file_is_left_alone_and_the_rest_goes_on(hass: HomeAssistant, zha: Zha, repo_dir: Path, quirks_dir: Path):
    zha.add_device(IEEE_A, "_TZE200_aaaa", "TS0601")
    entry = await setup_entry(hass, repo_dir)
    await apply_list(hass)
    zha.reload({IEEE_A: "z2m_tuya_a:TuyaA"})
    path = quirks_dir / "z2m_tuya_a.py"
    path.chmod(0)
    try:
        await entry.runtime_data.async_refresh()
        zha.add_device(IEEE_B, "Anyone", "B-1")
        await wait_for_refresh(hass)
        # Named in no list or notice: only the new device's file comes.
        assert listed(hass) == {**NOTHING, "install": ["z2m_acme_b.py"]}
        assert [i.translation_key for i in our_issues(hass).values()] == ["changes"]
        assert entry.runtime_data.summary()["installed"][str(path)]["state"] == "cannot be read, left alone"
        assert str(path) in entry.runtime_data.data["installed"]
    finally:
        path.chmod(0o644)


async def test_an_unreadable_folder_keeps_the_list_and_says_so(hass: HomeAssistant, zha: Zha, repo_dir: Path, quirks_dir: Path):
    zha.add_device(IEEE_A, "_TZE200_aaaa", "TS0601")
    entry = await setup_entry(hass, repo_dir)
    issue = issue_of(hass, "changes")
    with patch.object(files.os, "scandir", side_effect=PermissionError(errno.EACCES, "Permission denied")):
        await entry.runtime_data.async_refresh()
    assert sorted(i.translation_key for i in our_issues(hass).values()) == ["changes", "folder_unreadable"]
    assert issue_of(hass, "changes").issue_id == issue.issue_id
    assert "Permission denied" in issue_of(hass, "folder_unreadable").translation_placeholders["error"]
    await entry.runtime_data.async_refresh()
    assert [i.translation_key for i in our_issues(hass).values()] == ["changes"]


async def test_a_folder_that_does_not_exist_keeps_every_record(hass: HomeAssistant, zha: Zha, repo_dir: Path, quirks_dir: Path, tmp_path: Path, hass_storage):
    """A configured folder that is gone (a share not mounted yet) is not read as empty: read so,
    every record would count as deleted."""
    zha.add_device(IEEE_A, "_TZE200_aaaa", "TS0601")
    dev_b = zha.add_device(IEEE_B, "Anyone", "B-1")
    entry = await setup_entry(hass, repo_dir)
    await apply_list(hass)
    zha.reload({IEEE_A: "z2m_tuya_a:TuyaA", IEEE_B: "z2m_acme_b:AcmeB"})
    await entry.runtime_data.async_refresh()
    stored = copy.deepcopy(hass_storage[STORAGE_KEY]["data"])
    assert sorted(stored["installed"]) == [str(quirks_dir / "z2m_acme_b.py"), str(quirks_dir / "z2m_tuya_a.py")]
    quirks_dir.rename(tmp_path / "not mounted")
    await entry.runtime_data.async_refresh()
    # A device that goes meanwhile changes nothing either: there is no list without the folder.
    zha.remove_device(dev_b)
    await entry.runtime_data.async_refresh()
    assert [i.translation_key for i in our_issues(hass).values()] == ["folder_unreadable"]
    assert issue_of(hass, "folder_unreadable").translation_placeholders == {"folder": str(quirks_dir), "error": "No such file or directory"}
    assert hass_storage[STORAGE_KEY]["data"] == entry.runtime_data.data == stored
    # Mounted again: both files are ours as before.
    (tmp_path / "not mounted").rename(quirks_dir)
    await entry.runtime_data.async_refresh()
    assert entry.runtime_data.plan.ours == {"z2m_acme_b.py", "z2m_tuya_a.py"}
    assert listed(hass) == {**NOTHING, "remove": ["z2m_acme_b.py"]}


async def test_new_state_while_the_dialog_is_open(hass: HomeAssistant, zha: Zha, repo_dir: Path, quirks_dir: Path, hass_storage):
    zha.add_device(IEEE_B, "Anyone", "B-1")
    entry = await setup_entry(hass, repo_dir)
    await apply_list(hass)
    zha.reload({IEEE_B: "z2m_acme_b:AcmeB"})
    zha.add_device(IEEE_A, "_TZE200_aaaa", "TS0601")
    await wait_for_refresh(hass)
    flow = await start_fix(hass, issue_of(hass, "changes"))
    # Meanwhile a new state drops the file: the confirmation writes nothing.
    write_repo(repo_dir, {slug: e for slug, e in MANIFEST.items() if slug != "tuya_a"})
    REPOS[repo_dir].publish()
    await entry.runtime_data.async_check()
    flow = await continue_fix(hass, flow, {"next_step_id": "apply"})
    assert flow["type"] is FlowResultType.ABORT and flow["reason"] == "stale"
    assert not (quirks_dir / "z2m_tuya_a.py").exists()
    # What was installed before is saved.
    assert str(quirks_dir / "z2m_acme_b.py") in hass_storage[STORAGE_KEY]["data"]["installed"]


async def test_folder_change_lists_the_old_folder_and_the_new_one(hass: HomeAssistant, zha: Zha, repo_dir: Path, quirks_dir: Path, tmp_path: Path, hass_storage):
    zha.add_device(IEEE_A, "_TZE200_aaaa", "TS0601")
    entry = await setup_entry(hass, repo_dir)
    await apply_list(hass)
    new = tmp_path / "zha_quirks_new"
    new.mkdir()
    # Home Assistant starts with another folder: ZHA loads no file for the device there.
    zha.data.yaml_config["custom_quirks_path"] = str(new)
    zha.reload()
    await entry.runtime_data.async_refresh()
    assert listed(hass) == {"remove": ["z2m_tuya_a.py"], "update": [], "install": ["z2m_tuya_a.py"]}
    assert entry.runtime_data.plan.remove[0].path == str(quirks_dir / "z2m_tuya_a.py")
    flow = await start_fix(hass, issue_of(hass, "changes"))
    assert flow["description_placeholders"]["folder"] == str(new)
    assert "folder ZHA no longer loads" in flow["description_placeholders"]["changes"]
    flow = await continue_fix(hass, flow, {"next_step_id": "apply"})
    assert flow["type"] is FlowResultType.ABORT and flow["reason"] == "done", flow
    assert list(quirks_dir.iterdir()) == []
    assert [p.name for p in new.iterdir()] == ["z2m_tuya_a.py"]
    assert list(hass_storage[STORAGE_KEY]["data"]["installed"]) == [str(new / "z2m_tuya_a.py")]
    assert zha.reloads == 2


async def test_unreadable_zha_internals_warn_once_and_change_nothing(hass: HomeAssistant, zha: Zha, repo_dir: Path, caplog: pytest.LogCaptureFixture):
    zha.add_device(IEEE_A, "_TZE200_aaaa", "TS0601")
    entry = await setup_entry(hass, repo_dir)
    issue = issue_of(hass, "changes")
    zha.data.gateway_proxy = object()  # loaded, but not what this integration knows
    with caplog.at_level(logging.WARNING):
        await entry.runtime_data.async_refresh()
        await entry.runtime_data.async_refresh()
    assert caplog.text.count("Cannot read which quirks ZHA applied") == 1
    assert issue_of(hass, "changes").issue_id == issue.issue_id
    assert entry.runtime_data.summary()["zha"] == manager.ZHA_UNREADABLE


def test_applied_module_reads_quirk_applied():
    def device(quirk_class, applied):
        return type("D", (), {"quirk_class": quirk_class, "quirk_applied": applied})()

    assert manager.applied_module(device("z2m_tuya_a:(_TZE200_aaaa / TS0601)", True)) == "z2m_tuya_a"
    assert manager.applied_module(device("zigpy.device.Device", False)) == ""
    # Applied, but not in the "module:label" form: unknown, not "no quirk".
    assert manager.applied_module(device("zhaquirks.tuya.SomeClass", True)) is None


def test_applied_module_comes_from_the_quirk_source_file():
    """quirk_class names the TuyaQuirkBuilder's module for every quirk it builds: the source file decides."""
    import zhaquirks

    def device(source_file):
        entry = SimpleNamespace(source=SimpleNamespace(file=source_file, module="zhaquirks.tuya.builder"))
        zigpy_device = SimpleNamespace(**{manager._REGISTRY_ENTRY: entry})
        return SimpleNamespace(quirk_class="zhaquirks.tuya.builder:(_TZE200_aaaa / TS0601)", quirk_applied=True, device=zigpy_device)

    shipped = Path(zhaquirks.__file__).parent
    assert manager.applied_module(device("/config/custom_zha_quirks/z2m_tuya_a.py")) == "z2m_tuya_a"
    assert manager.applied_module(device(str(shipped / "tuya" / "ts0601_trv.py"))) == "zhaquirks.tuya.ts0601_trv"
    assert manager.applied_module(device(str(shipped / "tuya" / "builder" / "__init__.py"))) == "zhaquirks.tuya.builder"
    # Without a source file: quirk_class as before.
    assert manager.applied_module(device(None)) == "zhaquirks.tuya.builder"


def test_contract_with_zha(tmp_path: Path):
    """The attributes and formats read from ZHA exist as used (no stand-in)."""
    import inspect

    import zigpy.device
    from homeassistant.components.zha import helpers
    from zha.zigbee.device import Device
    from zhaquirks.builder.device import QuirkV2Device

    assert "self.device_proxies" in inspect.getsource(helpers.ZHAGatewayProxy.__init__)
    assert "self.device" in inspect.getsource(helpers.ZHADeviceProxy.__init__)
    from zha.quirks import QUIRK_REGISTRY_ENTRY_ATTR

    assert QUIRK_REGISTRY_ENTRY_ATTR == manager._REGISTRY_ENTRY
    # zha 2.4 moved both into BaseDevice, which Green Power devices share.
    device_property = inspect.getattr_static(Device, "device")
    assert isinstance(device_property, property)
    source = "".join(inspect.getsource(cls) for cls in Device.__mro__ if cls.__module__.startswith("zha."))
    assert "entry = getattr(self._zigpy_device, QUIRK_REGISTRY_ENTRY_ATTR, None)" in source
    assert "self.quirk_applied: bool = entry is not None" in source
    assert 'self.quirk_class: str = f"{entry.source.module}:{entry.source.label}"' in source
    # A quirk's friendly name replaces the manufacturer and model of the zha device (those the device
    # registry shows) only: the zigpy device under it keeps the names quirks match on.
    assert "return self._zigpy_device" in inspect.getsource(device_property.fget)
    assert "self._zigpy_device.manufacturer" in inspect.getsource(Device._resolve_manufacturer)
    assert "friendly_name" in inspect.getsource(QuirkV2Device._resolve_manufacturer)
    assert "friendly_name" in inspect.getsource(QuirkV2Device._resolve_model)
    assert all(isinstance(zigpy.device.Device.__dict__[name], property) for name in ("manufacturer", "model"))
    assert "gateway_proxy" in helpers.HAZHAData.__dataclass_fields__
    # The custom quirks folder: ZHA keeps its YAML config in hass.data and loads the folder named there.
    assert "yaml_config" in helpers.HAZHAData.__dataclass_fields__
    assert "custom_quirks_path=ha_zha_data.yaml_config.get(CONF_CUSTOM_QUIRKS_PATH)" in inspect.getsource(helpers)
    # A custom quirk file's source, as ZHA's registry records it, is the file in the custom
    # folder, for a Tuya quirk too (its module is the builder's): a QuirkBuilder file and a Tuya
    # builder file, frozen copies of generated files.
    script = """
import pathlib, shutil, sys, warnings
warnings.simplefilter("ignore")
import zhaquirks
from zha.quirks import DEVICE_REGISTRY
folder = pathlib.Path(sys.argv[1])
for quirk in sys.argv[2:]:
    shutil.copy(quirk, folder)
zhaquirks.setup(str(folder))
for quirk in sys.argv[2:]:
    stem = pathlib.Path(quirk).stem
    print(stem, any(e.source is not None and pathlib.Path(e.source.file).stem == stem and pathlib.Path(e.source.file).parent == folder for e in DEVICE_REGISTRY))
"""
    (tmp_path / "frozen").mkdir()
    (tmp_path / "custom").mkdir()
    quirks = [tmp_path / "frozen" / "z2m_sonoff_trv_zbt.py", tmp_path / "frozen" / "z2m_tuya_ts0105.py"]
    for path, frozen in zip(quirks, ("z2m_sonoff_trv_zbt_02bf5749.py.txt", "z2m_tuya_ts0105.py.txt"), strict=True):
        path.write_bytes((FROZEN / frozen).read_bytes())
    out = subprocess.run([sys.executable, "-I", "-c", script, str(tmp_path / "custom"), *map(str, quirks)], capture_output=True, text=True, timeout=300, check=False)
    assert out.stdout.strip().splitlines()[-2:] == [f"{q.stem} True" for q in quirks], out.stdout[-500:] + out.stderr[-2000:]


async def test_a_file_that_comes_back_unchanged_is_ours_again(hass: HomeAssistant, zha: Zha, repo_dir: Path, quirks_dir: Path, hass_storage):
    zha.add_device(IEEE_A, "_TZE200_aaaa", "TS0601")
    entry = await setup_entry(hass, repo_dir)
    await apply_list(hass)
    zha.reload({IEEE_A: "z2m_tuya_a:TuyaA"})
    path = quirks_dir / "z2m_tuya_a.py"
    record = entry.runtime_data.data["installed"][str(path)]
    assert record["names"] == TUYA_A_NAMES
    data = path.read_bytes()
    path.unlink()  # a share that is not mounted yet
    await entry.runtime_data.async_refresh()
    # Its record waits aside, names included.
    assert hass_storage[STORAGE_KEY]["data"]["installed"] == {}
    assert hass_storage[STORAGE_KEY]["data"]["forgotten"] == {str(path): record}
    assert our_issues(hass) == {}
    path.write_bytes(data)
    await entry.runtime_data.async_refresh()
    assert hass_storage[STORAGE_KEY]["data"]["installed"] == {str(path): record}
    assert hass_storage[STORAGE_KEY]["data"]["forgotten"] == {}
    assert entry.runtime_data.plan.ours == {"z2m_tuya_a.py"}
    assert our_issues(hass) == {}


async def test_a_dangling_symlink_counts_as_a_file_of_the_user(hass: HomeAssistant, zha: Zha, repo_dir: Path, quirks_dir: Path, tmp_path: Path):
    (quirks_dir / "z2m_tuya_a.py").symlink_to(tmp_path / "nowhere.py")
    zha.add_device(IEEE_A, "_TZE200_aaaa", "TS0601")
    entry = await setup_entry(hass, repo_dir)
    assert offered(hass) == []
    assert entry.runtime_data.plan.users_files == ["z2m_tuya_a.py"]
    assert issue_of(hass, "users_file").translation_placeholders["file"] == "z2m_tuya_a.py"
    assert (quirks_dir / "z2m_tuya_a.py").is_symlink() and not (tmp_path / "nowhere.py").exists()


async def test_a_symlinked_withdrawn_revision_gets_the_notice_of_a_copy(hass: HomeAssistant, zha: Zha, repo_dir: Path, quirks_dir: Path, tmp_path: Path):
    """A link into a checkout of the collection: ZHA imports what it points to, so a withdrawn revision
    there gets its notice. A link to a FIFO is never read (the refresh does not wait on it)."""
    checkout = tmp_path / "checkout"
    checkout.mkdir()
    (checkout / "z2m_tuya_a.py").write_bytes(GENERATED)
    (quirks_dir / "z2m_tuya_a.py").symlink_to(checkout / "z2m_tuya_a.py")
    revision = content.effective_revision(GENERATED)
    os.mkfifo(tmp_path / "pipe")
    (quirks_dir / "z2m_mine.py").symlink_to(tmp_path / "pipe")
    zha.add_device(IEEE_A, "_TZE200_aaaa", "TS0601")
    zha.apply_quirks({IEEE_A: "z2m_tuya_a:TuyaA"})
    (repo_dir / "data").mkdir(exist_ok=True)
    (repo_dir / "data" / "withdrawn.toml").write_text(f'[[withdrawn]]\nfile = "z2m_tuya_a.py"\nrevision = "{revision}"\nreason = "Drives the valve fully open."\n')
    entry = await setup_entry(hass, repo_dir)
    assert issue_of(hass, "withdrawn_copy", "z2m_tuya_a.py").translation_placeholders["revision"] == revision
    assert entry.runtime_data.plan.ours == frozenset()
    assert (quirks_dir / "z2m_tuya_a.py").is_symlink() and (checkout / "z2m_tuya_a.py").read_bytes() == GENERATED


def test_a_link_target_is_read_only_as_a_regular_file(tmp_path: Path):
    # Generated bytes one past the limit: a revision taken from them would show a read past it.
    (tmp_path / "big.py").write_bytes(GENERATED + b"#" * (const.MAX_DOWNLOAD + 1 - len(GENERATED)))
    at_limit = GENERATED + b"#" * (const.MAX_DOWNLOAD - len(GENERATED))
    (tmp_path / "limit.py").write_bytes(at_limit)
    (tmp_path / "link_limit").symlink_to(tmp_path / "limit.py")
    assert files.present_state(str(tmp_path / "link_limit")) == (files.UNREADABLE, content.effective_revision(at_limit))
    os.mkfifo(tmp_path / "pipe")
    (tmp_path / "dir").mkdir()
    for name in ("big.py", "pipe", "dir", "nowhere"):
        (tmp_path / f"link_{name}").symlink_to(tmp_path / name)
        assert files.present_state(str(tmp_path / f"link_{name}")) == (files.UNREADABLE, None)
    (tmp_path / "copy.py").write_bytes(GENERATED)
    (tmp_path / "link_copy").symlink_to(tmp_path / "copy.py")
    assert files.present_state(str(tmp_path / "link_copy")) == (files.UNREADABLE, content.effective_revision(GENERATED))


async def test_a_symlink_under_a_recorded_name_is_left_alone(hass: HomeAssistant, zha: Zha, repo_dir: Path, quirks_dir: Path, tmp_path: Path, hass_storage):
    """A link is never ours, even to the very bytes the record names: neither it nor what it points
    to is written or deleted. Its record waits until the name is a plain file again."""
    zha.add_device(IEEE_A, "_TZE200_aaaa", "TS0601")
    entry = await setup_entry(hass, repo_dir)
    await apply_list(hass)
    zha.reload({IEEE_A: "z2m_tuya_a:TuyaA"})
    path, target = quirks_dir / "z2m_tuya_a.py", tmp_path / "elsewhere.py"
    record = entry.runtime_data.data["installed"][str(path)]
    path.rename(target)
    path.symlink_to(target)
    await entry.runtime_data.async_refresh()
    assert entry.runtime_data.summary()["installed"][str(path)]["state"] == "cannot be read, left alone"
    # A newer version brings no update for it, nor a notice.
    write_repo(repo_dir, version=2)
    REPOS[repo_dir].publish()
    await entry.runtime_data.async_check()
    assert our_issues(hass) == {}
    assert path.is_symlink() and target.read_bytes() == quirk_text("tuya_a", 1)
    assert hass_storage[STORAGE_KEY]["data"]["installed"] == {str(path): record}
    # A plain file again: ours, the update comes.
    path.unlink()
    target.rename(path)
    await entry.runtime_data.async_refresh()
    assert listed(hass) == {**NOTHING, "update": ["z2m_tuya_a.py"]}


async def test_stale_temporary_files_are_cleaned_at_setup(hass: HomeAssistant, zha: Zha, repo_dir: Path, quirks_dir: Path):
    (quirks_dir / f"{files.TMP_PREFIX}abcd{files.TMP_SUFFIX}").write_text("half")
    (quirks_dir / ".someone_elses.tmp").write_text("not ours")
    await setup_entry(hass, repo_dir)
    assert [p.name for p in quirks_dir.iterdir()] == [".someone_elses.tmp"]


async def test_pending_changes_end_with_a_restart_of_home_assistant(hass: HomeAssistant, zha: Zha, repo_dir: Path):
    zha.add_device(IEEE_A, "_TZE200_aaaa", "TS0601")
    entry = await setup_entry(hass, repo_dir)
    await apply_list(hass)
    assert entry.runtime_data.summary()["pending_zha_reload"] == ["z2m_tuya_a.py: installed"]
    # An entry reload in the same run keeps what is pending.
    with published(repo_dir):
        await hass.config_entries.async_reload(entry.entry_id)
        await hass.async_block_till_done(wait_background_tasks=True)
    assert issue_of(hass, "reload")
    # A new start of Home Assistant loaded the folder: nothing pending, no reminder.
    await hass.config_entries.async_unload(entry.entry_id)
    with published(repo_dir), patch.object(integration.manager, "_RUN", uuid.uuid4().hex):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done(wait_background_tasks=True)
    assert issues_of(hass, "reload") == []
    assert entry.runtime_data.summary()["pending_zha_reload"] == []


def test_delete_drops_the_cached_bytecode_of_that_file_only(tmp_path: Path):
    path = tmp_path / "z2m_tuya_a.py"
    path.write_bytes(quirk_text("tuya_a"))
    cache = tmp_path / "__pycache__"
    cache.mkdir()
    for name in ("z2m_tuya_a.cpython-314.pyc", "z2m_tuya_a_aaaa.cpython-314.pyc", "mine.cpython-314.pyc"):
        (cache / name).write_bytes(b"")
    assert files.delete(str(path), content.sha256(quirk_text("tuya_a")))
    assert sorted(p.name for p in cache.iterdir()) == ["mine.cpython-314.pyc", "z2m_tuya_a_aaaa.cpython-314.pyc"]


# Holds: "Apply all" carries out only the list for the folder as it is now.


async def test_a_second_dialog_on_an_applied_list_finds_its_change_waiting(hass: HomeAssistant, zha: Zha, repo_dir: Path, quirks_dir: Path, hass_storage):
    """Two dialogs open on one list: the second finds the change of the first waiting for ZHA (here
    while ZHA reloads), the file keeps its record."""
    zha.add_device(IEEE_A, "_TZE200_aaaa", "TS0601")
    await setup_entry(hass, repo_dir)
    issue = issue_of(hass, "changes")
    first, second = await start_fix(hass, issue), await start_fix(hass, issue)
    first = await continue_fix(hass, first, {"next_step_id": "apply"})
    assert first["reason"] == "done", first
    zha.start_reload()
    second = await continue_fix(hass, second, {"next_step_id": "apply"})
    # Held for the change of the first dialog (ZHA's not being loaded comes second).
    assert second["type"] is FlowResultType.ABORT and second["reason"] == "held_pending", second
    assert (quirks_dir / "z2m_tuya_a.py").read_bytes() == quirk_text("tuya_a")
    record = hass_storage[STORAGE_KEY]["data"]["installed"][str(quirks_dir / "z2m_tuya_a.py")]
    assert record["sha256"] == content.sha256(quirk_text("tuya_a"))


async def test_while_zha_is_not_loaded_a_newer_list_waits_for_it(hass: HomeAssistant, zha: Zha, repo_dir: Path, quirks_dir: Path):
    """While ZHA is not loaded no list is applied, a newer state changes nothing at once; once ZHA
    is back the list for that state comes as a new issue."""
    zha.add_device(IEEE_A, "_TZE200_aaaa", "TS0601")
    entry = await setup_entry(hass, repo_dir)
    issue = issue_of(hass, "changes")
    flow = await start_fix(hass, issue)
    zha.start_reload()
    write_repo(repo_dir, version=2)
    REPOS[repo_dir].publish()
    await entry.runtime_data.async_check()
    assert entry.runtime_data.plan.held == integration.plan.ZHA_UNKNOWN
    assert issue_of(hass, "changes").issue_id == issue.issue_id
    flow = await continue_fix(hass, flow, {"next_step_id": "apply"})
    assert flow["type"] is FlowResultType.ABORT and flow["reason"] == "held_zha_unknown", flow
    assert list(quirks_dir.iterdir()) == []
    # ZHA is back: the list for version 2 comes as a new issue.
    zha.finish_reload()
    await entry.runtime_data.async_refresh()
    assert listed(hass) == {**NOTHING, "install": ["z2m_tuya_a.py"]}
    assert issue_of(hass, "changes").issue_id != issue.issue_id


async def test_without_a_content_state_the_list_shown_changes_nothing(hass: HomeAssistant, zha: Zha, repo: Repo, repo_dir: Path, quirks_dir: Path):
    device = zha.add_device(IEEE_A, "_TZE200_aaaa", "TS0601")
    entry = await setup_entry(hass, repo_dir)
    await apply_list(hass)
    zha.reload({IEEE_A: "z2m_tuya_a:TuyaA"})
    zha.remove_device(device)
    await entry.runtime_data.async_refresh()
    assert listed(hass) == {**NOTHING, "remove": ["z2m_tuya_a.py"]}
    issue = issue_of(hass, "changes")
    flow = await start_fix(hass, issue)
    # The tag in use is made anew on another commit, for a guard this release does not have.
    repo.moved[1] = "e" * 40
    tag = tag_files(repo_dir)
    tag["content.json"] = content_json("f" * 64)
    repo.tags[1] = tag
    await entry.runtime_data.async_check()
    assert entry.runtime_data.state is None
    assert issue_of(hass, "changes").issue_id == issue.issue_id
    flow = await continue_fix(hass, flow, {"next_step_id": "apply"})
    assert flow["type"] is FlowResultType.ABORT and flow["reason"] == "held_no_content", flow
    assert (quirks_dir / "z2m_tuya_a.py").read_bytes() == quirk_text("tuya_a")


async def test_a_folder_that_cannot_be_read_holds_the_list_shown(hass: HomeAssistant, zha: Zha, repo_dir: Path, quirks_dir: Path):
    zha.add_device(IEEE_A, "_TZE200_aaaa", "TS0601")
    entry = await setup_entry(hass, repo_dir)
    flow = await start_fix(hass, issue_of(hass, "changes"))
    quirks_dir.chmod(0o300)  # cannot be listed, a file in it could still be written
    try:
        await entry.runtime_data.async_refresh()
        assert issue_of(hass, "folder_unreadable")
        flow = await continue_fix(hass, flow, {"next_step_id": "apply"})
    finally:
        quirks_dir.chmod(0o755)
    assert flow["type"] is FlowResultType.ABORT and flow["reason"] == "held_unreadable_folder", flow
    assert list(quirks_dir.iterdir()) == []


async def test_a_missing_custom_quirks_path_keeps_the_list_put_aside(hass: HomeAssistant, zha: Zha, repo_dir: Path, quirks_dir: Path):
    zha.add_device(IEEE_A, "_TZE200_aaaa", "TS0601")
    entry = await setup_entry(hass, repo_dir)
    issue = issue_of(hass, "changes")
    flow = await continue_fix(hass, await start_fix(hass, issue), {"next_step_id": "not_now"})
    assert flow["reason"] == "not_now" and our_issues(hass) == {}
    # The path is taken out of ZHA's YAML (and a restart later), then put back.
    zha.data.yaml_config.pop("custom_quirks_path")
    await entry.runtime_data.async_refresh()
    assert list(our_issues(hass)) == ["missing_quirks_path"]
    assert entry.runtime_data.plan.held == integration.plan.NO_FOLDER
    kept = ir.async_get(hass).async_get_issue(DOMAIN, issue.issue_id)
    assert kept.dismissed_version is not None
    # Opened from the ignored repairs, its dialog says why it cannot apply now.
    flow = await start_fix(hass, kept)
    assert flow["type"] is FlowResultType.ABORT and flow["reason"] == "held_no_folder", flow
    zha.data.yaml_config["custom_quirks_path"] = str(quirks_dir)
    await entry.runtime_data.async_refresh()
    assert our_issues(hass) == {}


async def test_a_withdrawal_is_noticed_while_zha_cannot_be_read(hass: HomeAssistant, zha: Zha, repo_dir: Path, quirks_dir: Path):
    """After a restart, ZHA is loaded but what it applies cannot be read (a release renamed what the
    integration reads): no list can come, the notice of a withdrawn revision in use does."""
    zha.add_device(IEEE_A, "_TZE200_aaaa", "TS0601")
    entry = await setup_entry(hass, repo_dir)
    await apply_list(hass)
    zha.reload({IEEE_A: "z2m_tuya_a:TuyaA"})
    zha.data.gateway_proxy = object()
    with published(repo_dir), patch.object(integration.manager, "_RUN", uuid.uuid4().hex):
        await hass.config_entries.async_reload(entry.entry_id)
        await hass.async_block_till_done(wait_background_tasks=True)
    manager_ = entry.runtime_data
    assert manager_.zha_state == manager.ZHA_UNREADABLE
    (repo_dir / "data").mkdir(exist_ok=True)
    (repo_dir / "data" / "withdrawn.toml").write_text(f'[[withdrawn]]\nfile = "z2m_tuya_a.py"\nrevision = "{quirk_revision("tuya_a")}"\nreason = "Drives the valve fully open."\n')
    REPOS[repo_dir].publish()
    await manager_.async_check()
    assert [i.translation_key for i in our_issues(hass).values()] == ["withdrawn_installed"]
    assert manager_.plan.held == integration.plan.ZHA_UNKNOWN
    assert (quirks_dir / "z2m_tuya_a.py").read_bytes() == quirk_text("tuya_a")


def _slow(real):
    """real, run in its thread only once the test lets it go on."""
    started, go_on = threading.Event(), threading.Event()

    def slow(*args):
        started.set()
        assert go_on.wait(10)
        return real(*args)

    return slow, started, go_on


async def test_a_list_goes_on_when_the_browser_goes_away(hass: HomeAssistant, zha: Zha, repo_dir: Path, quirks_dir: Path, hass_storage):
    """Home Assistant cancels a dialog's request when the browser goes away: the list is carried out
    all the same, the reload of ZHA is left to the reminder."""
    zha.add_device(IEEE_A, "_TZE200_aaaa", "TS0601")
    entry = await setup_entry(hass, repo_dir)
    await apply_list(hass)
    zha.reload({IEEE_A: "z2m_tuya_a:TuyaA"})
    write_repo(repo_dir, version=2)
    REPOS[repo_dir].publish()
    await entry.runtime_data.async_check()
    flow = await start_fix(hass, issue_of(hass, "changes"))
    slow, started, go_on = _slow(files.replace)
    reloads = zha.reloads
    with patch.object(files, "replace", slow):
        request = hass.async_create_task(continue_fix(hass, flow, {"next_step_id": "apply"}))
        assert await hass.async_add_executor_job(started.wait, 10)
        request.cancel()
        go_on.set()
        with pytest.raises(asyncio.CancelledError):
            await request
        await hass.async_block_till_done()
    assert (quirks_dir / "z2m_tuya_a.py").read_bytes() == quirk_text("tuya_a", 2)
    record = hass_storage[STORAGE_KEY]["data"]["installed"][str(quirks_dir / "z2m_tuya_a.py")]
    assert record["sha256"] == content.sha256(quirk_text("tuya_a", 2)) and "previous" not in record
    assert zha.reloads == reloads
    assert [i.translation_key for i in our_issues(hass).values()] == ["reload"]


async def test_a_dialog_ends_the_hold_of_a_folder_readable_again(hass: HomeAssistant, zha: Zha, repo_dir: Path, quirks_dir: Path):
    """No event tells that the folder can be read again: the dialog plans anew before it decides."""
    zha.add_device(IEEE_A, "_TZE200_aaaa", "TS0601")
    entry = await setup_entry(hass, repo_dir)
    issue = issue_of(hass, "changes")
    quirks_dir.chmod(0o300)
    try:
        await entry.runtime_data.async_refresh()
    finally:
        quirks_dir.chmod(0o755)
    assert entry.runtime_data.plan.held == integration.plan.UNREADABLE_FOLDER and issue_of(hass, "folder_unreadable")
    flow = await start_fix(hass, issue)
    assert flow["type"] is FlowResultType.MENU, flow
    assert issues_of(hass, "folder_unreadable") == []
    flow = await continue_fix(hass, flow, {"next_step_id": "apply"})
    assert flow["type"] is FlowResultType.ABORT and flow["reason"] == "done", flow
    assert (quirks_dir / "z2m_tuya_a.py").read_bytes() == quirk_text("tuya_a")


async def test_the_timer_ends_the_hold_of_a_folder_readable_again(hass: HomeAssistant, zha: Zha, repo_dir: Path, quirks_dir: Path):
    zha.add_device(IEEE_A, "_TZE200_aaaa", "TS0601")
    entry = await setup_entry(hass, repo_dir)
    # The refresh the setup's device events scheduled runs first: only the timer is left.
    await wait_for_refresh(hass)
    quirks_dir.chmod(0o300)
    try:
        await entry.runtime_data.async_refresh()
    finally:
        quirks_dir.chmod(0o755)
    assert issue_of(hass, "folder_unreadable")
    async_fire_time_changed(hass, dt_util.utcnow() + const.RETRY_INTERVAL)
    await hass.async_block_till_done(wait_background_tasks=True)
    assert issues_of(hass, "folder_unreadable") == []
    assert entry.runtime_data.plan.held is None and listed(hass) == {**NOTHING, "install": ["z2m_tuya_a.py"]}


async def test_the_timer_ends_the_hold_after_a_dialog_that_went_away(hass: HomeAssistant, zha: Zha, repo_dir: Path, quirks_dir: Path):
    """A dialog's request cancelled while its refresh reads the folder leaves the old hold in place:
    the timer still ends it, it decides by the held list."""
    zha.add_device(IEEE_A, "_TZE200_aaaa", "TS0601")
    entry = await setup_entry(hass, repo_dir)
    manager_ = entry.runtime_data
    issue = issue_of(hass, "changes")
    await wait_for_refresh(hass)
    quirks_dir.chmod(0o300)
    try:
        await manager_.async_refresh()
    finally:
        quirks_dir.chmod(0o755)
    assert manager_.plan.held == integration.plan.UNREADABLE_FOLDER
    slow, started, go_on = _slow(manager_._read_disk)
    with patch.object(manager_, "_read_disk", slow):
        request = hass.async_create_task(start_fix(hass, issue))
        assert await hass.async_add_executor_job(started.wait, 10)
        request.cancel()
        go_on.set()
        with pytest.raises(asyncio.CancelledError):
            await request
        await hass.async_block_till_done()
    assert manager_.plan.held == integration.plan.UNREADABLE_FOLDER
    async_fire_time_changed(hass, dt_util.utcnow() + const.RETRY_INTERVAL)
    await hass.async_block_till_done(wait_background_tasks=True)
    assert manager_.plan.held is None and issues_of(hass, "folder_unreadable") == []
    assert listed(hass) == {**NOTHING, "install": ["z2m_tuya_a.py"]}
