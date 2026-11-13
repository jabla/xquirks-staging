"""The change list (one repair issue for every install, update and removal) with its fix flow, the
reload reminder and the notices: nothing is written without the confirmation of the whole list."""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from unittest.mock import patch

import pytest
from homeassistant.config_entries import ConfigEntryDisabler
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import issue_registry as ir
from homeassistant.util.async_ import run_callback_threadsafe

from . import integration
from .integration import DOMAIN, const, content

sha256 = content.sha256
STORAGE_KEY = const.STORAGE_KEY

from .conftest import (
    MANIFEST,
    NO_QUIRK,
    UPSTREAM_PR,
    Zha,
    apply_list,
    continue_fix,
    issue_of,
    issues_of,
    listed,
    manager_of,
    offered,
    our_issues,
    published,
    quirk_revision,
    quirk_text,
    setup_entry,
    start_fix,
    write_repo,
)

IEEE_A = "00:11:22:33:44:55:66:01"
IEEE_B = "00:11:22:33:44:55:66:02"
IEEE_C = "00:11:22:33:44:55:66:03"

NOTHING = {"remove": [], "update": [], "install": []}


async def restart_with(hass: HomeAssistant, entry, repo_dir: Path) -> None:
    """A restart of Home Assistant, with what repo_dir holds now published as the next content tag."""
    await hass.config_entries.async_unload(entry.entry_id)
    with published(repo_dir), patch.object(integration.manager, "_RUN", uuid.uuid4().hex):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done(wait_background_tasks=True)


async def test_missing_custom_quirks_path_only_explains(hass: HomeAssistant, zha: Zha, repo_dir: Path, quirks_dir: Path):
    zha.data.yaml_config.pop("custom_quirks_path")
    zha.add_device(IEEE_A, "_TZE200_aaaa", "TS0601")
    entry = await setup_entry(hass, repo_dir)
    assert list(our_issues(hass)) == ["missing_quirks_path"]
    assert not our_issues(hass)["missing_quirks_path"].is_fixable
    assert entry.runtime_data.plan.install == []
    # Configured later (ZHA reads it on its next start): the issue goes, the list comes.
    zha.data.yaml_config["custom_quirks_path"] = str(quirks_dir)
    await entry.runtime_data.async_refresh()
    assert [i.translation_key for i in our_issues(hass).values()] == ["changes"]


async def test_one_list_for_every_change_nothing_written_before_the_confirmation(hass: HomeAssistant, zha: Zha, repo_dir: Path, quirks_dir: Path, hass_storage):
    zha.add_device(IEEE_A, "_TZE200_aaaa", "TS0601", "Hallway radar")
    zha.add_device(IEEE_B, "Anyone", "B-1", "Plug")
    await setup_entry(hass, repo_dir)

    assert listed(hass) == {**NOTHING, "install": ["z2m_acme_b.py", "z2m_tuya_a.py"]}
    issue = issue_of(hass, "changes")
    assert issue.is_fixable and issue.severity is ir.IssueSeverity.WARNING
    assert issue.translation_placeholders == {"count": "2"}
    assert list(quirks_dir.iterdir()) == []

    flow = await start_fix(hass, issue)
    assert flow["type"] is FlowResultType.MENU and flow["menu_options"] == ["apply", "not_now"]
    # The dialog names each change with its devices and the folder.
    changes = flow["description_placeholders"]["changes"]
    assert "**Install** `z2m_tuya_a.py` (Tuya A) for Hallway radar." in changes
    assert "**Install** `z2m_acme_b.py` (Acme B-1) for Plug." in changes
    assert flow["description_placeholders"]["folder"] == str(quirks_dir)
    # Opening the dialog decides nothing.
    assert list(quirks_dir.iterdir()) == [] and hass_storage.get(STORAGE_KEY) is None

    flow = await continue_fix(hass, flow, {"next_step_id": "apply"})
    assert flow["type"] is FlowResultType.ABORT and flow["reason"] == "done", flow
    assert flow["description_placeholders"]["done"] == "- `z2m_acme_b.py`: installed\n- `z2m_tuya_a.py`: installed"
    # Both files at once, then one reload of ZHA; no reminder while it reloads, no list left.
    assert sorted(p.name for p in quirks_dir.iterdir()) == ["z2m_acme_b.py", "z2m_tuya_a.py"]
    assert (quirks_dir / "z2m_tuya_a.py").read_bytes() == quirk_text("tuya_a")
    assert zha.reloads == 1
    assert our_issues(hass) == {}

    stored = hass_storage[STORAGE_KEY]["data"]["installed"]
    assert stored[str(quirks_dir / "z2m_tuya_a.py")] == {
        "sha256": sha256(quirk_text("tuya_a")),
        "revision": quirk_revision("tuya_a"),
        "names": {"fingerprints": [["_TZE200_aaaa", "TS0601"]], "claimed_elsewhere": []},
    }
    assert stored[str(quirks_dir / "z2m_acme_b.py")]["names"] == {"fingerprints": [[None, "B-1"]], "claimed_elsewhere": [["Other", "B-1"]]}


