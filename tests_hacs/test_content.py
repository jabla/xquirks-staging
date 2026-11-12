"""Content states of the repository: the newest usable tag, newer files without a restart, files
checked before writing, withdrawn revisions, downloads that wait or cannot pass, nothing offered
without a state."""

from __future__ import annotations

import json
import os
import re
import time
import uuid
from contextlib import contextmanager
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

import aiohttp
import pytest
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import issue_registry as ir
from homeassistant.util import dt as dt_util
from pytest_homeassistant.common import async_fire_time_changed

from . import integration
from .conftest import (
    GUARD_ID,
    MANIFEST,
    NO_QUIRK,
    REPOS,
    Repo,
    Zha,
    apply_list,
    content_json,
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
    tag_files,
    write_repo,
)
from .integration import DOMAIN, const, diagnostics, manager
from .integration import content as integration_content
from .integration import plan as plans

TAGS_URL = const.TAGS_URL
BUTTON = "button.xquirks_check_for_quirk_updates"
IEEE_A = "00:11:22:33:44:55:66:01"
IEEE_B = "00:11:22:33:44:55:66:02"
IEEE_C = "00:11:22:33:44:55:66:03"
# What listed() shows while there is no change list to confirm.
NOTHING = {"remove": [], "update": [], "install": []}
# An older generated copy of z2m_tuya_a.py, as the user may have put it there by hand.
OLDER_GENERATED = (
    b'"""Tuya A: a device.\n\nGenerated from the Zigbee2MQTT definition (zigbee-herdsman-converters 1.0.0).\n'
    b"Data: zigbee-herdsman-converters, MIT, Copyright (c) 2018 Koen Kanters.\nStatus: generated, not verified on hardware.\n"
    b'Revision: 0badc0de\n"""\n# older\n'
)


def requested(aioclient_mock, suffix: str) -> int:
    """Requests whose URL ends with suffix; content-<n>/<path> stands for the path at that tag's commit."""
    if match := re.fullmatch(r"content-([0-9]+)/(.+)", suffix):
        repo = next(r for r in REPOS.values() if r.mock is aioclient_mock)
        suffix = f"/{repo.commit(int(match.group(1)))}/{match.group(2)}"
    return sum(1 for _method, url, _data, _headers in aioclient_mock.mock_calls if str(url).endswith(suffix))


def publish(repo_dir: Path, version: int, *, homeassistant: str = "2026.1.0", withdrawn: str = "", guard_id: str | None = GUARD_ID, content_json_file: bool = True) -> str:
    """The working tree with the files of `version` as the next content tag."""
    write_repo(repo_dir, version=version)
    (repo_dir / "hacs.json").write_text(json.dumps({"name": "xquirks", "homeassistant": homeassistant}))
    (repo_dir / "data").mkdir(exist_ok=True)
    (repo_dir / "data" / "withdrawn.toml").write_text(withdrawn)
    (repo_dir / "content.json").write_bytes(content_json(guard_id))
    tag = REPOS[repo_dir].publish()
    if not content_json_file:
        del REPOS[repo_dir].tags[int(tag.removeprefix("content-"))]["content.json"]
    return tag


def withdraw(slug: str, version: int, reason: str = "Drives the valve fully open.") -> str:
    """A withdrawn.toml entry for the revision of z2m_<slug>.py at that version."""
    return f'[[withdrawn]]\nfile = "z2m_{slug}.py"\nrevision = "{quirk_revision(slug, version)}"\nreason = "{reason}"\n'


async def restart_with(hass: HomeAssistant, entry, repo_dir: Path) -> None:
    """A restart of Home Assistant, with what repo_dir holds now published as the next content tag."""
    await hass.config_entries.async_unload(entry.entry_id)
    with published(repo_dir), patch.object(integration.manager, "_RUN", uuid.uuid4().hex):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done(wait_background_tasks=True)


async def apply_and_reload(hass: HomeAssistant, zha: Zha, quirks: dict[str, str] | None = None) -> dict:
    """Confirm the visible change list, then ZHA reloads and applies these quirks (ieee ->
    quirk_class): the next list may come. The abort the dialog ended with."""
    flow = await apply_list(hass)
    zha.reload(quirks)
    await manager_of(hass).async_refresh()
    return flow


async def not_now(hass: HomeAssistant) -> None:
    """Put the visible change list aside: the dialog's "Not now"."""
    flow = await start_fix(hass, issue_of(hass, "changes"))
    flow = await continue_fix(hass, flow, {"next_step_id": "not_now"})
    assert flow["type"] is FlowResultType.ABORT and flow["reason"] == "not_now", flow


def kinds(hass: HomeAssistant) -> set[str]:
    """The kinds of the issues the user sees."""
    return {issue.translation_key for issue in our_issues(hass).values()}


@contextmanager
def folder_writes():
    """Every write and delete of the file primitives meanwhile, as (primitive, file name)."""
    calls: list[tuple[str, str]] = []

    def watched(name: str):
        real = getattr(integration.files, name)

        def call(path: str, *args):
            calls.append((name, os.path.basename(path)))
            return real(path, *args)

        return call

    with patch.multiple(integration.files, write_new=watched("write_new"), replace=watched("replace"), delete=watched("delete")):
        yield calls


async def test_files_come_from_the_tag_one_at_a_time(hass: HomeAssistant, zha: Zha, repo_dir: Path, quirks_dir: Path, aioclient_mock):
    zha.add_device(IEEE_A, "_TZE200_aaaa", "TS0601")
    entry = await setup_entry(hass, repo_dir)
    assert entry.runtime_data.source.tag == "content-1"
    # The list of files, then each file the change list would write, once: the guard checks it before the list.
    assert requested(aioclient_mock, "content-1/quirks/z2m_tuya_a.py") == 1
    await apply_list(hass)
    # The apply writes the checked download.
    assert (quirks_dir / "z2m_tuya_a.py").read_bytes() == quirk_text("tuya_a", 1)
    assert requested(aioclient_mock, "content-1/quirks/z2m_tuya_a.py") == 1
    # Files of no device of the user are never downloaded.
    assert requested(aioclient_mock, "/quirks/z2m_acme_b.py") == 0


async def test_newer_state_brings_the_update_without_a_restart(hass: HomeAssistant, zha: Zha, repo_dir: Path, quirks_dir: Path, aioclient_mock):
    zha.add_device(IEEE_A, "_TZE200_aaaa", "TS0601")
    entry = await setup_entry(hass, repo_dir)
    await apply_and_reload(hass, zha, {IEEE_A: "z2m_tuya_a:TuyaA"})
    assert listed(hass) == NOTHING
    tag = publish(repo_dir, 2)
    await hass.services.async_call("button", "press", {"entity_id": BUTTON}, blocking=True)
    await hass.async_block_till_done()
    assert entry.runtime_data.source.tag == tag
    assert listed(hass) == {"remove": [], "update": ["z2m_tuya_a.py"], "install": []}
    await apply_list(hass)
    assert (quirks_dir / "z2m_tuya_a.py").read_bytes() == quirk_text("tuya_a", 2)
    assert requested(aioclient_mock, f"{tag}/quirks/z2m_tuya_a.py") == 1
    data = await diagnostics.async_get_config_entry_diagnostics(hass, entry)
    assert data["content"]["in_use"] == tag
    assert data["installed"][str(quirks_dir / "z2m_tuya_a.py")]["revision"] == quirk_revision("tuya_a", 2)


# Downloads that cannot pass, or not yet.


