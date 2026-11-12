"""The guard at the user's end: a file with code no quirk file of the collection holds, or with targets or
names outside its manifest entry, is never listed or written. Every write checks again; only the
undo of a failed list puts back, unchecked, the bytes the same list took away. A tag built for
another guard waits for its release."""

from __future__ import annotations

import ast
import errno
import os
import uuid
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import issue_registry as ir
from homeassistant.util import dt as dt_util

from . import integration
from .conftest import GUARD_ID, MANIFEST, REPOS, Zha, apply_list, continue_fix, issue_of, issues_of, listed, offered, our_issues, quirk_text, setup_entry, start_fix, write_repo
from .integration import DOMAIN, const, content, diagnostics, manager
from .integration import plan as plans
from .test_content import IEEE_A, IEEE_B, NOTHING, OLDER_GENERATED, apply_and_reload, folder_writes, not_now, publish, requested, restart_with, updated_to_2, withdraw

sha256 = content.sha256
# Frozen copies of generated quirks (fixtures/README.md).
FROZEN = Path(__file__).resolve().parent / "fixtures"


def poisoned(slug: str, version: int = 1) -> bytes:
    """A quirk file with code no quirk file of the collection holds."""
    return quirk_text(slug, version) + b"import os\n"


def poison(repo_dir: Path, slug: str = "tuya_a", version: int = 1) -> bytes:
    """The working tree's file for slug, poisoned; the next publish carries it with its sha256."""
    data = poisoned(slug, version)
    (repo_dir / "quirks" / f"z2m_{slug}.py").write_bytes(data)
    return data


@contextmanager
def guard_turns(manager_):
    """From now on the guard refuses everything it checks (the files of the list were checked before)."""
    manager_._verdicts.clear()
    with patch.object(manager_.guard, "problems", return_value=("line 1: refused for the test",)):
        yield


@contextmanager
def guard_turns_at_the_write(manager_):
    """From now on the check before each write refuses everything; the verdicts the plan reads stay as they were."""

    async def refused(content: bytes, name: str) -> tuple[str, ...]:
        return ("line 1: refused for the test",)

    with patch.object(manager_, "_checked", refused):
        yield


async def test_refused_file_is_never_listed_or_written(hass: HomeAssistant, zha: Zha, repo_dir: Path, quirks_dir: Path):
    zha.add_device(IEEE_A, "_TZE200_aaaa", "TS0601")
    zha.add_device(IEEE_B, "Anyone", "B-1")
    bad = poison(repo_dir)
    entry = await setup_entry(hass, repo_dir)
    # The other file is listed as ever.
    assert listed(hass) == {"remove": [], "update": [], "install": ["z2m_acme_b.py"]}
    issue = issue_of(hass, "refused", "z2m_tuya_a.py")
    assert not issue.is_fixable and issue.severity is ir.IssueSeverity.ERROR
    assert issue.translation_placeholders == {"file": "z2m_tuya_a.py", "quirk": "Tuya A", "revision": content.effective_revision(bad)}
    assert list(quirks_dir.iterdir()) == []
    data = await diagnostics.async_get_config_entry_diagnostics(hass, entry)
    refused = data["refused_by_the_guard"]["z2m_tuya_a.py"]
    assert refused["sha256"] == sha256(bad)
    assert refused["problems"] == ["line 7: import os"]
    assert data["change_list"]["install"] == ["z2m_acme_b.py"]
    assert data["content"]["guard"] == GUARD_ID
    # Applying the list writes the other file only.
    await apply_and_reload(hass, zha, {IEEE_B: "z2m_acme_b:AcmeB"})
    assert [p.name for p in quirks_dir.iterdir()] == ["z2m_acme_b.py"]
    # A tag with a clean file ends the notice and brings the file.
    write_repo(repo_dir, version=2)
    await restart_with(hass, entry, repo_dir)
    assert listed(hass) == {"remove": [], "update": ["z2m_acme_b.py"], "install": ["z2m_tuya_a.py"]}
    assert not issues_of(hass, "refused")


