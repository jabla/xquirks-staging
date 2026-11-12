"""The plan's invariants, checked on many small scenarios (seeded: every run checks the same scenarios).

A scenario is three file names of this collection, a custom quirks folder and four ZHA devices. Per
name: whether the state in use ships it, the names (fingerprints) of its offered version, which may
differ from those of an older version (names move between files), the guard's verdict and whether
the revision is withdrawn. Per name in the folder: a file of ours (at the offered or an older version,
with the names its record keeps), one the user changed, one that cannot be read, or the user's own
file; besides those, files of the user under other names and records of files that are gone or lie
in a folder ZHA no longer loads. Per device: its manufacturer and model (two devices may share
them), whether ZHA ships a quirk for it, disabled or excluded, not reported by ZHA, or reported with a
quirk whose file is gone since ZHA loaded the folder. ZHA applies, per device, the claiming file it
loaded last (our files step back where ZHA ships a quirk, except a version that takes the device's
exact name over from ZHA's quirk: the manifest's over_zha); the plan cannot see the names of the
user's files. A version may take names over; the record of a file of ours keeps the names of its
version, for a take-over version also the exact names it takes over (as the manager writes them, so
devices paired since and left-out devices that came back are covered by their names); a name the
state does not ship has no entry, an entry that says ZHA covers the device or an entry no file
could be built for (both without a file).

The list is applied as the manager does it (also with one step failing: its undo failing too, so the
steps before it stay done, or Home Assistant stopping after the step saved its record), ZHA reloads,
the plan is made again until the list is empty. A working undo is the manager's alone (it puts back
what the steps took): tests_hacs/test_repairs.py and test_edge_cases.py test it, the checker does
not. The checks look at the outcome only, never at why the plan decided:
- I1: after a complete apply the next list is empty, unless a user's file won a device whose file
  changed; then the lists end within three more rounds and none comes back;
- I2: no device is claimed by two files of ours after a complete apply, unless neither changed;
- I3: writes only of revisions that may be written, to files of ours or free names; deletes only of
  files of ours;
- I4: a device that needs a file the list can write runs it afterwards (or a user's file that wins);
- I5: a device that ran a file of ours keeps one, unless it gets none and its file had to change, or
  ZHA's own quirk took it back (the state dropped a file that took the device's name over, or the
  file's version no longer takes it over);
- I6: no file of ours is left at a withdrawn revision;
- I8: every file of ours is run by a device that is not left out (or a user's file won);
- I9: no write claims a device that ran a custom quirk of the user more strongly than before;
- I10: after a crash in the middle of a step (its record saved, the file not written yet) the files
  of ours are still ours;
- I11: a file of ours that the state no longer ships, whatever the reason, keeps no device whose exact
  name its version took over from ZHA's own quirk after a complete apply, unless a device on a name it
  did not take over runs it too;
- I12: no install or update of the list writes a version for a device whose layout the plan sees and
  that does not fit the version;
- I13: the misfit notices name exactly the devices the plan sees that the one offered file claiming
  them does not fit (not left out, not on a custom quirk of the user, not on ZHA's own quirk the
  file does not take over); the "ZHA does not apply it" notice names none of them;
- I14: a device the plan sees as running a file of ours that does not fit the offered version of the
  one file claiming it, left without a file by the list, is named with reason FILE_MISFIT.

Endpoints: a version may name the endpoints it puts clusters on (its ENDPOINTS, in the manifest
entry of the offered version); ZHA skips such a version for a device that does not fit them (the
runtime check). An older version may have none (written before the runtime check). Each device has
a layout ZHA knows; the plan sees it unless ZHA does not report it.

test_the_checker_catches_deliberate_plan_bugs runs the same checks against copies of plan.py with
one bug each: each must fail, in the random scenarios or in one written for it (TARGETED).
"""

from __future__ import annotations

import dataclasses
import hashlib
import importlib.util
import os
import random
import sys
from pathlib import Path

from . import integration

plan_module = integration.plan
content = integration.content
UNREADABLE = integration.files.UNREADABLE
matches = integration.matching.matches

FOLDER = "/config/custom_zha_quirks"
OLD_FOLDER = "/config/old_quirks"
NAMES = ("z2m_a.py", "z2m_b.py", "z2m_c.py")
USER_NAMES = ("my_quirk.py", "z2m_mine.py")
IDS = ("d1", "d2", "d3", "d4")
MAKERS = ("M1", "M2")
MODELS = ("X1", "X2", "X3")
# Scenarios per run; XQUIRKS_PLAN_SCENARIOS raises it for a deeper search.
SCENARIOS = int(os.environ.get("XQUIRKS_PLAN_SCENARIOS", "4000"))
MUTANT_SCENARIOS = int(os.environ.get("XQUIRKS_PLAN_MUTANT_SCENARIOS", "4000"))

# Device layouts (endpoint, announced input clusters) and the endpoints a version may put clusters on.
LAYOUTS = (
    ((1, frozenset({6})),),
    ((1, frozenset({6})), (2, frozenset({0x0702}))),
    ((2, frozenset({6, 0x0702})),),
    ((1, frozenset()), (3, frozenset({6}))),
    # Zigbee2MQTT's choice: cluster 6 on endpoint 1 first, also where endpoint 2 has it too.
    ((1, frozenset({6})), (2, frozenset({6, 0x0702}))),
)
# The last: a cluster no endpoint announces on endpoint 3, which a device with endpoint 1 does not
# fit (z2m sends it to the device's first endpoint).
ENDPOINT_CHOICES = (((1, (6,)),), ((1, ()), (2, (0x0702,))), ((2, (6,)),), ((1, (0xFC00,)),), ((3, (0xFC00,)),))

OK, REFUSED, UNCHECKED = "ok", "refused", "unchecked"
# Who a file in the folder belongs to.
OURS, CHANGED, UNREADABLE_FILE, USER = "ours", "changed", "unreadable", "user"