async def test_file_with_another_sha256_is_not_written(hass: HomeAssistant, zha: Zha, repo_dir: Path, quirks_dir: Path, aioclient_mock):
    """Other bytes than the manifest states cannot pass at that tag: the file is unavailable, its
    installed copy stays while its device runs it, the rest of the list goes on."""
    zha.add_device(IEEE_A, "_TZE200_aaaa", "TS0601")
    entry = await setup_entry(hass, repo_dir)
    await apply_and_reload(hass, zha, {IEEE_A: "z2m_tuya_a:TuyaA"})
    zha.add_device(IEEE_B, "Anyone", "B-1")
    tag = publish(repo_dir, 2)
    files = REPOS[repo_dir].tags[int(tag.removeprefix("content-"))]
    right, files["quirks/z2m_tuya_a.py"] = files["quirks/z2m_tuya_a.py"], b"import os  # not what the manifest says\n"
    manager_ = entry.runtime_data
    await manager_.async_check()
    assert listed(hass) == {"remove": [], "update": [], "install": ["z2m_acme_b.py"]}
    notice = issue_of(hass, "unavailable", "z2m_tuya_a.py")
    assert not notice.is_fixable and "does not have the sha256 its manifest states" in notice.translation_placeholders["error"]
    # Neither refused by the guard (it never saw the bytes) nor waiting for another try.
    assert issues_of(hass, "refused") == issues_of(hass, "download_waiting") == []
    data = await diagnostics.async_get_config_entry_diagnostics(hass, entry)
    assert "sha256" in data["cannot_be_downloaded"]["z2m_tuya_a.py"]
    assert data["waiting_for_the_check"] == {}
    await apply_list(hass)
    assert (quirks_dir / "z2m_acme_b.py").read_bytes() == quirk_text("acme_b", 2)
    assert (quirks_dir / "z2m_tuya_a.py").read_bytes() == quirk_text("tuya_a", 1)
    # Content at a commit never changes: the timer does not ask again, a refresh neither.
    files["quirks/z2m_tuya_a.py"] = right
    zha.reload({IEEE_B: "z2m_acme_b:AcmeB"})
    await manager_._interval_check(dt_util.utcnow())
    await manager_.async_refresh()
    assert requested(aioclient_mock, f"{tag}/quirks/z2m_tuya_a.py") == 1
    assert listed(hass) == NOTHING
    assert issue_of(hass, "unavailable", "z2m_tuya_a.py")
    # The next tag brings the update.
    publish(repo_dir, 3)
    await manager_.async_check()
    assert listed(hass) == {"remove": [], "update": ["z2m_acme_b.py", "z2m_tuya_a.py"], "install": []}
    assert issues_of(hass, "unavailable") == []


@pytest.mark.parametrize(("served", "error"), [(None, "HTTP 404"), (b"#" * (const.MAX_DOWNLOAD + 1), f"larger than {const.MAX_DOWNLOAD} bytes")], ids=["missing", "too_large"])
async def test_a_download_that_cannot_pass_makes_the_file_unavailable(hass: HomeAssistant, zha: Zha, repo: Repo, repo_dir: Path, quirks_dir: Path, aioclient_mock, served, error):
    """A file missing at the tag's commit, or above the size limit, cannot pass later either: the file
    is unavailable, the rest of the list goes on."""
    zha.add_device(IEEE_A, "_TZE200_aaaa", "TS0601")
    zha.add_device(IEEE_B, "Anyone", "B-1")
    repo.publish()
    if served is None:
        del repo.tags[1]["quirks/z2m_tuya_a.py"]
    else:
        repo.tags[1]["quirks/z2m_tuya_a.py"] = served
    await setup_entry(hass, repo_dir, publish=False)
    assert listed(hass) == {"remove": [], "update": [], "install": ["z2m_acme_b.py"]}
    notice = issue_of(hass, "unavailable", "z2m_tuya_a.py")
    assert notice.translation_placeholders["quirk"] == "Tuya A" and error in notice.translation_placeholders["error"]
    assert issues_of(hass, "refused") == issues_of(hass, "download_waiting") == []
    await apply_list(hass)
    assert [p.name for p in quirks_dir.iterdir()] == ["z2m_acme_b.py"]
    assert requested(aioclient_mock, "content-1/quirks/z2m_tuya_a.py") == 1


@pytest.mark.parametrize(("status", "error"), [(503, "HTTP 503"), (429, "rate limit")])
async def test_a_download_that_may_pass_later_holds_the_list(hass: HomeAssistant, zha: Zha, repo: Repo, repo_dir: Path, quirks_dir: Path, status, error):
    """A download that fails for now holds the whole list, with a notice that names the file and
    why. The timer tries again every 15 minutes: the list comes once the file is checked."""
    zha.add_device(IEEE_A, "_TZE200_aaaa", "TS0601")
    zha.add_device(IEEE_B, "Anyone", "B-1")
    repo.publish()
    files = repo.tags[1]
    right, files["quirks/z2m_tuya_a.py"] = files["quirks/z2m_tuya_a.py"], status
    entry = await setup_entry(hass, repo_dir, publish=False)
    manager_ = entry.runtime_data
    # No list, not even with the file that passed.
    assert manager_.plan.held == plans.UNCHECKED
    assert kinds(hass) == {"download_waiting"}
    waiting = issue_of(hass, "download_waiting").translation_placeholders["files"]
    assert waiting.startswith("- `z2m_tuya_a.py`: ") and error in waiting
    assert list(manager_.summary()["waiting_for_the_check"]) == ["z2m_tuya_a.py"]
    assert list(quirks_dir.iterdir()) == []
    # Refreshes still due from the setup (the device registry changed) run first, the file still fails.
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=const.REFRESH_COOLDOWN + 1))
    await hass.async_block_till_done(wait_background_tasks=True)
    assert manager_.plan.held == plans.UNCHECKED
    files["quirks/z2m_tuya_a.py"] = right
    async_fire_time_changed(hass, dt_util.utcnow() + const.RETRY_INTERVAL)
    await hass.async_block_till_done(wait_background_tasks=True)
    assert listed(hass) == {"remove": [], "update": [], "install": ["z2m_acme_b.py", "z2m_tuya_a.py"]}
    assert issues_of(hass, "download_waiting") == []
    await apply_list(hass)
    assert sorted(p.name for p in quirks_dir.iterdir()) == ["z2m_acme_b.py", "z2m_tuya_a.py"]


async def test_the_apply_checks_its_own_download(hass: HomeAssistant, zha: Zha, repo_dir: Path, quirks_dir: Path):
    """A download no longer kept is fetched again for the apply and checked like the first one:
    nothing is written before every file of the list is fetched."""
    zha.add_device(IEEE_A, "_TZE200_aaaa", "TS0601")
    zha.add_device(IEEE_B, "Anyone", "B-1")
    entry = await setup_entry(hass, repo_dir)
    assert listed(hass) == {"remove": [], "update": [], "install": ["z2m_acme_b.py", "z2m_tuya_a.py"]}
    entry.runtime_data._downloads.clear()
    REPOS[repo_dir].tags[1]["quirks/z2m_tuya_a.py"] = b"import os  # not what the manifest says\n"
    with folder_writes() as writes:
        flow = await apply_list(hass, expect=("failed",))
    assert flow["description_placeholders"]["failed"].startswith("`z2m_tuya_a.py`: cannot download it (")
    # z2m_acme_b.py comes first in the list and passed: not written either, not even for a moment.
    assert writes == [] and list(quirks_dir.iterdir()) == []
    # Content at a commit never changes: the next list goes on without that file, with its notice.
    assert listed(hass) == {"remove": [], "update": [], "install": ["z2m_acme_b.py"]}
    assert [i.data["file"] for i in issues_of(hass, "unavailable")] == ["z2m_tuya_a.py"]
    await apply_list(hass)
    assert [p.name for p in quirks_dir.iterdir()] == ["z2m_acme_b.py"]