async def test_review_payload_in_a_real_quirk_is_refused(hass: HomeAssistant, zha: Zha, repo_dir: Path, quirks_dir: Path):
    """A real quirk passes the guard the integration ships; the payload of the supply-chain review does not."""
    real = real_quirk(repo_dir, TS0105)
    zha.add_device(IEEE_A, "Tuya", "TS0105")
    entry = await setup_entry(hass, repo_dir)
    assert offered(hass) == ["z2m_tuya_a.py"]
    payload = "[__import__('os').environ.get('XQ_MARK') and open(__import__('os').environ['XQ_MARK'], 'w').write('payload ran on import'), 3][1]"
    (repo_dir / "quirks" / "z2m_tuya_a.py").write_bytes(real.replace(b"dp_id=3,", f"dp_id={payload},".encode(), 1))
    await restart_with(hass, entry, repo_dir)
    assert offered(hass) == []
    assert issue_of(hass, "refused", "z2m_tuya_a.py")
    assert entry.runtime_data.summary()["refused_by_the_guard"]["z2m_tuya_a.py"]["problems"][0].endswith("Subscript expression")
    assert list(quirks_dir.iterdir()) == []


# What a file targets and leaves to other files stays inside the manifest entry it is offered for.

# The manifest entry of z2m_tuya_ts0105.py as content tags hold it: the fingerprints it targets, the
# name it leaves to another file.
TS0105 = {"tuya_a": {**MANIFEST["tuya_a"], "fingerprints": [[None, "TS0105"], ["Tuya", "TS0105"]], "claimed_elsewhere": [["_TZE600_ogyg1y6b", "TS0105"]],
                     "endpoints": {"1": [0xEF00]}}}


def real_quirk(repo_dir: Path, manifest: dict, edit: tuple[bytes, bytes] | None = None) -> bytes:
    """The working tree with a real quirk (z2m_tuya_ts0105.py) as z2m_tuya_a.py under this manifest."""
    data = (FROZEN / "z2m_tuya_ts0105.py.txt").read_bytes()
    if edit:
        assert edit[0] in data
        data = data.replace(*edit, 1)
    write_repo(repo_dir, manifest)
    (repo_dir / "quirks" / "z2m_tuya_a.py").write_bytes(data)
    return data


async def test_target_outside_the_manifest_entry_is_refused(hass: HomeAssistant, zha: Zha, repo_dir: Path, quirks_dir: Path):
    # The entry lists Tuya's name only; the file also applies to any manufacturer.
    real_quirk(repo_dir, {"tuya_a": {**TS0105["tuya_a"], "fingerprints": [["Tuya", "TS0105"]]}})
    zha.add_device(IEEE_A, "Tuya", "TS0105")
    entry = await setup_entry(hass, repo_dir)
    assert offered(hass) == []
    assert issue_of(hass, "refused", "z2m_tuya_a.py")
    problems = entry.runtime_data.summary()["refused_by_the_guard"]["z2m_tuya_a.py"]["problems"]
    assert "targets (None, 'TS0105') (a manufacturer wildcard), which its manifest entry does not list" in problems[0]
    assert list(quirks_dir.iterdir()) == []


async def test_chain_without_the_upstream_first_filter_is_refused(hass: HomeAssistant, zha: Zha, repo_dir: Path, quirks_dir: Path):
    real_quirk(repo_dir, TS0105, (b"    .filter(no_builtin_quirk)\n", b""))
    zha.add_device(IEEE_A, "Tuya", "TS0105")
    entry = await setup_entry(hass, repo_dir)
    assert offered(hass) == []
    assert entry.runtime_data.summary()["refused_by_the_guard"]["z2m_tuya_a.py"]["problems"][0].endswith("a builder chain without exactly one .filter(no_builtin_quirk)")
    assert list(quirks_dir.iterdir()) == []