@dataclasses.dataclass(frozen=True)
class Version:
    """What a file registers: its names; the sha256 and revision of its bytes."""

    names: tuple[tuple[str | None, str], ...]
    claimed_elsewhere: tuple[tuple[str, str], ...]
    sha: str
    revision: str
    over_zha: bool = False  # takes its exact names over from ZHA's own quirk
    # (endpoint, the clusters it puts there) of its runtime check; None: a version without one
    endpoints: tuple[tuple[int, tuple[int, ...]], ...] | None = None

    @property
    def record_names(self) -> dict:
        """The names its record keeps, as the manager writes them (plan.names_of of its entry)."""
        names = {"fingerprints": [list(n) for n in self.names], "claimed_elsewhere": [list(n) for n in self.claimed_elsewhere]}
        if self.over_zha:
            names["takes_over"] = [list(n) for n in self.names if n[0] is not None]
        if self.endpoints is not None:
            names["endpoints"] = {str(ep): list(clusters) for ep, clusters in self.endpoints}
        return names


@dataclasses.dataclass(frozen=True)
class InFolder:
    owner: str  # OURS, CHANGED, UNREADABLE_FILE or USER
    version: Version  # what ZHA loads from it
    steps_back: bool = True  # steps back where ZHA ships a quirk (ours always do)
    generated: str | None = None  # a user's file with the collection's docstring: its revision


@dataclasses.dataclass(frozen=True)
class Facts:
    pair: tuple[str, str]
    zha_ships: bool = False
    disabled: bool = False
    excluded: bool = False
    unknown: bool = False  # ZHA does not say what it runs
    stale: str | None = None  # a file name ZHA still reports although the file is gone since
    # (endpoint, the input clusters it announces): what ZHA knows of the device as it joined
    layout: tuple[tuple[int, frozenset[int]], ...] = ((1, frozenset()),)
    layout_hidden: bool = False  # ZHA does not report the layout to the plan


@dataclasses.dataclass
class Scenario:
    offered: dict[str, Version]
    verdict: dict[str, str]
    withdrawn: frozenset[tuple[str, str]]
    folder: dict[str, InFolder]
    records: dict[str, dict]
    outside: dict[str, str]  # path -> sha256 of the files in the old folder
    devices: dict[str, Facts]
    order: tuple[str, ...]  # load order: ZHA tries the file loaded last first
    # Names not shipped that have an entry without a file (it says ZHA covers the device, or no
    # file could be built): name -> the manifest entry.
    fileless: dict[str, dict] = dataclasses.field(default_factory=dict)

    def copy(self, **changes) -> Scenario:
        return dataclasses.replace(self, **changes)


def stem(name: str) -> str:
    return name.removesuffix(".py")


def claims(version: Version, pair: tuple[str, str]) -> bool:
    entry = {"fingerprints": [list(n) for n in version.names], "claimed_elsewhere": [list(n) for n in version.claimed_elsewhere]}
    return bool(matches({"x": entry}, {pair}))


def strength(version: Version, pair: tuple[str, str]) -> int:
    """2 when a name of the version is the device's exact name, 1 for a model-only one, 0 for none."""
    if not claims(version, pair):
        return 0
    return 2 if (pair[0], pair[1]) in version.names else 1


def takes(version: Version, pair: tuple[str, str]) -> bool:
    """The version takes the device over from ZHA's own quirk: it lists the exact name with over_zha."""
    return version.over_zha and pair in version.names


def fits(version: Version, facts: Facts) -> bool:
    """The device fits the version's endpoints: each endpoint is there, each cluster lands where
    Zigbee2MQTT sends it (the first endpoint that announces it, the device's first endpoint when none
    does) on the endpoint the version puts it on. A version without endpoints fits all."""
    if version.endpoints is None:
        return True
    announced = dict(sorted(facts.layout))
    for ep, clusters in version.endpoints:
        if ep not in announced:
            return False
        if any(next((other for other, cs in announced.items() if c in cs), min(announced)) != ep for c in clusters):
            return False
    return True


def record_of(version: Version) -> dict:
    """The record the manager writes: no device in it, the names of the version only."""
    return {"sha256": version.sha, "revision": version.revision, "names": version.record_names}


def taken_names(record: dict | None) -> set[tuple[str, str]]:
    """The exact names a record's version takes over from ZHA's own quirk."""
    return {tuple(n) for n in (record or {}).get("names", {}).get("takes_over", ())}


def ours(scenario: Scenario) -> dict[str, Version]:
    """The files of ours in the folder: name -> the version its record names."""
    return {name: f.version for name, f in scenario.folder.items() if f.owner == OURS}


def load(scenario: Scenario) -> dict[str, str]:
    """What ZHA applies to each device when it loads the folder: a module, "" for none. It tries the
    quirks of the exact name before those of the model-only name, within one name the one loaded
    last first; a quirk ZHA ships has the exact name and loads before the custom ones."""
    applied = {}
    for device_id, facts in scenario.devices.items():
        candidates = [(2, -1, "zhaquirks.shipped")] if facts.zha_ships else []
        for index, name in enumerate(scenario.order):
            f = scenario.folder.get(name)
            if f is None or f.owner == UNREADABLE_FILE or (facts.zha_ships and f.steps_back and not takes(f.version, facts.pair)):
                continue
            if not fits(f.version, facts):
                continue  # its runtime check steps back
            if level := strength(f.version, facts.pair):
                candidates.append((level, index, stem(name)))
        applied[device_id] = max(candidates)[2] if candidates else ""
    return applied


def reports(scenario: Scenario, applied: dict[str, str], fresh: bool) -> dict[str, str | None]:
    """What ZHA reports: None where it does not say; a stale quirk until it loads the folder again."""
    out: dict[str, str | None] = {}
    for device_id, facts in scenario.devices.items():
        if facts.unknown:
            out[device_id] = None
        elif facts.stale and not fresh and facts.stale not in scenario.folder:
            out[device_id] = stem(facts.stale)
        else:
            out[device_id] = applied[device_id]
    return out