async def test_state_for_a_newer_home_assistant_is_skipped(hass: HomeAssistant, zha: Zha, repo_dir: Path, quirks_dir: Path):
    zha.add_device(IEEE_A, "_TZE200_aaaa", "TS0601")
    entry = await setup_entry(hass, repo_dir)
    await apply_and_reload(hass, zha, {IEEE_A: "z2m_tuya_a:TuyaA"})
    publish(repo_dir, 2, homeassistant="2099.1.0")
    manager_ = entry.runtime_data
    await manager_.async_check()
    assert manager_.source.tag == "content-1"
    assert listed(hass) == NOTHING
    data = await diagnostics.async_get_config_entry_diagnostics(hass, entry)
    assert data["content"]["skipped_tags"] == {"content-2": "needs Home Assistant 2099.1.0 or newer"}
    assert "2099.1.0" in data["content"]["last_check"]["result"]


async def test_newest_state_this_release_can_use_is_taken(hass: HomeAssistant, zha: Zha, repo: Repo, repo_dir: Path, aioclient_mock):
    zha.add_device(IEEE_A, "_TZE200_aaaa", "TS0601")
    repo.publish()
    publish(repo_dir, 2)
    publish(repo_dir, 3, homeassistant="2099.1.0")
    publish(repo_dir, 4, guard_id="f" * 64)
    publish(repo_dir, 5, content_json_file=False)
    entry = await setup_entry(hass, repo_dir, publish=False)
    manager_ = entry.runtime_data
    assert manager_.source.tag == "content-2"
    assert offered(hass) == ["z2m_tuya_a.py"]
    # Only the small metadata of the newer tags was read, the manifest of the one taken.
    assert requested(aioclient_mock, "content-3/manifest.json") == requested(aioclient_mock, "content-1/manifest.json") == 0
    assert requested(aioclient_mock, "content-2/manifest.json") == 1
    assert dict(manager_._skipped()) == {
        "content-3": "needs Home Assistant 2099.1.0 or newer",
        "content-4": f"was built for another xquirks release (guard {'f' * 12}, this release has {GUARD_ID[:12]})",
        "content-5": "states no guard",
    }
    # A new tag: what the others name was kept, they are not read again.
    publish(repo_dir, 6, homeassistant="2099.1.0")
    await manager_.async_check()
    assert manager_.source.tag == "content-2"
    assert requested(aioclient_mock, "content-3/hacs.json") == 1
    assert requested(aioclient_mock, "content-6/hacs.json") == 1


async def test_without_a_state_nothing_is_offered_and_a_notice_says_why(hass: HomeAssistant, zha: Zha, repo: Repo, repo_dir: Path):
    zha.add_device(IEEE_A, "_TZE200_aaaa", "TS0601")
    entry = await setup_entry(hass, repo_dir, publish=False)
    assert offered(hass) == []
    notice = issue_of(hass, "no_content_state")
    assert notice.translation_placeholders == {"reason": "the repository has no content state yet"}
    repo.publish()
    await hass.services.async_call("button", "press", {"entity_id": BUTTON}, blocking=True)
    await hass.async_block_till_done()
    assert entry.runtime_data.source.tag == "content-1"
    assert issues_of(hass, "no_content_state") == []
    assert offered(hass) == ["z2m_tuya_a.py"]


async def test_github_out_of_reach_at_the_first_setup(hass: HomeAssistant, zha: Zha, repo: Repo, repo_dir: Path, aioclient_mock):
    zha.add_device(IEEE_A, "_TZE200_aaaa", "TS0601")
    repo.publish()
    aioclient_mock.clear_requests()
    aioclient_mock.get(TAGS_URL, exc=aiohttp.ClientConnectionError("offline"))
    entry = await setup_entry(hass, repo_dir, publish=False)
    assert "offline" in issue_of(hass, "no_content_state").translation_placeholders["reason"]
    manager_ = entry.runtime_data
    # While there is no state the timer tries again after 15 minutes, not after 6 hours.
    aioclient_mock.clear_requests()
    repo.register()
    with patch.object(manager.time, "time", return_value=manager_._last_attempt + 10 * 60):
        await manager_._interval_check(None)
    assert manager_.source.tag is None
    with patch.object(manager.time, "time", return_value=manager_._last_attempt + 15 * 60):
        await manager_._interval_check(None)
    assert manager_.source.tag == "content-1"
    assert issues_of(hass, "no_content_state") == []
    assert offered(hass) == ["z2m_tuya_a.py"]
    # With a state: every 6 hours.
    calls = aioclient_mock.call_count
    with patch.object(manager.time, "time", return_value=manager_._last_attempt + 60 * 60):
        await manager_._interval_check(None)
    assert aioclient_mock.call_count == calls


async def test_state_survives_a_restart_without_network(hass: HomeAssistant, zha: Zha, repo_dir: Path, quirks_dir: Path, aioclient_mock):
    zha.add_device(IEEE_A, "_TZE200_aaaa", "TS0601")
    entry = await setup_entry(hass, repo_dir)
    publish(repo_dir, 2)
    await entry.runtime_data.async_check()
    await apply_list(hass)
    zha.apply_quirks({IEEE_A: "z2m_tuya_a:TuyaA"})
    aioclient_mock.clear_requests()
    aioclient_mock.get(TAGS_URL, exc=aiohttp.ClientConnectionError("offline"))
    await restart_with(hass, entry, repo_dir)
    manager_ = entry.runtime_data
    assert manager_.source.tag == "content-2"
    assert manager_.last_check["result"] == "failed"
    assert "offline" in manager_.last_check["error"]
    assert listed(hass) == NOTHING
    assert not issues_of(hass, "no_content_state")


def test_stored_state_is_used_only_when_this_release_reads_it():
    entry = {**MANIFEST["tuya_a"], "sha256": "0" * 64, "revision": "0123abcd"}
    stored = {
        "tag": "content-4",
        "number": 4,
        "commit": "c" * 40,
        "homeassistant": "2026.1.0",
        "withdrawn": [],
        "manifest": {"tuya_a": entry},
    }
    usable = {**stored, "guard": GUARD_ID}
    assert manager._stored_state(usable, GUARD_ID).commit == "c" * 40
    # Kept by a release with another guard, or by one from before the guard.
    assert manager._stored_state(usable, "f" * 64) is None
    assert manager._stored_state({**usable, "guard": None}, GUARD_ID) is None
    assert manager._stored_state({**usable, "homeassistant": "2099.1.0"}, GUARD_ID) is None
    assert manager._stored_state({**usable, "manifest": {"x": {**entry, "file": "../evil.py"}}}, GUARD_ID) is None
    # Bound to no commit.
    assert manager._stored_state({**usable, "commit": None}, GUARD_ID) is None
    assert manager._stored_state({**usable, "withdrawn": [["../evil.py", "0123abcd", "x"]]}, GUARD_ID) is None


async def test_rate_limit_is_respected(hass: HomeAssistant, zha: Zha, repo_dir: Path, aioclient_mock):
    entry = await setup_entry(hass, repo_dir)
    aioclient_mock.clear_requests()
    aioclient_mock.get(TAGS_URL, status=403, headers={"X-RateLimit-Remaining": "0", "X-RateLimit-Reset": str(int(time.time()) + 900)})
    manager_ = entry.runtime_data
    await manager_.async_check()
    assert "rate limit" in manager_.last_check["error"]
    calls = aioclient_mock.call_count
    await manager_.async_check()
    assert aioclient_mock.call_count == calls
    assert manager_.last_check["result"] == "skipped"