async def test_the_list_waits_for_zha_to_load_what_it_wrote(hass: HomeAssistant, zha: Zha, repo_dir: Path, quirks_dir: Path):
    zha.add_device(IEEE_A, "_TZE200_aaaa", "TS0601")
    entry = await setup_entry(hass, repo_dir)
    await apply_list(hass)
    # A new device before ZHA reloaded: ZHA's reports are older than the folder, the list waits.
    zha.add_device(IEEE_B, "Anyone", "B-1")
    await entry.runtime_data.async_refresh()
    assert entry.runtime_data.plan.held == integration.plan.PENDING and our_issues(hass) == {}
    # ZHA is back and applies the file: the list comes for the new device.
    zha.reload({IEEE_A: "z2m_tuya_a:TuyaA"})
    await entry.runtime_data.async_refresh()
    assert listed(hass) == {**NOTHING, "install": ["z2m_acme_b.py"]}
    assert entry.runtime_data.summary()["pending_zha_reload"] == []


async def test_while_zha_is_not_loaded_the_list_waits_for_it(hass: HomeAssistant, zha: Zha, repo_dir: Path, quirks_dir: Path):
    """What ZHA applies is unknown while it is not loaded: no list is applied, the one shown stays
    and can be applied once ZHA is back."""
    zha.add_device(IEEE_A, "_TZE200_aaaa", "TS0601")
    entry = await setup_entry(hass, repo_dir)
    issue = issue_of(hass, "changes")
    flow = await start_fix(hass, issue)
    zha.start_reload()
    flow = await continue_fix(hass, flow, {"next_step_id": "apply"})
    assert flow["type"] is FlowResultType.ABORT and flow["reason"] == "held_zha_unknown", flow
    assert list(quirks_dir.iterdir()) == [] and issue_of(hass, "changes").issue_id == issue.issue_id
    zha.finish_reload()
    await entry.runtime_data.async_refresh()
    await apply_list(hass)
    assert (quirks_dir / "z2m_tuya_a.py").read_bytes() == quirk_text("tuya_a")


