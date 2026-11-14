"""The target state of the custom quirks folder and the one change list that reaches it. No Home
Assistant imports, no I/O.

The inputs are plain data: the content state in use, the revisions withdrawn, the guard's verdicts,
the ZHA devices from the device registry with what ZHA applied to them, the records of the files this
integration wrote and what is in the folder now. Nothing here writes anything.

Ours is a file in the folder whose record has the sha256 it has on disk; every other file there is
the user's and is never written or deleted. A record holds the names (fingerprints) of the version
written, so the plan knows which devices each file of ours claims, older versions too.

- A device needs the shipped file F when F's offered version claims it, no other shipped file does,
  the device is not left out (disabled, or excluded in the options), it fits F and it runs no quirk
  or a file of ours, or ZHA's own quirk while F takes its exact name over (the manifest's over_zha:
  ZHA's quirk shows fewer features than F). A device ZHA does not report counts as running every
  file of ours that claims it.
- A device fits F when it has every endpoint of F's manifest entry (endpoints) and each cluster F
  puts on one of them lands there as Zigbee2MQTT picks the endpoint: the first one that announces
  the cluster, the device's first endpoint when none does (misfit(); F's runtime check applies the
  same rule and steps back on a device that does not fit). A device whose layout ZHA does not report
  fits. A device F claims that does not fit F gets a notice with a report link instead.
- The target holds F when all of these hold: a device needs it; its name in the folder is free or
  ours; its revision is not withdrawn; the guard passed it (when it is written); no other shipped file
  claims a device it claims; its write claims no device on a custom quirk that is not ours more
  strongly than the installed version did (ZHA tries an exact name before a model-only one; an
  installed version whose runtime check steps back on the device does not claim it at all); it is not
  held back.
- F is held back while the options do not offer high-risk files, its entry is high risk and not
  verified on a device (content.high_risk) and no file of ours has its name (in the folder ZHA loads
  or in one it loaded before): it is neither downloaded nor installed, a notice names the devices that
  need it. A file of ours is never held back: the devices that run it get its updates whatever its
  risk. A held-back file counts as one that cannot come: it takes no device from a file of ours that
  stays, and the notices that say the change list brings it once something is out of the way leave
  it out.
- A file of ours in the target is updated to the offered version. One not in the target stays as it
  is while three hold: its revision is not withdrawn; a device not left out runs it; no file of the
  target claims a device it claims. Else it is removed. A file of the target not in the folder is
  installed. A device that does not fit the offered version keeps the version it runs that way
  (written before the runtime check, it may do part of its job); an update for other devices takes
  it away (the change names it).
- A file of ours that the state no longer ships, whatever the reason, is removed too when every
  device not left out that runs it has an exact name its version took over from ZHA's own quirk (its
  record's names "takes_over"): ZHA's quirk takes them back. That quirk is there: a content state
  needs the exact Home Assistant release it was built for or newer. So the user's release is at least
  the one the take-over version was built for, whose ZHA shipped the quirk the take-over was
  measured against (unless Home Assistant went back to an older release since, or a newer zha-quirks dropped
  that quirk). A device on another name keeps the file.
- Before a take-over and before a hand-back the change names the entities that get another ID in Home
  Assistant: the manifest's swap lists what the file and ZHA's quirk show, a record keeps the list of
  the version written (swapped()). A removal for another reason (withdrawn, or moved to a file the
  device does not fit) names such a device among those that get no file of ours, with ZHA's quirk
  taking it back and its new IDs.

All changes go out as one list: confirmed as a whole or not at all (manager.async_apply).
"""

from __future__ import annotations

import dataclasses
import hashlib
import os
from collections.abc import Container, Mapping
from pathlib import PurePath

from .content import ContentState, high_risk, identities
from .files import UNREADABLE
from .guard import endpoint_map
from .matching import matches

PREFIX = "z2m_"

# What ZHA runs on a device, from the module of the quirk it applied.
UNKNOWN = "unknown"  # ZHA does not say, or names a file of this collection that is gone from the folder
NONE = "none"  # no quirk
ZHA_QUIRK = "shipped"  # a quirk ZHA ships
OURS = "ours"  # a file of ours in the folder
CUSTOM = "custom"  # a custom quirk that is not ours

# Why a file of ours goes (the first that holds).
WITHDRAWN = "withdrawn"  # its installed revision is withdrawn
MOVED = "moved"  # a file of the target claims a device it claims
SHIPPED = "shipped"  # ZHA applies a quirk it ships to every device it claims
HANDED_BACK = "handed_back"  # the state no longer ships it; it runs only on devices it took over from ZHA's quirk
LEFT_OUT = "left_out"  # the devices that ran it are all left out
UNUSED = "unused"  # no device runs it
OUTSIDE = "outside"  # it is in a folder ZHA no longer loads