async def test_alias_onto_devices_it_is_not_offered_for_is_refused(hass: HomeAssistant, zha: Zha, repo_dir: Path, quirks_dir: Path):
    """The alias payload of the guard bypass review: offered for one device, aliasing a wildcard."""
    alias = (FROZEN / "z2m_alias_moes_zc_hm.py.txt").read_text()
    payload = alias.replace("'fingerprints': [('JM720ES-EF-3.0', 'TS0601')]", "'fingerprints': [('JM720ES-EF-3.0', 'TS0601'), (None, 'TS0601')]", 1)
    entry_ = {**MANIFEST["tuya_a"], "fingerprints": [["JM720ES-EF-3.0", "TS0601"]], "target": ["_TZE200_hr0tdd47", "TS0601"]}
    write_repo(repo_dir, {"tuya_a": entry_})
    (repo_dir / "quirks" / "z2m_tuya_a.py").write_text(alias)
    zha.add_device(IEEE_A, "JM720ES-EF-3.0", "TS0601")
    entry = await setup_entry(hass, repo_dir)
    # The alias as built is offered; the one that also covers every TS0601 is not.
    assert offered(hass) == ["z2m_tuya_a.py"]
    (repo_dir / "quirks" / "z2m_tuya_a.py").write_text(payload)
    await restart_with(hass, entry, repo_dir)
    assert offered(hass) == []
    assert issue_of(hass, "refused", "z2m_tuya_a.py")
    assert list(quirks_dir.iterdir()) == []


async def test_verdict_follows_the_manifest_entry_not_only_the_content(hass: HomeAssistant, zha: Zha, repo_dir: Path):
    real_quirk(repo_dir, TS0105)
    zha.add_device(IEEE_A, "Tuya", "TS0105")
    entry = await setup_entry(hass, repo_dir)
    assert offered(hass) == ["z2m_tuya_a.py"]
    # The same bytes under an entry without the wildcard: checked again, refused.
    real_quirk(repo_dir, {"tuya_a": {**TS0105["tuya_a"], "fingerprints": [["Tuya", "TS0105"]]}})
    REPOS[repo_dir].publish()
    await entry.runtime_data.async_check()
    assert entry.runtime_data.source.tag == "content-2"
    assert offered(hass) == []
    assert issue_of(hass, "refused", "z2m_tuya_a.py")


CLAIMED_ELSEWHERE_REFUSED = "line 1: CLAIMED_ELSEWHERE other than its manifest entry's claimed_elsewhere"


async def test_claimed_elsewhere_other_than_the_manifest_entrys_is_refused(hass: HomeAssistant, zha: Zha, repo_dir: Path, quirks_dir: Path):
    """The integration reads what an installed file claims from its manifest entry: the same bytes
    pass under the entry the manifest holds, an entry that does not name what the file leaves to
    another file refuses them."""
    real_quirk(repo_dir, TS0105)
    zha.add_device(IEEE_A, "Tuya", "TS0105")
    entry = await setup_entry(hass, repo_dir)
    assert offered(hass) == ["z2m_tuya_a.py"]
    real_quirk(repo_dir, {"tuya_a": {**TS0105["tuya_a"], "claimed_elsewhere": []}})
    REPOS[repo_dir].publish()
    await entry.runtime_data.async_check()
    assert entry.runtime_data.source.tag == "content-2"
    assert offered(hass) == []
    assert issue_of(hass, "refused", "z2m_tuya_a.py")
    assert entry.runtime_data.summary()["refused_by_the_guard"]["z2m_tuya_a.py"]["problems"] == [CLAIMED_ELSEWHERE_REFUSED]
    assert list(quirks_dir.iterdir()) == []