async def test_zha_unloading_during_the_apply_leaves_the_change_to_its_start(hass: HomeAssistant, zha: Zha, repo_dir: Path, quirks_dir: Path):
    zha.add_device(IEEE_A, "_TZE200_aaaa", "TS0601")
    entry = await setup_entry(hass, repo_dir)
    flow = await start_fix(hass, issue_of(hass, "changes"))
    write_new = integration.files.write_new

    def unload_then_write(path, data):
        # ZHA unloads while the file is written (a reload of ZHA started elsewhere). The write waits
        # until it has: a job that ends before the loop awaits it does not hand the loop a turn, so
        # the apply could run on to the reload before a callback scheduled here.
        run_callback_threadsafe(hass.loop, zha.start_reload).result()
        return write_new(path, data)

    with patch.object(integration.files, "write_new", unload_then_write):
        flow = await continue_fix(hass, flow, {"next_step_id": "apply"})
    assert flow["type"] is FlowResultType.ABORT and flow["reason"] == "done_zha_not_loaded", flow
    assert zha.reloads == 0
    assert (quirks_dir / "z2m_tuya_a.py").exists()
    assert entry.runtime_data.summary()["pending_zha_reload"] == ["z2m_tuya_a.py: installed"]
    # ZHA starts and loads the folder: done.
    zha.apply_quirks({IEEE_A: "z2m_tuya_a:TuyaA"})
    zha.finish_reload()
    await entry.runtime_data.async_refresh()
    assert our_issues(hass) == {}
    assert entry.runtime_data.summary()["pending_zha_reload"] == []


async def test_a_change_written_while_zha_sets_up_waits_for_the_next_load(hass: HomeAssistant, zha: Zha, repo_dir: Path, quirks_dir: Path):
    """ZHA loads the custom quirks folder at the start of its setup: a file written while that setup
    runs is not loaded by it, the change stays pending with its reminder."""
    zha.add_device(IEEE_A, "_TZE200_aaaa", "TS0601")
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
    assert flow["type"] is FlowResultType.ABORT and flow["reason"] == "done_zha_not_loaded", flow
    assert (quirks_dir / "z2m_tuya_a.py").exists()
    zha.finish_reload()
    await entry.runtime_data.async_refresh()
    assert entry.runtime_data.summary()["pending_zha_reload"] == ["z2m_tuya_a.py: installed"]
    assert issue_of(hass, "reload")
    # The next load of ZHA has it.
    zha.reload({IEEE_A: "z2m_tuya_a:TuyaA"})
    await entry.runtime_data.async_refresh()
    assert entry.runtime_data.summary()["pending_zha_reload"] == []
    assert our_issues(hass) == {}


async def test_reminder_when_the_reload_is_not_known_to_have_happened(hass: HomeAssistant, zha: Zha, repo_dir: Path):
    """A reload of this integration forgets that ZHA was asked to reload: the reminder is the net."""
    zha.add_device(IEEE_A, "_TZE200_aaaa", "TS0601")
    entry = await setup_entry(hass, repo_dir)
    await apply_list(hass)
    assert issues_of(hass, "reload") == []
    with published(repo_dir):
        await hass.config_entries.async_reload(entry.entry_id)
        await hass.async_block_till_done(wait_background_tasks=True)
    pending = issue_of(hass, "reload")
    assert pending.translation_placeholders == {"count": "1"}
    flow = await start_fix(hass, pending)
    assert "z2m_tuya_a.py" in flow["description_placeholders"]["changes"]
    flow = await continue_fix(hass, flow, {"next_step_id": "apply"})
    assert flow["type"] is FlowResultType.CREATE_ENTRY
    assert zha.reloads == 2


async def test_not_now_puts_this_list_aside_and_another_list_comes_back(hass: HomeAssistant, zha: Zha, repo_dir: Path, quirks_dir: Path):
    zha.add_device(IEEE_A, "_TZE200_aaaa", "TS0601")
    entry = await setup_entry(hass, repo_dir)
    issue = issue_of(hass, "changes")
    flow = await continue_fix(hass, await start_fix(hass, issue), {"next_step_id": "not_now"})
    assert flow["type"] is FlowResultType.ABORT and flow["reason"] == "not_now"
    await entry.runtime_data.async_refresh()
    # Home Assistant's own ignore: the list waits under "Show ignored repairs", nothing is written.
    assert our_issues(hass) == {} and list(quirks_dir.iterdir()) == []
    assert ir.async_get(hass).async_get_issue(DOMAIN, issue.issue_id).dismissed_version
    # The list put aside can still be applied from there.
    flow = await start_fix(hass, ir.async_get(hass).async_get_issue(DOMAIN, issue.issue_id))
    assert flow["type"] is FlowResultType.MENU
    # A second device: another list, a new issue.
    zha.add_device(IEEE_B, "Anyone", "B-1")
    await entry.runtime_data.async_refresh()
    assert listed(hass) == {**NOTHING, "install": ["z2m_acme_b.py", "z2m_tuya_a.py"]}
    assert issue_of(hass, "changes").issue_id != issue.issue_id


