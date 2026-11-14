"""The plan: the target state of the folder and the change list that reaches it, from plain data.

test_plan_invariants.py checks the rules on random scenarios; these tests pin the cases one by one,
the reasons the list gives and the notices.
"""

from __future__ import annotations

import ast
import hashlib
import json
import random
from types import SimpleNamespace

import pytest

from . import integration

plan_module = integration.plan
content = integration.content
make_plan, Device, names_of = plan_module.make_plan, plan_module.Device, plan_module.names_of
UNREADABLE = integration.files.UNREADABLE

FOLDER = "/config/custom_zha_quirks"


def sha(name: str, version: int) -> str:
    return hashlib.sha256(f"{name}/{version}".encode()).hexdigest()


def rev(name: str, version: int) -> str:
    return sha(name, version)[:8]


def state(**files: dict) -> content.ContentState:
    """A content state: file name stem -> {"fingerprints", "claimed_elsewhere", "version", "over_zha", "swap", "endpoints", "status", "risk"}
    (generated, low risk unless the spec says otherwise)."""
    manifest, shas, revisions = {}, {}, {}
    for stem, spec in files.items():
        name, version = f"z2m_{stem}.py", spec.get("version", 2)
        manifest[stem] = {
            "file": f"quirks/{name}",
            "fingerprints": [list(fp) for fp in spec["fingerprints"]],
            "claimed_elsewhere": [list(fp) for fp in spec.get("claimed_elsewhere", [])],
            "status": "generated",
            "vendor": "V",
            "model": stem,
            "risk": "low",
        }
        for key in ("over_zha", "swap", "endpoints", "status", "risk"):
            if key in spec:
                manifest[stem][key] = spec[key]
        shas[name], revisions[name] = sha(name, version), rev(name, version)
    return content.ContentState(manifest, shas, revisions=revisions)


def record(stem: str, fingerprints, version: int = 1, claimed=()) -> dict:
    name = f"z2m_{stem}.py"
    return {"sha256": sha(name, version), "revision": rev(name, version), "names": {"fingerprints": [list(fp) for fp in fingerprints], "claimed_elsewhere": [list(fp) for fp in claimed]}}


def path(stem: str, folder: str = FOLDER) -> str:
    return f"{folder}/z2m_{stem}.py"


def dev(manufacturer: str, model: str, quirk: str | None = "", disabled: bool = False, name: str = "", layout: dict | None = None) -> Device:
    """layout: endpoint id -> the input clusters the device announces (None: ZHA does not say)."""
    joined = tuple((ep, frozenset(clusters)) for ep, clusters in sorted(layout.items())) if layout is not None else None
    return Device(manufacturer, model, name or f"{manufacturer} {model}", quirk, disabled, joined)


def plan_for(st, devices, records=None, **kwargs):
    """The plan with every record's file on disk as recorded (disk overrides) and every shipped file passed."""
    records = records or {}
    disk = {p: r["sha256"] for p, r in records.items()}
    disk.update(kwargs.pop("disk", {}))
    present = {p.rsplit("/", 1)[1]: d for p, d in disk.items() if p.startswith(FOLDER + "/") and d is not None}
    present.update(kwargs.pop("present", {}))
    verdicts = {name: () for name in st.shas}
    verdicts.update(kwargs.pop("verdicts", {}))
    return make_plan(st, devices, records, disk, FOLDER, present, verdicts=verdicts, **kwargs)


def kinds(plan) -> dict:
    return {
        "install": [(c.name, c.devices) for c in plan.install],
        "update": [(c.name, c.devices) for c in plan.update],
        "remove": [(c.name, c.reason) for c in plan.remove],
    }


A = {"fingerprints": [("Acme", "A-1")]}
B = {"fingerprints": [("Acme", "B-1")]}


def test_a_file_is_installed_for_the_devices_without_a_quirk():
    st = state(a=A, b=B)
    devices = {"d1": dev("Acme", "A-1", name="Hall"), "d2": dev("Acme", "A-1"), "d3": dev("Acme", "B-1", quirk="zhaquirks.acme.b")}
    plan = plan_for(st, devices)
    assert kinds(plan) == {"install": [("z2m_a.py", ("d1", "d2"))], "update": [], "remove": []}
    assert plan.target == {"z2m_a.py"} and plan.held is None
    assert plan.install[0].sha256 == st.shas["z2m_a.py"]


def test_a_device_zha_does_not_report_gets_no_install():
    assert make_plan(state(a=A), {"d1": dev("Acme", "A-1", quirk=None)}, {}, {}, FOLDER, {}, verdicts={"z2m_a.py": ()}).install == []


def test_a_device_zha_does_not_report_keeps_the_file_of_ours_that_claims_it():
    st = state(a=A)
    plan = plan_for(st, {"d1": dev("Acme", "A-1", quirk=None)}, {path("a"): record("a", [("Acme", "A-1")])})
    # It counts as running the file: the file is updated, not removed.
    assert kinds(plan) == {"install": [], "update": [("z2m_a.py", ("d1",))], "remove": []}


def test_a_report_of_a_file_that_is_gone_counts_as_not_reported():
    """ZHA has not loaded the folder since z2m_b.py went: no custom quirk of the user blocks z2m_a.py."""
    st = state(a=A)
    plan = plan_for(st, {"d1": dev("Acme", "A-1", quirk="z2m_b"), "d2": dev("Acme", "A-1")})
    assert kinds(plan)["install"] == [("z2m_a.py", ("d2",))] and plan.blocked == []


def test_a_device_on_another_custom_quirk_blocks_the_file_with_a_notice():
    st = state(a=A)
    plan = plan_for(st, {"d1": dev("Acme", "A-1", quirk="my_quirk"), "d2": dev("Acme", "A-1")})
    # Writing it would let ZHA pick ours for d1: not for d2 either.
    assert plan.install == [] and [(b.name, b.devices) for b in plan.blocked] == [("z2m_a.py", ("d1",))]


def test_the_block_counts_how_strongly_a_name_claims():
    """ZHA tries an exact name before a model-only one: an update from (None, A-1) to (Acme, A-1)
    would take d1 from the user's quirk, one the other way round would not."""
    devices = {"d1": dev("Acme", "A-1", quirk="my_quirk"), "d2": dev("Acme", "A-2", quirk="z2m_a")}
    st = state(a={"fingerprints": [("Acme", "A-1"), ("Acme", "A-2")]})
    plan = plan_for(st, devices, {path("a"): record("a", [(None, "A-1"), ("Acme", "A-2")])})
    assert plan.update == [] and [b.devices for b in plan.blocked] == [("d1",)]
    # The file stays as it is: d2 runs it.
    assert plan.remove == []
    st = state(a={"fingerprints": [(None, "A-1"), ("Acme", "A-2")]})
    plan = plan_for(st, devices, {path("a"): record("a", [("Acme", "A-1"), ("Acme", "A-2")])})
    assert [u.name for u in plan.update] == ["z2m_a.py"] and plan.blocked == []


def test_the_block_counts_a_name_the_installed_version_left_to_another_file():
    """The installed version leaves (Acme, A-1) to another file (claimed_elsewhere), the offered one
    no longer does: its model-only name would claim d1 anew, which runs the user's quirk."""
    devices = {"d1": dev("Acme", "A-1", quirk="my_quirk"), "d2": dev("Other", "A-1", quirk="z2m_a")}
    st = state(a={"fingerprints": [(None, "A-1")]})
    plan = plan_for(st, devices, {path("a"): record("a", [(None, "A-1")], claimed=[("Acme", "A-1")])})
    assert plan.update == [] and [b.devices for b in plan.blocked] == [("d1",)]
    assert plan.remove == []


def test_left_out_devices_get_nothing_and_keep_nothing():
    st = state(a=A, b=B)
    devices = {"d1": dev("Acme", "A-1", disabled=True), "d2": dev("Acme", "B-1", quirk="z2m_b")}
    plan = plan_for(st, devices, {path("b"): record("b", [("Acme", "B-1")], version=2)}, excluded={"d2"})
    assert plan.install == [] and kinds(plan)["remove"] == [("z2m_b.py", plan_module.LEFT_OUT)]


def test_a_file_another_device_needs_names_the_left_out_devices_it_claims_too():
    st = state(a={"fingerprints": [("Acme", "A-1"), ("Acme", "A-2")]})
    plan = plan_for(st, {"d1": dev("Acme", "A-1"), "d2": dev("Acme", "A-2")}, excluded={"d2"})
    assert [(c.devices, c.left_out) for c in plan.install] == [(("d1",), ("d2",))]


