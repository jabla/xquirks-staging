"""The installer at runtime: reads ZHA's devices, keeps the change list and the repair issues current
and writes files only when the user confirms the change list.

The files on offer come from the newest content-<n> state of the repository that this release
and this Home Assistant release can use (checked every few hours, kept across restarts). A file is
downloaded when the change list would write it: the guard (guard.py) checks its code before the
list and again before any write into the custom quirks folder. Without such a state nothing is
offered.

Once ZHA loaded a file the list installed or updated, each Tuya device that runs it gets one data
query: such a device sends its values by itself only when it joins, so its settings would stay
unknown until a value changes."""

from __future__ import annotations

import asyncio
import dataclasses
import errno
import functools
import hashlib
import importlib.util
import logging
import os
import time
import uuid
from collections.abc import Iterator, Mapping
from datetime import datetime
from pathlib import Path
from typing import Any

from awesomeversion import AwesomeVersion
from homeassistant.config_entries import SIGNAL_CONFIG_ENTRY_CHANGED, ConfigEntry, ConfigEntryChange, ConfigEntryState
from homeassistant.const import __version__ as HA_VERSION
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.debounce import Debouncer
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.start import async_at_started
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from . import changes, files, guard, remote, text
from .const import (
    CHECK_INTERVAL,
    CONF_CUSTOM_QUIRKS_PATH,
    CONF_EXCLUDED,
    CONTENT_STORAGE_KEY,
    CONTENT_STORAGE_VERSION,
    DOMAIN,
    MAX_DOWNLOAD,
    REFRESH_COOLDOWN,
    REPOSITORY,
    RETRY_INTERVAL,
    STORAGE_KEY,
    STORAGE_VERSION,
    TUYA_CLUSTER,
    TUYA_QUERY_DATA,
    ZHA_DOMAIN,
)
from .content import COMMIT, EMPTY, BadContent, ContentState, effective_revision, from_manifest, from_withdrawn_rows, risk, sha256, withdrawn_rows
from .pictures import Pictures, async_get_pictures
from .plan import (
    NO_CONTENT,
    NO_FOLDER,
    PREFIX,
    UNCHECKED,
    UNREADABLE_FOLDER,
    ZHA_UNKNOWN,
    Device,
    Plan,
    claimed_by,
    make_plan,
    names_of,
    shipped_files,
    stem,
)

_LOGGER = logging.getLogger(__name__)

MISSING_FOLDER = "missing_quirks_path"
FOLDER_UNREADABLE = "folder_unreadable"
FOLDER_ISSUES = (MISSING_FOLDER, FOLDER_UNREADABLE)
NO_STATE = "no_content_state"
# Issues that do not depend on the files on offer.
STATE_ISSUES = (*FOLDER_ISSUES, NO_STATE)
# Issues kept current also while the change list is held.
ALWAYS = ("reload", "withdrawn_installed", "download_waiting")

ZHA_LOADED = "loaded"
ZHA_NOT_LOADED = "not loaded"
ZHA_UNREADABLE = "loaded, but the quirks it applied cannot be read"

# Records of deleted files kept for a return of the same content (newest last).
FORGOTTEN_KEPT = 100

# Changes to quirk files take effect when ZHA loads the folder. A new start of Home Assistant
# (a new value here) loads it, so changes recorded under another value are done.
_RUN = uuid.uuid4().hex


def zha_folder(hass: HomeAssistant) -> str | None:
    """The custom quirks folder ZHA loads, from the YAML config ZHA keeps in hass.data (ZHA is a
    dependency: its setup stored that config before this integration starts)."""
    path = hass.data[ZHA_DOMAIN].yaml_config.get(CONF_CUSTOM_QUIRKS_PATH)
    # ZHA hands the value to pathlib as it is: relative paths start at the working directory.
    return os.path.abspath(path) if path else None


# The attribute zha keeps a device's quirk registry entry under (zha.quirks.QUIRK_REGISTRY_ENTRY_ATTR).
_REGISTRY_ENTRY = "_quirk_registry_entry"


@functools.cache
def _shipped_root() -> Path | None:
    """The folder of the zhaquirks package, None when it cannot be found."""
    spec = importlib.util.find_spec("zhaquirks")
    locations = list(spec.submodule_search_locations or []) if spec else []
    return Path(locations[0]).resolve() if locations else None


def _module_of(source_file: str) -> str:
    """The module a quirk's source file is loaded as: zhaquirks.<path> for a quirk that ships
    with ZHA, the file name for a custom quirk (ZHA imports those under their file name)."""
    path, root = Path(source_file).resolve(), _shipped_root()
    if root is not None and path.is_relative_to(root):
        return ".".join(("zhaquirks", *path.relative_to(root).with_suffix("").parts)).removesuffix(".__init__")
    return path.stem


def applied_module(device: Any) -> str | None:
    """Module of the quirk ZHA applied to a zha Device: "" for none, None when it does not say.

    The registry entry zha keeps on the zigpy device names the quirk's source file. quirk_class
    ("module:label" for a registry entry, the device's class path without one) is the fallback:
    quirks made with zhaquirks' TuyaQuirkBuilder all report the builder's module there, shipped
    ones and custom ones alike.
    """
    applied = getattr(device, "quirk_applied", None)
    if applied is False:
        return ""
    entry = getattr(getattr(device, "device", None), _REGISTRY_ENTRY, None)
    source_file = getattr(getattr(entry, "source", None), "file", None)
    if isinstance(source_file, str) and source_file:
        return _module_of(source_file)
    quirk_class = device.quirk_class
    if ":" in quirk_class:
        return quirk_class.split(":", 1)[0]
    return None if applied else ""


def _zigpy_pair(device: Any) -> tuple[str, str] | None:
    """Manufacturer and model of the zigpy device under a zha Device; None when it does not say."""
    zigpy_device = getattr(device, "device", None)
    pair = (getattr(zigpy_device, "manufacturer", None), getattr(zigpy_device, "model", None))
    return pair if all(isinstance(value, str) and value for value in pair) else None


def _signature(device: Any) -> dict[int, dict[str, Any]] | None:
    """The endpoints of the zigpy device under a zha Device as it joined, before any quirk (zigpy's
    original signature): endpoint id -> profile_id, device_type, input_clusters, output_clusters
    (sorted ids). None when it does not say or says it in another shape. A profile or device type
    zigpy does not know (None, an endpoint whose descriptor never came) keeps the layout: the fit
    reads only the endpoints and their input clusters."""
    signature = getattr(getattr(device, "device", None), "original_signature", None)
    endpoints = signature.get("endpoints") if isinstance(signature, dict) else None
    if not isinstance(endpoints, dict) or not endpoints:
        return None
    found = {}
    for ep, data in endpoints.items():
        if not (isinstance(ep, int) and not isinstance(ep, bool) and 1 <= ep <= 254 and isinstance(data, dict)):
            return None
        values = {key: data.get(key) for key in ("profile_id", "device_type", "input_clusters", "output_clusters")}
        if not all(values[key] is None or (isinstance(values[key], int) and not isinstance(values[key], bool)) for key in ("profile_id", "device_type")):
            return None
        clusters = [values[key] for key in ("input_clusters", "output_clusters")]
        if not all(isinstance(ids, (list, tuple)) and all(isinstance(i, int) and not isinstance(i, bool) for i in ids) for ids in clusters):
            return None
        found[ep] = {**values, "input_clusters": sorted(set(clusters[0])), "output_clusters": sorted(set(clusters[1]))}
    return found


def tuya_clusters(device: Any) -> list[Any]:
    """The Tuya MCU clusters (TUYA_CLUSTER) of the zigpy device under a zha Device, by endpoint; none
    for a device that does not talk through that cluster."""
    endpoints = getattr(getattr(device, "device", None), "endpoints", None)
    if not isinstance(endpoints, dict):
        return []
    found = (getattr(endpoints[ep_id], "in_clusters", {}).get(TUYA_CLUSTER) for ep_id in sorted(ep for ep in endpoints if isinstance(ep, int) and ep))
    return [cluster for cluster in found if cluster is not None]


def query_cluster(device: Any) -> Any | None:
    """The cluster of a zha Device that a Tuya data query goes to; None when it has none.

    That is the Tuya MCU cluster of the zigpy device under it, as the applied quirk made it: it
    names its server command TUYA_QUERY_DATA "query_data" (zhaquirks' Tuya clusters do). The raw
    cluster of a device without a quirk defines no commands.
    """
    for cluster in tuya_clusters(device):
        commands = getattr(cluster, "server_commands", None)
        if isinstance(commands, dict) and getattr(commands.get(TUYA_QUERY_DATA), "name", None) == "query_data":
            return cluster
    return None