def inputs(scenario: Scenario, reported: dict[str, str | None]) -> tuple[tuple, dict]:
    manifest = {
        stem(name).removeprefix("z2m_"): {
            "file": f"quirks/{name}",
            "fingerprints": [list(n) for n in v.names],
            "claimed_elsewhere": [list(n) for n in v.claimed_elsewhere],
            "status": "generated",
            "vendor": "V",
            "model": stem(name),
            **({"over_zha": {"adds": ["x"], "zha_only": []}} if v.over_zha else {}),
            **({"endpoints": {str(ep): list(clusters) for ep, clusters in v.endpoints}} if v.endpoints is not None else {}),
        }
        for name, v in scenario.offered.items()
    }
    for name, entry in scenario.fileless.items():
        if name not in scenario.offered:
            manifest[stem(name).removeprefix("z2m_")] = entry
    state = content.ContentState(manifest, {n: v.sha for n, v in scenario.offered.items()}, revisions={n: v.revision for n, v in scenario.offered.items()})
    devices = {
        i: plan_module.Device(f.pair[0], f.pair[1], i, reported[i], f.disabled, None if f.layout_hidden else f.layout) for i, f in scenario.devices.items()
    }
    disk = {}
    for path in scenario.records:
        name = os.path.basename(path)
        if os.path.dirname(path) == OLD_FOLDER:
            disk[path] = scenario.outside.get(path)
        elif (f := scenario.folder.get(name)) is None:
            disk[path] = None
        elif f.owner == UNREADABLE_FILE:
            disk[path] = UNREADABLE
        else:
            disk[path] = f.version.sha
    present = {name: (None if f.owner == UNREADABLE_FILE else f.version.sha) for name, f in scenario.folder.items()}
    generated = {name: f.generated for name, f in scenario.folder.items() if f.generated}
    verdicts = {name: {OK: (), REFUSED: ("refused",), UNCHECKED: None}[v] for name, v in scenario.verdict.items()}
    excluded = frozenset(i for i, f in scenario.devices.items() if f.excluded)
    args = (state, devices, dict(scenario.records), disk, FOLDER, present)
    return args, {"generated": generated, "withdrawn": scenario.withdrawn, "verdicts": verdicts, "excluded": excluded}


def plan_of(scenario: Scenario, reported: dict[str, str | None], module=plan_module):
    args, kwargs = inputs(scenario, reported)
    return module.make_plan(*args, **kwargs)


def writable(scenario: Scenario, name: str) -> bool:
    return name in scenario.offered and scenario.verdict[name] == OK and (name, scenario.offered[name].revision) not in scenario.withdrawn


def housekeeping(scenario: Scenario, plan) -> Scenario:
    """What the manager does with the records after a refresh: those of files that are gone go,
    those an apply left with the version before (a crash) settle."""
    records = {p: plan.settled.get(p, r) for p, r in scenario.records.items() if p not in plan.gone}
    return scenario.copy(records=records)


def apply(scenario: Scenario, plan, problems: list[str], fail: int | None = None, crash: bool = False) -> Scenario:
    """Carry the list out like manager.async_apply: removals, updates, installs. At the step fail the
    undo fails too: the steps before it stay done. With crash, Home Assistant stops at that step after
    saving its record (an update keeps the version before as previous), before the file changes."""
    steps = (
        [("remove", c.path) for c in plan.remove]
        + [("update", c.path) for c in plan.update]
        + [("install", f"{FOLDER}/{c.name}") for c in plan.install]
    )
    folder, records, outside = dict(scenario.folder), dict(scenario.records), dict(scenario.outside)

    def written(name: str) -> dict:
        """The record of the offered version."""
        return record_of(scenario.offered[name])

    for index, (kind, path) in enumerate(steps):
        name = os.path.basename(path)
        if os.path.dirname(path) == OLD_FOLDER:
            if kind != "remove" or path not in outside or records.get(path, {}).get("sha256") != outside[path]:
                problems.append(f"I3 {kind} of {path} in the old folder")
            if fail == index:
                break
            outside.pop(path, None)
            records.pop(path, None)
            continue
        f = folder.get(name)
        if kind in ("remove", "update") and (f is None or f.owner != OURS):
            problems.append(f"I3 {kind} of {name}, which is not ours")
        if kind == "install" and f is not None:
            problems.append(f"I3 install of {name} over a file in the folder")
        if kind in ("update", "install") and not writable(scenario, name):
            problems.append(f"I3 {kind} of {name}, which may not be written")
        if fail == index:
            if crash and kind == "update":
                records[path] = {**written(name), "previous": records[path]}
            elif crash and kind == "install":
                records[path] = written(name)
            break
        if kind == "remove":
            folder.pop(name, None)
            records.pop(path, None)
        else:
            folder[name] = InFolder(OURS, scenario.offered[name])
            records[path] = written(name)
    return scenario.copy(folder=folder, records=records, outside=outside)


def user_module(scenario: Scenario, module: str | None) -> bool:
    """The module is a custom quirk of the user: a file in the folder that is not ours."""
    if not module or module.startswith("zhaquirks."):
        return False
    f = scenario.folder.get(f"{module}.py")
    return f is not None and f.owner != OURS


def our_module(scenario: Scenario, module: str | None) -> str | None:
    f = scenario.folder.get(f"{module}.py") if module else None
    return f"{module}.py" if f is not None and f.owner == OURS else None


def fits_seen(version: Version, facts: Facts) -> bool:
    """The device fits the version as the plan sees it: a layout ZHA does not report fits."""
    return facts.layout_hidden or fits(version, facts)