def test_a_file_of_the_user_under_our_name_is_never_written():
    st = state(a=A)
    devices = {"d1": dev("Acme", "A-1")}
    plan = plan_for(st, devices, present={"z2m_a.py": "f" * 64})
    assert plan.install == [] and plan.users_files == ["z2m_a.py"]
    # An exact copy of the offered file without a record belongs to the user too.
    plan = plan_for(st, devices, present={"z2m_a.py": st.shas["z2m_a.py"]})
    assert plan.install == [] and plan.users_files == ["z2m_a.py"]
    # The notice is for devices that are not left out; the user's quirk under that name blocks nothing else.
    assert plan_for(st, {"d1": dev("Acme", "A-1", disabled=True)}, present={"z2m_a.py": "f" * 64}).users_files == []
    plan = plan_for(st, {"d1": dev("Acme", "A-1", quirk="z2m_a")}, present={"z2m_a.py": "f" * 64})
    assert plan.users_files == ["z2m_a.py"] and plan.blocked == []


def test_a_file_of_ours_the_user_changed_is_left_alone():
    st = state(a=A)
    records = {path("a"): record("a", [("Acme", "A-1")])}
    plan = plan_for(st, {"d1": dev("Acme", "A-1", quirk="z2m_a")}, records, disk={path("a"): "e" * 64})
    assert kinds(plan) == {"install": [], "update": [], "remove": []}
    assert plan.changed == [path("a")] and plan.users_files == []


def test_an_unreadable_file_or_link_is_left_alone_with_its_record():
    st = state(a=A)
    records = {path("a"): record("a", [("Acme", "A-1")])}
    plan = plan_for(st, {"d1": dev("Acme", "A-1", quirk="z2m_a")}, records, disk={path("a"): UNREADABLE}, present={"z2m_a.py": None})
    assert kinds(plan) == {"install": [], "update": [], "remove": []}
    assert plan.unreadable == [path("a")] and plan.users_files == [] and plan.gone == []


def test_an_older_version_is_updated_for_the_devices_that_need_it():
    st = state(a=A)
    plan = plan_for(st, {"d1": dev("Acme", "A-1", quirk="z2m_a")}, {path("a"): record("a", [("Acme", "A-1")])})
    (update,) = plan.update
    assert (update.name, update.before, update.sha256, update.devices, update.withdrawn) == ("z2m_a.py", sha("z2m_a.py", 1), st.shas["z2m_a.py"], ("d1",), False)


def test_a_name_that_moves_to_another_file_moves_in_one_list():
    """The data moved Acme / B-1 from z2m_a.py to z2m_b.py: the list updates the one and installs the other."""
    st = state(a=A, b=B)
    devices = {"d1": dev("Acme", "A-1", quirk="z2m_a"), "d2": dev("Acme", "B-1", quirk="z2m_a")}
    plan = plan_for(st, devices, {path("a"): record("a", [("Acme", "A-1"), ("Acme", "B-1")])})
    assert kinds(plan) == {"install": [("z2m_b.py", ("d2",))], "update": [("z2m_a.py", ("d1",))], "remove": []}
    assert plan.update[0].moves == (("d2", "z2m_b.py"),) and plan.update[0].lost == ()


def test_a_file_whose_devices_all_moved_goes():
    st = state(b=B)
    plan = plan_for(st, {"d2": dev("Acme", "B-1", quirk="z2m_a")}, {path("a"): record("a", [("Acme", "B-1")])})
    assert kinds(plan) == {"install": [("z2m_b.py", ("d2",))], "update": [], "remove": [("z2m_a.py", plan_module.MOVED)]}
    assert plan.remove[0].moves == (("d2", "z2m_b.py"),)


def test_a_file_whose_newer_version_cannot_be_written_stays_while_a_device_runs_it():
    st = state(a=A)
    records = {path("a"): record("a", [("Acme", "A-1")])}
    plan = plan_for(st, {"d1": dev("Acme", "A-1", quirk="z2m_a")}, records, verdicts={"z2m_a.py": ("refused",)})
    assert kinds(plan) == {"install": [], "update": [], "remove": []} and plan.refused == ["z2m_a.py"]


def test_a_file_that_must_go_names_the_devices_that_get_none():
    """z2m_a.py's newer version is refused while z2m_b.py takes one of its devices: z2m_a.py goes, d1 loses its quirk."""
    st = state(a=A, b=B)
    devices = {"d1": dev("Acme", "A-1", quirk="z2m_a"), "d2": dev("Acme", "B-1", quirk="z2m_a")}
    plan = plan_for(st, devices, {path("a"): record("a", [("Acme", "A-1"), ("Acme", "B-1")])}, verdicts={"z2m_a.py": ("refused",)})
    assert kinds(plan) == {"install": [("z2m_b.py", ("d2",))], "update": [], "remove": [("z2m_a.py", plan_module.MOVED)]}
    assert plan.remove[0].lost == (plan_module.Lost("d1", plan_module.FILE_REFUSED, "z2m_a.py"),)


def test_why_a_device_gets_no_file():
    lost = plan_module.Lost
    records = {path("a"): record("a", [("Acme", "A-1"), ("Acme", "B-1")])}
    devices = {"d1": dev("Acme", "A-1", quirk="z2m_a"), "d2": dev("Acme", "B-1", quirk="z2m_a")}
    withdrawn = {("z2m_a.py", rev("z2m_a.py", 1))}

    def reason(st, more_withdrawn=frozenset(), **kwargs):
        plan = plan_for(st, devices, records, withdrawn=withdrawn | more_withdrawn, **kwargs)
        (removal,) = plan.remove
        return removal.lost

    # No shipped file claims d1 any more.
    assert reason(state(b=B)) == (lost("d1", plan_module.NO_FILE),)
    # Two shipped files claim d1.
    assert reason(state(b=B, c=A, e=A)) == (lost("d1", plan_module.TWO_FILES),)
    # Its file's revision on offer is withdrawn.
    assert reason(state(b=B, c=A), {("z2m_c.py", rev("z2m_c.py", 2))}) == (lost("d1", plan_module.FILE_WITHDRAWN, "z2m_c.py"),)
    # Its file shares a device with another shipped file.
    st = state(b=B, c={"fingerprints": [("Acme", "A-1"), ("Acme", "C-1")]}, e={"fingerprints": [("Acme", "C-1")]})
    devices["d3"] = dev("Acme", "C-1")
    assert reason(st) == (lost("d1", plan_module.FILE_CONFLICT, "z2m_c.py"),)
    del devices["d3"]
    # A file of the user has its name.
    assert reason(state(b=B, c=A), present={"z2m_c.py": "f" * 64}) == (lost("d1", plan_module.USERS_NAME, "z2m_c.py"),)
    # The user's quirk runs on a device its file would claim.
    devices["d4"] = dev("Acme", "C-1", quirk="my_quirk")
    assert reason(state(b=B, c={"fingerprints": [("Acme", "A-1"), ("Acme", "C-1")]})) == (lost("d1", plan_module.USERS_QUIRK, "z2m_c.py", ("d4",)),)


def test_removal_reasons():
    st = state(b=B)
    one = {path("a"): record("a", [("Acme", "A-1")])}
    # A device on ZHA's own quirk.
    plan = plan_for(st, {"d1": dev("Acme", "A-1", quirk="zhaquirks.acme.a")}, one)
    assert kinds(plan)["remove"] == [("z2m_a.py", plan_module.SHIPPED)]
    # No device left at all: not "ZHA ships a quirk" (nothing to say that of).
    assert kinds(plan_for(st, {}, one))["remove"] == [("z2m_a.py", plan_module.UNUSED)]
    # Its device is on another custom quirk now.
    assert kinds(plan_for(st, {"d1": dev("Acme", "A-1", quirk="my_quirk")}, one))["remove"] == [("z2m_a.py", plan_module.UNUSED)]
    # Its revision is withdrawn and no writable version is for its device.
    plan = plan_for(st, {"d1": dev("Acme", "A-1", quirk="z2m_a")}, one, withdrawn={("z2m_a.py", rev("z2m_a.py", 1))})
    assert kinds(plan)["remove"] == [("z2m_a.py", plan_module.WITHDRAWN)] and plan.remove[0].withdrawn and plan.severe
    # In a folder ZHA no longer loads.
    plan = plan_for(st, {}, {path("a", "/config/old"): record("a", [("Acme", "A-1")])})
    assert [(c.path, c.reason) for c in plan.remove] == [(path("a", "/config/old"), plan_module.OUTSIDE)]


def test_a_file_the_collection_no_longer_ships_stays_while_a_device_runs_it():
    st = state(b=B)
    records = {path("a"): record("a", [("Acme", "A-1")])}
    assert kinds(plan_for(st, {"d1": dev("Acme", "A-1", quirk="z2m_a")}, records)) == {"install": [], "update": [], "remove": []}
    # Unless its revision is withdrawn.
    plan = plan_for(st, {"d1": dev("Acme", "A-1", quirk="z2m_a")}, records, withdrawn={("z2m_a.py", rev("z2m_a.py", 1))})
    assert kinds(plan)["remove"] == [("z2m_a.py", plan_module.WITHDRAWN)]