async def test_not_now_on_a_list_replaced_while_the_dialog_was_open_changes_nothing(hass: HomeAssistant, zha: Zha, repo_dir: Path, quirks_dir: Path):
    zha.add_device(IEEE_A, "_TZE200_aaaa", "TS0601")
    entry = await setup_entry(hass, repo_dir)
    issue = issue_of(hass, "changes")
    flow = await start_fix(hass, issue)
    zha.add_device(IEEE_B, "Anyone", "B-1")
    await entry.runtime_data.async_refresh()
    assert issue_of(hass, "changes").issue_id != issue.issue_id
    flow = await continue_fix(hass, flow, {"next_step_id": "not_now"})
    assert flow["type"] is FlowResultType.ABORT and flow["reason"] == "stale", flow
    assert issue_of(hass, "changes").dismissed_version is None and list(quirks_dir.iterdir()) == []


async def test_not_now_on_a_reminder_gone_while_the_dialog_was_open(hass: HomeAssistant, zha: Zha, repo_dir: Path):
    zha.add_device(IEEE_A, "_TZE200_aaaa", "TS0601")
    entry = await setup_entry(hass, repo_dir)
    await apply_list(hass)
    with published(repo_dir):
        await hass.config_entries.async_reload(entry.entry_id)
        await hass.async_block_till_done(wait_background_tasks=True)
    flow = await start_fix(hass, issue_of(hass, "reload"))
    # ZHA reloads while the dialog is open: the reminder goes.
    zha.reload({IEEE_A: "z2m_tuya_a:TuyaA"})
    await entry.runtime_data.async_refresh()
    assert issues_of(hass, "reload") == []
    flow = await continue_fix(hass, flow, {"next_step_id": "not_now"})
    assert flow["type"] is FlowResultType.ABORT and flow["reason"] == "nothing_to_do", flow


async def test_a_list_that_changed_while_the_dialog_was_open_is_not_applied(hass: HomeAssistant, zha: Zha, repo_dir: Path, quirks_dir: Path):
    zha.add_device(IEEE_A, "_TZE200_aaaa", "TS0601")
    entry = await setup_entry(hass, repo_dir)
    flow = await start_fix(hass, issue_of(hass, "changes"))
    zha.add_device(IEEE_B, "Anyone", "B-1")
    flow = await continue_fix(hass, flow, {"next_step_id": "apply"})
    assert flow["type"] is FlowResultType.ABORT and flow["reason"] == "stale", flow
    assert list(quirks_dir.iterdir()) == [] and zha.reloads == 0
    # The new list is there.
    assert offered(hass) == ["z2m_acme_b.py", "z2m_tuya_a.py"]
    assert entry.runtime_data.summary()["pending_zha_reload"] == []


async def test_a_held_list_says_why(hass: HomeAssistant, zha: Zha, repo_dir: Path, quirks_dir: Path):
    zha.add_device(IEEE_A, "_TZE200_aaaa", "TS0601")
    entry = await setup_entry(hass, repo_dir)
    issue = issue_of(hass, "changes")
    entry.runtime_data.data["pending"]["changes"] = [{"file": "z2m_other.py", "change": "installed"}]
    await entry.runtime_data.async_refresh()
    flow = await start_fix(hass, issue)
    assert flow["type"] is FlowResultType.ABORT and flow["reason"] == "held_pending"
    assert list(quirks_dir.iterdir()) == []