async def test_unchanged_tag_list_costs_a_conditional_request(hass: HomeAssistant, zha: Zha, repo_dir: Path, aioclient_mock):
    entry = await setup_entry(hass, repo_dir)
    manager_ = entry.runtime_data
    await manager_.async_check()
    (_method, _url, _data, headers) = aioclient_mock.mock_calls[-1]
    assert headers["If-None-Match"] == '"tags-1"'
    assert manager_.last_check["result"] == "newest state content-1 in use"
    assert manager_.source.tag == "content-1"


async def test_broken_manifest_keeps_what_is_in_use(hass: HomeAssistant, zha: Zha, repo_dir: Path):
    entry = await setup_entry(hass, repo_dir)
    tag = publish(repo_dir, 2)
    REPOS[repo_dir].tags[int(tag.removeprefix("content-"))]["manifest.json"] = json.dumps({"x": {**MANIFEST["tuya_a"], "file": "../../evil.py"}}).encode()
    manager_ = entry.runtime_data
    await manager_.async_check()
    assert manager_.source.tag == "content-1"
    assert "content-2 cannot be read (unexpected file in the manifest: ../../evil.py)" in manager_.last_check["result"]
    # The tag never changes: it is not read again.
    assert "content-2" in manager_._skipped()


# Withdrawn revisions: never written, taken out by the change list, noticed also while no list can come.


async def updated_to_2(hass: HomeAssistant, zha: Zha, repo_dir: Path):
    """z2m_tuya_a.py installed from content-1 (version 1), then updated from content-2 (version 2);
    ZHA runs it."""
    zha.add_device(IEEE_A, "_TZE200_aaaa", "TS0601")
    entry = await setup_entry(hass, repo_dir)
    await apply_and_reload(hass, zha, {IEEE_A: "z2m_tuya_a:TuyaA"})
    publish(repo_dir, 2)
    await entry.runtime_data.async_check()
    assert listed(hass) == {"remove": [], "update": ["z2m_tuya_a.py"], "install": []}
    await apply_and_reload(hass, zha)
    return entry


async def test_withdrawn_revision_goes_forward_with_the_list(hass: HomeAssistant, zha: Zha, repo_dir: Path, quirks_dir: Path):
    entry = await updated_to_2(hass, zha, repo_dir)
    path = quirks_dir / "z2m_tuya_a.py"
    publish(repo_dir, 3, withdrawn=withdraw("tuya_a", 2, "Reports the temperature ten times too high."))
    await entry.runtime_data.async_check()
    notice = issue_of(hass, "withdrawn_installed", "z2m_tuya_a.py")
    assert notice.severity is ir.IssueSeverity.ERROR and not notice.is_fixable
    assert notice.translation_placeholders["revision"] == quirk_revision("tuya_a", 2)
    assert notice.translation_placeholders["reason"] == "Reports the temperature ten times too high."
    # One entry for the file: the update to the revision on offer. The withdrawal makes the list an error.
    assert listed(hass) == {"remove": [], "update": ["z2m_tuya_a.py"], "install": []}
    issue = issue_of(hass, "changes")
    assert issue.severity is ir.IssueSeverity.ERROR and issue.data["severe"] is True
    flow = await start_fix(hass, issue)
    assert f"The installed revision {quirk_revision('tuya_a', 2)} is withdrawn: Reports the temperature ten times too high." in flow["description_placeholders"]["changes"]
    flow = await continue_fix(hass, flow, {"next_step_id": "apply"})
    assert flow["type"] is FlowResultType.ABORT and flow["reason"] == "done", flow
    assert path.read_bytes() == quirk_text("tuya_a", 3)
    assert issues_of(hass, "withdrawn_installed") == []


async def test_withdrawn_revision_without_a_way_out_is_removed(hass: HomeAssistant, zha: Zha, repo_dir: Path, quirks_dir: Path):
    zha.add_device(IEEE_A, "_TZE200_aaaa", "TS0601", "Radar")
    entry = await setup_entry(hass, repo_dir)
    await apply_and_reload(hass, zha, {IEEE_A: "z2m_tuya_a:TuyaA"})
    # The newest state withdraws the revision it still ships: nothing to update to.
    publish(repo_dir, 1, withdrawn=withdraw("tuya_a", 1, "Wrong unit."))
    manager_ = entry.runtime_data
    await manager_.async_check()
    assert issue_of(hass, "withdrawn_installed", "z2m_tuya_a.py")
    assert listed(hass) == {"remove": ["z2m_tuya_a.py"], "update": [], "install": []}
    issue = issue_of(hass, "changes")
    assert issue.severity is ir.IssueSeverity.ERROR
    flow = await start_fix(hass, issue)
    changes = flow["description_placeholders"]["changes"]
    assert f"`z2m_tuya_a.py` (Tuya A): its revision {quirk_revision('tuya_a')} is withdrawn: Wrong unit." in changes
    assert "Radar gets no quirk of this collection: the revision of `z2m_tuya_a.py` on offer is withdrawn" in changes
    flow = await continue_fix(hass, flow, {"next_step_id": "apply"})
    assert flow["type"] is FlowResultType.ABORT and flow["reason"] == "done", flow
    assert not (quirks_dir / "z2m_tuya_a.py").exists()
    assert issues_of(hass, "withdrawn_installed") == []
    # Nothing brings the withdrawn revision back.
    zha.reload({IEEE_A: NO_QUIRK})
    await manager_.async_refresh()
    assert our_issues(hass) == {}


async def test_the_reason_of_a_withdrawal_ends_its_line_once(hass: HomeAssistant, zha: Zha, repo_dir: Path):
    zha.add_device(IEEE_A, "_TZE200_aaaa", "TS0601")
    entry = await setup_entry(hass, repo_dir)
    await apply_and_reload(hass, zha, {IEEE_A: "z2m_tuya_a:TuyaA"})
    # A reason is one sentence (data/withdrawn.toml), with its period.
    publish(repo_dir, 1, withdrawn=withdraw("tuya_a", 1, "Wrong unit."))
    await entry.runtime_data.async_check()
    flow = await start_fix(hass, issue_of(hass, "changes"))
    assert "is withdrawn: Wrong unit.\n" in flow["description_placeholders"]["changes"]


async def test_a_withdrawal_is_noticed_while_the_list_is_held(hass: HomeAssistant, zha: Zha, repo: Repo, repo_dir: Path, quirks_dir: Path):
    """The notice of a withdrawn revision in use comes at once, also while no list can come: a change
    waits for ZHA's reload, then the new version waits for its download. The list follows the hold."""
    zha.add_device(IEEE_A, "_TZE200_aaaa", "TS0601")
    entry = await setup_entry(hass, repo_dir)
    manager_ = entry.runtime_data
    await apply_list(hass)
    tag = publish(repo_dir, 2, withdrawn=withdraw("tuya_a", 1))
    files = repo.tags[int(tag.removeprefix("content-"))]
    right, files["quirks/z2m_tuya_a.py"] = files["quirks/z2m_tuya_a.py"], 503
    await manager_.async_check()
    # ZHA has not loaded the folder since the install.
    assert manager_.plan.held == plans.PENDING
    assert issue_of(hass, "withdrawn_installed", "z2m_tuya_a.py").severity is ir.IssueSeverity.ERROR
    assert kinds(hass) == {"withdrawn_installed"}
    zha.reload({IEEE_A: "z2m_tuya_a:TuyaA"})
    await manager_.async_refresh()
    assert manager_.plan.held == plans.UNCHECKED
    assert kinds(hass) == {"withdrawn_installed", "download_waiting"}
    # The download works: the list takes the withdrawn revision out.
    files["quirks/z2m_tuya_a.py"] = right
    await manager_._interval_check(dt_util.utcnow())
    assert listed(hass) == {"remove": [], "update": ["z2m_tuya_a.py"], "install": []}
    assert issue_of(hass, "changes").severity is ir.IssueSeverity.ERROR
    assert kinds(hass) == {"changes", "withdrawn_installed"}
    await apply_list(hass)
    assert (quirks_dir / "z2m_tuya_a.py").read_bytes() == quirk_text("tuya_a", 2)
    assert our_issues(hass) == {}


