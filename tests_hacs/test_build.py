"""tools/build_integration.py (the release zip), the repository's metadata, the parsers of a content
tag's metadata on synthetic content and frozen real manifest entries."""

from __future__ import annotations

import importlib.util
import json
import re
import zipfile
from pathlib import Path

import pytest

from .conftest import content_json, tag_files, write_repo
from .integration import content, guard

ROOT = Path(__file__).resolve().parents[1]


def load_builder():
    spec = importlib.util.spec_from_file_location("build_integration", ROOT / "tools" / "build_integration.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_content_metadata_parses():
    """content.json names the guard a content tag was built for, hacs.json the Home Assistant release
    its files need (the integration's own hacs.json has the same key)."""
    assert content.parse_guard(content_json().decode()) == guard.Guard.load().id
    assert content.parse_guard(content_json(None).decode()) is None
    assert content.parse_guard('{"guard": "not a guard id"}') is None
    assert content.parse_homeassistant((ROOT / "hacs.json").read_text())
    assert content.parse_homeassistant('{"name": "xquirks"}') is None
    with pytest.raises(content.BadContent):
        content.parse_homeassistant('{"homeassistant": 2026}')


def release(text: str) -> tuple[int, int, int]:
    """(year, month, patch) of a Home Assistant release such as 2026.11.0."""
    found = re.fullmatch(r"([0-9]{4})\.([0-9]{1,2})\.([0-9]+)", text)
    assert found, text
    return int(found[1]), int(found[2]), int(found[3])


def test_the_minimum_is_no_older_than_the_release_ci_tests():
    """HACS installs the integration only on the Home Assistant release hacs.json names or a newer one.
    CI tests it with Home Assistant's own test package of one release (tests_hacs/requirements.txt;
    a release that does not exist turns the check red). The minimum is never older than that
    release: the integration never installs on a release older than the one its tests ran on."""
    minimum = json.loads((ROOT / "hacs.json").read_text())["homeassistant"]
    tested = re.findall(r"^pytest-homeassistant==(\S+)$", (ROOT / "tests_hacs" / "requirements.txt").read_text(), re.MULTILINE)
    assert len(tested) == 1, tested
    assert release(tested[0]) <= release(minimum)
    # By number, not as text: 2026.9.0 is older than 2026.10.0.
    assert release("2026.9.0") < release("2026.10.0") and "2026.9.0" > "2026.10.0"


def test_withdrawn_list_is_read():
    assert content.parse_withdrawn("") == {}
    text = '[[withdrawn]]\nfile = "z2m_a_b.py"\nrevision = "1a2b3c4d"\nreason = "Wrong unit."\n'
    assert content.parse_withdrawn(text) == {("z2m_a_b.py", "1a2b3c4d"): "Wrong unit."}
    with pytest.raises(content.BadContent):
        content.parse_withdrawn('[[withdrawn]]\nfile = "../evil.py"\nrevision = "1a2b3c4d"\nreason = "x"\n')


def test_fetched_state_needs_hashes_and_revisions(tmp_path: Path):
    files = tag_files(write_repo(tmp_path))
    sources = {"zigbee-herdsman-converters": "26.1.0", "zha-device-handlers": "1d6598c"}
    manifest = {slug: {**entry, "sources": sources} for slug, entry in json.loads(files["manifest.json"]).items()}
    state = content.from_manifest(manifest, tag="content-3", content=3, homeassistant="2026.10.0", withdrawn={})
    shipped = [e for e in manifest.values() if e.get("file")]
    assert len(shipped) >= 2
    assert state.shas == {Path(e["file"]).name: e["sha256"] for e in shipped}
    assert state.revisions == {Path(e["file"]).name: e["revision"] for e in shipped}
    assert state.paths == {Path(e["file"]).name: e["file"] for e in shipped}
    assert state.sources == sources
    # Every shipped file has the hash the manifest states.
    for name, path in state.paths.items():
        assert content.sha256(files[path]) == state.shas[name], name
    slug = next(s for s, e in manifest.items() if e.get("file"))
    broken = {**manifest, slug: {**manifest[slug], "sha256": "not a hash"}}
    with pytest.raises(content.BadContent):
        content.from_manifest(broken, tag="content-3", content=3, homeassistant=None, withdrawn={})


# Real manifest entries, one of each kind (fixtures/README.md).
REAL_ENTRIES = json.loads((Path(__file__).resolve().parent / "fixtures" / "manifest-kinds.json").read_text())


def test_real_manifest_entries_are_taken():
    """Frozen real entries: a zcl file with endpoints, a Tuya file that leaves a name to another file,
    alias files by target and by alias groups, a file that takes a device over, a refused take-over,
    a device not built, a file with open upstream pull requests, a new file whose picture is not
    pinned yet. A content state takes them; the guard reads each file's targets from its entry."""
    keys = {key for entry in REAL_ENTRIES.values() for key in entry}
    assert {"endpoints", "claimed_elsewhere", "target", "aliases", "over_zha", "swap", "not_built", "upstream_open_prs", "picture_sha256", "sources"} <= keys
    assert any(not entry.get("file") and entry.get("swap") for entry in REAL_ENTRIES.values())
    assert {type(entry.get("picture_sha256")) for entry in REAL_ENTRIES.values()} == {str, type(None)}
    state = content.from_manifest(REAL_ENTRIES, tag="content-3", content=3, homeassistant="2026.11.0", withdrawn={})
    files = {Path(entry["file"]).name: entry for entry in REAL_ENTRIES.values() if entry.get("file")}
    assert len(files) == 7
    assert state.shas == {name: entry["sha256"] for name, entry in files.items()}
    assert state.revisions == {name: entry["revision"] for name, entry in files.items()}
    assert state.sources == next(iter(REAL_ENTRIES.values()))["sources"]
    for name, entry in files.items():
        assert guard.Targets.of(entry) is not None, name


def test_release_zip_has_the_integration_at_its_root(tmp_path: Path):
    builder = load_builder()
    folder = builder.integration_folder()
    path = builder.write_zip(folder, tmp_path / "dist", "1.2.3")
    assert path.name == json.loads((ROOT / "hacs.json").read_text())["filename"]
    with zipfile.ZipFile(path) as archive:
        names = set(archive.namelist())
        manifest = json.loads(archive.read("manifest.json"))
        shipped = guard.identity(archive.read("guard.py"), archive.read(guard.FIXED_CODE))
    assert manifest["version"] == "1.2.3"
    assert {"__init__.py", "manifest.json", "translations/en.json", "content.py", "guard.py", guard.FIXED_CODE} <= names
    # The guard of the zip is the one this integration ships: content tags name it in content.json.
    assert shipped == guard.Guard.load().id
    assert not any("__pycache__" in name for name in names)
    # Code only: the quirk files come from the content-<n> tags.
    assert not any(name.startswith(("bundle/", "quirks/", "z2m_")) for name in names)
    # The source tree keeps its version.
    assert json.loads((folder / "manifest.json").read_text())["version"] == "0.0.0"


def test_hacs_and_integration_metadata():
    builder = load_builder()
    folder = builder.integration_folder()
    manifest = json.loads((folder / "manifest.json").read_text())
    hacs = json.loads((ROOT / "hacs.json").read_text())
    assert folder.name == manifest["domain"]
    assert hacs["filename"] == f"{manifest['domain']}.zip"
    assert hacs["zip_release"] is True
    for key in ("domain", "name", "version", "documentation", "issue_tracker", "codeowners", "iot_class", "config_flow"):
        assert manifest[key], key
    assert manifest["requirements"] == []
    # strings.json and translations/en.json are the same text.
    assert (folder / "strings.json").read_text() == (folder / "translations" / "en.json").read_text()


def _strings(tree: dict, prefix: str = "") -> dict[str, str]:
    out = {}
    for key, value in tree.items():
        if isinstance(value, dict):
            out.update(_strings(value, f"{prefix}{key}."))
        else:
            out[prefix + key] = value
    return out


def test_every_translation_has_the_keys_and_placeholders_of_en():
    folder = load_builder().integration_folder() / "translations"
    english = _strings(json.loads((folder / "en.json").read_text()))
    others = sorted(path for path in folder.glob("*.json") if path.name != "en.json")
    assert others
    for path in others:
        strings = _strings(json.loads(path.read_text()))
        assert strings.keys() == english.keys(), path.name
        for key, text in english.items():
            assert set(re.findall(r"{(\w+)}", strings[key])) == set(re.findall(r"{(\w+)}", text)), f"{path.name}: {key}"


def test_release_version_must_be_x_y_z(tmp_path: Path):
    builder = load_builder()
    folder = builder.integration_folder()
    for bad in ("release-1", "x1", "1.2.0 beta", "v1.2.3", "1.2"):
        with pytest.raises(SystemExit):
            builder.write_zip(folder, tmp_path / "dist", bad)
    assert not (tmp_path / "dist").exists()


@pytest.mark.parametrize(
    "change",
    [
        {"fingerprints": None},
        {"fingerprints": [["_TZE200_aaaa"]]},
        {"fingerprints": [[None, 5]]},
        {"claimed_elsewhere": [["Other"]]},
        {"file": 5},
        {"vendor": None},
        {"model": ["A"]},
        {"status": ["generated"]},
        {"description": 5},
        {"picture": {"name": "A.png"}},
        {"upstream_open_prs": [{"url": "https://attacker.example/login"}]},
        {"upstream_open_prs": [{"number": "4242"}]},
        {"upstream_open_prs": [{"number": True}]},
        {"upstream_open_prs": {"number": 4242}},
        {"sources": []},
    ],
)
def test_manifest_entries_need_every_field_the_integration_reads(change: dict):
    entry = {"file": "quirks/z2m_tuya_a.py", "fingerprints": [["_TZE200_aaaa", "TS0601"]], "vendor": "Tuya", "model": "A", "status": "generated", "sha256": "0" * 64, "revision": "0123abcd"}
    assert content.from_manifest({"tuya_a": entry}, tag="content-3", content=3, homeassistant=None, withdrawn={}).shas
    with pytest.raises(content.BadContent, match="tuya_a"):
        content.from_manifest({"tuya_a": {**entry, **change}}, tag="content-3", content=3, homeassistant=None, withdrawn={})


def test_entries_without_a_file_need_their_fingerprints_only():
    state = content.from_manifest({"acme_d": {"file": None, "fingerprints": [["Acme", "D-1"]]}}, tag="content-3", content=3, homeassistant=None, withdrawn={})
    assert state.shas == {}
    for broken in ({"x": []}, {"x": {"file": None}}, []):
        with pytest.raises(content.BadContent):
            content.from_manifest(broken, tag="content-3", content=3, homeassistant=None, withdrawn={})