def test_a_withdrawn_installed_revision_is_updated_and_noticed():
    st = state(a=A)
    plan = plan_for(st, {"d1": dev("Acme", "A-1", quirk="z2m_a")}, {path("a"): record("a", [("Acme", "A-1")])}, withdrawn={("z2m_a.py", rev("z2m_a.py", 1))})
    assert [u.withdrawn for u in plan.update] == [True] and plan.severe
    assert plan.withdrawn_installed == [(path("a"), rev("z2m_a.py", 1))]


def test_the_list_id_follows_the_list_and_a_withdrawal():
    st = state(a=A)
    devices = {"d1": dev("Acme", "A-1", quirk="z2m_a")}
    records = {path("a"): record("a", [("Acme", "A-1")])}
    key = plan_for(st, devices, records).key
    assert plan_for(st, devices, records).key == key
    # Withdrawn since: the same entries, another list ("Not now" on the earlier one does not hide it).
    assert plan_for(st, devices, records, withdrawn={("z2m_a.py", rev("z2m_a.py", 1))}).key != key
    assert plan_for(state(a={**A, "version": 3}), devices, records).key != key


def test_a_change_waiting_for_zha_holds_the_list():
    st = state(a=A)
    records = {path("a"): record("a", [("Acme", "A-1")])}
    plan = plan_for(st, {"d1": dev("Acme", "A-1", quirk="z2m_a")}, records, pending=True, withdrawn={("z2m_a.py", rev("z2m_a.py", 1))})
    assert plan.held == plan_module.PENDING and plan.changes == 0
    # The withdrawn revision in use is still noticed.
    assert plan.withdrawn_installed == [(path("a"), rev("z2m_a.py", 1))]


def test_a_file_the_guard_has_not_checked_holds_the_list():
    st = state(a=A, b=B)
    plan = plan_for(st, {"d1": dev("Acme", "A-1"), "d2": dev("Acme", "B-1")}, verdicts={"z2m_b.py": None})
    assert plan.held == plan_module.UNCHECKED and plan.unchecked == ["z2m_b.py"] and plan.changes == 0
    # A file installed at the offered version is never written: no check needed.
    records = {path("b"): record("b", [("Acme", "B-1")], version=2)}
    assert plan_for(st, {"d2": dev("Acme", "B-1", quirk="z2m_b")}, records, verdicts={"z2m_b.py": None}).held is None


def test_two_shipped_files_for_one_device_are_both_kept_out():
    st = state(a={"fingerprints": [("Acme", "A-1"), ("Acme", "X-1")]}, b={"fingerprints": [("Acme", "B-1"), ("Acme", "X-1")]})
    plan = plan_for(st, {"d1": dev("Acme", "A-1"), "d2": dev("Acme", "B-1"), "d3": dev("Acme", "X-1")})
    assert plan.install == [] and plan.target == frozenset()


def test_a_model_only_name_leaves_the_names_claimed_elsewhere():
    st = state(a={"fingerprints": [(None, "A-1")], "claimed_elsewhere": [("Other", "A-1")]}, b={"fingerprints": [("Other", "A-1")]})
    plan = plan_for(st, {"d1": dev("Acme", "A-1"), "d2": dev("Other", "A-1")})
    assert kinds(plan)["install"] == [("z2m_a.py", ("d1",)), ("z2m_b.py", ("d2",))]


def test_a_record_a_crash_left_settles_to_what_is_on_disk():
    st = state(a=A)
    new = record("a", [("Acme", "A-1")], version=2)
    old = record("a", [("Acme", "A-1")], version=1)
    devices = {"d1": dev("Acme", "A-1", quirk="z2m_a")}
    # The update's record was saved, the file not written yet: the version before is ours.
    plan = plan_for(st, devices, {path("a"): {**new, "previous": old}}, disk={path("a"): old["sha256"]})
    assert plan.settled == {path("a"): old} and plan.changed == [] and [u.before for u in plan.update] == [old["sha256"]]
    # The file was written: the record drops the version before.
    plan = plan_for(st, devices, {path("a"): {**new, "previous": old}}, disk={path("a"): new["sha256"]})
    assert plan.settled == {path("a"): new} and plan.changed == [] and plan.update == []


def test_a_copy_of_a_withdrawn_revision_without_a_record_gets_a_notice():
    st = state(a=A)
    withdrawn = {("z2m_a.py", rev("z2m_a.py", 2)), ("z2m_old.py", "0ldc0de0")}
    plan = plan_for(st, {}, present={"z2m_a.py": st.shas["z2m_a.py"], "z2m_old.py": "f" * 64}, generated={"z2m_old.py": "0ldc0de0"}, withdrawn=withdrawn)
    assert plan.withdrawn_copies == {"z2m_a.py": rev("z2m_a.py", 2), "z2m_old.py": "0ldc0de0"}


def test_zha_not_applying_a_file_at_the_offered_version_is_noticed():
    st = state(a=A)
    records = {path("a"): record("a", [("Acme", "A-1")], version=2)}
    devices = {"d1": dev("Acme", "A-1"), "d2": dev("Acme", "A-1", quirk="my_quirk"), "d3": dev("Acme", "A-1", quirk="z2m_a")}
    plan = plan_for(st, devices, records)
    assert [(n.name, n.devices) for n in plan.not_applied] == [("z2m_a.py", ("d1", "d2"))]
    # Not while the file is at an older version (its update is in the list).
    assert plan_for(st, devices, {path("a"): record("a", [("Acme", "A-1")])}).not_applied == []


def test_a_gone_file_drops_its_record():
    plan = plan_for(state(a=A), {"d1": dev("Acme", "A-1")}, {path("a"): record("a", [("Acme", "A-1")])}, disk={path("a"): None})
    assert plan.gone == [path("a")] and kinds(plan)["install"] == [("z2m_a.py", ("d1",))]


# A file that takes its exact name over from ZHA's own quirk (the manifest's over_zha), besides a
# model-only name; and the module of the quirk ZHA ships for the device.
TAKE = {"fingerprints": [(None, "T-1"), ("Acme", "T-1")], "over_zha": {"adds": ["Screen direction"], "zha_only": ["Boost mode"]}}
ZHAS = "zhaquirks.acme.t"


def taken(stem: str, fingerprints, version: int = 2) -> dict:
    """The record of a file of ours whose version takes its exact names over from ZHA's quirk, as the
    manager writes it (plan.names_of of an entry with over_zha)."""
    names = names_of({"fingerprints": [list(fp) for fp in fingerprints], "over_zha": TAKE["over_zha"]})
    return {**record(stem, fingerprints, version), "names": names}


def test_a_take_over_version_records_the_names_it_takes_over():
    assert names_of({"fingerprints": [[None, "T-1"], ["Acme", "T-1"]], "over_zha": TAKE["over_zha"]}) == {
        "fingerprints": [[None, "T-1"], ["Acme", "T-1"]], "claimed_elsewhere": [], "takes_over": [["Acme", "T-1"]]}
    # A version without over_zha takes nothing over: the record keeps the names it had before.
    assert names_of({"fingerprints": [[None, "T-1"], ["Acme", "T-1"]]}) == {"fingerprints": [[None, "T-1"], ["Acme", "T-1"]], "claimed_elsewhere": []}


def test_a_file_takes_a_device_over_from_zhas_quirk_that_shows_less():
    plan = plan_for(state(t=TAKE), {"d1": dev("Acme", "T-1", quirk=ZHAS)})
    assert kinds(plan) == {"install": [("z2m_t.py", ("d1",))], "update": [], "remove": []}
    assert plan.install[0].took_over == ("d1",)


def test_a_device_on_zhas_quirk_keeps_it_unless_the_file_takes_its_exact_name_over():
    st = state(t=TAKE)
    # Left out: disabled, or excluded in the options.
    assert plan_for(st, {"d1": dev("Acme", "T-1", quirk=ZHAS, disabled=True)}).changes == 0
    assert plan_for(st, {"d1": dev("Acme", "T-1", quirk=ZHAS)}, excluded={"d1"}).changes == 0
    # Another manufacturer the model-only name claims, on a quirk ZHA ships for it: upstream first.
    assert plan_for(st, {"d2": dev("Other", "T-1", quirk="zhaquirks.other.t")}).changes == 0
    # An entry without over_zha: upstream first.
    assert plan_for(state(t={"fingerprints": TAKE["fingerprints"]}), {"d1": dev("Acme", "T-1", quirk=ZHAS)}).changes == 0
    # A device without a quirk gets the file as before, nothing taken over.
    plan = plan_for(st, {"d2": dev("Other", "T-1")})
    assert kinds(plan)["install"] == [("z2m_t.py", ("d2",))] and plan.install[0].took_over == ()