async def test_a_withdrawal_brings_back_a_list_put_aside(hass: HomeAssistant, zha: Zha, repo_dir: Path):
    """The dialog's "Not now" puts aside exactly that list: the same changes with the installed
    revision withdrawn since are another list, shown again as an error. Its notice stays when that
    list is put aside too."""
    zha.add_device(IEEE_A, "_TZE200_aaaa", "TS0601")
    entry = await setup_entry(hass, repo_dir)
    manager_ = entry.runtime_data
    await apply_and_reload(hass, zha, {IEEE_A: "z2m_tuya_a:TuyaA"})
    publish(repo_dir, 2)
    await manager_.async_check()
    aside = issue_of(hass, "changes")
    assert aside.severity is ir.IssueSeverity.WARNING
    await not_now(hass)
    assert our_issues(hass) == {}
    # The next tag ships the same file and withdraws the installed revision.
    publish(repo_dir, 2, withdrawn=withdraw("tuya_a", 1))
    await manager_.async_check()
    assert manager_.source.tag == "content-3"
    assert listed(hass) == {"remove": [], "update": ["z2m_tuya_a.py"], "install": []}
    issue = issue_of(hass, "changes")
    assert issue.issue_id != aside.issue_id and issue.severity is ir.IssueSeverity.ERROR
    assert ir.async_get(hass).async_get_issue(DOMAIN, aside.issue_id) is None
    assert issue_of(hass, "withdrawn_installed", "z2m_tuya_a.py")
    await not_now(hass)
    assert kinds(hass) == {"withdrawn_installed"}


async def test_a_revision_the_tag_withdraws_is_never_offered(hass: HomeAssistant, zha: Zha, repo_dir: Path, quirks_dir: Path, aioclient_mock):
    zha.add_device(IEEE_A, "_TZE200_aaaa", "TS0601")
    # The tag still ships the revision its own list withdraws.
    publish(repo_dir, 1, withdrawn=withdraw("tuya_a", 1))
    entry = await setup_entry(hass, repo_dir)
    assert our_issues(hass) == {}
    assert entry.runtime_data.plan.target == frozenset()
    # No list could write it: not even downloaded.
    assert requested(aioclient_mock, "/quirks/z2m_tuya_a.py") == 0
    assert not (quirks_dir / "z2m_tuya_a.py").exists()


async def test_a_withdrawn_revision_never_replaces_a_copy_put_there_by_hand(hass: HomeAssistant, zha: Zha, repo_dir: Path, quirks_dir: Path):
    (quirks_dir / "z2m_tuya_a.py").write_bytes(OLDER_GENERATED)
    zha.add_device(IEEE_A, "_TZE200_aaaa", "TS0601")
    publish(repo_dir, 1, withdrawn=withdraw("tuya_a", 1))
    await setup_entry(hass, repo_dir)
    assert listed(hass) == NOTHING
    assert (quirks_dir / "z2m_tuya_a.py").read_bytes() == OLDER_GENERATED


async def test_no_notice_asks_to_delete_a_copy_for_a_withdrawn_revision(hass: HomeAssistant, zha: Zha, repo_dir: Path, quirks_dir: Path):
    # The notice for a file of the user under our name says the change list brings ours once it is gone.
    (quirks_dir / "z2m_tuya_a.py").write_bytes(OLDER_GENERATED)
    zha.add_device(IEEE_A, "_TZE200_aaaa", "TS0601")
    publish(repo_dir, 1, withdrawn=withdraw("tuya_a", 1))
    await setup_entry(hass, repo_dir)
    assert issues_of(hass, "users_file") == []


async def test_no_notice_asks_to_make_room_for_a_withdrawn_revision(hass: HomeAssistant, zha: Zha, repo_dir: Path, quirks_dir: Path):
    # The notice for a device on another custom quirk says the change list brings the file once that quirk is gone.
    (quirks_dir / "my_tuya_radar.py").write_text("# the user's own quirk for _TZE200_aaaa / TS0601\n")
    zha.add_device(IEEE_A, "_TZE200_aaaa", "TS0601", "Radar")
    zha.apply_quirks({IEEE_A: "my_tuya_radar:(_TZE200_aaaa / TS0601)"})
    publish(repo_dir, 1, withdrawn=withdraw("tuya_a", 1))
    await setup_entry(hass, repo_dir)
    assert issues_of(hass, "blocked") == []


async def test_no_update_to_a_revision_the_tag_withdraws(hass: HomeAssistant, zha: Zha, repo_dir: Path, quirks_dir: Path, aioclient_mock):
    zha.add_device(IEEE_A, "_TZE200_aaaa", "TS0601")
    entry = await setup_entry(hass, repo_dir)
    await apply_and_reload(hass, zha, {IEEE_A: "z2m_tuya_a:TuyaA"})
    publish(repo_dir, 2, withdrawn=withdraw("tuya_a", 2))
    manager_ = entry.runtime_data
    await manager_.async_check()
    assert manager_.source.tag == "content-2"
    # The installed revision is fine and stays; the withdrawn one is not listed, not even downloaded.
    assert our_issues(hass) == {}
    assert requested(aioclient_mock, "content-2/quirks/z2m_tuya_a.py") == 0
    assert (quirks_dir / "z2m_tuya_a.py").read_bytes() == quirk_text("tuya_a", 1)


async def test_the_write_step_itself_refuses_a_withdrawn_revision(hass: HomeAssistant, zha: Zha, repo_dir: Path, quirks_dir: Path, hass_storage):
    """Whatever plans a write: content of a withdrawn revision is never written, the record stays as
    it was (also the one in the store, which a crash would leave)."""
    zha.add_device(IEEE_A, "_TZE200_aaaa", "TS0601")
    entry = await setup_entry(hass, repo_dir)
    await apply_and_reload(hass, zha, {IEEE_A: "z2m_tuya_a:TuyaA"})
    publish(repo_dir, 2, withdrawn=withdraw("tuya_a", 2))
    manager_ = entry.runtime_data
    await manager_.async_check()
    path = quirks_dir / "z2m_tuya_a.py"
    record = dict(manager_.data["installed"][str(path)])
    new = await manager_._read_offered("z2m_tuya_a.py")
    # A step of a change list, as the apply carries it out.
    step = manager.Step("update", str(path), old=quirk_text("tuya_a", 1), new=new, record=record)
    with pytest.raises(manager.GuardRefused) as refused:
        await manager_._do(step)
    assert refused.value.reason == manager.WITHDRAWN_REVISION
    assert manager_.data["installed"][str(path)] == hass_storage[const.STORAGE_KEY]["data"]["installed"][str(path)] == record
    # The write itself, in place of the file and as a new one.
    with pytest.raises(manager.GuardRefused):
        await manager_._write(str(path), new, record["sha256"])
    assert path.read_bytes() == quirk_text("tuya_a", 1)
    path.unlink()
    with pytest.raises(manager.GuardRefused):
        await manager_._write(str(path), new)
    assert not path.exists()