def test_each_hold_has_a_text_of_its_own():
    """A held list aborts with a whole text per reason that names this reason (no English part in
    a translated sentence)."""
    plans = integration.plan
    # Per reason a phrase (English, German) that only its own text has.
    phrases = {
        plans.PENDING: ("waits for ZHA to load", "wartet darauf, dass ZHA"),
        plans.UNCHECKED: ("could not be downloaded and checked", "heruntergeladen und geprüft"),
        plans.ZHA_UNKNOWN: ("ZHA is not loaded", "ZHA ist nicht geladen"),
        plans.NO_CONTENT: ("no quirk list", "keine Quirk-Liste"),
        plans.NO_FOLDER: ("ZHA has no custom quirks folder", "ZHA hat keinen Ordner"),
        plans.UNREADABLE_FOLDER: ("cannot be read", "nicht lesbar"),
    }
    folder = Path(__file__).resolve().parents[1] / "custom_components" / DOMAIN / "translations"
    for index, language in enumerate(("en", "de")):
        abort = json.loads((folder / f"{language}.json").read_text())["issues"]["changes"]["fix_flow"]["abort"]
        texts = {key.removeprefix("held_"): text for key, text in abort.items() if key.startswith("held_")}
        assert texts.keys() == phrases.keys(), language
        assert not [text for text in texts.values() if "{" in text], language
        for reason, phrase in phrases.items():
            assert [held for held, text in texts.items() if phrase[index] in text] == [reason], (language, reason)


async def test_a_failed_step_undoes_the_steps_before_it(hass: HomeAssistant, zha: Zha, repo_dir: Path, quirks_dir: Path, hass_storage):
    zha.add_device(IEEE_A, "_TZE200_aaaa", "TS0601")
    zha.add_device(IEEE_B, "Anyone", "B-1")
    entry = await setup_entry(hass, repo_dir)
    issue = issue_of(hass, "changes")
    write_new = integration.files.write_new

    def failing(path: str, data: bytes) -> None:
        if path.endswith("z2m_tuya_a.py"):
            raise OSError(28, "No space left on device")
        write_new(path, data)

    with patch.object(integration.files, "write_new", failing):
        flow = await start_fix(hass, issue)
        flow = await continue_fix(hass, flow, {"next_step_id": "apply"})
    assert flow["type"] is FlowResultType.ABORT and flow["reason"] == "failed", flow
    assert flow["description_placeholders"]["failed"] == "`z2m_tuya_a.py`: No space left on device"
    # z2m_acme_b.py was installed first: taken back, with its record; ZHA is not reloaded.
    assert list(quirks_dir.iterdir()) == []
    assert hass_storage[STORAGE_KEY]["data"]["installed"] == {}
    assert entry.runtime_data.data["pending"]["changes"] == [] and zha.reloads == 0
    # The list stays: the next try works.
    assert issue_of(hass, "changes").issue_id == issue.issue_id
    await apply_list(hass)
    assert sorted(p.name for p in quirks_dir.iterdir()) == ["z2m_acme_b.py", "z2m_tuya_a.py"]


async def test_an_undo_that_fails_too_reports_what_is_left_and_reloads_zha(hass: HomeAssistant, zha: Zha, repo_dir: Path, quirks_dir: Path):
    zha.add_device(IEEE_A, "_TZE200_aaaa", "TS0601")
    zha.add_device(IEEE_B, "Anyone", "B-1")
    entry = await setup_entry(hass, repo_dir)
    write_new = integration.files.write_new

    def failing(path: str, data: bytes) -> None:
        if path.endswith("z2m_tuya_a.py"):
            raise OSError(5, "Input/output error")
        write_new(path, data)

    def stuck(path: str, expected: str) -> bool:
        raise OSError(13, "Permission denied")

    with patch.object(integration.files, "write_new", failing), patch.object(integration.files, "delete", stuck):
        flow = await start_fix(hass, issue_of(hass, "changes"))
        flow = await continue_fix(hass, flow, {"next_step_id": "apply"})
    assert flow["type"] is FlowResultType.ABORT and flow["reason"] == "failed_partly", flow
    assert flow["description_placeholders"]["left"] == "- `z2m_acme_b.py`: installed"
    assert zha.reloads == 1
    # What is on disk is ours: the next list starts from there.
    assert [p.name for p in quirks_dir.iterdir()] == ["z2m_acme_b.py"]
    assert entry.runtime_data.summary()["pending_zha_reload"] == ["z2m_acme_b.py: installed"]