def notice_problems(scenario: Scenario, plan, reported: dict[str, str | None]) -> tuple[list[str], list[tuple[str, str]]]:
    """I13: what the plan says about devices that do not fit; the I14 candidates (device, file): a
    device the plan sees running a file of ours whose offered version it does not fit and that is not
    named lost for that reason (check() keeps those the list leaves without a file)."""
    problems, unnamed = [], []
    owners = {i: [n for n, v in scenario.offered.items() if claims(v, f.pair)] for i, f in scenario.devices.items()}
    expected = set()
    for i, facts in scenario.devices.items():
        if len(owners[i]) != 1 or facts.disabled or facts.excluded or fits_seen(scenario.offered[owners[i][0]], facts):
            continue
        name = owners[i][0]
        module = reported[i]
        if user_module(scenario, module):
            continue
        if module == "zhaquirks.shipped" and not takes(scenario.offered[name], facts.pair):
            continue
        expected.add((name, i))
    noticed = {(m.name, i) for m in plan.misfits for i, _why in m.devices}
    if noticed != expected:
        problems.append(f"I13 misfit notices {sorted(noticed)}, expected {sorted(expected)}")
    unfit = {i for _name, i in expected}
    for item in plan.not_applied:
        if bad := sorted(set(item.devices) & unfit):
            problems.append(f"I13 {item.name}: ZHA-does-not-apply notice names devices that do not fit: {bad}")
    named = {(lost.device, lost.reason) for change in (*plan.update, *plan.remove) for lost in change.lost}
    for change in (*plan.update, *plan.remove):
        name = os.path.basename(change.path)
        if os.path.dirname(change.path) != FOLDER:
            continue  # a file in a folder ZHA no longer loads runs on no device
        for i, facts in scenario.devices.items():
            if facts.disabled or facts.excluded or len(owners[i]) != 1 or owners[i][0] != name or fits_seen(scenario.offered[name], facts):
                continue
            # Unreported: it runs the version in the folder where that version claims it and fits it.
            installed = change_version(scenario, name)
            runs_it = reported[i] == stem(name) or (reported[i] is None and claims(installed, facts.pair) and fits(installed, facts))
            if runs_it and (i, plan_module.FILE_MISFIT) not in named:
                unnamed.append((i, name))
    return problems, unnamed


def change_version(scenario: Scenario, name: str) -> Version:
    """The version of a file of ours in the folder (before the list)."""
    f = scenario.folder.get(name)
    return f.version if f is not None else scenario.offered[name]