async def test_devices_never_move_to_a_withdrawn_revision(hass: HomeAssistant, zha: Zha, repo_dir: Path, quirks_dir: Path):
    zha.add_device(IEEE_A, "_TZE200_aaaa", "TS0601", "Radar A")
    zha.add_device(IEEE_B, "_TZE200_bbbb", "TS0601", "Radar B")
    entry = await setup_entry(hass, repo_dir)
    await apply_and_reload(hass, zha, {IEEE_A: "z2m_tuya_a:TuyaA"})
    # content-2: device A moves to a file of its own, whose revision the tag withdraws; the old file
    # now serves device B.
    manifest = {**MANIFEST, "tuya_a": {**MANIFEST["tuya_a"], "fingerprints": [["_TZE200_bbbb", "TS0601"]]}}
    manifest["tuya_a_aaaa"] = {**MANIFEST["tuya_a"], "file": "quirks/z2m_tuya_a_aaaa.py"}
    write_repo(repo_dir, manifest, version=2)
    (repo_dir / "data").mkdir(exist_ok=True)
    (repo_dir / "data" / "withdrawn.toml").write_text(withdraw("tuya_a_aaaa", 2))
    REPOS[repo_dir].publish()
    manager_ = entry.runtime_data
    await manager_.async_check()
    # The old file is updated for B. A gets no file of this collection: the one for it is withdrawn.
    assert listed(hass) == {"remove": [], "update": ["z2m_tuya_a.py"], "install": []}
    flow = await start_fix(hass, issue_of(hass, "changes"))
    changes = flow["description_placeholders"]["changes"]
    assert "**Update** `z2m_tuya_a.py` (Tuya A) for Radar B." in changes
    assert "Radar A gets no quirk of this collection: the revision of `z2m_tuya_a_aaaa.py` on offer is withdrawn" in changes
    flow = await continue_fix(hass, flow, {"next_step_id": "apply"})
    assert flow["type"] is FlowResultType.ABORT and flow["reason"] == "done", flow
    assert (quirks_dir / "z2m_tuya_a.py").read_bytes() == quirk_text("tuya_a", 2)
    assert not (quirks_dir / "z2m_tuya_a_aaaa.py").exists()
    # content-3 ships a revision of A's file that is not withdrawn: the list brings it.
    zha.reload({IEEE_A: NO_QUIRK, IEEE_B: "z2m_tuya_a:TuyaA"})
    write_repo(repo_dir, manifest, version=3)
    REPOS[repo_dir].publish()
    await manager_.async_check()
    assert listed(hass) == {"remove": [], "update": ["z2m_tuya_a.py"], "install": ["z2m_tuya_a_aaaa.py"]}


async def test_a_move_names_the_file_the_device_goes_to(hass: HomeAssistant, zha: Zha, repo_dir: Path, quirks_dir: Path):
    zha.add_device(IEEE_A, "_TZE200_aaaa", "TS0601", "Radar A")
    entry = await setup_entry(hass, repo_dir)
    await apply_and_reload(hass, zha, {IEEE_A: "z2m_tuya_a:TuyaA"})
    manifest = {slug: entry for slug, entry in MANIFEST.items() if slug != "tuya_a"}
    manifest["tuya_a_aaaa"] = {**MANIFEST["tuya_a"], "file": "quirks/z2m_tuya_a_aaaa.py"}
    write_repo(repo_dir, manifest)
    REPOS[repo_dir].publish()
    await entry.runtime_data.async_check()
    assert listed(hass) == {"remove": ["z2m_tuya_a.py"], "update": [], "install": ["z2m_tuya_a_aaaa.py"]}
    changes = (await start_fix(hass, issue_of(hass, "changes")))["description_placeholders"]["changes"]
    # The old file is no longer in the manifest: the list names it by its file name.
    assert r"**Remove** `z2m_tuya_a.py` (z2m\_tuya\_a.py): another file of this collection is for one of its devices." in changes
    assert "Radar A moves to `z2m_tuya_a_aaaa.py`" in changes


async def test_an_older_copy_of_a_withdrawn_revision_gets_a_notice(hass: HomeAssistant, zha: Zha, repo_dir: Path, quirks_dir: Path):
    # Put there by hand, no record; the tag in use withdraws both the copy and the revision it ships.
    (quirks_dir / "z2m_tuya_a.py").write_bytes(OLDER_GENERATED)
    zha.add_device(IEEE_A, "_TZE200_aaaa", "TS0601")
    zha.apply_quirks({IEEE_A: "z2m_tuya_a:TuyaA"})
    copy = integration_content.effective_revision(OLDER_GENERATED)
    withdrawn = f'[[withdrawn]]\nfile = "z2m_tuya_a.py"\nrevision = "{copy}"\nreason = "Drives the valve fully open."\n'
    publish(repo_dir, 1, withdrawn=withdrawn + withdraw("tuya_a", 1))
    entry = await setup_entry(hass, repo_dir)
    issue = issue_of(hass, "withdrawn_copy", "z2m_tuya_a.py")
    assert issue.severity is ir.IssueSeverity.ERROR and not issue.is_fixable
    assert issue.translation_placeholders["revision"] == copy and issue.translation_placeholders["reason"] == "Drives the valve fully open."
    assert listed(hass) == NOTHING
    # The next tag ships a fine revision: the copy stays the user's, the notices say how to switch.
    publish(repo_dir, 2, withdrawn=withdrawn + withdraw("tuya_a", 1))
    await hass.services.async_call("button", "press", {"entity_id": BUTTON}, blocking=True)
    await hass.async_block_till_done()
    assert kinds(hass) == {"withdrawn_copy", "users_file"}
    assert (quirks_dir / "z2m_tuya_a.py").read_bytes() == OLDER_GENERATED
    # The user deletes the copy and reloads ZHA: the list brings the file of this collection.
    (quirks_dir / "z2m_tuya_a.py").unlink()
    zha.reload({IEEE_A: NO_QUIRK})
    await entry.runtime_data.async_refresh()
    assert kinds(hass) == {"changes"} and offered(hass) == ["z2m_tuya_a.py"]
    await apply_list(hass)
    assert our_issues(hass) == {}
    assert (quirks_dir / "z2m_tuya_a.py").read_bytes() == quirk_text("tuya_a", 2)


async def test_an_exact_copy_of_a_withdrawn_revision_gets_a_notice(hass: HomeAssistant, zha: Zha, repo_dir: Path, quirks_dir: Path, hass_storage):
    """The folder holds the offered file without a record (the integration was added anew): it is
    the user's file, never taken over, its withdrawn revision gets the notice of a copy."""
    (quirks_dir / "z2m_tuya_a.py").write_bytes(quirk_text("tuya_a"))
    zha.add_device(IEEE_A, "_TZE200_aaaa", "TS0601")
    zha.apply_quirks({IEEE_A: "z2m_tuya_a:TuyaA"})
    publish(repo_dir, 1, withdrawn=withdraw("tuya_a", 1))
    entry = await setup_entry(hass, repo_dir)
    issue = issue_of(hass, "withdrawn_copy", "z2m_tuya_a.py")
    assert issue.severity is ir.IssueSeverity.ERROR and issue.translation_placeholders["revision"] == quirk_revision("tuya_a")
    assert issues_of(hass, "withdrawn_installed") == []
    assert listed(hass) == NOTHING
    assert entry.runtime_data.plan.ours == frozenset()
    assert not hass_storage.get(const.STORAGE_KEY, {}).get("data", {}).get("installed")
    assert (quirks_dir / "z2m_tuya_a.py").read_bytes() == quirk_text("tuya_a")


async def test_withdrawals_are_merged_once_per_refresh(hass: HomeAssistant, zha: Zha, repo_dir: Path):
    """The refresh runs in the event loop: the withdrawals of the state in use and of a newer tag are
    merged a fixed number of times, not once per file on offer."""
    zha.add_device(IEEE_A, "_TZE200_aaaa", "TS0601")
    entry = await setup_entry(hass, repo_dir)
    merged, merges = manager.QuirkManager.withdrawn, []

    def counted(self):
        merges.append(1)
        return merged.fget(self)

    with patch.object(manager.QuirkManager, "withdrawn", property(counted)):
        await entry.runtime_data.async_refresh()
        one = len(merges)
        zha.add_device(IEEE_B, "Anyone", "B-1")
        zha.add_device(IEEE_C, "Acme", "C-1")
        # The first refresh with them downloads and checks their files.
        await entry.runtime_data.async_refresh()
        merges.clear()
        await entry.runtime_data.async_refresh()
    assert offered(hass) == ["z2m_acme_b.py", "z2m_acme_c.py", "z2m_tuya_a.py"]
    assert len(merges) == one