def supported(homeassistant: str | None, version: str = HA_VERSION) -> bool:
    """This Home Assistant release is at least the one a state's files need."""
    try:
        return homeassistant is None or AwesomeVersion(version) >= AwesomeVersion(homeassistant)
    except Exception:  # noqa: BLE001 - an unparsable minimum is never met
        return False


def unusable(homeassistant: str | None, tag_guard: str | None, own_guard: str, version: str = HA_VERSION) -> str | None:
    """Why this release cannot use a content state; None when it can.

    tag_guard: the guard the state's files were built for (content.json); own_guard: this
    release's. Another guard (or another content format, guard.FORMAT) would refuse files it does
    not know, a state for it waits for the release it was built for."""
    if tag_guard is None:
        return "states no guard"
    if tag_guard != own_guard:
        return f"was built for another xquirks release (guard {tag_guard[:12]}, this release has {own_guard[:12]})"
    if not supported(homeassistant, version):
        return f"needs Home Assistant {homeassistant} or newer"
    return None


def _stored_state(data: dict[str, Any], own_guard: str) -> ContentState | None:
    """The content state kept from the last check, None when there is none or it cannot be used."""
    if not data.get("tag"):
        return None
    try:
        if not COMMIT.fullmatch(str(data.get("commit"))):
            raise BadContent("not bound to a commit")
        withdrawn = from_withdrawn_rows(data.get("withdrawn", []))
        state = from_manifest(
            data["manifest"], tag=data["tag"], content=int(data["number"]), commit=data["commit"], homeassistant=data.get("homeassistant"), withdrawn=withdrawn
        )
    except (BadContent, KeyError, TypeError, ValueError):
        _LOGGER.warning("Dropping the stored content state %s: it does not load", data.get("tag"))
        return None
    if reason := unusable(state.homeassistant, data.get("guard"), own_guard):
        _LOGGER.info("Not using the stored content state %s: it %s", state.tag, reason)
        return None
    return state


def _kept_rows(rows: object) -> dict[tuple[str, str], str] | None:
    """Withdrawals kept in the store, None when there are none in the shape written."""
    try:
        return from_withdrawn_rows(rows)
    except BadContent:
        return None


def _digest(*items: str) -> str:
    return hashlib.sha256("\n".join(items).encode()).hexdigest()[:10]


@dataclasses.dataclass
class Step:
    """One change of a confirmed list, with what the apply needs to carry it out and to undo it."""

    kind: str  # "remove", "update" or "install"
    path: str
    old: bytes | None = None  # the content in the folder (remove, update)
    new: bytes | None = None  # the offered content (update, install)
    record: dict | None = None  # the record before (remove, update)

    @property
    def name(self) -> str:
        return os.path.basename(self.path)


@dataclasses.dataclass
class Applied:
    """What a confirmed change list did."""

    done: list[str] = dataclasses.field(default_factory=list)
    # The step that failed and why: the steps before it were undone, but those in left.
    failed: str = ""
    left: list[str] = dataclasses.field(default_factory=list)
    # The list was not applied: it changed while the dialog was open, or why there is no list now.
    stale: bool = False
    held: str | None = None


class Changed(Exception):
    """A file of the list no longer has the content the list was made for."""


# What a step of the list did, as the dialog lists it.
DONE = {"remove": "removed", "update": "updated", "install": "installed"}
# The changes after which the Tuya devices of a file get a data query, once ZHA loaded them.
QUERIED = (DONE["install"], DONE["update"])


def _why(err: Exception) -> str:
    """Why a step of a confirmed list failed, as the dialog says it."""
    if isinstance(err, GuardRefused):
        return err.reason
    if isinstance(err, Changed):
        return "changed since the list was made, left alone"
    if isinstance(err, remote.FetchError):
        return f"cannot download it ({err})"
    if isinstance(err, OSError):
        return str(err.strerror or err)
    return str(err)


# A change the guard stopped, as the dialog lists it.
REFUSED = "refused, it holds code this integration does not allow in a quirk file or targets devices it is not offered for (see the repair issue)"
# A change to a withdrawn revision, as the dialog lists it.
WITHDRAWN_REVISION = "not written, this revision was withdrawn"


class GuardRefused(Exception):
    """Content that was to be written is refused: the guard refuses it (REFUSED) or its revision is
    withdrawn (WITHDRAWN_REVISION)."""

    def __init__(self, path: str, reason: str = REFUSED) -> None:
        super().__init__(path)
        self.reason = reason


# The verdict on an offered file that cannot be downloaded for good: never written, like a refused one.
UNAVAILABLE = "cannot be downloaded"


class _Verdicts(Mapping[str, "tuple[str, ...] | None"]):
    """The guard's cached verdicts on the offered files, looked up when the plan asks for one."""

    def __init__(self, manager: QuirkManager) -> None:
        self._manager = manager

    def __getitem__(self, name: str) -> tuple[str, ...] | None:
        manager = self._manager
        if manager.unavailable(name):
            return (UNAVAILABLE,)
        return manager._verdict(manager.source.shas[name], name)

    def __iter__(self) -> Iterator[str]:
        return iter(self._manager.source.shas)

    def __len__(self) -> int:
        return len(self._manager.source.shas)