def test_after_the_take_over_nothing_changes():
    st = state(t=TAKE)
    plan = plan_for(st, {"d1": dev("Acme", "T-1", quirk="z2m_t")}, {path("t"): taken("t", TAKE["fingerprints"])})
    assert plan.changes == 0 and plan.not_applied == [] and plan.target == {"z2m_t.py"}


def test_a_take_over_zha_does_not_apply_is_noticed():
    st = state(t=TAKE)
    plan = plan_for(st, {"d1": dev("Acme", "T-1", quirk=ZHAS)}, {path("t"): taken("t", TAKE["fingerprints"])})
    assert plan.changes == 0 and [(n.name, n.devices) for n in plan.not_applied] == [("z2m_t.py", ("d1",))]
    # A device of another manufacturer on its own shipped quirk is no take-over: no notice for it.
    devices = {"d1": dev("Acme", "T-1", quirk="z2m_t"), "d2": dev("Other", "T-1", quirk="zhaquirks.other.t")}
    plan = plan_for(st, devices, {path("t"): taken("t", TAKE["fingerprints"])})
    assert plan.changes == 0 and plan.not_applied == []


def test_an_update_takes_over_a_device_its_older_version_left_to_zha():
    """The file at an older version stepped back (it took nothing over then): the update takes the device over."""
    st = state(t=TAKE)
    plan = plan_for(st, {"d1": dev("Acme", "T-1", quirk=ZHAS)}, {path("t"): record("t", [(None, "T-1")])})
    assert kinds(plan) == {"install": [], "update": [("z2m_t.py", ("d1",))], "remove": []}
    assert plan.update[0].took_over == ("d1",)
    # An update for a device that runs the file already takes nothing over anew.
    plan = plan_for(st, {"d1": dev("Acme", "T-1", quirk="z2m_t")}, {path("t"): taken("t", TAKE["fingerprints"], version=1)})
    assert kinds(plan)["update"] == [("z2m_t.py", ("d1",))] and plan.update[0].took_over == ()


def test_zha_takes_its_devices_back_when_the_state_drops_the_file():
    plan = plan_for(state(a=A), {"d1": dev("Acme", "T-1", quirk="z2m_t")}, {path("t"): taken("t", TAKE["fingerprints"])})
    assert kinds(plan) == {"install": [], "update": [], "remove": [("z2m_t.py", "handed_back")]}
    assert plan.remove[0].lost == ()


def test_zha_takes_its_devices_back_when_the_entry_says_it_covers_the_device():
    st = state(a=A)
    st.manifest["t"] = {"file": None, "fingerprints": [], "status": "upstream"}
    plan = plan_for(st, {"d1": dev("Acme", "T-1", quirk="z2m_t")}, {path("t"): taken("t", TAKE["fingerprints"])})
    assert kinds(plan)["remove"] == [("z2m_t.py", "handed_back")] and plan.remove[0].lost == ()


def test_a_dropped_file_hands_back_every_device_on_a_name_it_took_over():
    """The names decide, not the devices of the install: a second device paired since, one re-paired
    under a new id and one left out at the install that is back go to ZHA's quirk alike."""
    devices = {"d1": dev("Acme", "T-1", quirk="z2m_t"), "d2": dev("Acme", "T-1", quirk="z2m_t"), "d9": dev("Acme", "T-1", quirk=None)}
    plan = plan_for(state(a=A), devices, {path("t"): taken("t", TAKE["fingerprints"])})
    assert kinds(plan)["remove"] == [("z2m_t.py", "handed_back")] and plan.remove[0].lost == ()
    # A left-out device that runs it does not keep it either (it is left alone, the file goes).
    plan = plan_for(state(a=A), devices, {path("t"): taken("t", TAKE["fingerprints"])}, excluded={"d2"})
    assert kinds(plan)["remove"] == [("z2m_t.py", "handed_back")] and plan.remove[0].lost == ()


def test_a_dropped_file_stays_for_a_device_on_a_name_it_did_not_take_over():
    """d3 has another manufacturer: the model-only name gave it the file, no quirk of ZHA stands
    behind it. The file stays (also for d1, accepted). A record without "takes_over" (a version that
    took nothing over) keeps the file as before."""
    devices = {"d1": dev("Acme", "T-1", quirk="z2m_t"), "d3": dev("Other", "T-1", quirk="z2m_t")}
    assert plan_for(state(a=A), devices, {path("t"): taken("t", TAKE["fingerprints"])}).remove == []
    assert plan_for(state(a=A), {"d1": dev("Acme", "T-1", quirk="z2m_t")}, {path("t"): record("t", TAKE["fingerprints"], 2)}).remove == []


def test_a_dropped_file_hands_back_whatever_the_reason():
    """An entry without a file for another reason (no file could be built) counts like no
    entry: the state ships no file under the name, ZHA's quirk takes the device back. A device on a
    name the version did not take over keeps the file all the same."""
    st = state(a=A)
    st.manifest["t"] = {"file": None, "fingerprints": [list(fp) for fp in TAKE["fingerprints"]], "status": "generated", "not_built": "endpoint unclear"}
    records = {path("t"): taken("t", TAKE["fingerprints"])}
    plan = plan_for(st, {"d1": dev("Acme", "T-1", quirk="z2m_t")}, records)
    assert kinds(plan)["remove"] == [("z2m_t.py", "handed_back")] and plan.remove[0].lost == ()
    devices = {"d1": dev("Acme", "T-1", quirk="z2m_t"), "d3": dev("Other", "T-1", quirk="z2m_t")}
    assert plan_for(st, devices, records).remove == []


def test_a_renamed_take_over_file_moves_its_device_instead_of_handing_it_back():
    """The state ships the device under another file name: the old file goes as moved, the device
    gets the new file, not ZHA's quirk."""
    records = {path("t"): taken("t", TAKE["fingerprints"])}
    plan = plan_for(state(t2=TAKE), {"d1": dev("Acme", "T-1", quirk="z2m_t")}, records)
    assert kinds(plan) == {"install": [("z2m_t2.py", ("d1",))], "update": [], "remove": [("z2m_t.py", "moved")]}
    assert plan.remove[0].moves == (("d1", "z2m_t2.py"),) and plan.remove[0].lost == ()


# Entities that read an attribute, as the manifest holds them: [cluster, attribute id, platform, unique id, name].
OURS_IDS = [[0xFC11, 0x0000, "switch", "-1-child_lock", "Child lock"], [0xFC11, 0x6011, "number", "-1-temperature_trigger", "Temperature accuracy"],
            [0xFC11, 0x600E, "select", "-1-sensor_select", "Temperature sensor"], [0xFC11, 0x6020, "number", "-1-screen", "Screen"]]
ZHA_IDS = [[0xFC11, 0x0000, "switch", "-1-child_lock", "Child lock"], [0xFC11, 0x6011, "number", "-1-temperature_control_accuracy", "Temperature control accuracy"],
           [0xFC11, 0x600E, "switch", "-1-sensor_select", "External sensor"], [0xFC11, 0x6030, "button", "-1-boost", "Boost"]]


def test_swapped_names_the_entities_that_do_not_keep_their_id():
    # Same attribute: another unique id or another platform is another entity; an attribute only one side
    # reads is no swap; the names are those of the side the user has.
    assert plan_module.swapped(OURS_IDS, ZHA_IDS, "zha") == ("Temperature control accuracy", "External sensor")
    assert plan_module.swapped(OURS_IDS, ZHA_IDS, "ours") == ("Temperature accuracy", "Temperature sensor")
    # A second entity of the file on an attribute ZHA's quirk shows once: ZHA's keeps its id; the file's
    # second entity has no counterpart on ZHA's quirk, so a hand-back drops it.
    second = OURS_IDS + [[0xFC11, 0x0000, "binary_sensor", "-1-child_lock", "Child lock state"]]
    assert "Child lock" not in plan_module.swapped(second, ZHA_IDS, "zha")
    assert "Child lock state" in plan_module.swapped(second, ZHA_IDS, "ours")
    assert plan_module.swapped([], ZHA_IDS, "zha") == () and plan_module.swapped(OURS_IDS, [], "ours") == ()