@pytest.mark.parametrize(
    ("slug", "device", "edit"),
    [
        # The entry leaves ("Other", "B-1") to another file: the file leaves nothing, or one more name.
        ("acme_b", ("Anyone", "B-1"), (b"CLAIMED_ELSEWHERE = [('Other', 'B-1')]\n", b"")),
        ("acme_b", ("Anyone", "B-1"), (b"[('Other', 'B-1')]", b"[('Other', 'B-1'), ('Acme', 'B-1')]")),
        # The entry leaves nothing to other files.
        ("tuya_a", ("_TZE200_aaaa", "TS0601"), (b"# version 1\n", b"# version 1\nCLAIMED_ELSEWHERE = {('_TZE200_bbbb', 'TS0601')}\n")),
    ],
)
async def test_file_whose_claimed_elsewhere_differs_from_its_entry_is_refused(hass: HomeAssistant, zha: Zha, repo_dir: Path, quirks_dir: Path, slug, device, edit):
    path = repo_dir / "quirks" / f"z2m_{slug}.py"
    assert edit[0] in path.read_bytes()
    path.write_bytes(path.read_bytes().replace(*edit))
    zha.add_device(IEEE_A, *device)
    entry = await setup_entry(hass, repo_dir)
    assert offered(hass) == []
    assert issue_of(hass, "refused", f"z2m_{slug}.py")
    assert entry.runtime_data.summary()["refused_by_the_guard"][f"z2m_{slug}.py"]["problems"] == [CLAIMED_ELSEWHERE_REFUSED]
    assert list(quirks_dir.iterdir()) == []


# Refused files and what is in the folder.


async def test_refused_update_leaves_the_installed_file(hass: HomeAssistant, zha: Zha, repo_dir: Path, quirks_dir: Path):
    zha.add_device(IEEE_A, "_TZE200_aaaa", "TS0601")
    entry = await setup_entry(hass, repo_dir)
    await apply_and_reload(hass, zha, {IEEE_A: "z2m_tuya_a:TuyaA"})
    write_repo(repo_dir, version=2)
    poison(repo_dir, version=2)
    REPOS[repo_dir].publish()
    manager_ = entry.runtime_data
    await manager_.async_check()
    assert manager_.source.tag == "content-2"
    # Not listed: the installed copy stays while its device runs it and no other file takes it.
    assert listed(hass) == NOTHING
    assert manager_.plan.refused == ["z2m_tuya_a.py"]
    assert issue_of(hass, "refused", "z2m_tuya_a.py")
    path = quirks_dir / "z2m_tuya_a.py"
    assert path.read_bytes() == quirk_text("tuya_a", 1)
    # The next clean tag brings the update.
    publish(repo_dir, 3)
    await manager_.async_check()
    assert not issues_of(hass, "refused")
    assert listed(hass) == {"remove": [], "update": ["z2m_tuya_a.py"], "install": []}
    await apply_list(hass)
    assert path.read_bytes() == quirk_text("tuya_a", 3)


async def test_refused_replacement_is_not_listed(hass: HomeAssistant, zha: Zha, repo_dir: Path, quirks_dir: Path):
    """The device's name moves to a new file the guard refuses: neither the new file nor the removal
    of the old one is listed, the old file keeps the device."""
    zha.add_device(IEEE_A, "_TZE200_aaaa", "TS0601")
    entry = await setup_entry(hass, repo_dir)
    await apply_and_reload(hass, zha, {IEEE_A: "z2m_tuya_a:TuyaA"})
    manifest = {slug: entry for slug, entry in MANIFEST.items() if slug != "tuya_a"}
    manifest["tuya_a_aaaa"] = {**MANIFEST["tuya_a"], "file": "quirks/z2m_tuya_a_aaaa.py"}
    write_repo(repo_dir, manifest)
    poison(repo_dir, "tuya_a_aaaa")
    await restart_with(hass, entry, repo_dir)
    assert listed(hass) == NOTHING
    assert issue_of(hass, "refused", "z2m_tuya_a_aaaa.py")
    assert [p.name for p in quirks_dir.iterdir()] == ["z2m_tuya_a.py"]


async def test_refused_file_never_touches_a_copy_put_there_by_hand(hass: HomeAssistant, zha: Zha, repo_dir: Path, quirks_dir: Path, aioclient_mock):
    """A file of the user under the name of a refused one is left alone. The guard checks the files a
    list could write: once the user deleted the copy it refuses the offered file, nothing is written."""
    (quirks_dir / "z2m_tuya_a.py").write_bytes(OLDER_GENERATED)
    zha.add_device(IEEE_A, "_TZE200_aaaa", "TS0601")
    poison(repo_dir)
    entry = await setup_entry(hass, repo_dir)
    assert listed(hass) == NOTHING
    assert issue_of(hass, "users_file", "z2m_tuya_a.py")
    assert requested(aioclient_mock, "/quirks/z2m_tuya_a.py") == 0
    assert (quirks_dir / "z2m_tuya_a.py").read_bytes() == OLDER_GENERATED
    (quirks_dir / "z2m_tuya_a.py").unlink()
    zha.reload()
    await entry.runtime_data.async_refresh()
    assert issue_of(hass, "refused", "z2m_tuya_a.py")
    assert issues_of(hass, "users_file") == []
    assert listed(hass) == NOTHING
    assert list(quirks_dir.iterdir()) == []