class QuirkManager:
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self.data: dict[str, Any] = {"installed": {}}
        self.plan = Plan()
        self.devices: dict[str, Device] = {}
        # device id -> its endpoints as it joined (_signature), for the report links.
        self.signatures: dict[str, dict[int, dict[str, Any]]] = {}
        # device id -> its IEEE address, for the devices in self.devices.
        self.ieees: dict[str, str] = {}
        # Files ZHA loaded since the list installed or updated them: their Tuya devices get a data
        # query at the next refresh that reads what ZHA applies (_query_tuya_devices).
        self._query_due: set[str] = set()
        # File name -> the data queries sent after ZHA loaded it (this run only), for diagnostics.
        self.queries: dict[str, dict[str, Any]] = {}
        self.zha_state = ZHA_NOT_LOADED
        self.folder: str | None = None
        self.problem: str | None = None
        self.folder_error = ""
        self._store: Store[dict[str, Any]] = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self._lock = asyncio.Lock()
        self._debouncer = Debouncer(hass, _LOGGER, cooldown=REFRESH_COOLDOWN, immediate=False, function=self.async_refresh)
        self._zha_was_down = False
        self._zha_reloaded = False
        # ZHA loads the custom quirks folder at the start of its setup: a change pending then is loaded,
        # one written while the setup runs is not. Each pending change gets a number (this run of the
        # integration only; changes without one count as older than any setup).
        self._changes_made = 0
        self._change_number: dict[str, int] = {}
        self._changes_at_setup = 0
        self._changes_loaded = 0
        # A confirmed change asked ZHA to reload: the reminder waits until ZHA is back.
        self._reload_requested = False
        self._warned = False
        # The content state in use: the newest one this release can use (kept across restarts).
        self.state: ContentState | None = None
        # Withdrawn revisions of the newest tag when it is newer than the state in use (it needs a
        # newer Home Assistant): a withdrawal must not wait for that update.
        self.newer_withdrawn: dict[tuple[str, str], str] = {}
        self._content_store: Store[dict[str, Any]] = Store(hass, CONTENT_STORAGE_VERSION, CONTENT_STORAGE_KEY)
        self._content: dict[str, Any] = {}
        self._check_lock = asyncio.Lock()
        self._retry_after = 0.0
        self._last_attempt = 0.0
        self.last_check: dict[str, Any] = {"time": None, "result": "not checked yet", "error": None}
        # From the last refresh: path -> sha256 of each recorded file on disk.
        self._disk: dict[str, str | None] = {}
        self._downloads: dict[tuple[str, str, str], bytes] = {}
        # From the last refresh: name -> sha256 of the offered or forgotten names in the folder.
        self._present: dict[str, str | None] = {}
        self.pictures: Pictures | None = None
        self._pictures_task: asyncio.Task | None = None
        # The guard this release ships (guard.py, fixed_code.json), read at setup.
        self.guard: guard.Guard | None = None
        # (sha256, the targets of the file's manifest entry) -> the guard's reasons to refuse that
        # content for that entry, empty when it passes.
        self._verdicts: dict[tuple[str, str | None], tuple[str, ...]] = {}
        # From the last refresh: offered files the guard refused (name -> sha256, revision, reasons)
        # and offered files not checked yet (name -> why the download failed).
        self.refused: dict[str, dict[str, Any]] = {}
        self._unchecked: dict[str, str] = {}
        # (commit, name, sha256) -> why that offered file cannot be downloaded for good (content at a
        # commit never changes): the change list never writes it.
        self._unavailable: dict[tuple[str, str, str], str] = {}

    @property
    def source(self) -> ContentState:
        """The files on offer: the state in use, nothing while there is none."""
        return self.state or EMPTY

    async def async_setup(self) -> None:
        self.guard = await self.hass.async_add_executor_job(guard.Guard.load)
        self.pictures = await async_get_pictures(self.hass)
        if (stored := await self._store.async_load()) is not None:
            self.data = stored
        self._content = await self._content_store.async_load() or {}
        if not isinstance(self._content.get("facts"), dict):
            self._content["facts"] = {}
        self.state = _stored_state(self._content, self.guard.id)
        if self.state is not None and (tags := self._kept_tags()) is not None:
            self.newer_withdrawn = self._kept_newer(tags, self.state) or {}
        self.data.setdefault("installed", {})
        self.data.setdefault("forgotten", {})
        # Records without the names of the version written (from before the change list) go: their
        # files belong to the user from now on. Earlier releases also kept backups.
        for kind in ("installed", "forgotten"):
            self.data[kind] = {path: record for path, record in self.data[kind].items() if isinstance(record.get("names"), dict)}
        self.data.pop("backups", None)
        pending = self.data.setdefault("pending", {"run": _RUN, "changes": []})
        if pending.get("run") != _RUN:
            # Home Assistant started since: ZHA loaded the folder with these changes.
            self._query_due = {c["file"] for c in pending.get("changes", []) if c.get("change") in QUERIED}
            self.data["pending"] = {"run": _RUN, "changes": []}
        self._zha_was_down = not self.hass.config_entries.async_loaded_entries(ZHA_DOMAIN)
        entry = self.entry
        entry.async_on_unload(self._debouncer.async_cancel)
        entry.async_on_unload(self.hass.bus.async_listen(dr.EVENT_DEVICE_REGISTRY_UPDATED, self._device_changed))
        entry.async_on_unload(async_dispatcher_connect(self.hass, SIGNAL_CONFIG_ENTRY_CHANGED, self._entry_changed))
        entry.async_on_unload(async_at_started(self.hass, self._started))
        entry.async_on_unload(async_track_time_interval(self.hass, self._interval_check, RETRY_INTERVAL))
        entry.async_on_unload(entry.add_update_listener(self._options_changed))

    async def _options_changed(self, _hass: HomeAssistant, _entry: ConfigEntry) -> None:
        # The devices to leave alone changed.
        await self.async_refresh()

    async def _started(self, _hass: HomeAssistant) -> None:
        await self.async_refresh()
        self.entry.async_create_background_task(self.hass, self.async_check(), "xquirks content check")

    async def _interval_check(self, _now: datetime) -> None:
        if self.plan.held in (UNCHECKED, UNREADABLE_FOLDER):
            # The change list waits for files to be checked or for the folder to be readable again:
            # no event ends that, so look again. Decided by the held list, not by the fields a
            # refresh resets first: a dialog whose request went away mid-refresh keeps the old hold.
            await self.async_refresh()
        # Every few hours; while no state is in use, every few minutes. A minute of slack for the timer.
        due = RETRY_INTERVAL if self.state is None else CHECK_INTERVAL
        if time.time() - self._last_attempt >= due.total_seconds() - 60:
            await self.async_check()

    # The content states in the repository

    async def async_check(self) -> None:
        """Look for a newer content state; a new change list follows when one arrives. A failed check ends up
        in last_check (the notice without a state shows it), it never raises."""
        async with self._check_lock:
            found = await self._async_check()
            if found is not None:
                # Swapped under the refresh lock: a refresh or a confirmed change in progress ends
                # with the state it started with, the next one sees the new state complete.
                async with self._lock:
                    self.state, self.newer_withdrawn = found
                    await self._async_refresh()
                return
        if self.state is None:
            # Without a state, the notice says why after every check.
            await self.async_refresh()

    def _kept_tags(self) -> remote.Tags | None:
        """The tag list as the last check found it, with its ETag; None when none is kept."""
        rows = self._content.get("tags")
        if not isinstance(rows, list) or not all(
            isinstance(row, list) and len(row) == 2 and type(row[0]) is int and row[0] > 0 and COMMIT.fullmatch(str(row[1])) for row in rows
        ):
            return None
        return remote.Tags(tuple(remote.Ref(number, f"content-{number}", commit) for number, commit in rows), self._content.get("etag"))

    def _facts(self, ref: remote.Ref) -> dict[str, Any] | None:
        """What is kept about a tag at its commit: the guard and Home Assistant release it names or
        why it cannot be read, for the newest tag also its withdrawals. None when nothing is kept
        for that commit (a tag made anew on another commit is examined anew)."""
        facts = self._content["facts"].get(ref.tag)
        return facts if isinstance(facts, dict) and facts.get("commit") == ref.commit else None

    async def _examine(self, session: Any, ref: remote.Ref) -> dict[str, Any]:
        """The facts of a tag, read once: content at a commit never changes."""
        if (facts := self._facts(ref)) is None:
            try:
                meta = await remote.async_meta(session, ref.commit)
                facts = {"commit": ref.commit, "guard": meta.guard, "homeassistant": meta.homeassistant}
            except remote.BadTag as err:
                facts = {"commit": ref.commit, "bad": f"cannot be read ({err})"}
                _LOGGER.info("Content check: %s %s", ref.tag, facts["bad"])
            self._content["facts"][ref.tag] = facts
        return facts

    def _reason(self, facts: dict[str, Any]) -> str | None:
        """Why this release cannot use a tag with these facts on this Home Assistant release; None when it can."""
        return facts.get("bad") or unusable(facts.get("homeassistant"), facts.get("guard"), self.guard.id)

    def _skipped(self) -> dict[str, str]:
        """Tag -> why this release cannot use it, for the kept tags newer than the state in use."""
        tags, known = self._kept_tags(), self.state.content if self.state else 0
        return {ref.tag: reason for ref in (tags.found if tags else ()) if ref.number > known and (facts := self._facts(ref)) and (reason := self._reason(facts))}

    async def _async_check(self) -> tuple[ContentState | None, dict[tuple[str, str], str]] | None:
        """What to use from now on: (state, withdrawals of a newer tag); None when that stays as it is."""
        now = time.time()
        self._last_attempt = now
        stamp = dt_util.utcnow().isoformat(timespec="seconds")
        if now < self._retry_after:
            until = dt_util.utc_from_timestamp(self._retry_after).isoformat(timespec="minutes")
            self.last_check = {"time": stamp, "result": "skipped", "error": f"rate limited until {until}"}
            return None
        try:
            return await self._async_examine(stamp)
        except remote.RateLimited as err:
            self._retry_after = err.until
            self.last_check = {"time": stamp, "result": "failed", "error": str(err)}
            _LOGGER.info("Content check: %s", err)
        except remote.FetchError as err:
            self.last_check = {"time": stamp, "result": "failed", "error": str(err)}
            _LOGGER.info("Content check failed, keeping %s: %s", self.state.tag if self.state else "no content state", err)
        except (ValueError, TypeError, KeyError, AttributeError, OverflowError) as err:
            # An answer in a shape no check expects (remote.py refuses the known ones): the check
            # fails like any other, what is in use stays.
            self.last_check = {"time": stamp, "result": "failed", "error": f"unexpected answer: {err!r}"}
            _LOGGER.warning("Content check failed on an unexpected answer", exc_info=True)
        return None

    async def _async_examine(self, stamp: str) -> tuple[ContentState | None, dict[tuple[str, str], str]] | None:
        session = async_get_clientsession(self.hass)
        state = self.state
        known = state.content if state else 0
        kept = self._kept_tags()
        # The ETag answers whether the tag list changed: an unchanged list is the one kept. What this
        # release can use is decided anew from the kept facts (Home Assistant or the release may
        # have changed since), without a request.
        tags = await remote.async_tags(session, kept.etag if kept else None) or kept
        dropped = False
        if state is not None:
            in_use = tags.get(state.tag)
            # An empty list proves nothing; a list without the tag, or the tag on another commit, means
            # it was deleted (its number may come back on another commit, a tag deleted after an incident).
            if (in_use is None and tags.found) or (in_use is not None and in_use.commit != state.commit):
                _LOGGER.warning("The content state %s is no longer in %s as it was taken; looking again", state.tag, REPOSITORY)
                state, known, dropped = None, 0, True
        skipped, taken = [], None
        # Newest first: the first tag this release can use is the newest one it can use.
        for ref in tags.found:
            if ref.number <= known:
                break
            facts = await self._examine(session, ref)
            if (reason := self._reason(facts)) is None:
                try:
                    taken = await remote.async_state(session, ref, facts.get("homeassistant"))
                    break
                except remote.BadTag as err:
                    # Content at a commit never changes: this tag stays unusable, an older one may do.
                    reason = facts["bad"] = f"cannot be read ({err})"
                    _LOGGER.info("Content check: %s %s", ref.tag, reason)
            skipped.append(f"{ref.tag} {reason}")
        # The facts of tags no longer listed go.
        self._content["facts"] = {ref.tag: facts for ref in tags.found if (facts := self._facts(ref)) is not None}
        newer = await self._newer_withdrawals(session, tags, taken or state)
        listed = {"etag": tags.etag, "tags": [[ref.number, ref.commit] for ref in tags.found], "facts": self._content["facts"]}
        if taken is not None:
            self._content = {
                "tag": taken.tag,
                "number": taken.content,
                "commit": taken.commit,
                "guard": self.guard.id,
                "homeassistant": taken.homeassistant,
                "withdrawn": withdrawn_rows(taken.withdrawn),
                "manifest": taken.manifest,
                **listed,
            }
            await self._content_store.async_save(self._content)
            result = f"fetched {taken.tag}" + (f"; skipped {'; '.join(skipped)}" if skipped else "")
            self.last_check = {"time": stamp, "result": result, "error": None}
            return taken, newer
        # A state no longer listed is not kept either.
        self._content = listed if dropped else self._content | listed
        await self._content_store.async_save(self._content)
        if not tags.found:
            result = "the repository has no content state yet"
        elif skipped:
            result = f"nothing newer this release can use: {'; '.join(skipped)}"
        else:
            result = f"newest state {tags.found[0].tag} in use"
        self.last_check = {"time": stamp, "result": result, "error": None}
        if dropped or newer != self.newer_withdrawn:
            return state, newer
        return None

    def _kept_newer(self, tags: remote.Tags, base: ContentState | None) -> dict[tuple[str, str], str] | None:
        """The kept withdrawals of the newest tag when it is newer than base; {} when it is not,
        None when they are not read yet."""
        newest = tags.found[0] if tags.found else None
        if base is None or newest is None or newest.number <= base.content:
            return {}
        facts = self._facts(newest)
        return _kept_rows(facts.get("withdrawn")) if facts else None

    async def _newer_withdrawals(self, session: Any, tags: remote.Tags, base: ContentState | None) -> dict[tuple[str, str], str]:
        """The withdrawals of the newest tag when it is newer than base (the state in use from now
        on); read once per tag and kept with its facts. Its files may need a newer Home Assistant or
        another release, its list of withdrawn revisions applies already."""
        if (rows := self._kept_newer(tags, base)) is not None:
            return rows
        newest = tags.found[0]
        facts = await self._examine(session, newest)
        try:
            withdrawn = await remote.async_withdrawn(session, newest.commit)
        except remote.BadTag as err:
            _LOGGER.info("No withdrawn revisions from %s: %s", newest.tag, err)
            withdrawn = {}
        facts["withdrawn"] = withdrawn_rows(withdrawn)
        return withdrawn

    @callback
    def _device_changed(self, event: Event[dr.EventDeviceRegistryUpdatedData]) -> None:
        # sw_version: new firmware, after which ZHA may know other endpoints of the device (its layout).
        if event.data["action"] == "update" and not {"manufacturer", "model", "identifiers", "name_by_user", "disabled_by", "sw_version"} & set(event.data["changes"]):
            return
        self._debouncer.async_schedule_call()

    @callback
    def _entry_changed(self, change: ConfigEntryChange, entry: ConfigEntry) -> None:
        # ZHA loaded, reloaded or unloaded: the quirks it applies may have changed.
        if entry.domain != ZHA_DOMAIN:
            return
        if entry.state is ConfigEntryState.LOADED:
            if self._zha_was_down:
                self._zha_was_down = False
                self._zha_reloaded = True
                self._reload_requested = False
                self._changes_loaded = self._changes_at_setup
        else:
            # Not loaded, or its setup (which loads the folder) runs: the last of these before it is
            # loaded again tells which changes that setup saw.
            self._zha_was_down = True
            self._changes_at_setup = self._changes_made
        self._debouncer.async_schedule_call()

    # Reading the state

    def _applied_quirks(self) -> dict[str, tuple[str | None, tuple[str, str] | None, dict | None]] | None:
        """IEEE -> (module of the quirk ZHA applied: "" none, None unknown; the manufacturer and model
        of the zigpy device, which quirks match on: a quirk's friendly name changes only those of the
        device registry; its endpoints as it joined, None unknown). None while ZHA is not loaded."""
        if not self.hass.config_entries.async_loaded_entries(ZHA_DOMAIN):
            self.zha_state = ZHA_NOT_LOADED
            return None
        try:
            # A loaded ZHA entry has its gateway proxy (set before setup returns, cleared on unload).
            proxies = self.hass.data[ZHA_DOMAIN].gateway_proxy.device_proxies
            quirks = {str(proxy.device.ieee): (applied_module(proxy.device), _zigpy_pair(proxy.device), _signature(proxy.device)) for proxy in proxies.values()}
        except (AttributeError, KeyError, TypeError):
            self.zha_state = ZHA_UNREADABLE
            if not self._warned:
                self._warned = True
                _LOGGER.warning("Cannot read which quirks ZHA applied; the change list stays as it is until this is fixed", exc_info=True)
            return None
        self.zha_state = ZHA_LOADED
        return quirks

    def _zha_devices(self, quirks: dict[str, tuple[str | None, tuple[str, str] | None, dict | None]]) -> dict[str, Device]:
        registry = dr.async_get(self.hass)
        devices = {}
        self.signatures, self.ieees = {}, {}
        for zha_entry in self.hass.config_entries.async_entries(ZHA_DOMAIN):
            for device in dr.async_entries_for_config_entry(registry, zha_entry.entry_id):
                ieee = next((value for domain, value in device.identifiers if domain == ZHA_DOMAIN), None)
                if ieee is None:
                    continue
                module, pair, signature = quirks.get(ieee, (None, None, None))
                manufacturer, model = pair or (device.manufacturer, device.model)
                if not manufacturer or not model:
                    continue
                name = device.name_by_user or device.name or model
                layout = tuple((ep, frozenset(data["input_clusters"])) for ep, data in sorted(signature.items())) if signature else None
                devices[device.id] = Device(manufacturer, model, name, module, device.disabled_by is not None, layout)
                self.ieees[device.id] = ieee
                if signature:
                    # For the report link of a device a file does not fit.
                    self.signatures[device.id] = signature
        return devices

    def _read_disk(self) -> tuple[dict[str, str | None], dict[str, str | None], dict[str, str]]:
        """Records -> sha on disk; files in the folder -> sha (for the names this collection ships or
        has a record of and for every z2m_*.py); -> revision for the files of this collection."""
        if self.folder and not os.path.isdir(self.folder):
            # Read as empty, every record would count as deleted.
            raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), self.folder)
        disk = {path: files.sha_on_disk(path) for path in self.data["installed"]}
        present: dict[str, str | None] = {}
        generated: dict[str, str] = {}
        if self.folder:
            known = set(self.source.shas) | {os.path.basename(p) for p in (*self.data["installed"], *self.data["forgotten"])}
            for name in files.names_in(self.folder):
                if name not in known and not (name.startswith(PREFIX) and name.endswith(".py")):
                    present[name] = None
                    continue
                present[name], revision = files.present_state(os.path.join(self.folder, name))
                if revision is not None:
                    generated[name] = revision
        return disk, present, generated

    def _make_plan(self, disk: dict[str, str | None], present: dict[str, str | None], generated: dict[str, str]) -> Plan:
        return make_plan(
            self.source,
            self.devices,
            self.data["installed"],
            disk,
            self.folder or "",
            present,
            pending=bool(self.data["pending"]["changes"]),
            generated=generated,
            withdrawn=self.withdrawn,
            verdicts=_Verdicts(self),
            excluded=frozenset(self.entry.options.get(CONF_EXCLUDED, ())),
        )

    async def async_refresh(self) -> None:
        async with self._lock:
            await self._async_refresh()

    async def _async_refresh(self) -> None:
        # Files go only where ZHA loads them.
        self.folder, self.folder_error = zha_folder(self.hass), ""
        self.problem = None if self.folder else MISSING_FOLDER
        if self._zha_reloaded:
            # ZHA loaded the folder: what it loaded waits no longer.
            self._zha_reloaded = False
            changes = self.data["pending"]["changes"]
            loaded = [c for c in changes if self._change_number.get(c["file"], 0) <= self._changes_loaded]
            self.data["pending"]["changes"] = [c for c in changes if c not in loaded]
            # The Tuya devices of the files it loaded new or updated get a data query below.
            self._query_due.update(c["file"] for c in loaded if c["change"] in QUERIED)
            await self._store.async_save(self.data)
        quirks = self._applied_quirks()
        if quirks is not None:
            self.devices = self._zha_devices(quirks)
            self._query_tuya_devices()
        if self.state is None or self.folder is None:
            # No list of files yet, or no folder ZHA loads them from: nothing to change or compare. The
            # list and the notices stay as they are, ignored ones too; the next state or folder brings
            # a refresh.
            self.plan = Plan(held=NO_CONTENT if self.state is None else NO_FOLDER)
            self._sync_issues({**self._folder_issues(), **self._state_issue()}, only=STATE_ISSUES)
            return
        try:
            disk, present, generated = await self.hass.async_add_executor_job(self._read_disk)
        except OSError as err:
            self.problem, self.folder_error = FOLDER_UNREADABLE, str(err.strerror or err)
            _LOGGER.warning("Cannot read the custom quirks folder %s: %s", self.folder, err)
            self.plan = Plan(held=UNREADABLE_FOLDER)
            self._sync_issues(self._folder_issues(), only=STATE_ISSUES)
            return
        changed = self._restore_forgotten(present, disk)
        self._disk = disk
        self._unchecked = {}
        plan = self._make_plan(disk, present, generated)
        if plan.held == UNCHECKED:
            # The guard runs before the list, on every file it would write: a file it refused or
            # could not check yet is written by no list.
            await self._check_offers(plan.unchecked)
            plan = self._make_plan(disk, present, generated)
        if quirks is None and plan.held is None:
            # ZHA is (re)loading, or its internals changed: what it applies now is unknown, so no list
            # is applied. Planned with the devices as ZHA reported them last, the records and the
            # notice of a withdrawn revision in use stay current.
            plan.held = ZHA_UNKNOWN
        self._present = present
        for path, record in plan.settled.items():
            self.data["installed"][path] = record
            changed = True
        for path in plan.gone:
            # Kept aside: the same content coming back (a share mounted late) is ours again.
            self.data["forgotten"][path] = self.data["installed"].pop(path)
            changed = True
        for path in list(self.data["forgotten"])[:-FORGOTTEN_KEPT]:
            del self.data["forgotten"][path]
        if changed:
            await self._store.async_save(self.data)
        self.plan = plan
        source = self.source
        self.refused = {
            name: {"sha256": source.shas[name], "revision": source.revisions.get(name), "problems": self._verdict(source.shas[name], name)}
            for name in plan.refused
            if not self.unavailable(name)
        }
        always = {**self._folder_issues(), **self._reload_issue(), **self._withdrawn_issues(plan), **self._waiting_issue(plan)}
        if plan.held:
            # A change waits for ZHA to load the folder, a file of the list is not checked yet or what
            # ZHA applies is unknown: the list and the other notices stay as they are, ignored ones
            # too. The list comes once that is over.
            self._sync_issues(always, only=(*STATE_ISSUES, *ALWAYS))
        else:
            self._sync_issues({**always, **self._plan_issues(plan), **self._refused_issues(), **self._unavailable_issues(plan)})
        self._fetch_pictures()

    # The guard

    def _targets(self, name: str) -> guard.Targets | None:
        """What the file name may target: its entry in the state in use (None without one: refused)."""
        return guard.Targets.of(self._entry(name))

    def _verdict(self, sha: str, name: str) -> tuple[str, ...] | None:
        """The cached verdict on content with this sha256 as the file name, None when not checked yet."""
        targets = self._targets(name)
        return self._verdicts.get((sha, targets.key if targets else None))

    async def _checked(self, content: bytes, name: str) -> tuple[str, ...]:
        """The guard's reasons to refuse content as the file name of the state in use, empty when it
        passes; per sha256 and manifest entry, parsed in the executor."""
        targets = self._targets(name)
        key = (sha256(content), targets.key if targets else None)
        if (verdict := self._verdicts.get(key)) is None:
            verdict = self._verdicts[key] = await self.hass.async_add_executor_job(self.guard.problems, content, targets)
        return verdict

    async def _check_offers(self, names: list[str]) -> None:
        """Run the guard on these offered files (downloaded from the state in use): the verdicts decide
        what the change list may write."""
        for name in sorted(names):
            if self._verdict(self.source.shas[name], name) is not None:
                continue
            try:
                if problems := await self._checked(await self._read_offered(name), name):
                    _LOGGER.warning("Refused %s of %s: %s", name, self.source.tag, "; ".join(problems[:3]))
            except remote.BadTag as err:
                # Asking again does not help: the list goes on without this file.
                _LOGGER.warning("Cannot use %s of %s: %s", name, self.source.tag, err)
                self._unavailable[self._download_key(name)] = str(err)
            except remote.FetchError as err:
                _LOGGER.info("Cannot check %s yet: %s", name, err)
                self._unchecked[name] = str(err)

    def unavailable(self, name: str) -> str | None:
        """Why the offered file cannot be downloaded for good; None when it can or was not tried."""
        return self._unavailable.get(self._download_key(name))

    def _restore_forgotten(self, present: dict[str, str | None], disk: dict[str, str | None]) -> bool:
        """A file this integration wrote came back unchanged: take its record back."""
        restored = False
        for path, kept in list(self.data["forgotten"].items()):
            name = os.path.basename(path)
            if os.path.dirname(path) == self.folder and path not in self.data["installed"] and present.get(name) == kept["sha256"]:
                self.data["installed"][path] = kept
                disk[path] = kept["sha256"]
                del self.data["forgotten"][path]
                restored = True
        return restored

    # Repair issues

    def _folder_issues(self) -> dict[str, tuple[str, bool, dict[str, str], dict[str, str]]]:
        if self.problem == MISSING_FOLDER:
            return {MISSING_FOLDER: (MISSING_FOLDER, False, {}, {})}
        if self.problem == FOLDER_UNREADABLE:
            return {FOLDER_UNREADABLE: (FOLDER_UNREADABLE, False, {"folder": self.folder or "", "error": self.folder_error}, {})}
        return {}

    def _state_issue(self) -> dict[str, tuple[str, bool, dict[str, str], dict[str, str]]]:
        """Why nothing is offered: no content state in use after a check."""
        check = self.last_check
        if self.state is not None or check["time"] is None:
            return {}
        return {NO_STATE: (NO_STATE, False, {"reason": check["error"] or check["result"]}, {})}

    def _entry(self, name: str) -> dict | None:
        manifest = self.source.manifest
        slug = shipped_files(manifest).get(name)
        return manifest.get(slug) if slug else None

    def _quirk(self, name: str) -> str:
        """The device a file is for, as the notices name it."""
        return text.label(self._entry(name), name)

    def picture(self, name: str) -> str:
        """The picture of the device a file is for, as a markdown paragraph; empty without one."""
        entry = self._entry(name)
        return self.pictures.markdown(entry.get("picture"), entry.get("picture_sha256")) if entry and self.pictures else ""

    def _named_files(self) -> set[str]:
        """The files whose device a notice names."""
        plan = self.plan
        names = {item.name for items in (plan.blocked, plan.not_applied, plan.misfits) for item in items}
        names |= {os.path.basename(path) for path in plan.changed} | {os.path.basename(path) for path, _rev in plan.withdrawn_installed}
        return names | set(plan.users_files) | set(plan.withdrawn_copies)

    @callback
    def _fetch_pictures(self) -> None:
        """Fetch the missing pictures of the devices the notices name; the notices show them once fetched."""
        if self.pictures is None or (self._pictures_task is not None and not self._pictures_task.done()):
            return
        entries = (self._entry(name) for name in self._named_files())
        if missing := self.pictures.missing((entry.get("picture"), entry.get("picture_sha256")) for entry in entries if entry):
            self._pictures_task = self.entry.async_create_background_task(self.hass, self._async_fetch_pictures(missing), "xquirks pictures")

    async def _async_fetch_pictures(self, pins: list[tuple[str, str]]) -> None:
        if self.pictures is not None and await self.pictures.async_fetch(pins):
            await self.async_refresh()

    def _plan_issues(self, plan: Plan) -> dict[str, tuple[str, bool, dict[str, str], dict[str, Any]]]:
        """issue id -> (translation key, fixable, placeholders, data for the fix flow): the change list
        and the notices."""
        devices, wanted = self.devices, {}
        if plan.changes:
            # The id is the list's: "Not now" puts exactly this list aside, another list is a new issue.
            wanted[f"changes_{plan.key}"] = ("changes", True, {"count": str(plan.changes)}, {"key": plan.key, "severe": plan.severe})
        for blocked in plan.blocked:
            entry = self._entry(blocked.name)
            key = f"blocked_{stem(blocked.name)}_{_digest(*blocked.devices, *(devices[i].quirk or '' for i in blocked.devices))}"
            placeholders = {
                **text.offer_title(entry, len(blocked.devices)),
                "file": blocked.name,
                "devices": text.device_list(blocked.devices, devices, plan.ours),
                "status": text.status(entry),
                "picture": self.picture(blocked.name),
            }
            wanted[key] = ("blocked", False, placeholders, {})
        for name in plan.users_files:
            sha = self._present.get(name) or ""
            placeholders = {"file": name, "quirk": self._quirk(name), "folder": self.folder or "", "picture": self.picture(name)}
            wanted[f"users_file_{stem(name)}_{sha[:10]}"] = ("users_file", False, placeholders, {"file": name})
        for item in plan.not_applied:
            key = f"not_applied_{stem(item.name)}_{_digest(*item.devices, *(devices[i].quirk or '' for i in item.devices))}"
            placeholders = {"file": item.name, "quirk": self._quirk(item.name), "devices": text.device_list(item.devices, devices, plan.ours), "picture": self.picture(item.name)}
            wanted[key] = ("not_applied", False, placeholders, {})
        for item in plan.misfits:
            entry = self._entry(item.name) or {}
            key = f"misfit_{stem(item.name)}_{_digest(*(f'{device_id} {why}' for device_id, why in item.devices))}"
            links = {
                device_id: text.report_url(entry, item.name, devices[device_id], self.signatures[device_id], why, HA_VERSION)
                for device_id, why in item.devices if device_id in devices and device_id in self.signatures
            }
            placeholders = {"file": item.name, "quirk": self._quirk(item.name), "devices": text.misfit_list(item, devices, links), "picture": self.picture(item.name)}
            wanted[key] = ("misfit", False, placeholders, {})
        for path in plan.changed:
            name = os.path.basename(path)
            key = f"changed_{stem(name)}_{_digest(path, self._disk.get(path) or '')}"
            placeholders = {"file": name, "folder": os.path.dirname(path), "quirk": self._quirk(name), "picture": self.picture(name)}
            wanted[key] = ("changed", False, placeholders, {})
        for name, rev in plan.withdrawn_copies.items():
            reason = text.plain(self.withdrawn.get((name, rev), ""))
            placeholders = {"file": name, "quirk": self._quirk(name), "folder": self.folder or "", "revision": rev, "reason": reason, "picture": self.picture(name)}
            wanted[f"withdrawn_copy_{stem(name)}_{rev}"] = ("withdrawn_copy", False, placeholders, {"file": name})
        return wanted

    def _withdrawn_issues(self, plan: Plan) -> dict[str, tuple[str, bool, dict[str, str], dict[str, Any]]]:
        """An error notice per file of ours at a withdrawn revision: also while the list is held or
        was put aside (the list takes it out of the folder)."""
        wanted = {}
        for path, rev in plan.withdrawn_installed:
            name = os.path.basename(path)
            reason = text.plain(self.withdrawn.get((name, rev), ""))
            placeholders = {"file": name, "quirk": self._quirk(name), "folder": os.path.dirname(path), "revision": rev, "reason": reason, "picture": self.picture(name)}
            wanted[f"withdrawn_installed_{stem(name)}_{rev}"] = ("withdrawn_installed", False, placeholders, {"file": name})
        return wanted

    def _waiting_issue(self, plan: Plan) -> dict[str, tuple[str, bool, dict[str, str], dict[str, Any]]]:
        """While the list waits for files the guard could not check yet: which ones and why."""
        if plan.held != UNCHECKED or not self._unchecked:
            return {}
        rows = [f"`{name}`: {text.plain(error)}" for name, error in sorted(self._unchecked.items())]
        return {"download_waiting": ("download_waiting", False, {"files": text.name_list(rows)}, {})}

    def _unavailable_issues(self, plan: Plan) -> dict[str, tuple[str, bool, dict[str, str], dict[str, Any]]]:
        """A notice per file of the list that cannot be downloaded for good."""
        wanted = {}
        for name in plan.refused:
            if error := self.unavailable(name):
                placeholders = {"file": name, "quirk": self._quirk(name), "error": text.plain(error)}
                wanted[f"unavailable_{stem(name)}_{self.source.shas[name][:10]}"] = ("unavailable", False, placeholders, {"file": name})
        return wanted

    def _reload_issue(self) -> dict[str, tuple[str, bool, dict[str, str], dict[str, Any]]]:
        if (changes := self.data["pending"]["changes"]) and not self._reload_requested:
            # Only when the reload right after a change did not happen (ZHA was not loaded).
            return {"reload": ("reload", True, {"count": str(len(changes))}, {})}
        return {}

    def _refused_issues(self) -> dict[str, tuple[str, bool, dict[str, str], dict[str, Any]]]:
        """A security notice per offered file the guard refused."""
        wanted = {}
        for name, refusal in self.refused.items():
            placeholders = {"file": name, "quirk": self._quirk(name), "revision": refusal["revision"] or "unknown"}
            wanted[f"refused_{stem(name)}_{refusal['sha256'][:10]}"] = ("refused", False, placeholders, {"file": name, "sha256": refusal["sha256"]})
        return wanted

    @property
    def withdrawn(self) -> dict[tuple[str, str], str]:
        """(file name, revision) -> why it must not be used: from the state in use and a newer tag."""
        return {**self.source.withdrawn, **self.newer_withdrawn}

    @callback
    def _sync_issues(
        self, wanted: dict[str, tuple[str, bool, dict[str, str], dict[str, Any]]], only: tuple[str, ...] | None = None, keep: frozenset[str] = frozenset()
    ) -> None:
        """Create the wanted issues; delete the others (only those of the given kinds, if given) but those to keep."""
        registry = ir.async_get(self.hass)
        for (domain, issue_id), issue in list(registry.issues.items()):
            if domain != DOMAIN or issue_id in wanted or issue_id in keep:
                continue
            if only is not None and (issue.data or {}).get("kind", issue.translation_key) not in only:
                continue
            ir.async_delete_issue(self.hass, DOMAIN, issue_id)
        for issue_id, (key, fixable, placeholders, data) in wanted.items():
            ir.async_create_issue(
                self.hass,
                DOMAIN,
                issue_id,
                data={"kind": key, **data},
                is_fixable=fixable,
                severity=ir.IssueSeverity.ERROR if key in ("withdrawn_copy", "withdrawn_installed", "refused") or data.get("severe") else ir.IssueSeverity.WARNING,
                translation_key=key,
                translation_placeholders=placeholders,
            )

    @callback
    def async_delete_issues(self) -> None:
        registry = ir.async_get(self.hass)
        for domain, issue_id in list(registry.issues):
            if domain == DOMAIN:
                ir.async_delete_issue(self.hass, DOMAIN, issue_id)

    # The change list, confirmed by the user as a whole

    def _pending(self, name: str, change: str) -> None:
        self._changes_made += 1
        self._change_number[name] = self._changes_made
        changes = [c for c in self.data["pending"]["changes"] if c["file"] != name]
        self.data["pending"]["changes"] = [*changes, {"file": name, "change": change}]

    def _download_key(self, name: str) -> tuple[str, str, str]:
        source = self.source
        return (source.commit or "", name, source.shas[name])

    async def _read_offered(self, name: str) -> bytes:
        """The offered content of a file, downloaded from the state in use."""
        source = self.source
        # The guard's check before the list downloads the file; the dialog and the apply reuse it.
        key = self._download_key(name)
        if (content := self._downloads.get(key)) is None:
            content = await remote.async_file(async_get_clientsession(self.hass), source, name)
            self._downloads = {**dict(list(self._downloads.items())[-7:]), key: content}
        return content

    async def async_changes(self, old_path: str, name: str) -> changes.Summary | None:
        """What the offered file name changes against the file at old_path; None when either cannot be read."""
        old = await self.hass.async_add_executor_job(files.read_bounded, old_path, MAX_DOWNLOAD)
        if old is None:
            return None
        try:
            new = await self._read_offered(name)
        except (OSError, KeyError, remote.FetchError) as err:
            _LOGGER.debug("No change list for %s: %s", name, err or type(err).__name__)
            return None
        return await self.hass.async_add_executor_job(changes.summarize, old, new)

    async def async_change_text(self) -> str:
        """The change list as its dialog shows it (markdown)."""
        plan = self.plan
        summaries = {update.path: await self.async_changes(update.path, update.name) for update in plan.update}
        return text.change_list(plan, self.devices, self._quirk, self.withdrawn, summaries, self._entry, self.data["installed"].get)

    async def _change_summaries(self) -> dict[str, Any]:
        """The full entity changes of every update in the list whose offered file was downloaded
        already: diagnostics download nothing."""
        out: dict[str, Any] = {}
        for update in self.plan.update:
            if self._download_key(update.name) not in self._downloads:
                out[update.name] = "not downloaded yet"
                continue
            summary = await self.async_changes(update.path, update.name)
            out[update.name] = summary.as_dict() if summary else None
        return out

    async def _refuse(self, path: str, content: bytes) -> None:
        """GuardRefused when content must not be written to path: the guard refuses it for the file's
        manifest entry, or its revision (from the content itself) is withdrawn."""
        name = os.path.basename(path)
        if problems := await self._checked(content, name):
            _LOGGER.error("Refused to write %s: %s", path, "; ".join(problems[:3]))
            raise GuardRefused(path)
        if (name, revision := effective_revision(content)) in self.withdrawn:
            _LOGGER.error("Refused to write %s: revision %s is withdrawn", path, revision)
            raise GuardRefused(path, WITHDRAWN_REVISION)

    async def _write(self, path: str, content: bytes, expected: str | None = None) -> bool:
        """Write content into the custom quirks folder: a new file (expected None) or in place of the
        file with the sha256 expected (False while it has another). Every write of new content goes
        through here (only the undo of a list puts back bytes the same list took away): content the
        guard refuses for the file's manifest entry or of a withdrawn revision is never written
        (GuardRefused)."""
        await self._refuse(path, content)
        if expected is None:
            await self.hass.async_add_executor_job(files.write_new, path, content)
            return True
        return await self.hass.async_add_executor_job(files.replace, path, content, expected)

    def _record(self, name: str, content: bytes) -> dict[str, Any]:
        """The record of a file written from the state in use: with the names of its version (for a
        version that takes names over from ZHA's own quirk, those names too: plan.names_of), its status
        and its risk (an update that raises it says so in the change list)."""
        entry = self._entry(name)
        return {"sha256": sha256(content), "revision": self.source.revisions[name], "names": names_of(entry), "status": entry.get("status"), "risk": risk(entry)}

    async def _read_ours(self, path: str, sha: str) -> bytes:
        """The content of a file of ours while it has the sha256 the plan saw (Changed otherwise)."""
        content = await self.hass.async_add_executor_job(files.read_if, path, sha)
        if content is None:
            raise Changed(path)
        return content

    async def _saved(self, path: str, record: dict[str, Any] | None) -> None:
        """Set (or, with None, drop) the record of path and save it, before the file changes: after a
        crash the record still names what is on disk (the version before stays as previous)."""
        if record is None:
            self.data["installed"].pop(path, None)
        else:
            self.data["installed"][path] = record
        await self._store.async_save(self.data)

    async def _do(self, step: Step) -> None:
        installed = self.data["installed"]
        if step.kind == "remove":
            if not await self.hass.async_add_executor_job(files.delete, step.path, step.record["sha256"]):
                raise Changed(step.path)
            del installed[step.path]
            if os.path.dirname(step.path) == self.folder:
                self._pending(step.name, DONE[step.kind])
            return
        record = self._record(step.name, step.new)
        await self._refuse(step.path, step.new)
        before = installed.get(step.path)
        await self._saved(step.path, {**record, "previous": step.record} if step.record else record)
        try:
            if not await self._write(step.path, step.new, step.record["sha256"] if step.record else None):
                raise Changed(step.path)
        except BaseException:
            # The write failed, or Home Assistant cancelled the apply (it cancels running tasks at
            # the end of a stop): the record is what it was before the step. After a cancellation the
            # thread may still finish the write; the file then counts as changed and is left alone.
            self._put_back(step.path, before)
            raise
        installed[step.path] = record
        self.data["forgotten"].pop(step.path, None)
        self._pending(step.name, DONE[step.kind])

    def _put_back(self, path: str, record: dict[str, Any] | None) -> None:
        if record is None:
            self.data["installed"].pop(path, None)
        else:
            self.data["installed"][path] = record

    async def _undo(self, step: Step) -> None:
        """Put back what a step changed: only bytes the same list took away, each while the file has
        what the step left there (no guard: nothing new reaches the folder)."""
        installed, run = self.data["installed"], self.hass.async_add_executor_job
        if step.kind == "install":
            if not await run(files.delete, step.path, sha256(step.new)):
                raise Changed(step.path)
            del installed[step.path]
        elif step.kind == "update":
            current = installed[step.path]
            await self._saved(step.path, {**step.record, "previous": current})
            if not await run(files.replace, step.path, step.old, sha256(step.new)):
                installed[step.path] = current
                raise Changed(step.path)
            installed[step.path] = step.record
        else:
            await self._saved(step.path, step.record)
            try:
                await run(files.write_new, step.path, step.old)
            except BaseException:
                installed.pop(step.path, None)
                raise

    async def async_apply(self, key: str) -> Applied:
        """Carry out the change list the dialog showed (key: its id) as a whole: removals, updates,
        installs. Nothing is written before every file is read and every new version fetched and
        checked; a failed step undoes the steps done before it."""
        async with self._lock:
            await self._async_refresh()
            plan = self.plan
            if plan.held or self.folder is None:
                return Applied(held=plan.held or NO_FOLDER)
            if not plan.changes or plan.key != key:
                return Applied(stale=True)
            applied, name = Applied(), ""
            pending = list(self.data["pending"]["changes"])
            # The refresh above settled the records an apply stopped by a crash left with a previous
            # version: each file of the list has the sha256 of its record.
            installed = self.data["installed"]
            steps: list[Step] = []
            done: list[Step] = []
            try:
                try:
                    for removal in plan.remove:
                        name = removal.name
                        old = await self._read_ours(removal.path, removal.before)
                        steps.append(Step("remove", removal.path, old=old, record=installed[removal.path]))
                    for update in plan.update:
                        name = update.name
                        new = await self._read_offered(name)
                        await self._refuse(update.path, new)
                        old = await self._read_ours(update.path, update.before)
                        steps.append(Step("update", update.path, old=old, new=new, record=installed[update.path]))
                    for install in plan.install:
                        name, path = install.name, os.path.join(self.folder, install.name)
                        new = await self._read_offered(name)
                        await self._refuse(path, new)
                        steps.append(Step("install", path, new=new))
                    for step in steps:
                        name = step.name
                        await self._do(step)
                        done.append(step)
                        # Saved per step: after a crash the records still say what is on disk.
                        await self._store.async_save(self.data)
                except Exception as err:  # noqa: BLE001 - whatever stopped a step, the steps done are undone
                    _LOGGER.error("Change list: %s failed: %s", name, _why(err), exc_info=not isinstance(err, (Changed, GuardRefused, remote.FetchError, OSError)))
                    if isinstance(err, remote.BadTag) and name in self.source.shas:
                        # Asking again does not help: the next list goes on without this file.
                        self._unavailable[self._download_key(name)] = str(err)
                    applied.failed = f"`{name}`: {_why(err)}"
                    left = await self._undo_all(done)
                    self.data["pending"]["changes"] = pending
                    for step in left:
                        self._pending(step.name, DONE[step.kind])
                    applied.left = [f"`{step.name}`: {DONE[step.kind]}" for step in left]
                else:
                    applied.done = [f"`{step.name}`: {DONE[step.kind]}" for step in steps]
                    ir.async_delete_issue(self.hass, DOMAIN, f"changes_{key}")
            finally:
                await self._store.async_save(self.data)
                await self._async_refresh()
            return applied

    async def _undo_all(self, done: list[Step]) -> list[Step]:
        """Undo the steps done, newest first; the steps that could not be undone."""
        left = []
        for step in reversed(done):
            try:
                await self._undo(step)
            except Exception as err:  # noqa: BLE001 - the next step back is still tried
                _LOGGER.error("Change list: cannot undo the %s of %s: %s", step.kind, step.path, _why(err))
                left.append(step)
        return left

    @callback
    def async_reload_zha(self) -> bool:
        """Reload ZHA so it loads the custom quirks folder again (right after a confirmed change).

        False when ZHA is not loaded: the change waits for its next start, the reminder says so."""
        entries = self.hass.config_entries.async_loaded_entries(ZHA_DOMAIN)
        for entry in entries:
            self.hass.config_entries.async_schedule_reload(entry.entry_id)
        if entries:
            self._reload_requested = True
            self._sync_issues({}, only=("reload",))
        return bool(entries)

    # Tuya data queries

    @callback
    def _query_tuya_devices(self) -> None:
        """Send one Tuya data query to each Tuya device that runs a file ZHA loaded new or updated.

        Called right after a refresh read what ZHA applies, so self.devices is current. A device is
        asked when ZHA reports that it runs the file, it is not left out (disabled or excluded in the
        options), the quirk ZHA applied gives it the Tuya data query and ZHA reports it available. Any
        kind of file counts, an alias file too: the quirk decides. A device on another quirk is never
        asked, one without a Tuya MCU cluster is not listed either. The files are due once: a device
        that misses the query is not asked again.
        """
        if not self._query_due:
            return
        names, self._query_due = self._query_due, set()
        due = {stem(name): name for name in names}
        excluded = frozenset(self.entry.options.get(CONF_EXCLUDED, ()))
        wanted = {
            self.ieees[device_id]: (due[device.quirk], device)
            for device_id, device in self.devices.items()
            if device.quirk in due and not device.disabled and device_id not in excluded and device_id in self.ieees
        }
        if not wanted:
            return
        try:
            found = {str(proxy.device.ieee): proxy.device for proxy in self.hass.data[ZHA_DOMAIN].gateway_proxy.device_proxies.values()}
        except (AttributeError, KeyError, TypeError):
            _LOGGER.debug("No Tuya data query: cannot read ZHA's devices", exc_info=True)
            return
        # What became of each device, per file (the devices by manufacturer and model only: people
        # share diagnostics in public issues).
        stamp = dt_util.utcnow().isoformat(timespec="seconds")
        results: dict[str, list[str]] = {}
        targets = []
        for ieee, (name, device) in sorted(wanted.items()):
            # The refresh read the quirk of each device in self.devices from these devices just now.
            zha_device = found.get(ieee)
            if not tuya_clusters(zha_device):
                # Not a Tuya MCU device: nothing to ask, nothing to list.
                continue
            label = f"{device.manufacturer} {device.model}"
            if name not in results:
                results[name] = []
                self.queries[name] = {"time": stamp, "devices": results[name]}
            if (cluster := query_cluster(zha_device)) is None:
                why = "its quirk has no Tuya data query"
            elif not getattr(zha_device, "available", False):
                why = "ZHA reports it unavailable"
            else:
                targets.append((cluster, ieee, name, label, results[name]))
                continue
            _LOGGER.debug("No Tuya data query to %s for %s: %s", ieee, name, why)
            results[name].append(f"{label}: skipped, {why}")
        if targets:
            self.entry.async_create_background_task(self.hass, self._async_query(targets), "xquirks Tuya data query")

    async def _async_query(self, targets: list[tuple[Any, str, str, str, list[str]]]) -> None:
        """Send the data queries, one device after the other: (cluster, IEEE, file, label, results).

        The device answers with its datapoints, not with a reply to the query: none is awaited, zigpy
        waits only until the frame is sent (and tries again when that fails, as for any request).
        A sleepy battery device may miss it: it shows its values when it next reports.
        """
        for cluster, ieee, name, label, results in targets:
            try:
                await cluster.command(TUYA_QUERY_DATA, expect_reply=False)
            except Exception as err:  # noqa: BLE001 - best effort: whatever went wrong, the next device is asked
                why = str(err) or type(err).__name__
                _LOGGER.debug("Tuya data query to %s for %s not delivered: %s", ieee, name, why)
                results.append(f"{label}: not delivered ({why})")
            else:
                _LOGGER.debug("Sent a Tuya data query to %s for %s", ieee, name)
                results.append(f"{label}: sent")

    async def async_clean_temp(self) -> None:
        if folder := zha_folder(self.hass):
            async with self._lock:
                await self.hass.async_add_executor_job(files.remove_stale_temp, folder)

    # Diagnostics

    async def async_diagnostics(self) -> dict[str, Any]:
        return self.summary() | {"offered_changes": await self._change_summaries()}

    def _content_summary(self) -> dict[str, Any]:
        state = self.state
        return {
            "in_use": state.tag if state else None,
            "state": {"commit": state.commit, "homeassistant": state.homeassistant, "files": len(state.shas), "sources": state.sources} if state else None,
            "last_check": self.last_check,
            "skipped_tags": dict(sorted(self._skipped().items())),
            "guard": self.guard.id if self.guard else None,
            "withdrawn_revisions": len(self.withdrawn),
            "withdrawn_by_a_newer_tag": len(self.newer_withdrawn),
            "pictures": {"on_disk": len(self.pictures.cached), "failed": sorted(self.pictures.failed)} if self.pictures else None,
        }

    def summary(self) -> dict[str, Any]:
        """The state for diagnostics."""
        plan = self.plan
        states = {}
        for label, items in (("update in the change list", plan.update), ("removal in the change list", plan.remove), ("installed, not applied by ZHA", plan.not_applied)):
            for item in items:
                states[item.path] = label
        for path in plan.changed:
            states[path] = "changed by you, left alone"
        for path in plan.unreadable:
            states[path] = "cannot be read, left alone"
        installed = {}
        for path, record in sorted(self.data["installed"].items()):
            name = os.path.basename(path)
            claimed = claimed_by(record["names"], self.devices)
            # Device names stay out: people share diagnostics in public issues.
            installed[path] = {
                "state": states.get(path, "installed"),
                "claims": sorted(f"{d.manufacturer} {d.model}" for i, d in self.devices.items() if i in claimed),
                "active_for": sorted(f"{d.manufacturer} {d.model}" for d in self.devices.values() if d.quirk == stem(name)),
                "revision": record["revision"],
                "offered_revision": self.source.revisions.get(name),
                "unchanged_on_disk": self._disk.get(path) == record["sha256"],
            }
        other = {f"{self.devices[i].manufacturer} {self.devices[i].model}": self.devices[i].quirk for b in plan.blocked for i in b.devices}
        return {
            "folder": self.folder,
            "zha": self.zha_state,
            "problem": self.problem,
            "content": self._content_summary(),
            "zha_devices": len(self.devices),
            "zha_quirks_known": self.zha_state == ZHA_LOADED,
            "unknown_quirk_devices": sorted(f"{d.manufacturer} {d.model}" for d in self.devices.values() if d.quirk is None),
            "devices_left_alone": len(self.entry.options.get(CONF_EXCLUDED, ())),
            "installed": installed,
            "change_list": {
                "held": plan.held,
                "id": plan.key if plan.changes else None,
                "remove": {c.path: c.reason for c in plan.remove},
                "update": [c.name for c in plan.update],
                "install": [c.name for c in plan.install],
            },
            "target": sorted(plan.target),
            "devices_on_other_custom_quirks": other,
            # Shipped files whose endpoints a device does not fit, with why (no device names).
            "devices_that_do_not_fit": {m.name: sorted(f"{self.devices[i].manufacturer} {self.devices[i].model}: {why}" for i, why in m.devices if i in self.devices)
                                        for m in plan.misfits},
            "files_of_yours_under_offered_names": plan.users_files,
            "withdrawn_copies": dict(plan.withdrawn_copies),
            # Files the guard refused: never written.
            "refused_by_the_guard": {name: {**refusal, "problems": list(refusal["problems"] or ())} for name, refusal in sorted(self.refused.items())},
            "waiting_for_the_check": dict(sorted(self._unchecked.items())),
            "cannot_be_downloaded": {name: error for name in plan.refused if (error := self.unavailable(name))},
            "pending_zha_reload": [f"{c['file']}: {c['change']}" for c in self.data["pending"]["changes"]],
            # The Tuya data queries after ZHA loaded a file the list installed or updated (this run).
            "tuya_data_queries": dict(sorted(self.queries.items())),
        }