def test_take_over_and_hand_back_name_the_entities_that_get_another_id():
    entry = {**TAKE, "swap": {"ours": OURS_IDS, "zha": ZHA_IDS}}
    plan = plan_for(state(t=entry), {"d1": dev("Acme", "T-1", quirk=ZHAS)})
    assert plan.install[0].took_over == ("d1",) and plan.install[0].new_ids == ("Temperature control accuracy", "External sensor")
    # A device that runs the file already: no take-over, nothing to name.
    assert plan_for(state(t=entry), {"d1": dev("Acme", "T-1")}).install[0].new_ids == ()
    # The hand-back compares the version written (its record) with ZHA's quirk (the state's entry
    # without a file): the record's names, not those of the newer file.
    st = state(a=A)
    st.manifest["t"] = {"file": None, "fingerprints": [["Acme", "T-1"]], "status": "upstream",
                        "swap": {"ours": [[0xFC11, 0x6011, "number", "-1-temperature_control_accuracy", "New name"]], "zha": ZHA_IDS}}
    record = taken("t", TAKE["fingerprints"])
    record["names"]["swap"] = OURS_IDS
    plan = plan_for(st, {"d1": dev("Acme", "T-1", quirk="z2m_t")}, {path("t"): record})
    assert kinds(plan)["remove"] == [("z2m_t.py", "handed_back")] and plan.remove[0].new_ids == ("Temperature accuracy", "Temperature sensor")
    # A record written before records kept them: the state's list of the file stands in.
    plan = plan_for(st, {"d1": dev("Acme", "T-1", quirk="z2m_t")}, {path("t"): taken("t", TAKE["fingerprints"])})
    assert plan.remove[0].new_ids == ()
    # No entry: nothing to compare with.
    assert plan_for(state(a=A), {"d1": dev("Acme", "T-1", quirk="z2m_t")}, {path("t"): record}).remove[0].new_ids == ()
    # Another reason (the device is left out): no names.
    plan = plan_for(st, {"d1": dev("Acme", "T-1", quirk="z2m_t")}, {path("t"): record}, excluded={"d1"})
    assert kinds(plan)["remove"] == [("z2m_t.py", "left_out")] and plan.remove[0].new_ids == ()


def test_the_record_keeps_the_identities_of_a_take_over_version():
    entry = {"fingerprints": [[None, "T-1"], ["Acme", "T-1"]], "over_zha": TAKE["over_zha"], "swap": {"ours": OURS_IDS, "zha": ZHA_IDS}}
    assert names_of(entry)["swap"] == OURS_IDS
    assert "swap" not in names_of({"fingerprints": [[None, "T-1"]], "swap": {"ours": OURS_IDS, "zha": ZHA_IDS}})


def test_a_dropped_take_over_file_whose_device_is_left_out_goes_as_left_out():
    plan = plan_for(state(a=A), {"d1": dev("Acme", "T-1", quirk="z2m_t")}, {path("t"): taken("t", TAKE["fingerprints"])}, excluded={"d1"})
    assert kinds(plan)["remove"] == [("z2m_t.py", "left_out")]


BOOST_SWAP = {"ours": [[0xFC11, 1, "number", "-1-boost", "Boost"]], "zha": [[0xFC11, 1, "number", "-1-boost_time", "Boost time"]]}


def dropped_take_over(st, stem: str = "x"):
    """The state drops the take-over file z2m_<stem>.py (an entry without a file, with the swap); its record
    took (Acme, T-1) over from ZHA's own quirk."""
    st.manifest[stem] = {"file": None, "fingerprints": [], "status": "upstream", "swap": BOOST_SWAP}
    record = taken(stem, [["Acme", "T-1"]])
    record["names"]["swap"] = BOOST_SWAP["ours"]
    return record


def test_a_withdrawn_take_over_file_names_the_devices_zhas_quirk_takes_back():
    """Withdrawn wins over the hand-back as the reason: the device and its new IDs are named among
    those that get no file of ours."""
    st = state(a=A)
    record = dropped_take_over(st, "t")
    devices = {"d1": dev("Acme", "T-1", quirk="z2m_t", name="Taken")}
    plan = plan_for(st, devices, {path("t"): record}, withdrawn={("z2m_t.py", record["revision"])})
    assert kinds(plan)["remove"] == [("z2m_t.py", "withdrawn")]
    (lost,) = plan.remove[0].lost
    assert (lost.device, lost.reason, lost.back, lost.new_ids) == ("d1", plan_module.NO_FILE, True, ("Boost",))
    shown = integration.text.change_list(plan, devices, lambda n: n, {}, {})
    assert "Taken gets no file from xquirks: xquirks no longer has a quirk for it. ZHA's own quirk takes it back" in shown
    assert "new IDs in Home Assistant for Boost" in shown
    # Without a withdrawal the removal hands the device back and names the new IDs itself.
    plan = plan_for(st, devices, {path("t"): record})
    assert kinds(plan)["remove"] == [("z2m_t.py", "handed_back")] and plan.remove[0].lost == () and plan.remove[0].new_ids == ("Boost",)


def test_a_device_handed_back_past_a_target_it_does_not_fit_stays_in_the_list():
    """The state moves (Acme, T-1) from the dropped z2m_x.py to z2m_t.py, which the device does not fit:
    the removal says moved, the device is named with ZHA's quirk taking it back and its new IDs."""
    st = state(t={"fingerprints": [("Acme", "T-1"), ("Acme", "T-2")], "over_zha": TAKE["over_zha"], "swap": BOOST_SWAP, "endpoints": {"2": [0x0702]}})
    records = {path("x"): dropped_take_over(st), path("t"): {"sha256": st.shas["z2m_t.py"], "revision": st.revisions["z2m_t.py"], "names": names_of(st.manifest["t"])}}
    devices = {"d1": dev("Acme", "T-1", quirk="z2m_x", name="Hall", layout={1: {0x0702}}), "d2": dev("Acme", "T-2", quirk="z2m_t", name="Bath", layout={2: {0x0702}})}
    plan = plan_for(st, devices, records)
    assert kinds(plan)["remove"] == [("z2m_x.py", "moved")]
    (lost,) = plan.remove[0].lost
    assert (lost.device, lost.reason, lost.file, lost.back, lost.new_ids) == ("d1", plan_module.FILE_MISFIT, "z2m_t.py", True, ("Boost",))
    assert "Hall gets no file from xquirks: its endpoints do not fit `z2m_t.py`" in integration.text.change_list(plan, devices, lambda n: n, {}, {})
    # One device that fits moves, the other is named; a device on a name the file did not take over gets no new IDs.
    st2 = state(t={"fingerprints": [("Acme", "T-1")], "over_zha": TAKE["over_zha"], "swap": BOOST_SWAP, "endpoints": {"2": [0x0702]}})
    record = dropped_take_over(st2)
    record["names"]["fingerprints"].append([None, "T-9"])
    devices = {"d1": dev("Acme", "T-1", quirk="z2m_x", layout={1: {0x0702}}), "d2": dev("Acme", "T-1", quirk="z2m_x", layout={2: {0x0702}}),
               "d3": dev("Other", "T-9", quirk="z2m_x")}
    plan = plan_for(st2, devices, {path("x"): record})
    (removal,) = plan.remove
    assert removal.reason == "moved" and removal.moves == (("d2", "z2m_t.py"),)
    assert [(item.device, item.reason, item.back, item.new_ids) for item in removal.lost] == [
        ("d1", plan_module.FILE_MISFIT, True, ("Boost",)), ("d3", plan_module.NO_FILE, False, ())]


# A file whose runtime check needs cluster 0x0406 on endpoint 37 and 0x0301 on endpoint 3 (manifest endpoints).
FIT = {"fingerprints": [(None, "F-1")], "endpoints": {"3": [0x0301], "37": [0x0406]}}
FITS = {3: {0x0000, 0x0301}, 37: {0x0406}, 242: set()}
WRONG = {1: {0x0000, 0x0301, 0x0406}}


def test_misfit_follows_the_runtime_rule():
    misfit = plan_module.misfit
    assert misfit(FIT, dev("Acme", "F-1", layout=FITS)) is None
    assert misfit(FIT, dev("Acme", "F-1", layout=WRONG)) == "it has no endpoint 3"
    assert misfit(FIT, dev("Acme", "F-1", layout={3: {0x0301}, 37: set(), 38: {0x0406}})) == "the first endpoint with cluster 0x0406 is 38, not 37"
    # z2m sends a cluster to the first endpoint that announces it, one announced nowhere to the first
    # endpoint: a lower endpoint with it as well, or none with it, takes it away from the file's.
    assert misfit(FIT, dev("Acme", "F-1", layout={1: {0x0406}, 3: {0x0301}, 37: {0x0406}})) == "the first endpoint with cluster 0x0406 is 1, not 37"
    assert misfit(FIT, dev("Acme", "F-1", layout={3: {0x0301}, 37: set()})) == "no endpoint has cluster 0x0406 and the first endpoint is 3, not 37"
    assert misfit({**FIT, "endpoints": {"3": [0x0301, 0xFC11]}}, dev("Acme", "F-1", layout={3: {0x0301}, 37: set()})) is None
    # The endpoints in order (an entry may list them in any), the lowest problem first.
    assert misfit({**FIT, "endpoints": {"37": [0x0406], "3": [0x0301]}}, dev("Acme", "F-1", layout={37: {0x0301}, 3: {0x0406}})) == "the first endpoint with cluster 0x0301 is 37, not 3"
    # Nor does a device whose layout ZHA does not report.
    assert misfit(FIT, dev("Acme", "F-1")) is None
    assert misfit({"fingerprints": FIT["fingerprints"]}, dev("Acme", "F-1", layout=WRONG)) is None