async def test_refused_file_put_there_by_hand_never_becomes_ours(hass: HomeAssistant, zha: Zha, repo_dir: Path, quirks_dir: Path, hass_storage):
    """An exact copy of the refused file, put there by hand, ZHA runs it: it stays the user's (no
    record), so no list ever writes or deletes it."""
    bad = poison(repo_dir)
    (quirks_dir / "z2m_tuya_a.py").write_bytes(bad)
    zha.add_device(IEEE_A, "_TZE200_aaaa", "TS0601")
    zha.apply_quirks({IEEE_A: "z2m_tuya_a:TuyaA"})
    entry = await setup_entry(hass, repo_dir)
    assert listed(hass) == NOTHING
    assert issue_of(hass, "users_file", "z2m_tuya_a.py")
    assert entry.runtime_data.plan.ours == frozenset()
    assert not hass_storage.get(const.STORAGE_KEY, {}).get("data", {}).get("installed")
    assert (quirks_dir / "z2m_tuya_a.py").read_bytes() == bad


async def test_refused_revision_is_no_way_out_of_a_withdrawn_one(hass: HomeAssistant, zha: Zha, repo_dir: Path, quirks_dir: Path):
    """The installed revision is withdrawn, the one on offer refused: the list removes the file, the refused one is not written."""
    entry = await updated_to_2(hass, zha, repo_dir)
    write_repo(repo_dir, version=3)
    poison(repo_dir, version=3)
    (repo_dir / "data" / "withdrawn.toml").write_text(withdraw("tuya_a", 2))
    REPOS[repo_dir].publish()
    await entry.runtime_data.async_check()
    assert issue_of(hass, "refused", "z2m_tuya_a.py")
    assert issue_of(hass, "withdrawn_installed", "z2m_tuya_a.py")
    assert listed(hass) == {"remove": ["z2m_tuya_a.py"], "update": [], "install": []}
    flow = await start_fix(hass, issue_of(hass, "changes"))
    assert "`z2m_tuya_a.py` cannot be written: the guard refused it" in flow["description_placeholders"]["changes"]
    flow = await continue_fix(hass, flow, {"next_step_id": "apply"})
    assert flow["type"] is FlowResultType.ABORT and flow["reason"] == "done", flow
    assert list(quirks_dir.iterdir()) == []


# Each write into the custom quirks folder checks again (the guard turns between the dialog and "Apply all").


async def test_install_checks_again_before_it_writes(hass: HomeAssistant, zha: Zha, repo_dir: Path, quirks_dir: Path):
    zha.add_device(IEEE_A, "_TZE200_aaaa", "TS0601")
    entry = await setup_entry(hass, repo_dir)
    flow = await start_fix(hass, issue_of(hass, "changes"))
    with guard_turns(entry.runtime_data):
        flow = await continue_fix(hass, flow, {"next_step_id": "apply"})
    # The apply plans again first: without the refused file the list is another one.
    assert flow["type"] is FlowResultType.ABORT and flow["reason"] == "stale", flow
    assert list(quirks_dir.iterdir()) == []
    assert listed(hass) == NOTHING
    assert issue_of(hass, "refused", "z2m_tuya_a.py")


