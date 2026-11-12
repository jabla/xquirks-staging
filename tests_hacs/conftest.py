"""Fixtures: a small repository with content-<n> tags, a stand-in for ZHA, ZHA devices in the device registry."""

from __future__ import annotations

import ast
import hashlib
import json
import re
import string
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from homeassistant.components.zha.helpers import HAZHAData
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.setup import async_setup_component
from pytest_homeassistant.common import MockConfigEntry, MockModule, mock_integration
from pytest_homeassistant.test_util.aiohttp import AiohttpClientMockResponse
from yarl import URL

from .integration import DOMAIN, const, content, guard

STRINGS = json.loads((Path(__file__).resolve().parents[1] / "custom_components" / DOMAIN / "strings.json").read_text())
# The guard this release ships: content tags name it in content.json.
GUARD_ID = guard.Guard.load().id


def content_json(guard_id: str | None = GUARD_ID) -> bytes:
    """content.json of a tag built for this release (another guard where given)."""
    return json.dumps({"guard": guard_id} if guard_id else {}).encode()

UPSTREAM_PR = {"author": "someone", "number": 4242, "title": "Add A", "url": "https://github.com/zigpy/zha-device-handlers/pull/4242"}

MANIFEST = {
    "tuya_a": {
        "file": "quirks/z2m_tuya_a.py",
        "fingerprints": [["_TZE200_aaaa", "TS0601"]],
        "claimed_elsewhere": [],
        "vendor": "Tuya",
        "model": "A",
        "status": "generated",
        "path": "tuya",
        "upstream_open_prs": [UPSTREAM_PR],
    },
    "acme_b": {"file": "quirks/z2m_acme_b.py", "fingerprints": [[None, "B-1"]], "claimed_elsewhere": [["Other", "B-1"]], "vendor": "Acme", "model": "B-1", "status": "verified", "path": "zcl"},
    "acme_c": {"file": "quirks/z2m_acme_c.py", "fingerprints": [["Acme", "C-1"]], "claimed_elsewhere": [], "vendor": "Acme", "model": "C-1", "status": "generated", "path": "zcl"},
    "acme_d": {"file": None, "fingerprints": [["Acme", "D-1"]], "vendor": "Acme", "model": "D-1", "status": "generated", "path": "zcl", "not_built": "endpoint unclear"},
}


def quirk_revision(slug: str, version: int = 1, entry: dict | None = None) -> str:
    return hashlib.sha256(_quirk_body(slug, version, entry).encode()).hexdigest()[:8]


def take_over_filter() -> str:
    """The upstream-first filter of a file that takes names over from ZHA's own quirk, as
    fixed_code.json of this release holds it."""
    fixed = json.loads((Path(__file__).resolve().parents[1] / "custom_components" / DOMAIN / guard.FIXED_CODE).read_text())
    text = fixed["take_over"][0]
    node = next(n for n in ast.parse(text).body if isinstance(n, ast.FunctionDef) and n.name == "no_builtin_quirk")
    return ast.get_source_segment(text, node) + "\n"


def _quirk_body(slug: str, version: int, entry: dict | None = None) -> str:
    entry = MANIFEST.get(slug, {}) if entry is None else entry
    # The guard wants CLAIMED_ELSEWHERE as the manifest entry has it. It wants the take-over filter
    # exactly in a file whose entry has over_zha.
    claimed = {tuple(pair) for pair in entry.get("claimed_elsewhere", [])}
    literal = f"CLAIMED_ELSEWHERE = {sorted(claimed)!r}\n" if claimed else ""
    if entry.get("endpoints"):
        # The guard wants ENDPOINTS as the manifest entry has them.
        endpoints = {int(ep): tuple(ids) for ep, ids in entry["endpoints"].items()}
        literal += f"ENDPOINTS = {endpoints!r}\n"
    if entry.get("over_zha") is not None:
        literal += take_over_filter()
    return f'"""Quirk {slug}.\n\nStatus: generated.\n"""\n# version {version}\n{literal}'


def quirk_text(slug: str, version: int = 1, entry: dict | None = None) -> bytes:
    """A quirk file with its Revision line, as the file states it (entry: its manifest
    entry when it is not the one in MANIFEST)."""
    head, tail = _quirk_body(slug, version, entry).split("Status: generated.\n")
    return f"{head}Status: generated.\nRevision: {quirk_revision(slug, version, entry)}\n{tail}".encode()