def runtime_misfits() -> list:
    """The runtime check every quirk file with endpoints carries (_misfit of the fixed code this
    release ships), each distinct version once, as a function of ENDPOINTS and the device."""
    fixed = json.loads((integration.FOLDER / integration.guard.FIXED_CODE).read_text())
    sources = set()
    for text in fixed["module"] + fixed["take_over"]:
        for node in ast.parse(text).body:
            if isinstance(node, ast.FunctionDef) and node.name == "_misfit":
                sources.add(ast.get_source_segment(text, node))
    checks = []
    for source in sorted(sources):
        def check(endpoints: dict, device, source=source):
            scope = {"ENDPOINTS": endpoints}
            exec(source, scope)  # the fixed code this release ships, not content from a tag
            return scope["_misfit"](device)

        checks.append(check)
    return checks


def test_misfit_equals_the_runtime_check_on_random_devices():
    """The integration's rule (plan.misfit) and the runtime check in the files (_misfit) agree on
    random devices: the integration offers a file to a device exactly when the file would take it."""
    checks = runtime_misfits()
    assert checks
    rng = random.Random(11)
    clusters = [0x0000, 0x0006, 0x0301, 0x0406, 0x0702, 0xFC04]
    for _ in range(300):
        layout = {e: set(rng.sample(clusters, rng.randint(0, 4))) for e in rng.sample([1, 2, 3, 37], rng.randint(1, 3))}
        endpoints = {e: tuple(sorted(rng.sample(clusters, rng.randint(0, 3)))) for e in sorted(rng.sample([1, 2, 3, 37], rng.randint(1, 2)))}
        entry = {"fingerprints": [[None, "F-1"]], "endpoints": {str(e): list(ids) for e, ids in endpoints.items()}}
        # zigpy's device: endpoint 0 is ZDO (no clusters of its own), the others hold their input clusters.
        device = SimpleNamespace(endpoints={0: object(), **{e: SimpleNamespace(in_clusters=dict.fromkeys(ids)) for e, ids in layout.items()}})
        for check in checks:
            assert plan_module.misfit(entry, dev("Acme", "F-1", layout=layout)) == check(endpoints, device), (endpoints, layout)


def test_a_device_that_does_not_fit_gets_a_notice_instead_of_the_file():
    st = state(f=FIT)
    plan = plan_for(st, {"d1": dev("Acme", "F-1", layout=WRONG), "d2": dev("Acme", "F-1", layout=FITS)})
    assert kinds(plan)["install"] == [("z2m_f.py", ("d2",))]
    assert [(m.name, m.devices) for m in plan.misfits] == [("z2m_f.py", (("d1", "it has no endpoint 3"),))]
    plan = plan_for(st, {"d1": dev("Acme", "F-1", layout=WRONG)})
    assert plan.changes == 0 and plan.target == frozenset() and len(plan.misfits) == 1


def test_no_misfit_notice_where_the_file_would_not_apply_anyway():
    st = state(f=FIT)
    for device in (dev("Acme", "F-1", quirk="my_quirk", layout=WRONG), dev("Acme", "F-1", quirk="zhaquirks.acme.f", layout=WRONG),
                   dev("Acme", "F-1", layout=WRONG, disabled=True)):
        assert plan_for(st, {"d1": device}).misfits == []
    # Excluded in the options: left out too.
    assert plan_for(st, {"d1": dev("Acme", "F-1", layout=WRONG)}, excluded={"d1"}).misfits == []


def test_a_take_over_file_that_does_not_fit_leaves_the_device_on_zhas_quirk():
    st = state(t={**TAKE, "endpoints": {"2": [0x0702]}})
    plan = plan_for(st, {"d1": dev("Acme", "T-1", quirk=ZHAS, layout={1: {0x0702}})})
    assert plan.changes == 0
    assert [(m.name, m.devices) for m in plan.misfits] == [("z2m_t.py", (("d1", "it has no endpoint 2"),))]


def test_a_device_that_does_not_fit_the_offered_version_keeps_the_version_it_runs():
    st = state(f=FIT)
    # The version installed before the runtime check: the device runs it, it may do part of its job.
    records = {path("f"): record("f", FIT["fingerprints"])}
    plan = plan_for(st, {"d1": dev("Acme", "F-1", quirk="z2m_f", layout=WRONG)}, records)
    assert plan.changes == 0 and len(plan.misfits) == 1
    # The version on offer, whose runtime check stepped back: no notice that ZHA does not apply it.
    records = {path("f"): record("f", FIT["fingerprints"], version=2)}
    plan = plan_for(st, {"d1": dev("Acme", "F-1", layout=WRONG), "d2": dev("Acme", "F-1", quirk="z2m_f", layout=FITS)}, records)
    assert plan.changes == 0 and plan.not_applied == [] and len(plan.misfits) == 1


def test_an_update_names_a_device_that_does_not_fit_the_new_version_as_lost():
    st = state(f=FIT)
    records = {path("f"): record("f", FIT["fingerprints"])}
    devices = {"d1": dev("Acme", "F-1", quirk="z2m_f", layout=WRONG), "d2": dev("Acme", "F-1", quirk="z2m_f", layout=FITS)}
    plan = plan_for(st, devices, records)
    assert kinds(plan)["update"] == [("z2m_f.py", ("d2",))]
    assert [(lost.device, lost.reason) for lost in plan.update[0].lost] == [("d1", plan_module.FILE_MISFIT)]


def test_a_record_keeps_the_endpoints_of_the_version_written():
    assert names_of({"fingerprints": [[None, "F-1"]], "endpoints": {"3": [0x0301]}})["endpoints"] == {"3": [0x0301]}
    # A device ZHA does not report runs a file of ours only where it fits the version written.
    st = state(f=FIT)
    records = {path("f"): {**record("f", FIT["fingerprints"], version=2), "names": names_of({"fingerprints": [[None, "F-1"]], "endpoints": FIT["endpoints"]})}}
    plan = plan_for(st, {"d1": dev("Acme", "F-1", quirk=None, layout=WRONG)}, records)
    assert kinds(plan)["remove"] == [("z2m_f.py", plan_module.UNUSED)]
    plan = plan_for(st, {"d1": dev("Acme", "F-1", quirk=None, layout=FITS)}, records)
    assert plan.changes == 0


def test_a_custom_quirk_on_a_device_that_does_not_fit_blocks_nothing():
    """The file would step back on that device anyway: no block, no advice to drop the user's quirk;
    a fitting device of the same model gets the file."""
    st = state(f=FIT)
    devices = {"d1": dev("Acme", "F-1", quirk="my_quirk", layout=WRONG), "d2": dev("Acme", "F-1", layout=FITS)}
    plan = plan_for(st, devices)
    assert plan.blocked == [] and kinds(plan)["install"] == [("z2m_f.py", ("d2",))]
    # The user's own copy under our name: noticed only for a device the file fits.
    plan = plan_for(st, {"d1": dev("Acme", "F-1", quirk="z2m_f", layout=WRONG)}, present={"z2m_f.py": "c" * 64})
    assert plan.users_files == []
    plan = plan_for(st, {"d1": dev("Acme", "F-1", quirk="z2m_f", layout=FITS)}, present={"z2m_f.py": "c" * 64})
    assert plan.users_files == ["z2m_f.py"]


def test_a_device_that_does_not_fit_the_target_does_not_move_there():
    st = state(new={"fingerprints": [(None, "F-1")], "endpoints": FIT["endpoints"]})
    records = {path("old"): record("old", [(None, "F-1")])}
    devices = {"d1": dev("Acme", "F-1", quirk="z2m_old", layout=WRONG), "d2": dev("Acme", "F-1", layout=FITS)}
    plan = plan_for(st, devices, records)
    (removal,) = plan.remove
    assert removal.moves == () and [(lost.device, lost.reason) for lost in removal.lost] == [("d1", plan_module.FILE_MISFIT)]


def test_a_left_out_device_that_does_not_fit_is_not_named_as_getting_the_file():
    st = state(f=FIT)
    plan = plan_for(st, {"d1": dev("Acme", "F-1", layout=FITS), "d2": dev("Acme", "F-1", layout=WRONG, disabled=True)})
    assert plan.install[0].left_out == ()


def test_an_unreported_device_keeps_needing_its_file():
    """ZHA does not say what the device runs; it fits the offered version but not the one written:
    the file is updated, not removed now and installed again after the next reload."""
    st = state(f=FIT)
    old = {**record("f", FIT["fingerprints"]), "names": names_of({"fingerprints": [[None, "F-1"]], "endpoints": {"1": [0x0301]}})}
    plan = plan_for(st, {"d1": dev("Acme", "F-1", quirk=None, layout=FITS)}, {path("f"): old})
    assert kinds(plan) == {"install": [], "update": [("z2m_f.py", ("d1",))], "remove": []}