# Why a device that ran a file of ours gets none after the change.
NO_FILE = "no_file"  # no shipped file claims it
TWO_FILES = "two_files"  # two shipped files claim it
FILE_WITHDRAWN = "file_withdrawn"  # the revision of its file is withdrawn
FILE_REFUSED = "file_refused"  # the guard refused its file, or it cannot be downloaded
FILE_CONFLICT = "file_conflict"  # its file shares a device with another shipped file
USERS_NAME = "users_name"  # a file of the user has the name of its file
USERS_QUIRK = "users_quirk"  # its file would claim a device that runs the user's quirk
FILE_MISFIT = "file_misfit"  # it does not fit the endpoints of its file's offered version
FILE_NO_TAKE_OVER = "file_no_take_over"  # its file does not take its exact name over from ZHA's own quirk, which ZHA ships for it
FILE_HELD_BACK = "file_held_back"  # its file is held back: high risk, not verified on a device

# Why there is no change list now.
PENDING = "pending"  # a change of ours waits for ZHA to load the folder
UNCHECKED = "unchecked"  # a file the list would write is not checked by the guard yet
# The manager's holds (manager._async_refresh), set around make_plan.
ZHA_UNKNOWN = "zha_unknown"  # what ZHA applies cannot be read (ZHA is not loaded, or its internals changed)
NO_CONTENT = "no_content"  # no content state in use
NO_FOLDER = "no_folder"  # ZHA has no custom quirks folder
UNREADABLE_FOLDER = "unreadable_folder"  # the custom quirks folder cannot be read


@dataclasses.dataclass(frozen=True)
class Device:
    manufacturer: str
    model: str
    name: str
    # Module of the quirk ZHA applied ("" for none), None while ZHA does not say.
    quirk: str | None = None
    # Disabled in Home Assistant: left out like a device excluded in the options.
    disabled: bool = False
    # (endpoint id, the input clusters it announces) of the device as it joined, before any quirk
    # (zigpy's original signature); None while ZHA does not say.
    layout: tuple[tuple[int, frozenset[int]], ...] | None = None

    @property
    def on_shipped_quirk(self) -> bool:
        return self.quirk is not None and self.quirk.startswith("zhaquirks.")


def stem(name: str) -> str:
    return name.removesuffix(".py")


@dataclasses.dataclass(frozen=True)
class Lost:
    """A device that runs a file of ours now and none after the change, with the reason."""

    device: str
    reason: str  # NO_FILE, TWO_FILES, FILE_WITHDRAWN, FILE_REFUSED, FILE_CONFLICT, USERS_NAME, USERS_QUIRK, FILE_MISFIT, FILE_NO_TAKE_OVER or FILE_HELD_BACK
    file: str = ""  # the file that would be for it
    others: tuple[str, ...] = ()  # USERS_QUIRK: the devices on the user's quirk
    # The installed version took the device's exact name over from ZHA's own quirk: ZHA's quirk takes
    # it back (back), these entities get another ID in Home Assistant (new_ids).
    back: bool = False
    new_ids: tuple[str, ...] = ()


@dataclasses.dataclass(frozen=True)
class Install:
    name: str
    sha256: str
    devices: tuple[str, ...]  # the devices that need it
    left_out: tuple[str, ...] = ()  # left-out devices it claims too (ZHA applies it to them as well)
    took_over: tuple[str, ...] = ()  # the devices among them that run ZHA's own quirk, which it takes over
    new_ids: tuple[str, ...] = ()  # took_over: the entities of ZHA's quirk that get another ID in Home Assistant


@dataclasses.dataclass(frozen=True)
class Update:
    path: str
    sha256: str  # the offered version
    before: str  # the sha256 in the folder
    revision: str  # the installed revision
    withdrawn: bool  # the installed revision is withdrawn
    devices: tuple[str, ...]  # the devices that need it
    moves: tuple[tuple[str, str], ...] = ()  # (device, file of the target) for devices that move
    lost: tuple[Lost, ...] = ()
    left_out: tuple[str, ...] = ()
    took_over: tuple[str, ...] = ()  # the devices among them that run ZHA's own quirk, which it takes over
    new_ids: tuple[str, ...] = ()  # took_over: the entities of ZHA's quirk that get another ID in Home Assistant

    @property
    def name(self) -> str:
        return PurePath(self.path).name