def write_repo(folder: Path, manifest: dict | None = None, version: int = 1) -> Path:
    """The repository's working tree: manifest.json (without hashes) and the files it ships."""
    manifest = MANIFEST if manifest is None else manifest
    (folder / "quirks").mkdir(parents=True, exist_ok=True)
    for old in (folder / "quirks").glob("*.py"):
        old.unlink()
    (folder / "manifest.json").write_text(json.dumps(manifest))
    for slug, entry in manifest.items():
        if entry.get("file"):
            # An entry with over_zha gets a file with the take-over filter, one with endpoints its ENDPOINTS;
            # the others as MANIFEST has them.
            own = entry.get("over_zha") is not None or bool(entry.get("endpoints"))
            (folder / entry["file"]).write_bytes(quirk_text(slug, version, entry if own else None))
    return folder


def tag_files(folder: Path) -> dict[str, bytes]:
    """What a content tag of the working tree holds: the manifest with each file's sha256 and
    revision (as content tags hold them), the files, hacs.json, content.json, withdrawn.toml."""
    manifest = json.loads((folder / "manifest.json").read_text())
    found = {}
    for slug, entry in manifest.items():
        if entry.get("file"):
            data = (folder / entry["file"]).read_bytes()
            found[entry["file"]] = data
            manifest[slug] = {**entry, "sha256": content.sha256(data), "revision": content.effective_revision(data)}
    found["manifest.json"] = json.dumps(manifest).encode()
    defaults = {"hacs.json": b'{"name": "xquirks", "homeassistant": "2026.1.0"}', "content.json": content_json(), "data/withdrawn.toml": b""}
    for name, default in defaults.items():
        path = folder / name
        found[name] = path.read_bytes() if path.is_file() else default
    return found


def load_state(folder: Path, tag: str = "content-1") -> content.ContentState:
    """The content state a tag of the working tree in folder would be."""
    found = tag_files(folder)
    return content.from_manifest(json.loads(found["manifest.json"]), tag=tag, content=int(tag.rsplit("-", 1)[1]), homeassistant=None, withdrawn={})


RAW = re.compile("^" + re.escape(const.RAW_URL.split("{commit}")[0]) + r"([0-9a-f]{40})/(.+)$")


def fake_sha(*parts: object) -> str:
    return hashlib.sha1("/".join(map(str, parts)).encode()).hexdigest()


class Repo:
    """The repository as the integration reads it, served through aioclient_mock: the content-<n>
    tags (each a snapshot of the working tree in folder on a commit of its own) with conditional
    requests by ETag. Files are served by commit only, as raw.githubusercontent.com serves them."""

    def __init__(self, mock, folder: Path) -> None:
        self.mock = mock
        self.folder = folder
        self.tags: dict[int, dict[str, bytes]] = {}
        # Tag number -> commit, for a tag moved to another commit (a re-created repository).
        self.moved: dict[int, str] = {}
        self.register()

    def register(self) -> None:
        """Serve the repository (again: clear_requests() in a test drops it)."""
        self.mock.get(const.TAGS_URL, side_effect=self._tag_list)
        self.mock.get(RAW, side_effect=self._raw)

    def commit(self, number: int) -> str:
        """The commit content-<number> points to."""
        return self.moved.get(number) or fake_sha(self.folder, "commit", number)

    def ref(self, number: int) -> dict:
        """content-<number> as GitHub's matching-refs lists it."""
        return {"ref": f"refs/tags/content-{number}", "object": {"sha": self.commit(number), "type": "commit"}}

    @property
    def etag(self) -> str:
        moved = f"-{fake_sha(sorted(self.moved.items()))[:8]}" if self.moved else ""
        return f'"tags-{max(self.tags, default=0)}{moved}"'

    def publish(self) -> str:
        """The working tree as the next content tag."""
        number = max(self.tags, default=0) + 1
        self.tags[number] = tag_files(self.folder)
        return f"content-{number}"

    def publish_if_changed(self) -> None:
        if not self.tags or self.tags[max(self.tags)] != tag_files(self.folder):
            self.publish()

    async def _tag_list(self, method, url, data):
        headers = self.mock.mock_calls[-1][3] or {}
        if headers.get("If-None-Match") == self.etag:
            return AiohttpClientMockResponse(method, URL(url), status=304)
        refs = [self.ref(n) for n in sorted(self.tags)] + [{"ref": "refs/tags/content-x", "object": {"sha": "0" * 40, "type": "commit"}}]
        return AiohttpClientMockResponse(method, URL(url), json=refs, headers={"ETag": self.etag})

    async def _raw(self, method, url, data):
        match = RAW.match(str(url))
        number = next((n for n in self.tags if self.commit(n) == match.group(1)), None)
        found = self.tags.get(number, {}).get(match.group(2))
        if found is None:
            return AiohttpClientMockResponse(method, URL(url), status=404)
        if isinstance(found, int):
            # A test's stand-in for a server error on this file.
            return AiohttpClientMockResponse(method, URL(url), status=found)
        return AiohttpClientMockResponse(method, URL(url), response=found)