def check(scenario: Scenario, module=plan_module, fail: int | None = None, crash: bool = False) -> list[str]:
    problems: list[str] = []
    applied = load(scenario)
    reported = reports(scenario, applied, fresh=False)
    plan = plan_of(scenario, reported, module)
    if plan.held:
        if plan.remove or plan.update or plan.install:
            problems.append("held with changes")
        return problems
    noticed, unnamed = notice_problems(scenario, plan, reported)
    problems += noticed
    base = housekeeping(scenario, plan)
    after = apply(base, plan, problems, fail, crash)
    if fail is not None and crash:
        # I10: after a crash in the middle of a step the files of ours are still ours.
        again = plan_of(after, reports(after, load(after), fresh=True), module)
        if lost := set(again.changed) - set(plan.changed):
            problems.append(f"I10 after a crash, files of ours count as changed by the user: {sorted(lost)}")
    after_applied = load(after)
    complete = fail is None
    before_ours, after_ours = ours(base), ours(after)
    pairs = {i: f.pair for i, f in scenario.devices.items()}

    def left_out(i: str) -> bool:
        return scenario.devices[i].disabled or scenario.devices[i].excluded

    def stale(i: str) -> bool:
        """ZHA reports a file of this collection that is gone from the folder."""
        module = reported[i]
        return bool(module) and module.startswith("z2m_") and f"{module}.py" not in base.folder

    def ran(i: str) -> set[str]:
        """The files of ours the device ran: what ZHA applied, or those claiming it where ZHA never says
        (not a version whose runtime check steps back for it)."""
        if scenario.devices[i].unknown:
            return {n for n, v in before_ours.items() if claims(v, pairs[i]) and fits(v, scenario.devices[i])}
        return {n} if (n := our_module(base, applied[i])) else set()

    def runs_after(i: str) -> set[str]:
        if scenario.devices[i].unknown:
            return {n for n, v in after_ours.items() if claims(v, pairs[i]) and fits(v, scenario.devices[i])}
        return {n} if (n := our_module(after, after_applied[i])) else set()

    def user_won(i: str) -> bool:
        return not scenario.devices[i].unknown and after_applied[i] != applied[i] and user_module(after, after_applied[i])

    def zha_took_back(i: str) -> bool:
        """The device ran a file of ours, runs ZHA's own quirk after the apply and no file of ours takes
        its exact name over any more. The plan saw it run a file of ours only: a version or a file that
        does not take it over may have been written for it, which steps back (the next list removes it)."""
        return (
            not scenario.devices[i].unknown and scenario.devices[i].zha_ships and after_applied[i] == "zhaquirks.shipped" and bool(ran(i))
            and not any(takes(v, pairs[i]) for v in after_ours.values() if claims(v, pairs[i]))
        )

    def back_to_zha(i: str) -> bool:
        """ZHA's own quirk (or a file of the user, which wins anyway) took the device back, as it
        should: for each file of ours it ran, the state dropped the file while it had taken the device
        over (the hand-back), the file's version no longer takes the device over, or the state gives
        the device's name to another file that does not take it over."""
        if not (scenario.devices[i].zha_ships and (after_applied[i] == "zhaquirks.shipped" or user_module(after, after_applied[i]))):
            return False
        offered_to = [m for m, v in scenario.offered.items() if claims(v, pairs[i])]
        return all(
            (n not in scenario.offered and pairs[i] in taken_names(base.records.get(f"{FOLDER}/{n}")))
            or (n in after_ours and not takes(after_ours[n], pairs[i]))
            or (n not in after_ours and offered_to and n not in offered_to and not any(takes(scenario.offered[m], pairs[i]) for m in offered_to))
            for n in ran(i)
        )

    # Facts the plan could not see: a user's file won a device, a report was older than the folder, or
    # ZHA's own quirk took a device back that the plan saw run a file of ours.
    unseen = any(user_won(i) or stale(i) or zha_took_back(i) for i in pairs)
    # ... or a device whose layout the plan does not see that does not fit a version of a file claiming
    # it (offered, or in the folder): the plan counts it as running or needing the file, its runtime
    # check steps back.
    unseen = unseen or any(
        f.layout_hidden and any(claims(v, f.pair) and not fits(v, f) for v in (*scenario.offered.values(), *before_ours.values()))
        for f in scenario.devices.values()
    )

    for name, f in base.folder.items():
        if f.owner != OURS and after.folder.get(name) != f:
            problems.append(f"I3 the user's {name} changed")

    # I14: a device the list leaves without a file of ours (no user's file won it) that ran a file whose
    # offered version it does not fit is named lost for that reason.
    for i, name in unnamed:
        if not runs_after(i) and not user_won(i):
            problems.append(f"I14 {i} runs {name}, does not fit its offered version, is left without a file and not named as lost for that reason")

    # I12: no write for a device that does not fit the version written.
    for change in (*plan.install, *plan.update):
        for i in change.devices:
            facts = scenario.devices[i]
            if not facts.layout_hidden and not fits(scenario.offered[change.name], facts):
                problems.append(f"I12 {change.name} is written for {i}, which does not fit it")

    # I9: no write claims anew a device that ran a custom quirk of the user. An installed version that
    # does not fit the device (as the plan sees it) never claimed it: its runtime check stepped back.
    for name, v in after_ours.items():
        if before_ours.get(name) == v:
            continue
        old = before_ours.get(name)
        for i, pair in pairs.items():
            before = strength(old, pair) if old and fits_seen(old, scenario.devices[i]) else 0
            if strength(v, pair) > before and user_module(base, reported[i]) and fits(v, scenario.devices[i]):
                problems.append(f"I9 {name} claims {i} more strongly, which runs the user's {reported[i]}")

    if complete:
        # I2
        for i, pair in pairs.items():
            holders = [n for n, v in after_ours.items() if claims(v, pair)]
            if len(holders) > 1 and any(before_ours.get(n) != after_ours[n] for n in holders):
                problems.append(f"I2 {i} is claimed by {holders}")
        # I6
        for name, v in after_ours.items():
            if (name, v.revision) in scenario.withdrawn:
                problems.append(f"I6 {name} stays at a withdrawn revision")

        owners = {i: [n for n, v in scenario.offered.items() if claims(v, pair)] for i, pair in pairs.items()}

        def blocked(name: str) -> bool:
            # The installed version claims a device it does not fit (as the plan sees it) with no strength:
            # its runtime check steps back there, the user's quirk wins only so.
            old = before_ours.get(name)
            return any(
                strength(scenario.offered[name], pair) > (strength(old, pair) if old and fits_seen(old, scenario.devices[e]) else 0)
                and user_module(base, reported[e]) and fits_seen(scenario.offered[name], scenario.devices[e])
                for e, pair in pairs.items()
            )

        def conflicted(name: str) -> bool:
            return any(len(owners[i]) > 1 and name in owners[i] for i in pairs)

        def can_have(name: str) -> bool:
            """The file may be written (or is there at the offered version) and nothing keeps it out."""
            at_offer = before_ours.get(name) == scenario.offered[name]
            fine = (name, scenario.offered[name].revision) not in scenario.withdrawn and (at_offer or scenario.verdict[name] == OK)
            held = (f := base.folder.get(name)) is not None and f.owner != OURS
            return fine and not held and not blocked(name) and not conflicted(name)

        # I4
        for i in pairs:
            if left_out(i) or len(owners[i]) != 1:
                continue
            (name,) = owners[i]
            if not scenario.devices[i].unknown and scenario.devices[i].zha_ships and not takes(scenario.offered[name], pairs[i]):
                continue  # a file that does not take the device over steps back for ZHA's quirk
            if not fits(scenario.offered[name], scenario.devices[i]):
                continue  # its runtime check steps back for the device
            # Needs it by the rule, with what ZHA said in line with what it applied (no stale report).
            if scenario.devices[i].unknown:
                needed = bool(ran(i))
            else:
                taken = applied[i] == "zhaquirks.shipped" and takes(scenario.offered[name], pairs[i])
                needed = not stale(i) and (applied[i] == "" or bool(ran(i)) or taken)
            if not needed or not can_have(name):
                continue
            if name not in runs_after(i) and not user_won(i):
                problems.append(f"I4 {i} needs {name}, runs {after_applied[i]!r}")

        # I5
        for i in pairs:
            if left_out(i) or not ran(i) or runs_after(i) or user_won(i) or back_to_zha(i):
                continue
            # A device that does not fit the one file on offer for it gets none: the plan leaves it out, or
            # (a layout the plan does not see) the file's runtime check steps back.
            gets_none = len(owners[i]) != 1 or not can_have(owners[i][0]) or not fits(scenario.offered[owners[i][0]], scenario.devices[i])
            had_to = any(
                (n, before_ours[n].revision) in scenario.withdrawn
                or after_ours.get(n, before_ours[n]) != before_ours[n]
                or any(g != n and v == scenario.offered.get(g) and any(claims(v, p) and claims(before_ours[n], p) for p in pairs.values()) for g, v in after_ours.items())
                for n in ran(i)
            )
            if not (gets_none and had_to):
                problems.append(f"I5 {i} lost its file (gets none: {gets_none}, had to change: {had_to})")

        # I8
        for name, v in after_ours.items():
            used = [i for i, pair in pairs.items() if not left_out(i) and claims(v, pair) and name in runs_after(i)]
            if not used and not unseen:
                problems.append(f"I8 {name} is run by no device")

        # I11: a dropped file keeps no device on a name its version took over, unless a device on
        # another name runs it too (that device would be left without a quirk).
        for name in before_ours:
            if name in scenario.offered or unseen:
                continue
            taken = taken_names(base.records.get(f"{FOLDER}/{name}"))
            users = {i for i in pairs if not left_out(i) and name in ran(i)}
            if any(pairs[i] not in taken for i in users):
                continue
            for i in sorted(users):
                if name in runs_after(i):
                    problems.append(f"I11 {name} keeps {i}, whose name {pairs[i]} it took over from ZHA's quirk, after the state dropped it")


    # I1: the lists end; none comes back.
    current, seen, rounds = after, [], 0
    while True:
        fresh = reports(current, load(current), fresh=True)
        again = plan_of(current, fresh, module)
        if not (again.remove or again.update or again.install):
            break
        if complete and rounds == 0 and not unseen:
            problems.append(f"I1 another list after a complete apply: {again.key}")
        if again.key in seen:
            problems.append("I1 a list came back")
            break
        seen.append(again.key)
        current = apply(housekeeping(current, again), again, problems)
        rounds += 1
        if rounds > 3:
            problems.append("I1 no end within three more rounds")
            break
    return problems