@dataclasses.dataclass(frozen=True)
class Removal:
    path: str
    before: str  # the sha256 in the folder
    revision: str  # the installed revision
    withdrawn: bool  # the installed revision is withdrawn
    reason: str  # WITHDRAWN, MOVED, HANDED_BACK, SHIPPED, LEFT_OUT, UNUSED or OUTSIDE
    moves: tuple[tuple[str, str], ...] = ()
    lost: tuple[Lost, ...] = ()
    # HANDED_BACK: the entities of the installed version that get another ID in Home Assistant on ZHA's quirk.
    new_ids: tuple[str, ...] = ()

    @property
    def name(self) -> str:
        return PurePath(self.path).name


@dataclasses.dataclass(frozen=True)
class Blocked:
    """A shipped file whose write would claim devices that run a custom quirk that is not ours."""

    name: str
    devices: tuple[str, ...]


@dataclasses.dataclass(frozen=True)
class HeldBack:
    """A shipped file that devices need, held back: high risk, not verified on a device, high-risk
    files not offered in the options."""

    name: str
    devices: tuple[str, ...]


@dataclasses.dataclass(frozen=True)
class NotApplied:
    """A file of ours at the offered version that ZHA does not apply to devices it claims."""

    path: str
    devices: tuple[str, ...]

    @property
    def name(self) -> str:
        return PurePath(self.path).name


@dataclasses.dataclass(frozen=True)
class Misfit:
    """A device a shipped file claims that does not fit the file's endpoints: why, per device."""

    name: str
    devices: tuple[tuple[str, str], ...]  # (device id, why it does not fit)


@dataclasses.dataclass
class Plan:
    # Why there is no change list now (PENDING, UNCHECKED, the manager's holds), None when there is one (maybe empty).
    held: str | None = None
    # Files the list would write that the guard has not checked yet; those it refused.
    unchecked: list[str] = dataclasses.field(default_factory=list)
    refused: list[str] = dataclasses.field(default_factory=list)
    target: frozenset[str] = frozenset()
    # Names of the files of ours in the folder.
    ours: frozenset[str] = frozenset()
    remove: list[Removal] = dataclasses.field(default_factory=list)
    update: list[Update] = dataclasses.field(default_factory=list)
    install: list[Install] = dataclasses.field(default_factory=list)
    # Notices: no change, nothing to confirm.
    blocked: list[Blocked] = dataclasses.field(default_factory=list)
    held_back: list[HeldBack] = dataclasses.field(default_factory=list)
    # Shipped names for devices not left out whose file in the folder is the user's (no record).
    users_files: list[str] = dataclasses.field(default_factory=list)
    # Files of ours at a withdrawn revision: noticed also while the list is held or put aside.
    withdrawn_installed: list[tuple[str, str]] = dataclasses.field(default_factory=list)
    # Files of ours the user changed since: left alone.
    changed: list[str] = dataclasses.field(default_factory=list)
    # Files of the user whose revision is withdrawn: name -> revision.
    withdrawn_copies: dict[str, str] = dataclasses.field(default_factory=dict)
    not_applied: list[NotApplied] = dataclasses.field(default_factory=list)
    # Shipped files with devices that do not fit their endpoints: noticed with a report link.
    misfits: list[Misfit] = dataclasses.field(default_factory=list)
    # Records whose file is missing (the user deleted it): their records go.
    gone: list[str] = dataclasses.field(default_factory=list)
    # Records whose file cannot be read: left alone, records kept.
    unreadable: list[str] = dataclasses.field(default_factory=list)
    # Records an apply left with the version before (a crash): path -> the record that holds.
    settled: dict[str, dict] = dataclasses.field(default_factory=dict)

    @property
    def changes(self) -> int:
        return len(self.remove) + len(self.update) + len(self.install)

    @property
    def key(self) -> str:
        """The change list's id: the same list has the same key, another list another one. A revision
        withdrawn since makes another list: "Not now" on the list before does not hide it."""
        rows = sorted(
            [f"remove {c.path} {c.before} - {c.withdrawn}" for c in self.remove]
            + [f"update {c.path} {c.before} {c.sha256} {c.withdrawn}" for c in self.update]
            + [f"install {c.name} - {c.sha256}" for c in self.install]
        )
        return hashlib.sha256("\n".join(rows).encode()).hexdigest()[:12]

    @property
    def severe(self) -> bool:
        """The list takes an installed revision that is withdrawn out of the folder."""
        return any(c.withdrawn for c in (*self.remove, *self.update))


def shipped_files(manifest: dict) -> dict[str, str]:
    """File name -> manifest slug, for every file the manifest ships."""
    return {PurePath(entry["file"]).name: slug for slug, entry in manifest.items() if entry.get("file")}