async def test_update_checks_again_before_it_writes(hass: HomeAssistant, zha: Zha, repo_dir: Path, quirks_dir: Path):
    zha.add_device(IEEE_A, "_TZE200_aaaa", "TS0601")
    plug = zha.add_device(IEEE_B, "Anyone", "B-1")
    entry = await setup_entry(hass, repo_dir)
    await apply_and_reload(hass, zha, {IEEE_A: "z2m_tuya_a:TuyaA", IEEE_B: "z2m_acme_b:AcmeB"})
    # The plug is gone: its file goes in the list, before the update.
    zha.remove_device(plug)
    publish(repo_dir, 2)
    manager_ = entry.runtime_data
    await manager_.async_check()
    assert listed(hass) == {"remove": ["z2m_acme_b.py"], "update": ["z2m_tuya_a.py"], "install": []}
    path = str(quirks_dir / "z2m_tuya_a.py")
    record = dict(manager_.data["installed"][path])
    with guard_turns_at_the_write(manager_), folder_writes() as writes:
        flow = await apply_list(hass, expect=("failed",))
    assert flow["description_placeholders"]["failed"] == f"`z2m_tuya_a.py`: {manager.REFUSED}"
    # Nothing written, not even the removal: the check runs before the first step.
    assert writes == [] and Path(path).read_bytes() == quirk_text("tuya_a", 1)
    assert (quirks_dir / "z2m_acme_b.py").read_bytes() == quirk_text("acme_b", 1)
    # The record still names version 1, with nothing kept as previous.
    assert manager_.data["installed"][path] == record
    assert listed(hass) == {"remove": ["z2m_acme_b.py"], "update": ["z2m_tuya_a.py"], "install": []}


async def test_replace_checks_again_before_it_writes(hass: HomeAssistant, zha: Zha, repo_dir: Path, quirks_dir: Path):
    zha.add_device(IEEE_A, "_TZE200_aaaa", "TS0601")
    entry = await setup_entry(hass, repo_dir)
    await apply_and_reload(hass, zha, {IEEE_A: "z2m_tuya_a:TuyaA"})
    manifest = {slug: entry for slug, entry in MANIFEST.items() if slug != "tuya_a"}
    manifest["tuya_a_aaaa"] = {**MANIFEST["tuya_a"], "file": "quirks/z2m_tuya_a_aaaa.py"}
    write_repo(repo_dir, manifest)
    await restart_with(hass, entry, repo_dir)
    # The device moves to the new file: the old one goes in the same list.
    assert listed(hass) == {"remove": ["z2m_tuya_a.py"], "update": [], "install": ["z2m_tuya_a_aaaa.py"]}
    with guard_turns_at_the_write(entry.runtime_data), folder_writes() as writes:
        flow = await apply_list(hass, expect=("failed",))
    assert flow["description_placeholders"]["failed"] == f"`z2m_tuya_a_aaaa.py`: {manager.REFUSED}"
    # Neither the new file nor the removal of the old one, which comes first in the list: the check
    # runs before the first step, there is nothing to undo.
    assert writes == [] and [p.name for p in quirks_dir.iterdir()] == ["z2m_tuya_a.py"]
    assert listed(hass) == {"remove": ["z2m_tuya_a.py"], "update": [], "install": ["z2m_tuya_a_aaaa.py"]}


def test_every_write_into_the_quirks_folder_goes_through_the_guard():
    """files.write_new and files.replace write new content in QuirkManager._write only, which checks
    first (_refuse: the guard, then the withdrawn revisions). The undo of a list calls them with the
    bytes the same list read from the folder before its first step (step.old) and nothing else."""
    tree = ast.parse(Path(integration.manager.__file__).read_text())
    users = {
        function.name
        for function in ast.walk(tree)
        if isinstance(function, (ast.FunctionDef, ast.AsyncFunctionDef))
        for node in ast.walk(function)
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == "files" and node.attr in ("write_new", "replace")
    }
    assert users == {"_write", "_undo"}
    functions = {f.name: f for f in ast.walk(tree) if isinstance(f, ast.AsyncFunctionDef)}
    first = functions["_write"].body[1]  # after the docstring
    assert ast.unparse(first) == "await self._refuse(path, content)"
    refuse = functions["_refuse"].body[2]  # after the docstring and the name
    assert isinstance(refuse, ast.If) and ast.unparse(refuse.test).startswith("(problems := (await self._checked(content, ")
    # The undo: run(files.write_new or files.replace, path, content, ...) with the step's old bytes.
    writes = [
        node
        for node in ast.walk(functions["_undo"])
        if isinstance(node, ast.Call) and node.args and ast.unparse(node.args[0]) in ("files.write_new", "files.replace")
    ]
    assert len(writes) == 2 and all(ast.unparse(node.args[2]) == "step.old" for node in writes)
    # Those are read from the folder while they have the sha256 the plan saw, before the first step.
    apply = functions["async_apply"]
    olds = [node.value for node in ast.walk(apply) if isinstance(node, ast.Assign) and [ast.unparse(t) for t in node.targets] == ["old"]]
    assert len(olds) == 2 and all(ast.unparse(value).startswith("await self._read_ours(") for value in olds)
    steps = [node for node in ast.walk(apply) if isinstance(node, ast.Call) and ast.unparse(node.func) == "Step"]
    assert steps and all(ast.unparse(keyword.value) == "old" for node in steps for keyword in node.keywords if keyword.arg == "old")