def _sha(*parts: object) -> str:
    return hashlib.sha256("/".join(map(str, parts)).encode()).hexdigest()


# How often a name a version's model-only name catches is given to another definition (claimed_elsewhere).
ELSEWHERE = 0.4


def left_to_others(pair: tuple[str, str], names) -> bool:
    """A name a version may leave to other definitions, as manifests hold claimed_elsewhere: one its
    model-only name would catch, never one of its own exact names.
    (Checked after the draw: the draws of a scenario stay the same.)"""
    return pair not in names and (None, pair[1]) in names


def random_names(rng: random.Random, pool: list[tuple[str, str]]) -> tuple[tuple[str | None, str], ...]:
    names = set()
    for pair in pool:
        if rng.random() < 0.35:
            names.add(pair)
    if rng.random() < 0.2:
        names.add((None, rng.choice(MODELS)))
    return tuple(sorted(names, key=str))


def random_scenario(rng: random.Random, fit_rng: random.Random | None = None) -> Scenario:
    """fit_rng draws the endpoints of versions and the layouts of devices: a stream of its own, so the
    other facts of each scenario stay what they were before endpoints came in."""
    fit_rng = fit_rng or random.Random(16)
    pool = [(m, x) for m in MAKERS for x in MODELS]
    pairs = [rng.choice(pool) for _ in IDS]
    if rng.random() < 0.3:
        pairs[3] = pairs[2]  # two devices of one model
    devices = {}
    for i, pair in zip(IDS, pairs):
        stale = rng.choice(NAMES) if rng.random() < 0.08 else None
        layout = fit_rng.choice(LAYOUTS) if fit_rng.random() < 0.3 else LAYOUTS[0]
        devices[i] = Facts(pair, rng.random() < 0.15, rng.random() < 0.08, rng.random() < 0.08, rng.random() < 0.12, stale, layout, fit_rng.random() < 0.1)
    # The offered versions: mostly one file per device name, sometimes two (the safety net).
    # Sorted: a set's order follows the string hashes, which change from run to run.
    owner = {pair: rng.choice((*NAMES, None)) for pair in sorted(set(pairs))}
    offered, verdict = {}, {}
    for name in NAMES:
        if rng.random() < 0.85:
            names = {pair for pair, o in owner.items() if o == name}
            if rng.random() < 0.1:
                names.add(rng.choice(pairs))
            if rng.random() < 0.1:
                names.add((None, rng.choice(MODELS)))
            elsewhere = tuple(sorted({p for p in pairs if rng.random() < ELSEWHERE and left_to_others(p, names)}))
            endpoints = fit_rng.choice(ENDPOINT_CHOICES) if fit_rng.random() < 0.5 else None
            offered[name] = Version(tuple(sorted(names, key=str)), elsewhere, _sha(name, "new"), _sha(name, "new")[:8], rng.random() < 0.3, endpoints)
            verdict[name] = rng.choice((OK, OK, OK, OK, REFUSED, UNCHECKED if rng.random() < 0.3 else OK))
    withdrawn = set()
    for name in NAMES:
        if name in offered and rng.random() < 0.12:
            withdrawn.add((name, offered[name].revision))
        if rng.random() < 0.2:
            withdrawn.add((name, _sha(name, "old")[:8]))
    folder, records, outside, older = {}, {}, {}, {}
    for name in NAMES:
        # An older version may leave names to another file too (its record keeps claimed_elsewhere). It
        # takes names over only where the state's version does or the state no longer ships the name
        # (a state never turns a take-over file into a plain one while ZHA still ships the quirk).
        old_names = random_names(rng, sorted(set(pairs)))
        old = Version(old_names, tuple(sorted({p for p in pairs if rng.random() < ELSEWHERE and left_to_others(p, old_names)})), _sha(name, "old"), _sha(name, "old")[:8])
        if (name not in offered or offered[name].over_zha) and rng.random() < 0.3:
            old = dataclasses.replace(old, over_zha=True)
        if fit_rng.random() < 0.3:
            old = dataclasses.replace(old, endpoints=fit_rng.choice(ENDPOINT_CHOICES))
        older[name] = old
        k = rng.random()
        if k < 0.3:
            pass
        elif k < 0.5 and name in offered:
            folder[name] = InFolder(OURS, offered[name])
        elif k < 0.78:
            folder[name] = InFolder(OURS, old)
        elif k < 0.84:
            folder[name] = InFolder(CHANGED, Version(random_names(rng, sorted(set(pairs))), (), _sha(name, "edited"), "edited0"), rng.random() < 0.5)
            records[f"{FOLDER}/{name}"] = record_of(old)
        elif k < 0.87:
            folder[name] = InFolder(UNREADABLE_FILE, old)
            records[f"{FOLDER}/{name}"] = record_of(old)
        elif k < 0.9:
            records[f"{FOLDER}/{name}"] = record_of(old)  # deleted by the user
        else:
            copy = offered.get(name) if name in offered and rng.random() < 0.4 else old
            folder[name] = InFolder(USER, copy, rng.random() < 0.5, copy.revision if rng.random() < 0.7 else None)
        if folder.get(name) and folder[name].owner == OURS:
            # As the manager wrote it: the names of the version, no devices. The devices of the
            # scenario may have joined after the write, or been left out then and be back now.
            records[f"{FOLDER}/{name}"] = record_of(folder[name].version)
        if rng.random() < 0.05:
            records[f"{OLD_FOLDER}/{name}"] = record_of(old)
            outside[f"{OLD_FOLDER}/{name}"] = old.sha
    # A guarantee of the exact coupling, which the hand-back relies on: ZHA ships a quirk for every name
    # the take-over record of a file the state no longer ships names. A content state needs the Home
    # Assistant release it was built for or newer, so the user's release is at least the one the
    # take-over version was built for, whose ZHA shipped the quirk the take-over was measured against.
    # It breaks only when Home Assistant goes back to an older release or a newer zha-quirks drops
    # that quirk; the scenarios hold neither.
    taken = {tuple(n) for path, r in records.items() if os.path.basename(path) not in offered for n in r["names"].get("takes_over", ())}
    devices = {i: dataclasses.replace(f, zha_ships=True) if f.pair in taken else f for i, f in devices.items()}
    for name in USER_NAMES:
        if rng.random() < 0.25:
            mine = Version(random_names(rng, sorted(set(pairs))), (), _sha(name, "mine"), "mine0000")
            folder[name] = InFolder(USER, mine, rng.random() < 0.5)
    order = list((*NAMES, *USER_NAMES))
    rng.shuffle(order)
    # A name the state does not ship: no entry, an entry that says ZHA covers the device or an entry no
    # file could be built for (it keeps the names of the version before), about a third each.
    fileless = {}
    for name in NAMES:
        k = rng.random()
        if name in offered or k < 1 / 3:
            continue
        if k < 2 / 3:
            fileless[name] = {"file": None, "fingerprints": [], "status": "upstream"}
        else:
            names = {"fingerprints": [list(n) for n in older[name].names], "claimed_elsewhere": [list(n) for n in older[name].claimed_elsewhere]}
            fileless[name] = {"file": None, **names, "status": "generated", "not_built": "no file could be built"}
    return Scenario(offered, verdict, frozenset(withdrawn), folder, records, outside, devices, tuple(order), fileless)


