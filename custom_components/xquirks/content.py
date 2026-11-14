"""The quirk files on offer: a content state of the repository (remote.py fetches it), and what
a quirk file states about itself."""

from __future__ import annotations

import dataclasses
import hashlib
import json
import re
import tomllib
from pathlib import PurePosixPath

from .guard import endpoint_map

# Every shipped file sits directly in quirks/ under a name ZHA imports as a module.
FILE_NAME = re.compile(r"z2m_[a-z0-9_]+\.py")
# The docstring line naming the file's content (effective_revision below).
REVISION_LINE = re.compile(rb"^Revision: [0-9a-f]{8}\n", re.M)
HEX8 = re.compile(r"[0-9a-f]{8}")
# The module docstring of a generated file: title, "Generated from the Zigbee2MQTT definition ...",
# optional notes, the data line, the status line and the revision.
GENERATED = re.compile(
    rb'"""[^\n]*\n\nGenerated from the Zigbee2MQTT definition[^\n]*\n'
    rb'(?:(?![^\n]*""")[^\n]*\n)*?'
    rb"Data: zigbee-herdsman-converters, MIT, Copyright \(c\) 2018 Koen Kanters\.\n"
    rb"Status: [^\n]*\.\n"
    rb"Revision: [0-9a-f]{8}\n"
    rb'"""\n'
)
HEX64 = re.compile(r"[0-9a-f]{64}")
# A git object name: SHA-1, or SHA-256 in a repository that uses it.
COMMIT = re.compile(r"[0-9a-f]{40}|[0-9a-f]{64}")

# How likely a file is to do something wrong on the device (an entry's risk), lowest first. A
# missing or unknown value counts as the highest.
RISKS = ("low", "medium", "high")
HIGH = "high"
# The reasons an entry may give for its risk (risk_why), as codes: text.py and the finder have a
# sentence for each. A code this release does not know is skipped.
RISK_REASONS = (
    "cover", "thermostat", "state_dependency", "mixed_manufacturer_code", "take_over_drops", "defect_found", "number_settings", "local_occupancy",
    "take_over", "alias_differs",
)


def sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def effective_revision(content: bytes) -> str:
    """The revision of a file's content, computed from the file without its Revision line. The
    line itself plays no part: a copy edited below an unchanged
    Revision line has another revision."""
    return sha256(REVISION_LINE.sub(b"", content, count=1))[:8]


def generated(content: bytes) -> bool:
    """The file starts with the module docstring every quirk file of this collection starts with."""
    return GENERATED.match(content) is not None


class BadContent(ValueError):
    """The manifest names a file outside quirks/ or a name twice, or its metadata is off."""


@dataclasses.dataclass(frozen=True)
class ContentState:
    """The files of one content-<n> tag of the repository, as its manifest states them."""

    manifest: dict[str, dict]
    # File name -> sha256 of its content, for every file the manifest ships.
    shas: dict[str, str]
    # File name -> its path in the repository, as the manifest names it.
    paths: dict[str, str] = dataclasses.field(default_factory=dict)
    # File name -> the revision the file states.
    revisions: dict[str, str | None] = dataclasses.field(default_factory=dict)
    # The number of the content-<n> tag; 0 for the empty state.
    content: int = 0
    # The content-<n> tag the files come from; None for the empty state.
    tag: str | None = None
    # The oldest Home Assistant release these files support (hacs.json), None when unknown.
    homeassistant: str | None = None
    # (file name, revision) -> why that revision must not be used.
    withdrawn: dict[tuple[str, str], str] = dataclasses.field(default_factory=dict)
    # The commit the tag points to: files are read there. None for the empty state.
    commit: str | None = None

    @property
    def sources(self) -> dict[str, str]:
        """The Zigbee2MQTT and zha-device-handlers versions the files come from."""
        return next(iter(self.manifest.values()), {}).get("sources", {})


# No state yet: nothing on offer.
EMPTY = ContentState({}, {})


def _text(value: object, *, optional: bool = False) -> bool:
    return isinstance(value, str) or (optional and value is None)