async def test_device_on_a_hand_made_custom_quirk_gets_a_notice_only(hass: HomeAssistant, zha: Zha, repo_dir: Path, quirks_dir: Path):
    zha.add_device(IEEE_A, "_TZE200_aaaa", "TS0601", "Radar")
    zha.add_device(IEEE_C, "_TZE200_aaaa", "TS0601", "Second radar")
    zha.apply_quirks({IEEE_A: "my_radar:Radar"})
    await setup_entry(hass, repo_dir)
    # The file would claim the radar on the user's own quirk too: written for neither.
    assert listed(hass) == NOTHING
    notice = issue_of(hass, "blocked")
    assert not notice.is_fixable
    assert "Radar" in notice.translation_placeholders["devices"] and "the custom quirk `my_radar`" in notice.translation_placeholders["devices"]
    assert list(quirks_dir.iterdir()) == []


async def test_a_file_of_the_user_under_our_name_gets_a_notice(hass: HomeAssistant, zha: Zha, repo_dir: Path, quirks_dir: Path):
    (quirks_dir / "z2m_tuya_a.py").write_bytes(b"# my own copy\n")
    zha.add_device(IEEE_A, "_TZE200_aaaa", "TS0601")
    zha.apply_quirks({IEEE_A: "z2m_tuya_a:Mine"})
    entry = await setup_entry(hass, repo_dir)
    assert listed(hass) == NOTHING
    notice = issue_of(hass, "users_file")
    assert notice.translation_placeholders["file"] == "z2m_tuya_a.py" and not notice.is_fixable
    assert (quirks_dir / "z2m_tuya_a.py").read_bytes() == b"# my own copy\n"
    # Deleted and ZHA reloaded: the list brings ours.
    (quirks_dir / "z2m_tuya_a.py").unlink()
    zha.reload({IEEE_A: NO_QUIRK})
    await entry.runtime_data.async_refresh()
    assert offered(hass) == ["z2m_tuya_a.py"] and issues_of(hass, "users_file") == []


async def test_installed_file_that_zha_does_not_apply(hass: HomeAssistant, zha: Zha, repo_dir: Path):
    zha.add_device(IEEE_A, "_TZE200_aaaa", "TS0601")
    entry = await setup_entry(hass, repo_dir)
    await apply_list(hass)
    # ZHA loaded the folder but applies nothing to the device: an import error, say.
    zha.reload()
    await entry.runtime_data.async_refresh()
    notice = issue_of(hass, "not_applied")
    assert notice.translation_placeholders["file"] == "z2m_tuya_a.py"
    assert listed(hass) == NOTHING


async def test_removal_once_zha_applies_its_own_quirk(hass: HomeAssistant, zha: Zha, repo_dir: Path, quirks_dir: Path):
    zha.add_device(IEEE_A, "_TZE200_aaaa", "TS0601")
    entry = await setup_entry(hass, repo_dir)
    await apply_list(hass)
    zha.reload({IEEE_A: "zhaquirks.tuya.ts0601_radar:Radar"})
    await entry.runtime_data.async_refresh()
    assert listed(hass) == {**NOTHING, "remove": ["z2m_tuya_a.py"]}
    flow = await start_fix(hass, issue_of(hass, "changes"))
    assert "ZHA ships a quirk for this device now. This file steps back" in flow["description_placeholders"]["changes"]
    await continue_fix(hass, flow, {"next_step_id": "apply"})
    assert list(quirks_dir.iterdir()) == []