def failures(scenario: Scenario, rng: random.Random, module=plan_module) -> list[tuple[int | None, bool]]:
    """The complete apply plus one failing step (its undo failing, or a crash) when the list has steps."""
    plan = plan_of(scenario, reports(scenario, load(scenario), fresh=False), module)
    steps = 0 if plan.held else plan.changes
    runs = [(None, False)]
    if steps:
        runs.append((rng.randrange(steps), rng.random() < 0.5))
    return runs


def without_endpoints(scenario: Scenario) -> Scenario:
    """The scenario as it was before endpoints came in: no version has a runtime check."""
    def plain(version: Version) -> Version:
        return dataclasses.replace(version, endpoints=None)

    records = {path: {**r, "names": {k: v for k, v in r["names"].items() if k != "endpoints"}} for path, r in scenario.records.items()}
    return scenario.copy(
        offered={name: plain(v) for name, v in scenario.offered.items()},
        folder={name: dataclasses.replace(f, version=plain(f.version)) for name, f in scenario.folder.items()},
        records=records,
        devices={i: dataclasses.replace(f, layout=LAYOUTS[0], layout_hidden=False) for i, f in scenario.devices.items()},
    )


def search(scenarios: int, module=plan_module, stop_at_first: bool = False) -> list[tuple[Scenario, list[str]]]:
    """Each scenario twice: without endpoints (what the checker searched before they came in, a
    misfit hides no other bug there) and with them; each with its own stream for the failing step."""
    rng, fit_rng = random.Random(6), random.Random(16)
    found = []
    for _ in range(scenarios):
        scenario = random_scenario(rng, fit_rng)
        for variant, draws in ((without_endpoints(scenario), rng), (scenario, fit_rng)):
            for fail, crash in failures(variant, draws, module):
                if problems := check(variant, module, fail, crash):
                    found.append((variant, problems))
                    if stop_at_first:
                        return found
    return found


def test_plan_invariants():
    found = search(SCENARIOS)
    assert not found, found[:3]