def matching_devices(manifest: dict, devices: dict[str, Device]) -> dict[str, set[str]]:
    """File name -> ids of the devices its fingerprints match (the rules of matching.py)."""
    found: dict[str, set[str]] = {}
    pairs = {(d.manufacturer, d.model) for d in devices.values()}
    for pair, _slug, entry in matches(manifest, pairs):
        if entry.get("file"):
            ids = {i for i, d in devices.items() if (d.manufacturer, d.model) == pair}
            found.setdefault(PurePath(entry["file"]).name, set()).update(ids)
    return found


def takes_over(entry: dict, device: Device) -> bool:
    """The entry's file takes the device over from ZHA's own quirk: the entry says ZHA's quirk shows
    less (over_zha) and lists the device's exact name."""
    return entry.get("over_zha") is not None and [device.manufacturer, device.model] in entry["fingerprints"]


def misfit(entry: dict, device: Device) -> str | None:
    """Why the device does not fit the entry's file, None when it fits: the rule of the file's runtime
    check (_misfit in fixed_code.json). Every endpoint of the entry's endpoints must be on the device;
    each cluster the file puts on one must land there as Zigbee2MQTT picks the endpoint: the first
    endpoint that announces the cluster, the device's first endpoint when none does. Without
    endpoints in the entry or a layout of the device: it fits."""
    endpoints = endpoint_map(entry.get("endpoints"), str) if entry.get("endpoints") is not None else None
    if not endpoints or device.layout is None:
        return None
    announced = {ep_id: clusters for ep_id, clusters in sorted(dict(device.layout).items()) if ep_id}
    for ep_id, cluster_ids in sorted(endpoints.items()):
        if ep_id not in announced:
            return f"it has no endpoint {ep_id}"
        for cluster_id in sorted(cluster_ids):
            first = next((other for other, clusters in announced.items() if cluster_id in clusters), None)
            if first is None and min(announced) != ep_id:
                return f"no endpoint has cluster 0x{cluster_id:04X} and the first endpoint is {min(announced)}, not {ep_id}"
            if first is not None and first != ep_id:
                return f"the first endpoint with cluster 0x{cluster_id:04X} is {first}, not {ep_id}"
    return None


def names_of(entry: dict) -> dict[str, list]:
    """The names a record keeps of the version written: those of its manifest entry. A version that
    takes names over from ZHA's own quirk (over_zha) keeps those exact names too ("takes_over"): once
    the state drops the file, devices with them go back to ZHA's quirk, also those paired since. A
    version with a runtime check keeps its endpoints: a device it does not fit never runs it."""
    names = {"fingerprints": [list(fp) for fp in entry["fingerprints"]], "claimed_elsewhere": [list(fp) for fp in entry.get("claimed_elsewhere", [])]}
    if entry.get("endpoints") is not None:
        names["endpoints"] = {ep: list(ids) for ep, ids in entry["endpoints"].items()}
    if entry.get("over_zha") is not None:
        names["takes_over"] = [list(fp) for fp in entry["fingerprints"] if fp[0] is not None]
        # Its entities as identities: a hand-back compares the version written, not the one on offer.
        if entry.get("swap") is not None:
            names["swap"] = [list(row) for row in entry["swap"]["ours"]]
    return names


def swapped(ours: list, zha: list, side: str) -> tuple[str, ...]:
    """The entities that do not keep their ID in Home Assistant when ZHA's own quirk and a file swap:
    for each attribute both read, the entities of one side ("zha" before a take-over, "ours" before a
    hand-back: what the user has then) with no entity of the other side of the same platform and
    unique id. Rows as content.check_entry takes them: [cluster, attribute id, platform, unique id, name]."""
    keys = {"ours": {}, "zha": {}}
    for which, rows in (("ours", ours), ("zha", zha)):
        for cluster, attribute, platform, uid, _name in rows:
            keys[which].setdefault((cluster, attribute), set()).add((platform, uid))
    other = "zha" if side == "ours" else "ours"
    found = []
    for cluster, attribute, platform, uid, name in ours if side == "ours" else zha:
        mine = keys[other].get((cluster, attribute))
        if mine is not None and (platform, uid) not in mine and name not in found:
            found.append(name)
    return tuple(found)


def claimed_by(names: dict, devices: dict[str, Device]) -> set[str]:
    """Ids of the devices that a file with these names claims."""
    return matching_devices({"file": {"file": "file", **names}}, devices).get("file", set())


def strength(names: dict, device: Device) -> int:
    """How a file with these names claims the device: 2 by an exact name, 1 by a model-only one, 0
    not at all. ZHA tries the quirks of the exact name before those of the model-only one."""
    manufacturer, model = device.manufacturer, device.model
    if [manufacturer, model] in names.get("claimed_elsewhere", []):
        return 0
    return max((2 if m == manufacturer else 1 for m, x in names["fingerprints"] if x == model and m in (None, manufacturer)), default=0)