REPOS: dict[Path, Repo] = {}


@contextmanager
def published(repo_dir: Path):
    """Publish the working tree as the next content tag when it changed."""
    REPOS[repo_dir].publish_if_changed()
    yield


@pytest.fixture(autouse=True)
def config_dir(hass: HomeAssistant, tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A config folder of the test's own (outside tmp_path)."""
    folder = tmp_path_factory.mktemp("config")
    hass.config.config_dir = str(folder)
    return folder


def render(template: str, placeholders: dict | None) -> str:
    """Fill a translation like the frontend does; KeyError when a placeholder is missing."""
    return template.format(**(placeholders or {}))


@pytest.fixture(autouse=True)
def issues_render(hass: HomeAssistant):
    """Every issue a test leaves behind has a translation that renders with its placeholders."""
    yield
    for (domain, _issue_id), issue in ir.async_get(hass).issues.items():
        if domain == DOMAIN and issue.active:
            strings = STRINGS["issues"][issue.translation_key]
            render(strings["title"], issue.translation_placeholders)
            if not issue.is_fixable:
                render(strings["description"], issue.translation_placeholders)
            assert (issue.data or {}).get("kind") == issue.translation_key


def issues_of(hass: HomeAssistant, kind: str) -> list[ir.IssueEntry]:
    return sorted((issue for issue in our_issues(hass).values() if issue.translation_key == kind), key=lambda issue: issue.issue_id)


def manager_of(hass: HomeAssistant):
    """The loaded integration's manager."""
    return hass.config_entries.async_loaded_entries(DOMAIN)[0].runtime_data


def listed(hass: HomeAssistant) -> dict[str, list[str]]:
    """What the change list the user sees does: file names per kind (empty without a visible list)."""
    if not issues_of(hass, "changes"):
        return {"remove": [], "update": [], "install": []}
    plan = manager_of(hass).plan
    return {
        "remove": sorted(c.name for c in plan.remove),
        "update": sorted(c.name for c in plan.update),
        "install": sorted(c.name for c in plan.install),
    }


def offered(hass: HomeAssistant) -> list[str]:
    """Files the visible change list installs."""
    return listed(hass)["install"]


async def apply_list(hass: HomeAssistant, expect: tuple[str, ...] = ("done", "done_zha_not_loaded")) -> dict:
    """Confirm the visible change list: the dialog's "Apply all"; the abort it ends with."""
    from homeassistant.data_entry_flow import FlowResultType

    flow = await start_fix(hass, issue_of(hass, "changes"))
    assert flow["type"] is FlowResultType.MENU and flow["menu_options"] == ["apply", "not_now"], flow
    flow = await continue_fix(hass, flow, {"next_step_id": "apply"})
    assert flow["type"] is FlowResultType.ABORT and flow["reason"] in expect, flow
    await hass.async_block_till_done(wait_background_tasks=True)
    return flow


@pytest.fixture
def repo(tmp_path: Path, aioclient_mock):
    """The repository; setup_entry publishes its working tree as content-1."""
    found = Repo(aioclient_mock, write_repo(tmp_path / "repo"))
    REPOS[found.folder] = found
    yield found
    REPOS.pop(found.folder, None)


@pytest.fixture
def repo_dir(repo: Repo) -> Path:
    """The repository's working tree: setup_entry and restarts publish what it holds then."""
    return repo.folder


@pytest.fixture
def quirks_dir(tmp_path: Path) -> Path:
    folder = tmp_path / "custom_zha_quirks"
    folder.mkdir()
    return folder


# zha's quirk_class for a device without a quirk: its zigpy class path.
NO_QUIRK = "zigpy.device.Device"


@dataclass
class Zha:
    """The parts of ZHA the integration reads: its YAML config, its gateway, its devices.

    The gateway is loaded and knows every device added here, without a quirk, until
    apply_quirks says otherwise or a reload starts.
    """

    hass: HomeAssistant
    entry: MockConfigEntry
    data: HAZHAData
    quirks: dict[str, str] = field(default_factory=dict)  # ieee -> quirk_class
    # ZHA reloads asked for (async_schedule_reload of its entry). The stand-in only counts them: a
    # test plays the reload with start_reload, apply_quirks and finish_reload.
    reloads: int = 0
    sources: dict[str, str] = field(default_factory=dict)  # ieee -> source file of the applied quirk
    # ieee -> (manufacturer, model) of the zigpy device where it differs from the device registry's
    # (a quirk's friendly name changes only the registry's).
    zigpy: dict[str, tuple[str, str]] = field(default_factory=dict)
    # ieee -> zigpy's original signature of the device (endpoints as it joined)
    signatures: dict[str, dict] = field(default_factory=dict)

    def add_device(self, ieee: str, manufacturer: str, model: str, name: str | None = None) -> str:
        device = dr.async_get(self.hass).async_get_or_create(
            config_entry_id=self.entry.entry_id,
            identifiers={("zha", ieee)},
            manufacturer=manufacturer,
            model=model,
            name=name or f"{manufacturer} {model}",
        )
        self.quirks.setdefault(ieee, NO_QUIRK)
        self._publish()
        return device.id

    def remove_device(self, device_id: str) -> None:
        device = dr.async_get(self.hass).async_get(device_id)
        for domain, ieee in device.identifiers:
            if domain == "zha":
                self.quirks.pop(ieee, None)
        dr.async_get(self.hass).async_remove_device(device_id)
        self._publish()

    def apply_quirks(self, quirks: dict[str, str], sources: dict[str, str] | None = None) -> None:
        """ZHA applied these quirks (ieee -> quirk_class; NO_QUIRK for none), from these source files
        (ieee -> path; without one the device has no registry entry the integration can read)."""
        self.quirks.update(quirks)
        self.sources.update(sources or {})
        self._publish()

    def _publish(self) -> None:
        if self.entry.state is ConfigEntryState.LOADED:
            proxies = {ieee: SimpleNamespace(device=self._device(ieee, quirk)) for ieee, quirk in self.quirks.items()}
            self.data.gateway_proxy = SimpleNamespace(device_proxies=proxies)

    def _device(self, ieee: str, quirk: str) -> SimpleNamespace:
        device = SimpleNamespace(ieee=ieee, quirk_class=quirk, quirk_applied=":" in quirk)
        zigpy_device = SimpleNamespace()
        if ieee in self.sources:
            zigpy_device._quirk_registry_entry = SimpleNamespace(source=SimpleNamespace(file=self.sources[ieee], module=quirk.split(":", 1)[0]))
        if ieee in self.zigpy:
            zigpy_device.manufacturer, zigpy_device.model = self.zigpy[ieee]
        if ieee in self.signatures:
            zigpy_device.original_signature = self.signatures[ieee]
        if vars(zigpy_device):
            device.device = zigpy_device
        return device

    def schedule_reload(self, entry_id: str) -> None:
        """A reload of ZHA the integration asked for."""
        self.reloads += 1

    def start_reload(self) -> None:
        """ZHA unloads (a reload or a setup retry): no gateway until finish_reload."""
        self.entry.mock_state(self.hass, ConfigEntryState.NOT_LOADED)
        self.data.gateway_proxy = None
        async_dispatcher_send(self.hass, "config_entry_changed", "updated", self.entry)

    def begin_setup(self) -> None:
        """ZHA's setup starts: it loads the custom quirks folder now, before it is loaded."""
        self.entry.mock_state(self.hass, ConfigEntryState.SETUP_IN_PROGRESS)
        async_dispatcher_send(self.hass, "config_entry_changed", "updated", self.entry)

    def finish_reload(self) -> None:
        """ZHA is loaded again (its setup starts here unless begin_setup came first)."""
        if self.entry.state is not ConfigEntryState.SETUP_IN_PROGRESS:
            self.begin_setup()
        self.entry.mock_state(self.hass, ConfigEntryState.LOADED)
        self._publish()
        async_dispatcher_send(self.hass, "config_entry_changed", "updated", self.entry)

    def reload(self, quirks: dict[str, str] | None = None) -> None:
        """A whole reload of ZHA that applies these quirks (ieee -> quirk_class) afterwards."""
        self.start_reload()
        self.quirks.update(quirks or {})
        self.finish_reload()


@pytest.fixture
async def zha(hass: HomeAssistant, quirks_dir: Path):
    """ZHA stand-in: keeps its YAML config in hass.data like the real async_setup does."""

    async def async_setup(hass: HomeAssistant, config: dict) -> bool:
        hass.data["zha"] = HAZHAData(yaml_config=config.get("zha", {}))
        return True

    mock_integration(hass, MockModule("zha", async_setup=async_setup))
    assert await async_setup_component(hass, "zha", {"zha": {"custom_quirks_path": str(quirks_dir)}})
    entry = MockConfigEntry(domain="zha")
    entry.add_to_hass(hass)
    entry.mock_state(hass, ConfigEntryState.LOADED)
    zha = Zha(hass, entry, hass.data["zha"])
    zha._publish()
    schedule_reload = hass.config_entries.async_schedule_reload

    def reload(entry_id: str) -> None:
        if entry_id == entry.entry_id:
            zha.schedule_reload(entry_id)
        else:
            schedule_reload(entry_id)

    with patch.object(hass.config_entries, "async_schedule_reload", reload):
        yield zha


async def setup_entry(hass: HomeAssistant, repo_dir: Path, options: dict | None = None, *, publish: bool = True) -> MockConfigEntry:
    """Set the integration up with the working tree in repo_dir published (unless publish is
    False); its first check ran."""
    assert await async_setup_component(hass, "repairs", {})
    entry = MockConfigEntry(domain=DOMAIN, options=options or {})
    entry.add_to_hass(hass)
    if publish:
        REPOS[repo_dir].publish_if_changed()
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done(wait_background_tasks=True)
    return entry


def our_issues(hass: HomeAssistant) -> dict[str, ir.IssueEntry]:
    """The issues the user sees in Repairs: active and not ignored."""
    return {issue_id: issue for (domain, issue_id), issue in ir.async_get(hass).issues.items() if domain == DOMAIN and issue.active and issue.dismissed_version is None}


def issue_of(hass: HomeAssistant, kind: str, file: str | None = None) -> ir.IssueEntry:
    found = [
        issue
        for issue in our_issues(hass).values()
        if issue.translation_key == kind and (file is None or (issue.data or {}).get("file") == file or (issue.data or {}).get("path", "").endswith("/" + file))
    ]
    assert len(found) == 1, our_issues(hass)
    return found[0]


def check_flow_texts(kind: str, result: dict) -> dict:
    """The step or abort text of a fix flow result renders with the placeholders it got."""
    flow = STRINGS["issues"][kind]["fix_flow"]
    if result["type"] in ("form", "menu"):
        step = flow["step"][result["step_id"]]
        render(step["description"], result["description_placeholders"])
        for option in result.get("menu_options", []):
            assert option in step["menu_options"]
        if result["type"] == "form" and result.get("data_schema"):
            for field_name in result["data_schema"].schema:
                assert str(field_name) in step["data"]
        # No placeholder handed to a step goes unused: each one is there for the text.
        unused = set(result.get("description_placeholders") or {}) - {name for name in _fields(step["description"])}
        assert not unused, unused
    elif result["type"] == "abort":
        render(flow["abort"][result["reason"]], result["description_placeholders"])
    return result


def _fields(template: str) -> set[str]:
    return {name for _literal, name, _spec, _conv in string.Formatter().parse(template) if name}


async def start_fix(hass: HomeAssistant, issue: ir.IssueEntry) -> dict:
    result = await hass.data["repairs"]["flow_manager"].async_init(DOMAIN, context={"issue_id": issue.issue_id})
    result["kind"] = issue.translation_key
    return check_flow_texts(issue.translation_key, result)


async def continue_fix(hass: HomeAssistant, flow: dict, user_input: dict | None = None) -> dict:
    result = await hass.data["repairs"]["flow_manager"].async_configure(flow["flow_id"], user_input)
    result["kind"] = flow["kind"]
    return check_flow_texts(flow["kind"], result)