@pytest.mark.parametrize("change", ["remove", "update"])
async def test_the_undo_puts_back_a_withdrawn_revision_without_the_guard(hass: HomeAssistant, zha: Zha, repo_dir: Path, quirks_dir: Path, hass_storage, change):
    """A later step of the list fails: the undo puts back the bytes of the withdrawn revision the list
    took away, although a new write of them would be refused. It writes only what the same list read
    from the folder."""
    zha.add_device(IEEE_A, "_TZE200_aaaa", "TS0601")
    entry = await setup_entry(hass, repo_dir)
    await apply_and_reload(hass, zha, {IEEE_A: "z2m_tuya_a:TuyaA"})
    manager_ = entry.runtime_data
    path = quirks_dir / "z2m_tuya_a.py"
    record = dict(manager_.data["installed"][str(path)])
    zha.add_device(IEEE_B, "Anyone", "B-1")
    if change == "remove":
        # The next tag no longer ships the file and withdraws the installed revision: without a
        # manifest entry the guard refuses these bytes as well.
        write_repo(repo_dir, {**MANIFEST, "tuya_a": {**MANIFEST["tuya_a"], "file": None}}, version=2)
        (repo_dir / "data").mkdir(exist_ok=True)
        (repo_dir / "data" / "withdrawn.toml").write_text(withdraw("tuya_a", 1))
        REPOS[repo_dir].publish()
    else:
        publish(repo_dir, 2, withdrawn=withdraw("tuya_a", 1))
    await manager_.async_check()
    expected = {"remove": [], "update": [], "install": ["z2m_acme_b.py"], change: ["z2m_tuya_a.py"]}
    assert listed(hass) == expected
    assert issue_of(hass, "changes").severity is ir.IssueSeverity.ERROR
    write_new = integration.files.write_new

    def disk_full(target: str, data: bytes) -> None:
        if os.path.basename(target) == "z2m_acme_b.py":
            raise OSError(errno.ENOSPC, os.strerror(errno.ENOSPC), target)
        write_new(target, data)

    with patch.object(integration.files, "write_new", disk_full):
        flow = await apply_list(hass, expect=("failed",))
    assert flow["description_placeholders"]["failed"] == f"`z2m_acme_b.py`: {os.strerror(errno.ENOSPC)}"
    # As before the list: the withdrawn revision back in place, its record, no change waits for ZHA.
    assert path.read_bytes() == quirk_text("tuya_a", 1)
    assert not (quirks_dir / "z2m_acme_b.py").exists()
    assert manager_.data["installed"][str(path)] == record
    assert hass_storage[const.STORAGE_KEY]["data"]["installed"][str(path)] == record
    assert manager_.data["pending"]["changes"] == [] and zha.reloads == 1
    # A new write of the same bytes is refused.
    with pytest.raises(manager.GuardRefused) as refused:
        await manager_._write(str(path), quirk_text("tuya_a", 1), record["sha256"])
    assert refused.value.reason == (manager.REFUSED if change == "remove" else manager.WITHDRAWN_REVISION)
    # The list stays for another try.
    assert listed(hass) == expected