def test_a_staying_version_a_device_does_not_fit_leaves_it_lost():
    """z2m_a goes (withdrawn). The device's other claimant z2m_b stays, another device runs it, at the
    installed version, whose endpoints the device does not fit: its runtime check steps back there, so
    the device is named. The offered version of z2m_b, which it would fit, is refused."""
    st = state(b={"fingerprints": [(None, "F-1")], "endpoints": {"1": [0x0006]}})
    b_old = {**record("b", [(None, "F-1")]), "names": names_of({"fingerprints": [[None, "F-1"]], "endpoints": {"2": [0x0006]}})}
    records = {path("a"): record("a", [("Acme", "F-1")]), path("b"): b_old}
    devices = {"d1": dev("Acme", "F-1", quirk="z2m_a", layout={1: {0x0006}}), "d2": dev("Other", "F-1", quirk="z2m_b", layout={1: set(), 2: {0x0006}})}
    plan = plan_for(st, devices, records, withdrawn={("z2m_a.py", rev("z2m_a.py", 1))}, verdicts={"z2m_b.py": ("refused",)})
    assert kinds(plan) == {"install": [], "update": [], "remove": [("z2m_a.py", "withdrawn")]}
    (removal,) = plan.remove
    assert [(lost.device, lost.reason, lost.file) for lost in removal.lost] == [("d1", plan_module.FILE_REFUSED, "z2m_b.py")]


def test_a_device_that_does_not_fit_its_next_file_is_named_so_before_a_users_file_of_that_name():
    """Its next file would not run on it in any case: that is the reason the list gives, also where a
    file of the user has the name."""
    records = {path("a"): record("a", [("Acme", "A-1")])}
    devices = {"d1": dev("Acme", "A-1", quirk="z2m_a", layout={1: {0x0006}})}
    plan = plan_for(state(c={**A, "endpoints": {"2": [0x0006]}}), devices, records, withdrawn={("z2m_a.py", rev("z2m_a.py", 1))}, present={"z2m_c.py": "f" * 64})
    (removal,) = plan.remove
    assert [(lost.device, lost.reason, lost.file) for lost in removal.lost] == [("d1", plan_module.FILE_MISFIT, "z2m_c.py")]


def test_an_update_that_would_newly_fit_a_device_on_the_users_quirk_is_blocked():
    """The installed version steps back on Garage (no endpoint 2), so Garage runs the user's quirk; the
    offered version fits it under the same exact name and ZHA could apply ours instead. The list does
    not write it: the notice says the user's quirk is in the way, also for a left-out Garage."""
    st = state(f={"fingerprints": [("Acme", "F-1")], "endpoints": {"1": [0x0006]}})
    installed = {**record("f", [("Acme", "F-1")]), "names": names_of({"fingerprints": [["Acme", "F-1"]], "endpoints": {"2": []}})}
    for disabled in (False, True):
        devices = {"d1": dev("Acme", "F-1", quirk="z2m_f", name="Hall", layout={1: {0x0006}, 2: set()}),
                   "d2": dev("Acme", "F-1", quirk="my_quirk", name="Garage", disabled=disabled, layout={1: {0x0006}})}
        plan = plan_for(st, devices, {path("f"): installed}, present={"my_quirk.py": "u" * 64})
        assert kinds(plan)["update"] == [] and [(b.name, b.devices) for b in plan.blocked] == [("z2m_f.py", ("d2",))], disabled
    # Where the installed version fits Garage as well, the user's quirk wins already: the update goes out.
    installed["names"]["endpoints"] = {"1": [0x0006]}
    plan = plan_for(st, devices, {path("f"): installed}, present={"my_quirk.py": "u" * 64})
    assert kinds(plan)["update"] == [("z2m_f.py", ("d1",))] and plan.blocked == []


def test_left_out_devices_the_list_names_are_those_the_file_applies_to():
    """An update lists the left-out devices ZHA applies the file to as well: not one on the user's own
    quirk (it keeps winning there), not one on ZHA's own quirk the file does not take over (it steps
    back), not one it does not fit."""
    st = state(f={"fingerprints": [(None, "F-1")], "endpoints": {"1": [0x0006]}})
    records = {path("f"): record("f", [("Acme", "F-1")])}
    devices = {"d1": dev("Acme", "F-1", quirk="z2m_f", name="Hall", layout={1: {0x0006}}),
               "d2": dev("Acme", "F-1", quirk="my_quirk", name="Garage", disabled=True, layout={1: {0x0006}}),
               "d3": dev("Other", "F-1", quirk="zhaquirks.other.f", name="Attic", disabled=True, layout={1: {0x0006}}),
               "d4": dev("Third", "F-1", quirk=None, name="Cellar", disabled=True, layout={2: {0x0006}}),
               "d5": dev("Fourth", "F-1", quirk=None, name="Porch", disabled=True, layout={1: {0x0006}})}
    plan = plan_for(st, devices, records, present={"my_quirk.py": "u" * 64})
    assert kinds(plan)["update"] == [("z2m_f.py", ("d1",))] and plan.update[0].left_out == ("d5",)
    shown = integration.text.change_list(plan, devices, lambda n: n, {}, {})
    assert "also applies to Porch, which you left out" in shown and "Garage" not in shown and "Attic" not in shown


def test_the_hand_back_names_the_ids_of_the_version_written():
    """ZHA's quirk takes the device back from the version installed: the IDs that change are those of
    the record's entities, not of the version the state would ship now."""
    st = state(a=A)
    st.manifest["t"] = {"file": None, "fingerprints": [], "status": "upstream",
                        "swap": {"ours": [[0xFC11, 1, "number", "-1-boost_level", "Boost level"]], "zha": BOOST_SWAP["zha"]}}
    record = taken("t", [["Acme", "T-1"]])
    record["names"]["swap"] = BOOST_SWAP["ours"]
    devices = {"d1": dev("Acme", "T-1", quirk="z2m_t", name="Taken")}
    plan = plan_for(st, devices, {path("t"): record}, withdrawn={("z2m_t.py", record["revision"])})
    (lost,) = plan.remove[0].lost
    assert (lost.reason, lost.back, lost.new_ids) == (plan_module.NO_FILE, True, ("Boost",))


def test_an_update_that_hands_a_device_back_names_the_new_ids():
    swap = {"ours": [[0xFC11, 1, "number", "-1-boost", "Boost"]], "zha": [[0xFC11, 1, "number", "-1-boost_time", "Boost time"]]}
    st = state(t={**TAKE, "endpoints": {"2": [0x0702]}, "swap": swap})
    t_old = {**taken("t", TAKE["fingerprints"], version=1)}
    t_old["names"]["swap"] = swap["ours"]
    devices = {"d1": dev("Acme", "T-1", quirk="z2m_t", layout={1: {0x0702}}), "d2": dev("Other", "T-1", quirk="z2m_t", layout={2: {0x0702}})}
    plan = plan_for(st, devices, {path("t"): t_old})
    (update,) = plan.update
    (lost,) = update.lost
    assert (lost.device, lost.reason, lost.new_ids) == ("d1", plan_module.FILE_MISFIT, ("Boost",))
    assert "ZHA's own quirk takes it back" in integration.text._lost(lost, devices)


def test_odd_endpoints_in_a_record_count_as_unknown():
    assert plan_module.misfit({"endpoints": {"x": [1]}}, dev("Acme", "F-1", layout=WRONG)) is None
    assert plan_module.misfit({"endpoints": {"1": "6"}}, dev("Acme", "F-1", layout=WRONG)) is None
    assert plan_module.misfit({"endpoints": ["1"]}, dev("Acme", "F-1", layout=WRONG)) is None