# Files at the tag's commit, the state bound to it.


def raw_requests(aioclient_mock) -> list[str]:
    return [str(url) for _method, url, _data, _headers in aioclient_mock.mock_calls if str(url).startswith("https://raw.githubusercontent.com/")]


async def test_files_are_read_at_the_tags_commit_never_by_its_name(hass: HomeAssistant, zha: Zha, repo: Repo, repo_dir: Path, aioclient_mock, hass_storage):
    zha.add_device(IEEE_A, "_TZE200_aaaa", "TS0601")
    entry = await setup_entry(hass, repo_dir)
    await apply_list(hass)
    # A branch named like the tag would be found under the tag's name: no request uses it.
    urls = raw_requests(aioclient_mock)
    assert urls and all(f"/{repo.commit(1)}/" in url for url in urls)
    assert not any("/content-" in url for url in urls)
    assert entry.runtime_data.source.commit == repo.commit(1)
    assert hass_storage[const.CONTENT_STORAGE_KEY]["data"]["commit"] == repo.commit(1)


async def test_a_tag_on_another_commit_is_taken_anew(hass: HomeAssistant, zha: Zha, repo: Repo, repo_dir: Path, quirks_dir: Path, caplog):
    zha.add_device(IEEE_A, "_TZE200_aaaa", "TS0601")
    entry = await setup_entry(hass, repo_dir)
    await apply_and_reload(hass, zha, {IEEE_A: "z2m_tuya_a:TuyaA"})
    # The repository was made anew: content-1 points to another commit, with other files.
    repo.moved[1] = "e" * 40
    write_repo(repo_dir, version=2)
    repo.tags[1] = tag_files(repo_dir)
    await entry.runtime_data.async_check()
    assert "is no longer in" in caplog.text
    assert (entry.runtime_data.source.tag, entry.runtime_data.source.commit) == ("content-1", "e" * 40)
    assert listed(hass) == {"remove": [], "update": ["z2m_tuya_a.py"], "install": []}
    await apply_list(hass)
    assert (quirks_dir / "z2m_tuya_a.py").read_bytes() == quirk_text("tuya_a", 2)


async def test_an_empty_tag_list_keeps_the_state(hass: HomeAssistant, zha: Zha, repo: Repo, repo_dir: Path):
    entry = await setup_entry(hass, repo_dir)
    tags = dict(repo.tags)
    repo.tags.clear()
    await entry.runtime_data.async_check()
    assert entry.runtime_data.source.tag == "content-1"
    repo.tags.update(tags)


# Withdrawals of a newer tag this Home Assistant cannot use yet.


async def test_withdrawal_in_a_tag_for_a_newer_home_assistant_applies_at_once(hass: HomeAssistant, zha: Zha, repo_dir: Path, aioclient_mock):
    zha.add_device(IEEE_A, "_TZE200_aaaa", "TS0601")
    entry = await setup_entry(hass, repo_dir)
    await apply_and_reload(hass, zha, {IEEE_A: "z2m_tuya_a:TuyaA"})
    publish(repo_dir, 2, homeassistant="2099.1.0", withdrawn=withdraw("tuya_a", 1))
    await entry.runtime_data.async_check()
    assert entry.runtime_data.source.tag == "content-1"
    notice = issue_of(hass, "withdrawn_installed", "z2m_tuya_a.py")
    assert notice.translation_placeholders["reason"] == "Drives the valve fully open."
    # Nothing to switch to on this Home Assistant release: the list removes the file.
    assert listed(hass) == {"remove": ["z2m_tuya_a.py"], "update": [], "install": []}
    assert issue_of(hass, "changes").severity is ir.IssueSeverity.ERROR
    # Read once, kept across restarts.
    await restart_with(hass, entry, repo_dir)
    assert issue_of(hass, "withdrawn_installed", "z2m_tuya_a.py")
    assert listed(hass) == {"remove": ["z2m_tuya_a.py"], "update": [], "install": []}
    assert requested(aioclient_mock, "content-2/data/withdrawn.toml") == 1
    assert (await entry.runtime_data.async_diagnostics())["content"]["withdrawn_by_a_newer_tag"] == 1
    # Once a state this release can use comes, its own list counts.
    publish(repo_dir, 3)
    await entry.runtime_data.async_check()
    assert entry.runtime_data.source.tag == "content-3"
    assert entry.runtime_data.newer_withdrawn == {}
    assert issues_of(hass, "withdrawn_installed") == []
    assert listed(hass) == {"remove": [], "update": ["z2m_tuya_a.py"], "install": []}
    assert issue_of(hass, "changes").severity is ir.IssueSeverity.WARNING


async def test_withdrawal_in_a_tag_for_a_newer_home_assistant_stops_the_install_offer(hass: HomeAssistant, zha: Zha, repo_dir: Path, quirks_dir: Path):
    zha.add_device(IEEE_A, "_TZE200_aaaa", "TS0601")
    entry = await setup_entry(hass, repo_dir)
    assert offered(hass) == ["z2m_tuya_a.py"]
    # The withdrawal comes while the dialog is open.
    flow = await start_fix(hass, issue_of(hass, "changes"))
    publish(repo_dir, 2, homeassistant="2099.1.0", withdrawn=withdraw("tuya_a", 1))
    manager_ = entry.runtime_data
    await manager_.async_check()
    assert manager_.source.tag == "content-1"
    assert our_issues(hass) == {}
    flow = await continue_fix(hass, flow, {"next_step_id": "apply"})
    assert flow["type"] is FlowResultType.ABORT and flow["reason"] == "stale", flow
    assert not (quirks_dir / "z2m_tuya_a.py").exists()


async def test_withdrawals_of_a_tag_for_another_release_apply_too(hass: HomeAssistant, zha: Zha, repo_dir: Path):
    zha.add_device(IEEE_A, "_TZE200_aaaa", "TS0601")
    entry = await setup_entry(hass, repo_dir)
    await apply_and_reload(hass, zha, {IEEE_A: "z2m_tuya_a:TuyaA"})
    # Built for another guard (or content format): the fields of withdrawn.toml never change.
    publish(repo_dir, 2, guard_id="f" * 64, withdrawn=withdraw("tuya_a", 1))
    await entry.runtime_data.async_check()
    assert entry.runtime_data.source.tag == "content-1"
    assert issue_of(hass, "withdrawn_installed", "z2m_tuya_a.py")
    assert listed(hass) == {"remove": ["z2m_tuya_a.py"], "update": [], "install": []}
    # A list this release cannot read is left alone.
    publish(repo_dir, 3, guard_id="f" * 64, withdrawn=withdraw("tuya_a", 1).replace("revision =", "revisions ="))
    await entry.runtime_data.async_check()
    assert issues_of(hass, "withdrawn_installed") == []
    assert listed(hass) == NOTHING


# Tags that cannot be used, odd answers.