def _pairs(value: object) -> bool:
    """A list of [manufacturer or None, model], as the manifest writes fingerprints."""
    return isinstance(value, list) and all(isinstance(pair, list) and len(pair) == 2 and _text(pair[0], optional=True) and _text(pair[1]) for pair in value)


def _pull_requests(value: object) -> bool:
    return isinstance(value, list) and all(
        isinstance(pr, dict) and isinstance(pr.get("number"), int) and not isinstance(pr["number"], bool) and pr["number"] > 0 for pr in value
    )


def _over_zha(value: object) -> bool:
    """Absent, or what a file that takes names over from ZHA's own quirk shows that ZHA's quirk lacks
    (adds) and what only ZHA's quirk shows (zha_only): entity names."""
    return value is None or (
        isinstance(value, dict) and set(value) == {"adds", "zha_only"}
        and all(isinstance(names, list) and all(isinstance(name, str) for name in names) for names in value.values())
    )


def identities(value: object) -> bool:
    """Entities that read an attribute: [cluster, attribute id, platform, unique id after the IEEE
    address, name], as the manifest holds them."""
    return isinstance(value, list) and all(
        isinstance(row, list) and len(row) == 5 and all(isinstance(n, int) and not isinstance(n, bool) for n in row[:2])
        and all(isinstance(text, str) and text for text in row[2:])
        for row in value
    )


def _swap(value: object) -> bool:
    """Absent, or the entities of a file that takes names over (ours) and of ZHA's own quirk (zha) that
    read an attribute, on that file's entry and on the entry without a file that hands its devices back."""
    return value is None or (isinstance(value, dict) and set(value) == {"ours", "zha"} and all(identities(rows) for rows in value.values()))


def check_entry(slug: str, entry: object) -> None:
    """BadContent when a manifest entry lacks a field this integration reads, or has it in another shape.

    Every entry takes part in the matching (fingerprints); the entries that ship a file also name
    their device in the notices and dialogs."""
    if not isinstance(entry, dict):
        raise BadContent(f"manifest entry {slug} is not an object")
    checks = {
        "file": _text(entry.get("file"), optional=True),
        "fingerprints": _pairs(entry.get("fingerprints")),
        "claimed_elsewhere": _pairs(entry.get("claimed_elsewhere", [])),
        "status": _text(entry.get("status"), optional=True),
        "swap": _swap(entry.get("swap")),
    }
    if entry.get("file"):
        checks |= {
            "vendor": _text(entry.get("vendor")),
            "model": _text(entry.get("model")),
            "status": _text(entry.get("status")),
            "description": _text(entry.get("description"), optional=True),
            "picture": _text(entry.get("picture"), optional=True),
            # The sha256 of the picture's bytes: without it, no picture.
            "picture_sha256": entry.get("picture_sha256") is None or (isinstance(entry["picture_sha256"], str) and bool(HEX64.fullmatch(entry["picture_sha256"]))),
            "upstream_open_prs": _pull_requests(entry.get("upstream_open_prs", [])),
            "sources": isinstance(entry.get("sources", {}), dict),
            "over_zha": _over_zha(entry.get("over_zha")),
            # The endpoints a file's runtime check needs (its ENDPOINTS), in the shape the guard compares.
            "endpoints": entry.get("endpoints") is None or endpoint_map(entry["endpoints"], str) is not None,
        }
    if wrong := [key for key, fine in checks.items() if not fine]:
        raise BadContent(f"manifest entry {slug}: {', '.join(wrong)} missing or malformed")


def risk(entry: dict) -> str:
    """An entry's risk (RISKS): HIGH when it states none or one this release does not know."""
    value = entry.get("risk")
    return value if isinstance(value, str) and value in RISKS else HIGH


def risk_why(entry: dict) -> tuple[str, ...]:
    """The reasons for an entry's risk this release knows (RISK_REASONS), each once, in the entry's order."""
    codes = entry.get("risk_why")
    if not isinstance(codes, list):
        return ()
    return tuple(dict.fromkeys(code for code in codes if isinstance(code, str) and code in RISK_REASONS))


def verified(entry: dict) -> bool:
    """A device test checked the entry's file: it counts as checked, whatever its risk."""
    return entry.get("status") == "verified"