# Deliberate bugs: (what it breaks, text of plan.py, the text with the bug). Each must fail the checker.
BUGS = [
    ("no overlap check", "and users_of and not claimed & set(claimed_by_target)", "and users_of"),
    ("a withdrawn revision stays", 'if (name, record["revision"]) not in withdrawn and users_of', "if users_of"),
    ("no user-quirk block", "if name in conflicted or withdrawn_offer(name) or custom[name]:", "if name in conflicted or withdrawn_offer(name):"),
    ("unreported devices not counted", "if kind[device_id] == UNKNOWN:\n            return {name", "if False:\n            return {name"),
    ("left-out devices counted", "return devices[device_id].disabled or device_id in excluded", "return False"),
    ("unwritable writes", "if verdict:\n                plan.refused", "if False:\n                plan.refused"),
    ("unused files stay", "and users_of and not claimed", "and True and not claimed"),
    ("the user's file under our name ignored", "        if name in users:\n            if name not in recorded and", "        if False:\n            if name not in recorded and"),
    ("no update offered", 'if record["sha256"] != state.shas[name]:\n                plan.update', 'if False:\n                plan.update'),
    ("the conflict net missing", "if name in conflicted or", "if False or"),
    ("a stale report counted as the user's quirk", 'if quirk.startswith(PREFIX) and f"{quirk}.py" not in present:', "if False:"),
    (
        "the user-quirk block by devices, not by how strongly a name claims",
        "strength(offered_names, devices[i]) > installed_strength(installed_names, devices[i])",
        "strength(offered_names, devices[i]) > 0 and not (name in ours and i in ours[name][2])",
    ),
    (
        "the user-quirk block trusts an installed version that steps back on the device",
        "return 0 if misfit(names, device) is not None else strength(names, device)",
        "return strength(names, device)",
    ),
    ("a record a crash left is not settled", 'if on_disk == previous["sha256"]:\n                record', 'if False:\n                record'),
    ("the installed version's claimed_elsewhere left out of the strength", 'if [manufacturer, model] in names.get("claimed_elsewhere", []):\n        return 0', "if False:\n        return 0"),
    ("no take-over offer", "or bool(running(device_id)) or taken_over(device_id, name) or unreported))", "or bool(running(device_id)) or unreported))"),
    ("a take-over beyond the exact name", ' and [device.manufacturer, device.model] in entry["fingerprints"]', ""),
    ("no hand-back", "if users_of and name not in slugs and all((devices[i].manufacturer, devices[i].model) in taken for i in users_of):", "if False:"),
    ("a hand-back of devices on names it did not take over", "all((devices[i].manufacturer, devices[i].model) in taken for i in users_of)", "True"),
    ("a hand-back of a file the state still offers", "if users_of and name not in slugs and all(", "if users_of and all("),
    ("a hand-back while a device on another name runs it", "and all((devices[i].manufacturer, devices[i].model) in taken", "and any((devices[i].manufacturer, devices[i].model) in taken"),
    ("devices that do not fit a file need it", "and misfit_of(device_id, name) is None\n", "\n"),
    ("an unreported device runs a version it does not fit", 'if device_id in claimed and misfit(record["names"], devices[device_id]) is None}', "if device_id in claimed}"),
    ("an update serves devices that do not fit it",
     'fits = misfit_of(device_id, name) is None if name in target else misfit(ours[name][1]["names"], devices[device_id]) is None', "fits = True"),
    ("the ZHA-does-not-apply notice names devices that do not fit", "if not left_out(i) and misfit_of(i, name) is None\n                               and (kind", "if not left_out(i)\n                               and (kind"),
    ("misfit notices for devices on the user's quirk", "or left_out(device_id) or kind[device_id] == CUSTOM:", "or left_out(device_id):"),
    ("no FILE_MISFIT reason", "if misfit_of(device_id, other) is not None:\n                found.append(Lost(device_id, FILE_MISFIT", "if False:\n                found.append(Lost(device_id, FILE_MISFIT"),
    (
        "a hand-back only without an entry or with one that says ZHA covers the device (the rule before the exact coupling)",
        "if users_of and name not in slugs and all(",
        'if users_of and name not in slugs and state.manifest.get(stem(name).removeprefix(PREFIX), {}).get("status", "upstream") == "upstream" and all(',
    ),
]


def _mutant(index: int, old: str, new: str):
    source = Path(plan_module.__file__).read_text()
    assert source.count(old) == 1, old
    name = f"{plan_module.__name__}_bug{index}"
    spec = importlib.util.spec_from_loader(name, loader=None)
    module = importlib.util.module_from_spec(spec)
    module.__package__ = plan_module.__package__
    sys.modules[name] = module
    try:
        exec(compile(source.replace(old, new), f"<plan.py with bug {index}>", "exec"), module.__dict__)
    finally:
        del sys.modules[name]
    return module


def strength_scenario() -> Scenario:
    """The installed version leaves (M1, X1) to another definition (claimed_elsewhere beside its
    model-only name), the offered one does not; d1 runs the user's quirk for it, d2 needs the update.
    The random scenarios hold this rarely since claimed_elsewhere comes as manifests hold it."""
    old = Version(((None, "X1"),), (("M1", "X1"),), _sha("z2m_a.py", "old"), _sha("z2m_a.py", "old")[:8])
    new = Version(((None, "X1"),), (), _sha("z2m_a.py", "new"), _sha("z2m_a.py", "new")[:8])
    mine = Version((("M1", "X1"),), (), _sha("my_quirk.py", "mine"), "mine0000")
    return Scenario(offered={"z2m_a.py": new}, verdict={"z2m_a.py": OK}, withdrawn=frozenset(),
                    folder={"z2m_a.py": InFolder(OURS, old), "my_quirk.py": InFolder(USER, mine, False)},
                    records={f"{FOLDER}/z2m_a.py": record_of(old)}, outside={},
                    devices={"d1": Facts(("M1", "X1")), "d2": Facts(("M2", "X1"))}, order=("z2m_a.py", "my_quirk.py"))


def stepped_back_scenario() -> Scenario:
    """The installed version needs endpoint 2: d2 lacks it, so d2 runs the user's model-only quirk; the
    offered version fits d2 under the same exact name and would win there. d1 needs the update. The
    random scenarios rarely give a device on the user's quirk that the installed version does not fit."""
    old = Version((("M1", "X1"),), (), _sha("z2m_a.py", "old"), _sha("z2m_a.py", "old")[:8], endpoints=((2, ()),))
    new = Version((("M1", "X1"),), (), _sha("z2m_a.py", "new"), _sha("z2m_a.py", "new")[:8], endpoints=((1, (6,)),))
    mine = Version(((None, "X1"),), (), _sha("my_quirk.py", "mine"), "mine0000")
    return Scenario(offered={"z2m_a.py": new}, verdict={"z2m_a.py": OK}, withdrawn=frozenset(),
                    folder={"z2m_a.py": InFolder(OURS, old), "my_quirk.py": InFolder(USER, mine, False)},
                    records={f"{FOLDER}/z2m_a.py": record_of(old)}, outside={},
                    devices={"d1": Facts(("M1", "X1"), layout=((1, frozenset({6})), (2, frozenset()))),
                             "d2": Facts(("M1", "X1"), layout=((1, frozenset({6})),))},
                    order=("z2m_a.py", "my_quirk.py"))


# Scenarios the random search reaches too rarely for MUTANT_SCENARIOS; each passes with plan.py.
TARGETED = (strength_scenario, stepped_back_scenario)


def test_the_targeted_scenarios_pass():
    for make in TARGETED:
        assert check(make()) == []


def test_the_checker_catches_deliberate_plan_bugs():
    missed = []
    for index, (what, old, new) in enumerate(BUGS):
        module = _mutant(index, old, new)
        if not any(check(make(), module) for make in TARGETED) and not search(MUTANT_SCENARIOS, module, stop_at_first=True):
            missed.append(what)
    assert not missed