async def test_an_update_comes_with_a_newer_state(hass: HomeAssistant, zha: Zha, repo_dir: Path, quirks_dir: Path):
    zha.add_device(IEEE_A, "_TZE200_aaaa", "TS0601", "Radar")
    entry = await setup_entry(hass, repo_dir)
    await apply_list(hass)
    zha.reload({IEEE_A: "z2m_tuya_a:TuyaA"})
    write_repo(repo_dir, version=2)
    await restart_with(hass, entry, repo_dir)
    assert listed(hass) == {**NOTHING, "update": ["z2m_tuya_a.py"]}
    flow = await start_fix(hass, issue_of(hass, "changes"))
    assert "**Update** `z2m_tuya_a.py` (Tuya A) for Radar." in flow["description_placeholders"]["changes"]
    await continue_fix(hass, flow, {"next_step_id": "apply"})
    assert (quirks_dir / "z2m_tuya_a.py").read_bytes() == quirk_text("tuya_a", 2)


async def test_an_update_leaves_a_file_changed_after_the_list_was_made(hass: HomeAssistant, zha: Zha, repo_dir: Path, quirks_dir: Path):
    zha.add_device(IEEE_A, "_TZE200_aaaa", "TS0601")
    entry = await setup_entry(hass, repo_dir)
    await apply_list(hass)
    zha.reload({IEEE_A: "z2m_tuya_a:TuyaA"})
    write_repo(repo_dir, version=2)
    await restart_with(hass, entry, repo_dir)
    flow = await start_fix(hass, issue_of(hass, "changes"))
    (quirks_dir / "z2m_tuya_a.py").write_bytes(b"# edited\n")
    flow = await continue_fix(hass, flow, {"next_step_id": "apply"})
    assert flow["type"] is FlowResultType.ABORT and flow["reason"] == "stale", flow
    assert (quirks_dir / "z2m_tuya_a.py").read_bytes() == b"# edited\n"
    assert issue_of(hass, "changed").translation_placeholders["file"] == "z2m_tuya_a.py"


async def test_fix_flow_when_the_entry_is_not_loaded(hass: HomeAssistant, zha: Zha, repo_dir: Path):
    zha.add_device(IEEE_A, "_TZE200_aaaa", "TS0601")
    entry = await setup_entry(hass, repo_dir)
    issue = issue_of(hass, "changes")
    await hass.config_entries.async_unload(entry.entry_id)
    flow = await start_fix(hass, issue)
    assert flow["type"] is FlowResultType.ABORT and flow["reason"] == "not_loaded"


async def test_disabling_the_entry_removes_its_issues(hass: HomeAssistant, zha: Zha, repo_dir: Path):
    zha.add_device(IEEE_A, "_TZE200_aaaa", "TS0601")
    entry = await setup_entry(hass, repo_dir)
    assert our_issues(hass)
    await hass.config_entries.async_set_disabled_by(entry.entry_id, ConfigEntryDisabler.USER)
    await hass.async_block_till_done(wait_background_tasks=True)
    assert our_issues(hass) == {}


async def test_removing_the_entry_removes_its_issues_not_its_files(hass: HomeAssistant, zha: Zha, repo_dir: Path, quirks_dir: Path):
    zha.add_device(IEEE_A, "_TZE200_aaaa", "TS0601")
    entry = await setup_entry(hass, repo_dir)
    await apply_list(hass)
    zha.add_device(IEEE_B, "Anyone", "B-1")
    zha.reload({IEEE_A: "z2m_tuya_a:TuyaA"})
    await entry.runtime_data.async_refresh()
    assert our_issues(hass)
    await hass.config_entries.async_remove(entry.entry_id)
    await hass.async_block_till_done(wait_background_tasks=True)
    assert our_issues(hass) == {}
    assert (quirks_dir / "z2m_tuya_a.py").exists()