def high_risk(entry: dict) -> bool:
    """The entry's file is high risk and not verified on a device."""
    return not verified(entry) and risk(entry) == HIGH


def shipped_entries(manifest: dict) -> dict[str, tuple[PurePosixPath, dict]]:
    """File name -> (path in the repository, manifest entry) for every shipped file; BadContent when off."""
    found: dict[str, tuple[PurePosixPath, dict]] = {}
    for entry in manifest.values():
        if not entry.get("file"):
            continue
        path = PurePosixPath(entry["file"])
        if path.parent != PurePosixPath("quirks") or not FILE_NAME.fullmatch(path.name) or path.name in found:
            raise BadContent(f"unexpected file in the manifest: {entry['file']}")
        found[path.name] = (path, entry)
    return found


def parse_homeassistant(text: str) -> str | None:
    """The minimum Home Assistant release from hacs.json."""
    value = json.loads(text).get("homeassistant")
    if value is not None and not isinstance(value, str):
        raise BadContent(f"hacs.json: homeassistant is {value!r}")
    return value


def parse_guard(text: str) -> str | None:
    """The guard content.json names (guard.identity of the release the tag was built for); None when it names none."""
    value = json.loads(text).get("guard")
    return value if isinstance(value, str) and HEX64.fullmatch(value) else None


def _withdrawn_item(name: object, rev: object, reason: object) -> bool:
    return isinstance(name, str) and FILE_NAME.fullmatch(name) is not None and isinstance(rev, str) and HEX8.fullmatch(rev) is not None and isinstance(reason, str)


def parse_withdrawn(text: str) -> dict[tuple[str, str], str]:
    """data/withdrawn.toml: (file name, revision) -> reason. Its fields never change (guard.FORMAT)."""
    try:
        items = tomllib.loads(text).get("withdrawn", [])
    except tomllib.TOMLDecodeError as err:
        raise BadContent(f"withdrawn.toml: {err}") from err
    if not isinstance(items, list):
        raise BadContent("withdrawn.toml: withdrawn is not a list")
    withdrawn = {}
    for item in items:
        if not isinstance(item, dict) or not _withdrawn_item(item.get("file"), item.get("revision"), item.get("reason")):
            raise BadContent(f"withdrawn.toml: bad entry {item!r}")
        withdrawn[(item["file"], item["revision"])] = item["reason"]
    return withdrawn


def withdrawn_rows(withdrawn: dict[tuple[str, str], str]) -> list[list[str]]:
    """Withdrawn revisions as the store keeps them: [file name, revision, reason], sorted."""
    return sorted([name, rev, reason] for (name, rev), reason in withdrawn.items())


def from_withdrawn_rows(rows: object) -> dict[tuple[str, str], str]:
    """Withdrawn revisions kept in the store; BadContent when they are not in the shape written."""
    if not isinstance(rows, list) or not all(isinstance(row, list) and len(row) == 3 and _withdrawn_item(*row) for row in rows):
        raise BadContent("stored withdrawn revisions are malformed")
    return {(name, rev): reason for name, rev, reason in rows}


def from_manifest(
    manifest: object, *, tag: str, content: int, homeassistant: str | None, withdrawn: dict[tuple[str, str], str], commit: str | None = None
) -> ContentState:
    """A content state of the repository: hashes and revisions as its manifest states them.

    Every entry is checked for the fields this integration reads: a malformed manifest is never
    taken (or kept), so the plan, the notices and the dialogs can rely on them."""
    if not isinstance(manifest, dict):
        raise BadContent("manifest.json is not an object")
    for slug, entry in manifest.items():
        check_entry(slug, entry)
    shas, paths, revisions = {}, {}, {}
    for name, (path, entry) in shipped_entries(manifest).items():
        sha, rev = entry.get("sha256"), entry.get("revision")
        if not isinstance(sha, str) or not HEX64.fullmatch(sha) or not isinstance(rev, str) or not HEX8.fullmatch(rev):
            raise BadContent(f"manifest entry for {name} lacks its sha256 or revision")
        shas[name], paths[name], revisions[name] = sha, str(path), rev
    return ContentState(manifest, shas, paths, revisions, content, tag, homeassistant, withdrawn, commit)