# Tags built for another guard (or content format): skipped, no security notice.


async def test_tag_for_another_guard_is_skipped_without_a_notice(hass: HomeAssistant, zha: Zha, repo_dir: Path, aioclient_mock):
    zha.add_device(IEEE_A, "_TZE200_aaaa", "TS0601")
    entry = await setup_entry(hass, repo_dir)
    publish(repo_dir, 2, guard_id="f" * 64)
    publish(repo_dir, 3, guard_id=None)
    manager_ = entry.runtime_data
    await manager_.async_check()
    assert manager_.source.tag == "content-1"
    data = await diagnostics.async_get_config_entry_diagnostics(hass, entry)
    assert data["content"]["skipped_tags"] == {
        "content-2": f"was built for another xquirks release (guard {'f' * 12}, this release has {GUARD_ID[:12]})",
        "content-3": "states no guard",
    }
    assert offered(hass) == ["z2m_tuya_a.py"]
    assert not issues_of(hass, "refused")
    # Neither its manifest nor its files are read.
    assert requested(aioclient_mock, "content-2/manifest.json") == requested(aioclient_mock, "content-2/quirks/z2m_tuya_a.py") == 0


async def test_a_release_with_another_guard_takes_the_tags_built_for_it(hass: HomeAssistant, zha: Zha, repo_dir: Path, aioclient_mock):
    zha.add_device(IEEE_A, "_TZE200_aaaa", "TS0601")
    entry = await setup_entry(hass, repo_dir)
    other = "e" * 64
    publish(repo_dir, 2, guard_id=other)
    await entry.runtime_data.async_check()
    assert entry.runtime_data.source.tag == "content-1"
    # The integration is updated to the release of that guard: the kept state was found with the old one.
    await hass.config_entries.async_unload(entry.entry_id)
    with patch.object(integration.guard, "identity", return_value=other), patch.object(integration.manager, "_RUN", uuid.uuid4().hex):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done(wait_background_tasks=True)
    assert entry.runtime_data.guard.id == other
    assert entry.runtime_data.source.tag == "content-2"
    assert offered(hass) == ["z2m_tuya_a.py"]
    # What content-2 names was kept: the new release decides from it without reading it again.
    assert requested(aioclient_mock, "content-2/content.json") == 1


async def test_list_waits_for_its_check_and_keeps_its_ignore(hass: HomeAssistant, zha: Zha, repo_dir: Path):
    zha.add_device(IEEE_A, "_TZE200_aaaa", "TS0601")
    entry = await setup_entry(hass, repo_dir)
    issue = issue_of(hass, "changes")
    await not_now(hass)
    # A restart while GitHub serves no files: the list cannot be checked, it stays as it was.
    files = REPOS[repo_dir].tags[1]
    right, files["quirks/z2m_tuya_a.py"] = files["quirks/z2m_tuya_a.py"], 503
    await hass.config_entries.async_unload(entry.entry_id)
    with patch.object(integration.manager, "_RUN", uuid.uuid4().hex):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done(wait_background_tasks=True)
    manager_ = entry.runtime_data
    assert manager_.plan.held == plans.UNCHECKED and manager_.plan.install == []
    assert list(manager_.summary()["waiting_for_the_check"]) == ["z2m_tuya_a.py"]
    assert {i.translation_key for i in our_issues(hass).values()} == {"download_waiting"}
    kept = ir.async_get(hass).async_get_issue(DOMAIN, issue.issue_id)
    assert kept is not None and kept.dismissed_version is not None
    # Its dialog says why it cannot apply now.
    flow = await start_fix(hass, kept)
    assert flow["type"] is FlowResultType.ABORT and flow["reason"] == "held_unchecked"
    files["quirks/z2m_tuya_a.py"] = right
    await manager_._interval_check(dt_util.utcnow())
    # The same list: still put aside.
    assert [o.name for o in manager_.plan.install] == ["z2m_tuya_a.py"]
    assert ir.async_get(hass).async_get_issue(DOMAIN, issue.issue_id).dismissed_version is not None
    assert our_issues(hass) == {}