async def test_a_tag_made_anew_on_another_commit_is_examined_anew(hass: HomeAssistant, zha: Zha, repo: Repo, repo_dir: Path):
    zha.add_device(IEEE_A, "_TZE200_aaaa", "TS0601")
    entry = await setup_entry(hass, repo_dir)
    publish(repo_dir, 2, homeassistant="2099.1.0")
    await entry.runtime_data.async_check()
    assert entry.runtime_data._skipped() == {"content-2": "needs Home Assistant 2099.1.0 or newer"}
    # content-2 is deleted after an incident; the next tag from main gets its number again.
    repo.moved[2] = "d" * 40
    (repo_dir / "hacs.json").write_text(json.dumps({"name": "xquirks", "homeassistant": "2026.1.0"}))
    repo.tags[2] = tag_files(repo_dir)
    await entry.runtime_data.async_check()
    assert (entry.runtime_data.source.tag, entry.runtime_data.source.commit) == ("content-2", "d" * 40)


async def test_a_broken_newest_tag_leaves_the_older_ones_usable(hass: HomeAssistant, zha: Zha, repo: Repo, repo_dir: Path, aioclient_mock):
    zha.add_device(IEEE_A, "_TZE200_aaaa", "TS0601")
    repo.publish()
    publish(repo_dir, 2)
    del repo.tags[2]["hacs.json"]
    entry = await setup_entry(hass, repo_dir, publish=False)
    manager_ = entry.runtime_data
    assert manager_.source.tag == "content-1"
    assert offered(hass) == ["z2m_tuya_a.py"]
    assert manager_._skipped()["content-2"].startswith("cannot be read (") and "hacs.json: HTTP 404" in manager_._skipped()["content-2"]
    # Content at a commit never changes: the broken tag is not read again.
    reads = requested(aioclient_mock, "content-2/content.json")
    publish(repo_dir, 3, homeassistant="2099.1.0")
    await manager_.async_check()
    assert requested(aioclient_mock, "content-2/content.json") == reads


async def test_a_server_error_is_no_broken_tag(hass: HomeAssistant, zha: Zha, repo: Repo, repo_dir: Path):
    zha.add_device(IEEE_A, "_TZE200_aaaa", "TS0601")
    repo.publish()
    publish(repo_dir, 2)
    hacs_json = repo.tags[2]["hacs.json"]
    repo.tags[2]["hacs.json"] = 503
    entry = await setup_entry(hass, repo_dir, publish=False)
    manager_ = entry.runtime_data
    assert manager_.source.tag is None
    assert "hacs.json: HTTP 503" in issue_of(hass, "no_content_state").translation_placeholders["reason"]
    assert "content-2" not in manager_._skipped()
    repo.tags[2]["hacs.json"] = hacs_json
    await manager_.async_check()
    assert manager_.source.tag == "content-2"


async def test_a_malformed_manifest_entry_is_never_taken(hass: HomeAssistant, zha: Zha, repo: Repo, repo_dir: Path, hass_storage):
    zha.add_device(IEEE_A, "_TZE200_aaaa", "TS0601")
    entry = await setup_entry(hass, repo_dir)
    manager_ = entry.runtime_data
    publish(repo_dir, 2)
    manifest = json.loads(repo.tags[2]["manifest.json"])
    del manifest["acme_b"]["fingerprints"]
    repo.tags[2]["manifest.json"] = json.dumps(manifest).encode()
    await manager_.async_check()
    assert manager_.source.tag == "content-1"
    assert "manifest entry acme_b: fingerprints missing or malformed" in manager_._skipped()["content-2"]
    assert hass_storage[const.CONTENT_STORAGE_KEY]["data"]["tag"] == "content-1"
    await manager_.async_refresh()
    assert offered(hass) == ["z2m_tuya_a.py"]


@pytest.mark.parametrize(
    ("response", "error"),
    [
        ({"status": 429, "headers": {"Retry-After": "9" * 400}}, "rate limit"),
        ({"status": 429, "headers": {"Retry-After": "999999999999"}}, "rate limit"),
        ({"status": 403, "headers": {"X-RateLimit-Remaining": "0", "X-RateLimit-Reset": "9" * 12}}, "rate limit"),
        ({"status": 403, "headers": {"X-RateLimit-Remaining": "0", "X-RateLimit-Reset": "9" * 30}}, "HTTP 403"),
        ({"json": 5}, "not a list of refs"),
        ({"text": "null"}, "not a list of refs"),
        ({"json": [{"ref": "refs/tags/content-2"}, "refs/tags/content-3"]}, "not a list of refs"),
        # Depending on the Python build this nesting either exceeds the recursion limit or decodes.
        ({"text": "[" * 100000 + "]" * 100000}, ("decoding a JSON array", "not a list of refs")),
        ({"text": "[" * 50 + "]" * 50}, "not a list of refs"),
    ],
)
async def test_odd_tag_list_answers_fail_the_check_only(hass: HomeAssistant, zha: Zha, repo_dir: Path, aioclient_mock, response, error):
    entry = await setup_entry(hass, repo_dir)
    manager_ = entry.runtime_data
    aioclient_mock.clear_requests()
    aioclient_mock.get(TAGS_URL, **response)
    manager_._content.pop("etag", None)
    await manager_.async_check()
    assert manager_.last_check["result"] == "failed"
    assert any(e in manager_.last_check["error"] for e in ((error,) if isinstance(error, str) else error))
    assert manager_.source.tag == "content-1"
    # A rate limit is followed for a day at most.
    assert manager_._retry_after <= time.time() + 24 * 3600


async def test_refs_in_other_shapes_are_left_out(hass: HomeAssistant, zha: Zha, repo: Repo, repo_dir: Path, aioclient_mock):
    entry = await setup_entry(hass, repo_dir)
    manager_ = entry.runtime_data
    odd = [
        {"ref": "refs/tags/content-" + "9" * 5000, "object": {"sha": "a" * 40, "type": "commit"}},
        {"ref": "refs/tags/content-7", "object": {"sha": "not a sha", "type": "commit"}},
        {"ref": "refs/tags/content-8", "object": {"sha": "b" * 40, "type": "tree"}},
        # An annotated tag: content.yml writes lightweight ones only.
        {"ref": "refs/tags/content-9", "object": {"sha": "c" * 40, "type": "tag"}},
        {"ref": "refs/tags/content-10"},
    ]
    aioclient_mock.clear_requests()
    aioclient_mock.get(TAGS_URL, json=[repo.ref(1), *odd])
    repo.register()
    manager_._content.pop("etag", None)
    await manager_.async_check()
    assert manager_.last_check == {"time": manager_.last_check["time"], "result": "newest state content-1 in use", "error": None}


# What the diagnostics and the stored state hold.


async def test_diagnostics_download_nothing(hass: HomeAssistant, zha: Zha, repo_dir: Path, aioclient_mock):
    zha.add_device(IEEE_A, "_TZE200_aaaa", "TS0601")
    entry = await setup_entry(hass, repo_dir)
    await apply_and_reload(hass, zha, {IEEE_A: "z2m_tuya_a:TuyaA"})
    publish(repo_dir, 2)
    await entry.runtime_data.async_check()
    # The check before the list downloaded the file: the diagnostics have its entity changes.
    assert requested(aioclient_mock, "content-2/quirks/z2m_tuya_a.py") == 1
    data = await diagnostics.async_get_config_entry_diagnostics(hass, entry)
    assert data["change_list"]["update"] == ["z2m_tuya_a.py"]
    assert data["offered_changes"]["z2m_tuya_a.py"]["comments_only"] is True
    assert data["content"]["guard"] == GUARD_ID
    # A download no longer kept is not fetched again for them; the dialog downloads it.
    entry.runtime_data._downloads.clear()
    data = await diagnostics.async_get_config_entry_diagnostics(hass, entry)
    assert data["offered_changes"] == {"z2m_tuya_a.py": "not downloaded yet"}
    assert requested(aioclient_mock, "content-2/quirks/z2m_tuya_a.py") == 1
    await start_fix(hass, issue_of(hass, "changes"))
    assert requested(aioclient_mock, "content-2/quirks/z2m_tuya_a.py") == 2