def make_plan(
    state: ContentState,
    devices: dict[str, Device],
    records: dict[str, dict],
    disk: dict[str, str | None],
    folder: str,
    present: dict[str, str | None],
    *,
    pending: bool = False,
    generated: Mapping[str, str] | None = None,
    withdrawn: Container[tuple[str, str]] = frozenset(),
    verdicts: Mapping[str, tuple[str, ...] | None] | None = None,
    excluded: Container[str] = frozenset(),
    offer_high_risk: bool = False,
) -> Plan:
    """
    devices: device id -> Device, the ZHA devices of the device registry
    records: path -> {"sha256", "revision", "names": {"fingerprints", "claimed_elsewhere"[, "takes_over"]}}: what was written
    disk: path -> sha256 of the file on disk now, None when it is missing, UNREADABLE (every record)
    folder: the folder ZHA loads custom quirks from
    present: name -> sha256 of the files in folder (None where it was not read)
    pending: a change of ours waits for ZHA to load the folder
    generated: name -> revision of the files in folder whose content starts with the docstring of this collection's files
    withdrawn: (file name, revision) of the revisions the state in use or a newer tag withdraws
    verdicts: name -> the guard's reasons to refuse the offered file (empty: passed), missing or None
        while it is not checked
    excluded: ids of the devices the options leave out
    offer_high_risk: the options offer high-risk files that are not verified (none held back)
    """
    plan = Plan()
    generated = generated or {}
    verdicts = verdicts or {}

    ours: dict[str, tuple[str, dict, set[str]]] = {}
    outside: list[tuple[str, dict]] = []
    for path, record in sorted(records.items()):
        on_disk = disk.get(path)
        if (previous := record.get("previous")) is not None:
            # An apply saves the record before it writes the file, with the version before as
            # previous: after a crash in between, the folder holds one of the two.
            if on_disk == previous["sha256"]:
                record = plan.settled[path] = previous
            elif on_disk == record["sha256"]:
                record = plan.settled[path] = {key: value for key, value in record.items() if key != "previous"}
        if on_disk is None:
            plan.gone.append(path)
        elif on_disk == UNREADABLE:
            plan.unreadable.append(path)
        elif on_disk != record["sha256"]:
            plan.changed.append(path)
        elif os.path.dirname(path) != folder:
            # ZHA loads another folder now: this file does nothing there.
            outside.append((path, record))
        else:
            ours[PurePath(path).name] = (path, record, claimed_by(record["names"], devices))
    plan.ours = frozenset(ours)
    for name, (path, record, _claimed) in sorted(ours.items()):
        if (name, record["revision"]) in withdrawn:
            plan.withdrawn_installed.append((path, record["revision"]))
    if pending:
        # ZHA's reports are older than the folder: no list until it loaded the folder again.
        plan.held = PENDING
        return plan
    users = {name for name in present if name not in ours}
    recorded = {PurePath(path).name for path in records}

    for name in sorted(users):
        copy = state.revisions.get(name) if present[name] is not None and present[name] == state.shas.get(name) else generated.get(name)
        if copy is not None and (name, copy) in withdrawn:
            plan.withdrawn_copies[name] = copy

    ours_stems = {stem(name): name for name in ours}

    def reported(device: Device) -> str:
        quirk = device.quirk
        if quirk is None:
            return UNKNOWN
        if quirk == "":
            return NONE
        if device.on_shipped_quirk:
            return ZHA_QUIRK
        if quirk in ours_stems:
            return OURS
        if quirk.startswith(PREFIX) and f"{quirk}.py" not in present:
            # Named like a file of this collection that is gone from the folder: ZHA has not loaded
            # the folder since, so what it runs now is not known.
            return UNKNOWN
        return CUSTOM

    kind = {i: reported(d) for i, d in devices.items()}

    def running(device_id: str) -> set[str]:
        """The files of ours the device runs; a device ZHA does not report runs each one claiming it
        whose written version it fits (the record's endpoints: its runtime check steps back otherwise)."""
        if kind[device_id] == OURS:
            return {ours_stems[devices[device_id].quirk]}
        if kind[device_id] == UNKNOWN:
            return {name for name, (_path, record, claimed) in ours.items() if device_id in claimed and misfit(record["names"], devices[device_id]) is None}
        return set()

    def left_out(device_id: str) -> bool:
        return devices[device_id].disabled or device_id in excluded

    offered = matching_devices(state.manifest, devices)
    owners: dict[str, set[str]] = {}
    for name, ids in offered.items():
        for device_id in ids:
            owners.setdefault(device_id, set()).add(name)
    # A safety net: no content state ships two files for one device name.
    conflicted = {name for names in owners.values() if len(names) > 1 for name in names}

    slugs = shipped_files(state.manifest)

    def taken_over(device_id: str, name: str) -> bool:
        """The device runs ZHA's own quirk, which the offered version of the file takes over."""
        return kind[device_id] == ZHA_QUIRK and takes_over(state.manifest[slugs[name]], devices[device_id])

    def misfit_of(device_id: str, name: str) -> str | None:
        """Why the device does not fit the offered version of the file, None when it fits, when the
        offered version does not claim it (it would not run that version) or when the state ships no
        file of that name."""
        if name not in slugs or device_id not in offered.get(name, ()):
            return None
        return misfit(state.manifest[slugs[name]], devices[device_id])

    def taken_back(name: str, device_id: str) -> bool:
        """The installed version of the file took the device's exact name over from ZHA's own quirk (its
        record's takes_over): without a file of ours ZHA's quirk takes the device back."""
        device = devices[device_id]
        return name in ours and [device.manufacturer, device.model] in ours[name][1]["names"].get("takes_over", [])

    def steps_back(device_id: str, names: dict) -> bool:
        """A version with these names steps back for ZHA's own quirk on the device: ZHA ships one for the
        device's exact name, as far as the plan can tell (the device runs it, or a file of ours whose
        version took the name over: ZHA shipped it then), and the version does not take that name over.
        For the change list only (who moves, who gets no file): a file is still written for such a device,
        a quirk ZHA dropped since would leave it without one otherwise."""
        device = devices[device_id]
        ships = kind[device_id] == ZHA_QUIRK or any(taken_back(n, device_id) for n in running(device_id))
        return ships and [device.manufacturer, device.model] not in names.get("takes_over", [])

    def names_on_offer(name: str) -> dict:
        return names_of(state.manifest[slugs[name]])

    def needs(device_id: str, name: str) -> bool:
        # A device ZHA does not report needs the file while a file of ours claims it, also one whose
        # written version it does not fit (it runs none of ours then, the offered version may fit).
        unreported = kind[device_id] == UNKNOWN and any(device_id in claimed for _path, _record, claimed in ours.values())
        return (owners.get(device_id) == {name} and not left_out(device_id) and misfit_of(device_id, name) is None
                and (kind[device_id] == NONE or bool(running(device_id)) or taken_over(device_id, name) or unreported))

    # A device a shipped file claims that does not fit it: a notice with a report link, so the next
    # content can fit it. Not for a device on a custom quirk that is not ours, nor for one on ZHA's own
    # quirk that the file does not take over: the file would not apply to either.
    for name, ids in sorted(offered.items()):
        unfit = []
        for device_id in sorted(ids):
            if owners.get(device_id) != {name} or left_out(device_id) or kind[device_id] == CUSTOM:
                continue
            if kind[device_id] == ZHA_QUIRK and not taken_over(device_id, name):
                continue
            if (why := misfit_of(device_id, name)) is not None:
                unfit.append((device_id, why))
        if unfit:
            plan.misfits.append(Misfit(name, tuple(unfit)))

    def withdrawn_offer(name: str) -> bool:
        return (name, state.revisions[name]) in withdrawn

    # The names of the files of ours, also those in a folder ZHA loaded before: never held back.
    names_of_ours = set(ours) | {PurePath(path).name for path, _record in outside}

    def held(name: str) -> bool:
        """The shipped file is held back: high risk, not verified, not offered in the options, not ours."""
        return not offer_high_risk and name not in names_of_ours and high_risk(state.manifest[slugs[name]])

    needing = {name: tuple(sorted(i for i in ids if needs(i, name))) for name, ids in offered.items()}

    def installed_strength(names: dict, device: Device) -> int:
        """How strongly the installed version claims the device: none where its runtime check steps back."""
        return 0 if misfit(names, device) is not None else strength(names, device)
    custom: dict[str, tuple[str, ...]] = {}
    target: set[str] = set()
    for name, ids in sorted(offered.items()):
        offered_names = names_of(state.manifest[slugs[name]])
        installed_names = ours[name][1]["names"] if name in ours else {"fingerprints": []}
        # Devices on a custom quirk that is not ours (left-out ones too) that the write would claim more
        # strongly than the installed version: ZHA might then apply ours instead of theirs.
        # Not a device the file does not fit: its runtime check steps back there, ZHA keeps the custom quirk.
        # An installed version that does not fit the device claims it with no strength: its runtime check
        # steps back there, the custom quirk wins only so.
        custom[name] = tuple(sorted(i for i in ids if kind[i] == CUSTOM and misfit_of(i, name) is None
                                    and strength(offered_names, devices[i]) > installed_strength(installed_names, devices[i])))
        # The notices below say the change list brings the file once the user's file or quirk is gone:
        # not for a file that could not come anyway (withdrawn, held back, refused, two files for one device).
        could_come = not withdrawn_offer(name) and name not in conflicted and not held(name) and not verdicts.get(name)
        if name in users:
            if name not in recorded and could_come and any(not left_out(i) and misfit_of(i, name) is None for i in ids):
                plan.users_files.append(name)
            continue
        if custom[name] and could_come:
            plan.blocked.append(Blocked(name, custom[name]))
        if not needing[name]:
            continue
        if name in conflicted or withdrawn_offer(name) or custom[name]:
            continue
        if held(name):
            # Before the guard: a held-back file is not downloaded either.
            plan.held_back.append(HeldBack(name, needing[name]))
            continue
        if name not in ours or ours[name][1]["sha256"] != state.shas[name]:
            verdict = verdicts.get(name)
            if verdict is None:
                plan.unchecked.append(name)
                continue
            if verdict:
                plan.refused.append(name)
                continue
        target.add(name)
    if plan.unchecked:
        plan.held = UNCHECKED
        return plan
    plan.target = frozenset(target)

    claimed_by_target = {i: name for name in target for i in offered[name]}

    staying: dict[str, set[str]] = {}
    handed_back: dict[str, set[str]] = {}
    for name, (path, record, claimed) in sorted(ours.items()):
        if name in target:
            continue
        users_of = {i for i in claimed if not left_out(i) and name in running(i)}
        taken = {tuple(pair) for pair in record["names"].get("takes_over", ())}
        if users_of and name not in slugs and all((devices[i].manufacturer, devices[i].model) in taken for i in users_of):
            # The state ships no file under this name, whatever the reason. Every device that runs it has a
            # name its version took over from ZHA's own quirk: ZHA's quirk takes them back.
            handed_back[name] = users_of
        elif (name, record["revision"]) not in withdrawn and users_of and not claimed & set(claimed_by_target):
            staying[name] = claimed
    # Device -> the files of ours that claim it after the change.
    after: dict[str, set[str]] = {}
    for name, claimed in [*((n, offered[n]) for n in target), *staying.items()]:
        for device_id in claimed:
            # A device that does not fit the version a change writes, or the version that stays (its
            # record's endpoints): its runtime check steps back, the device gets none from it. So does a
            # version that steps back for ZHA's own quirk on it.
            fits = misfit_of(device_id, name) is None if name in target else misfit(ours[name][1]["names"], devices[device_id]) is None
            if fits and not steps_back(device_id, names_on_offer(name) if name in target else ours[name][1]["names"]):
                after.setdefault(device_id, set()).add(name)

    def lost(name: str, claimed: set[str], handing_back: bool = False) -> tuple[Lost, ...]:
        """The devices that run this file now and no file of ours after the change. A removal that hands
        its devices back to ZHA's own quirk (handing_back) names their new IDs itself."""
        found = []
        for device_id in sorted(claimed):
            if left_out(device_id) or name not in running(device_id) or after.get(device_id) or (handing_back and device_id in handed_back.get(name, ())):
                continue
            files = owners.get(device_id, set())
            # A name the installed version took over: ZHA's own quirk takes the device back, unless a
            # file of the user with the name of its file is there for it (USERS_NAME).
            back = {"back": True, "new_ids": back_to_zha(name, device_id)} if taken_back(name, device_id) else {}
            if not files:
                found.append(Lost(device_id, NO_FILE, **back))
                continue
            if len(files) > 1:
                found.append(Lost(device_id, TWO_FILES, **back))
                continue
            (other,) = files
            if misfit_of(device_id, other) is not None:
                found.append(Lost(device_id, FILE_MISFIT, other, **back))
            elif other in target and steps_back(device_id, names_on_offer(other)):
                found.append(Lost(device_id, FILE_NO_TAKE_OVER, other, **back))
            elif other in users:
                found.append(Lost(device_id, USERS_NAME, other))
            elif withdrawn_offer(other):
                found.append(Lost(device_id, FILE_WITHDRAWN, other, **back))
            elif other in conflicted:
                found.append(Lost(device_id, FILE_CONFLICT, other, **back))
            elif custom[other]:
                found.append(Lost(device_id, USERS_QUIRK, other, custom[other], **back))
            elif held(other):
                found.append(Lost(device_id, FILE_HELD_BACK, other, **back))
            else:
                found.append(Lost(device_id, FILE_REFUSED, other, **back))
        return tuple(found)

    def entry_swap(name: str) -> dict | None:
        """The swap of the file's entry in the state: the shipped one, or the entry without a file that a
        dropped file leaves (its slug from the file name)."""
        entry = state.manifest.get(slugs[name]) if name in slugs else state.manifest.get(stem(name).removeprefix(PREFIX))
        if not entry or (name not in slugs and entry.get("file")):
            return None
        return entry.get("swap")

    def back_to_zha(name: str, device_id: str) -> tuple[str, ...]:
        """For a device whose exact name the installed version of the file took over from ZHA's own quirk
        and that gets no file of ours after the change: ZHA's quirk takes it back, these entities get
        another ID (the record's identities against the state's swap of ZHA's quirk)."""
        if not taken_back(name, device_id):
            return ()
        swap = entry_swap(name)
        installed = ours[name][1]["names"].get("swap")
        return swapped(installed if identities(installed) else swap["ours"], swap["zha"], "ours") if swap else ()

    def left_alone(name: str) -> tuple[str, ...]:
        """The left-out devices the offered version claims, fits and does not step back on: ZHA applies it
        to them as well. Not one on a custom quirk that is not ours: that quirk keeps winning there (the
        write claims it no more strongly than before, or it would not be written)."""
        return tuple(sorted(i for i in offered[name] if left_out(i) and kind[i] != CUSTOM and misfit_of(i, name) is None
                            and not steps_back(i, names_on_offer(name))))

    def new_ids(name: str) -> tuple[str, ...]:
        """Before a take-over: ZHA's entities that do not keep their ID."""
        swap = state.manifest[slugs[name]].get("swap")
        return swapped(swap["ours"], swap["zha"], "zha") if swap and took_over(name) else ()

    def took_over(name: str) -> tuple[str, ...]:
        """The devices that need the file and run ZHA's own quirk, which it takes over."""
        return tuple(i for i in needing[name] if taken_over(i, name))

    def moves(name: str, claimed: set[str]) -> tuple[tuple[str, str], ...]:
        # Not to a file the device does not fit, nor to one that steps back for ZHA's own quirk on it: it
        # is lost then (FILE_MISFIT, FILE_NO_TAKE_OVER).
        return tuple(sorted((i, claimed_by_target[i]) for i in claimed
                            if claimed_by_target.get(i, name) != name and name in running(i) and misfit_of(i, claimed_by_target[i]) is None
                            and not steps_back(i, names_on_offer(claimed_by_target[i]))))

    for path, record in outside:
        plan.remove.append(Removal(path, record["sha256"], record["revision"], (PurePath(path).name, record["revision"]) in withdrawn, OUTSIDE))
    for name, (path, record, claimed) in sorted(ours.items()):
        if name in staying:
            continue
        is_withdrawn = (name, record["revision"]) in withdrawn
        if name in target:
            if record["sha256"] != state.shas[name]:
                plan.update.append(
                    Update(path, state.shas[name], record["sha256"], record["revision"], is_withdrawn, needing[name], moves(name, claimed), lost(name, claimed), left_alone(name),
                           took_over(name), new_ids(name))
                )
            continue
        not_left_out = {i for i in claimed if not left_out(i)}
        if is_withdrawn:
            reason = WITHDRAWN
        elif claimed & set(claimed_by_target):
            reason = MOVED
        elif name in handed_back:
            reason = HANDED_BACK
        elif not_left_out and all(kind[i] == ZHA_QUIRK for i in not_left_out):
            reason = SHIPPED
        elif any(name in running(i) for i in claimed - not_left_out):
            reason = LEFT_OUT
        else:
            reason = UNUSED
        # Before a hand-back: the entities of the installed version (its record; one written before the
        # record kept them: the state's) that do not keep their ID on ZHA's quirk (the state's entry
        # without a file). A device handed back under another reason (a target it does not fit, a
        # withdrawn revision) is named among the lost devices with its own.
        swap = entry_swap(name) if reason == HANDED_BACK else None
        installed = record["names"].get("swap")
        ids = swapped(installed if identities(installed) else swap["ours"], swap["zha"], "ours") if swap else ()
        plan.remove.append(Removal(path, record["sha256"], record["revision"], is_withdrawn, reason, moves(name, claimed),
                                   lost(name, claimed, handing_back=reason == HANDED_BACK), ids))
    for name in sorted(target - set(ours)):
        plan.install.append(Install(name, state.shas[name], needing[name], left_alone(name), took_over(name), new_ids(name)))

    for name, (path, record, claimed) in sorted(ours.items()):
        if record["sha256"] == state.shas.get(name) and (name in target or name in staying):
            # A device it takes over that still runs ZHA's own quirk counts too.
            # A device that does not fit the file has a notice of its own (misfits).
            off = tuple(sorted(i for i in claimed if not left_out(i) and misfit_of(i, name) is None
                               and (kind[i] in (NONE, CUSTOM) or (name in target and taken_over(i, name)))))
            if off:
                plan.not_applied.append(NotApplied(path, off))
    return plan