def test_a_file_that_does_not_take_a_name_over_is_no_file_for_its_device():
    """ZHA ships a quirk for a name the installed version took over: a file of the target or one that
    stays and does not take that name over steps back on the device. The list does not say it moves
    there or keeps it, it names the device with ZHA's quirk taking it back (the outcome is the same)."""
    # The offered version of the file no longer takes the name over: the update hands the device back.
    st = state(t={"fingerprints": [("Acme", "T-1")]})
    devices = {"d1": dev("Acme", "T-1", quirk="z2m_t", name="Hall")}
    plan = plan_for(st, devices, {path("t"): taken("t", [["Acme", "T-1"]], version=1)})
    (update,) = plan.update
    assert update.devices == ("d1",)
    (lost,) = update.lost
    assert (lost.device, lost.reason, lost.file, lost.back) == ("d1", plan_module.FILE_NO_TAKE_OVER, "z2m_t.py", True)
    assert "Hall gets no file from xquirks: `z2m_t.py` does not take it over from ZHA's own quirk. ZHA's own quirk takes it back" in (
        integration.text.change_list(plan, devices, lambda n: n, {}, {}))
    # The state moves the name from a take-over file to one that does not take it over: no move.
    st = state(b={"fingerprints": [(None, "T-1")]})
    plan = plan_for(st, devices, {path("t"): taken("t", [["Acme", "T-1"]])})
    removal = next(c for c in plan.remove if c.name == "z2m_t.py")
    assert removal.moves == () and [(item.device, item.reason, item.file) for item in removal.lost] == [("d1", plan_module.FILE_NO_TAKE_OVER, "z2m_b.py")]
    # A withdrawn take-over file and a file of ours that stays without taking the name over: the device
    # does not keep that one either.
    st = state(b={"fingerprints": [(None, "T-1")], "version": 1})
    records = {path("t"): taken("t", [["Acme", "T-1"]], version=1), path("b"): record("b", [[None, "T-1"]], 1)}
    devices = {"d1": dev("Acme", "T-1", quirk="z2m_t"), "d2": dev("Other", "T-1", quirk="z2m_b")}
    plan = plan_for(st, devices, records, withdrawn={("z2m_t.py", rev("z2m_t.py", 1))})
    (removal,) = plan.remove
    assert removal.reason == "withdrawn" and [(item.device, item.reason, item.back) for item in removal.lost] == [("d1", plan_module.FILE_NO_TAKE_OVER, True)]


# A high-risk file that is not verified: held back while the options do not offer such files.
HIGH = {**A, "risk": "high"}


def held_back(plan) -> list:
    return [(item.name, item.devices) for item in plan.held_back]


def test_a_high_risk_file_is_held_back_with_a_notice_and_not_downloaded():
    st = state(a=HIGH, b=B)
    devices = {"d1": dev("Acme", "A-1", name="Hall"), "d2": dev("Acme", "B-1")}
    # Not checked by the guard: a held-back file holds no list while it waits for a download.
    plan = plan_for(st, devices, verdicts={"z2m_a.py": None})
    assert plan.held is None and plan.unchecked == []
    assert kinds(plan) == {"install": [("z2m_b.py", ("d2",))], "update": [], "remove": []}
    assert held_back(plan) == [("z2m_a.py", ("d1",))] and plan.target == {"z2m_b.py"}


def test_the_options_offer_high_risk_files():
    plan = plan_for(state(a=HIGH), {"d1": dev("Acme", "A-1")}, offer_high_risk=True)
    assert kinds(plan)["install"] == [("z2m_a.py", ("d1",))] and plan.held_back == []


@pytest.mark.parametrize(
    ("spec", "held"),
    [
        ({"risk": "high"}, True),
        # Missing or unknown: high.
        ({"risk": None}, True),
        ({"risk": "severe"}, True),
        ({"risk": "medium"}, False),
        ({"risk": "low"}, False),
        # Verified: checked, whatever its risk.
        ({"risk": "high", "status": "verified"}, False),
    ],
)
def test_only_high_risk_files_that_are_not_verified_are_held_back(spec: dict, held: bool):
    st = state(a={**A, **spec})
    if spec.get("risk", "") is None:
        del st.manifest["a"]["risk"]
    plan = plan_for(st, {"d1": dev("Acme", "A-1")})
    assert bool(plan.held_back) is held and bool(plan.install) is not held


def test_a_file_of_ours_is_never_held_back():
    """The devices that run it get its updates whatever its risk; a device paired since gets it too."""
    st = state(a=HIGH)
    records = {path("a"): record("a", [("Acme", "A-1")])}
    devices = {"d1": dev("Acme", "A-1", quirk="z2m_a"), "d2": dev("Acme", "A-1")}
    plan = plan_for(st, devices, records)
    assert kinds(plan) == {"install": [], "update": [("z2m_a.py", ("d1", "d2"))], "remove": []} and plan.held_back == []
    # At the offered version already: nothing to do, no notice.
    plan = plan_for(st, devices, {path("a"): record("a", [("Acme", "A-1")], version=2)})
    assert plan.changes == 0 and plan.held_back == [] and plan.target == {"z2m_a.py"}
    # One in a folder ZHA loaded before moves to the folder it loads now.
    plan = plan_for(st, {"d1": dev("Acme", "A-1")}, {path("a", "/config/old"): record("a", [("Acme", "A-1")])})
    assert kinds(plan) == {"install": [("z2m_a.py", ("d1",))], "update": [], "remove": [("z2m_a.py", plan_module.OUTSIDE)]}


def test_a_name_that_moves_to_a_held_back_file_stays_with_the_file_of_ours():
    """The data moved Acme / B-1 to a high-risk file: the file of ours keeps the device while the state no
    longer ships it, an update that drops the name names the device as getting none."""
    devices = {"d1": dev("Acme", "A-1", quirk="z2m_a"), "d2": dev("Acme", "B-1", quirk="z2m_a")}
    records = {path("a"): record("a", [("Acme", "A-1"), ("Acme", "B-1")])}
    plan = plan_for(state(b={**B, "risk": "high"}), devices, records)
    assert plan.changes == 0 and held_back(plan) == [("z2m_b.py", ("d2",))]
    plan = plan_for(state(a=A, b={**B, "risk": "high"}), devices, records)
    assert kinds(plan) == {"install": [], "update": [("z2m_a.py", ("d1",))], "remove": []}
    assert plan.update[0].moves == () and plan.update[0].lost == (plan_module.Lost("d2", plan_module.FILE_HELD_BACK, "z2m_b.py"),)
    assert held_back(plan) == [("z2m_b.py", ("d2",))]
    text = integration.text.change_list(plan, devices, lambda n: n, {}, {})
    assert "Acme B-1 gets no file from xquirks: `z2m_b.py` is held back until it is verified on a device (see its notice)" in text


def test_no_notice_promises_a_held_back_file():
    """The notices that say the change list brings the file once the user's file or quirk is gone
    leave a held-back file out: the list would not bring it."""
    st = state(a=HIGH)
    plan = plan_for(st, {"d1": dev("Acme", "A-1")}, present={"z2m_a.py": "f" * 64})
    assert plan.users_files == [] and plan.held_back == [] and plan.changes == 0
    plan = plan_for(st, {"d1": dev("Acme", "A-1", quirk="my_quirk")})
    assert plan.blocked == [] and plan.held_back == []
    # Nor one that could not come anyway.
    assert plan_for(st, {"d1": dev("Acme", "A-1")}, withdrawn={("z2m_a.py", rev("z2m_a.py", 2))}).held_back == []
    assert plan_for(state(a=HIGH, c=A), {"d1": dev("Acme", "A-1")}).held_back == []


def test_a_held_back_take_over_leaves_the_device_on_zhas_quirk():
    st = state(t={**TAKE, "risk": "high"})
    plan = plan_for(st, {"d1": dev("Acme", "T-1", quirk=ZHAS)})
    assert plan.changes == 0 and held_back(plan) == [("z2m_t.py", ("d1",))]
    # Offered: the take-over as before.
    plan = plan_for(st, {"d1": dev("Acme", "T-1", quirk=ZHAS)}, offer_high_risk=True)
    assert kinds(plan)["install"] == [("z2m_t.py", ("d1",))] and plan.install[0].took_over == ("d1",)


def test_a_held_back_file_still_gets_its_misfit_notices():
    """A device that does not fit gets the notice with its report link either way: the next version can
    fit it. The held-back notice names the devices that fit."""
    st = state(f={**FIT, "risk": "high"})
    plan = plan_for(st, {"d1": dev("Acme", "F-1", layout=WRONG), "d2": dev("Acme", "F-1", layout=FITS)})
    assert plan.changes == 0 and held_back(plan) == [("z2m_f.py", ("d2",))]
    assert [(m.name, m.devices) for m in plan.misfits] == [("z2m_f.py", (("d1", "it has no endpoint 3"),))]


def test_a_dropped_take_over_file_is_handed_back_while_its_successor_is_held_back():
    """The state drops z2m_t.py and gives its device to a high-risk file: the hand-back does not wait
    for it, ZHA's quirk takes the device back and the notice names the file held back."""
    st = state(u={"fingerprints": [("Acme", "T-1")], "risk": "high"})
    devices = {"d1": dev("Acme", "T-1", quirk="z2m_t")}
    plan = plan_for(st, devices, {path("t"): taken("t", TAKE["fingerprints"])})
    assert kinds(plan) == {"install": [], "update": [], "remove": [("z2m_t.py", plan_module.HANDED_BACK)]}
    assert plan.remove[0].lost == () and held_back(plan) == [("z2m_u.py", ("d1",))]
    # Offered: the device moves to it instead.
    plan = plan_for(st, devices, {path("t"): taken("t", TAKE["fingerprints"])}, offer_high_risk=True)
    assert kinds(plan) == {"install": [("z2m_u.py", ("d1",))], "update": [], "remove": [("z2m_t.py", plan_module.MOVED)]}