async def test_an_issue_of_an_earlier_release_does_nothing(hass: HomeAssistant, zha: Zha, repo_dir: Path):
    await setup_entry(hass, repo_dir)
    ir.async_create_issue(hass, DOMAIN, "install_z2m_tuya_a_123", is_fixable=True, severity=ir.IssueSeverity.WARNING, translation_key="changes", data={"kind": "install"})
    flow = await hass.data["repairs"]["flow_manager"].async_init(DOMAIN, context={"issue_id": "install_z2m_tuya_a_123"})
    assert flow["type"] is FlowResultType.ABORT and flow["reason"] == "nothing_to_do"
    ir.async_delete_issue(hass, DOMAIN, "install_z2m_tuya_a_123")


async def test_manifest_and_device_strings_reach_the_list_as_plain_text(hass: HomeAssistant, zha: Zha, repo_dir: Path):
    zha.add_device(IEEE_A, "_TZE200_aaaa", "TS0601", "Radar ![x](https://tracker.example/name.png)")
    manifest = {**MANIFEST, "tuya_a": {**MANIFEST["tuya_a"], "vendor": "Tuya ![](https://tracker.example/seen.png)"}}
    manifest["tuya_a"]["upstream_open_prs"] = [{**UPSTREAM_PR, "url": "https://attacker.example/login"}]
    await setup_entry(hass, write_repo(repo_dir, manifest))
    flow = await start_fix(hass, issue_of(hass, "changes"))
    changes = flow["description_placeholders"]["changes"]
    assert r"Radar !\[x\](https://tracker.example/name.png)" in changes
    assert r"Tuya !\[\](https://tracker.example/seen.png)" in changes
    # The link is built from the pull request's number.
    assert "attacker.example" not in changes and "[#4242](https://github.com/zigpy/zha-device-handlers/pull/4242)" in changes
    assert "Status: generated, not verified on a device yet." in changes


@pytest.mark.parametrize(
    ("numbers", "line"),
    [
        ([4242], "an open zha-device-handlers pull request adds this device. Testing it helps more: [#4242](https://github.com/zigpy/zha-device-handlers/pull/4242)"),
        (
            [4242, 4343],
            "open zha-device-handlers pull requests add this device. Testing them helps more: "
            "[#4242](https://github.com/zigpy/zha-device-handlers/pull/4242), [#4343](https://github.com/zigpy/zha-device-handlers/pull/4343)",
        ),
    ],
)
async def test_open_pull_requests_share_one_line_in_the_list(hass: HomeAssistant, zha: Zha, repo_dir: Path, numbers: list[int], line: str):
    zha.add_device(IEEE_A, "_TZE200_aaaa", "TS0601")
    manifest = {**MANIFEST, "tuya_a": {**MANIFEST["tuya_a"], "upstream_open_prs": [{**UPSTREAM_PR, "number": number} for number in numbers]}}
    await setup_entry(hass, write_repo(repo_dir, manifest))
    flow = await start_fix(hass, issue_of(hass, "changes"))
    assert f"\n    - {line}\n" in flow["description_placeholders"]["changes"] + "\n"


async def test_left_out_devices_are_named_in_the_list(hass: HomeAssistant, zha: Zha, repo_dir: Path):
    dev_b = zha.add_device(IEEE_B, "Anyone", "B-1", "Plug")
    zha.add_device(IEEE_C, "Somebody", "B-1", "Lamp")
    entry = await setup_entry(hass, repo_dir, options={const.CONF_EXCLUDED: [dev_b]})
    # z2m_acme_b.py claims every B-1: installed for the lamp, it applies to the plug too.
    flow = await start_fix(hass, issue_of(hass, "changes"))
    changes = flow["description_placeholders"]["changes"]
    assert "for Lamp." in changes and "also applies to Plug, which you left out" in changes
    assert manager_of(hass) is entry.runtime_data
