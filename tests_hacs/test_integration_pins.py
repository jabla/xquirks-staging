"""tools/integration_pins.py: the Home Assistant release the integration's tests run on, its minimum.

The network is a fake: Home Assistant's tags, the components' manifests at a release, zha and the
test package on PyPI.
"""

from __future__ import annotations

import base64
import importlib.util
import json
import os
import re
import sys
import urllib.error
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("integration_pins", ROOT / "tools" / "integration_pins.py")
pins_tool = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pins_tool)

CORE = "https://api.github.com/repos/home-assistant/core"
RELEASE = "2026.11.1"
ZHA_URL = "https://pypi.org/pypi/zha/2.4.3/json"
REQUIREMENTS = """\
# The test harness: Home Assistant's own pytest-homeassistant of the release it tests.
pytest-homeassistant==2026.11.0
# Home Assistant's zha integration and its dependencies (usb, homeassistant_hardware, hassio), pinned as in 2026.11.0.
zha==2.4.2
zha-quirks==2.4.1
aiousbwatcher==1.1.2
serialx==1.15.1
universal-silabs-flasher==1.3.0
ha-silabs-firmware-client==0.4.0
pygbl==1.2.0
aiohasupervisor==0.8.1
"""
RAISED = """\
# The test harness: Home Assistant's own pytest-homeassistant of the release it tests.
pytest-homeassistant==2026.11.1
# Home Assistant's zha integration and its dependencies (usb, homeassistant_hardware, hassio), pinned as in 2026.11.1.
zha==2.4.3
zha-quirks==2.4.2
aiousbwatcher==1.1.2
serialx==1.15.2
universal-silabs-flasher==1.3.1
ha-silabs-firmware-client==0.4.0
pygbl==1.2.0
aiohasupervisor==0.8.2
"""
HACS = {"name": "xquirks", "homeassistant": "2026.11.0", "zip_release": True, "filename": "xquirks.zip", "hide_default_branch": True}
NEEDED = {"zha": "2.4.3", "zha-quirks": "2.4.2", "aiousbwatcher": "1.1.2", "serialx": "1.15.2", "universal-silabs-flasher": "1.3.1",
          "ha-silabs-firmware-client": "0.4.0", "pygbl": "1.2.0", "aiohasupervisor": "0.8.2", "pytest-homeassistant": RELEASE}
# zha's own exact pins (zha does not pin zha-quirks: the release does) and the test package's.
FROM_ZHA = {"bellows": "1.2.2", "zigpy": "2.4.2"}
FROM_HARNESS = {"homeassistant": RELEASE, "pytest": "9.1.1", "pytest-timeout": "1.4.0"}
SAID = f"- Home Assistant release of the integration's tests: {RELEASE} (was 2026.11.0)\n"


def manifest(*requirements: str) -> dict:
    return {"content": base64.b64encode(json.dumps({"requirements": list(requirements)}).encode()).decode()}


def component(name: str, release: str = RELEASE) -> str:
    return f"{CORE}/contents/homeassistant/components/{name}/manifest.json?ref={release}"


def harness_url(release: str = RELEASE) -> str:
    return f"https://pypi.org/pypi/pytest-homeassistant/{release}/json"


def harness_requires(release: str = RELEASE) -> dict:
    return {"info": {"requires_dist": [f"homeassistant=={release}", "pytest==9.1.1", "pytest-timeout==1.4.0", 'freezegun==1.5.1; extra == "time"']}}


NETWORK = {
    f"{CORE}/tags?per_page=100&page=1": [{"name": name} for name in ("2026.12.0b1", RELEASE, "2026.11.0", "2026.10.4", "dev")],
    component("zha"): manifest("zha==2.4.3", "zha-quirks==2.4.2"),
    component("usb"): manifest("aiousbwatcher==1.1.2", "serialx==1.15.2"),
    component("homeassistant_hardware"): manifest("universal-silabs-flasher==1.3.1", "ha-silabs-firmware-client==0.4.0", "pygbl==1.2.0"),
    component("hassio"): manifest("aiohasupervisor==0.8.2"),
    ZHA_URL: {"info": {"requires_dist": ["attrs", "bellows==1.2.2", "zigpy==2.4.2", 'pytest; extra == "testing"']}},
    harness_url(): harness_requires(),
}


@pytest.fixture(autouse=True)
def network(monkeypatch):
    def get_json(url: str):
        if url not in NETWORK:
            raise urllib.error.HTTPError(url, 404, "Not Found", {}, None)
        return NETWORK[url]

    monkeypatch.setattr(pins_tool, "get_json", get_json)


@pytest.fixture
def files(tmp_path: Path) -> tuple[Path, Path]:
    (tmp_path / "tests").mkdir()
    requirements, hacs = tmp_path / "tests" / "requirements.txt", tmp_path / "hacs.json"
    requirements.write_text(REQUIREMENTS)
    hacs.write_text(json.dumps(HACS, indent=2) + "\n")
    return requirements, hacs


def run(monkeypatch, capsys, *args: str) -> str:
    monkeypatch.setattr(sys, "argv", ["integration_pins.py", *args])
    pins_tool.main()
    return capsys.readouterr().out


def refused(monkeypatch, capsys, files, *args: str, code=None) -> SystemExit:
    """The tool stops; both files stay as they were, nothing is printed."""
    requirements, hacs = files
    before = requirements.read_text(), hacs.read_text()
    with pytest.raises(SystemExit) as stop:
        run(monkeypatch, capsys, "--requirements", str(requirements), "--hacs-json", str(hacs), *args)
    assert stop.value.code not in (0, None) if code is None else stop.value.code == code
    assert (requirements.read_text(), hacs.read_text()) == before
    assert capsys.readouterr().out == ""
    assert sorted(path.name for path in requirements.parent.parent.rglob("*") if path.is_file()) == ["hacs.json", "requirements.txt"]
    return stop.value


def test_the_newest_release_and_its_pins():
    assert pins_tool.release_tags()[-1] == (2026, 11, 1)
    found = pins_tool.pins(RELEASE)
    assert (found.needed, found.zha, found.harness, found.marked) == (NEEDED, FROM_ZHA, FROM_HARNESS, {})
    assert found.known == FROM_HARNESS | FROM_ZHA | NEEDED


def test_requirements_and_hacs_json(files, monkeypatch, capsys):
    requirements, hacs = files
    assert run(monkeypatch, capsys, "--requirements", str(requirements), "--hacs-json", str(hacs)) == SAID
    assert requirements.read_text() == RAISED
    assert hacs.read_text() == json.dumps({**HACS, "homeassistant": RELEASE}, indent=2) + "\n"
    # The same release again: nothing raised, nothing changed.
    assert run(monkeypatch, capsys, "--requirements", str(requirements)) == f"- Home Assistant release of the integration's tests: {RELEASE}\n"
    assert requirements.read_text() == RAISED


def test_an_exact_release(files, monkeypatch, capsys):
    """--release pins an older release than the newest one; a release Home Assistant has not tagged
    or a malformed one stops it."""
    requirements, _ = files
    for name, *pins in (("zha", "zha==2.4.2", "zha-quirks==2.4.1"), ("usb", "aiousbwatcher==1.1.2", "serialx==1.15.1"),
                        ("homeassistant_hardware", "universal-silabs-flasher==1.3.0", "ha-silabs-firmware-client==0.4.0", "pygbl==1.2.0"),
                        ("hassio", "aiohasupervisor==0.8.1")):
        monkeypatch.setitem(NETWORK, component(name, "2026.11.0"), manifest(*pins))
    monkeypatch.setitem(NETWORK, "https://pypi.org/pypi/zha/2.4.2/json", {"info": {"requires_dist": ["zigpy==2.4.1"]}})
    monkeypatch.setitem(NETWORK, harness_url("2026.11.0"), harness_requires("2026.11.0"))
    requirements.write_text(RAISED)
    assert run(monkeypatch, capsys, "--requirements", str(requirements), "--release", "2026.11.0") == (
        f"- Home Assistant release of the integration's tests: 2026.11.0 (was {RELEASE})\n")
    assert requirements.read_text() == REQUIREMENTS
    assert "no release 2026.11.7" in str(refused(monkeypatch, capsys, files, "--release", "2026.11.7").code)
    for malformed in ("2026.11", "2026.011.0", "2026.11.0b1", "latest"):
        refused(monkeypatch, capsys, files, "--release", malformed, code=2)


def test_a_requirement_the_release_adds_is_named_not_added(files, monkeypatch, capsys):
    requirements, _ = files
    monkeypatch.setitem(NETWORK, component("hassio"), manifest("aiohasupervisor==0.8.2", "newpkg==0.1.0"))
    out = run(monkeypatch, capsys, "--requirements", str(requirements))
    assert out.splitlines()[1:] == [f"- {requirements} lacks newpkg==0.1.0, a requirement of Home Assistant {RELEASE}: add it by hand"]
    assert requirements.read_text() == RAISED


def test_zha_quirks_from_zha_when_the_release_leaves_it_to_zha(files, monkeypatch, capsys):
    requirements, _ = files
    monkeypatch.setitem(NETWORK, component("zha"), manifest("zha==2.4.3"))
    monkeypatch.setitem(NETWORK, ZHA_URL, {"info": {"requires_dist": ["zigpy==2.4.2", "zha-quirks (==2.4.2)"]}})
    assert run(monkeypatch, capsys, "--requirements", str(requirements)) == SAID
    assert requirements.read_text() == RAISED


def test_the_components_pin_wins_over_zhas_and_the_test_packages(files, monkeypatch, capsys):
    requirements, _ = files
    monkeypatch.setitem(NETWORK, ZHA_URL, {"info": {"requires_dist": ["zigpy==2.4.2", "zha-quirks==2.4.0", "serialx==1.0.0"]}})
    monkeypatch.setitem(NETWORK, harness_url(), {"info": {"requires_dist": [f"homeassistant=={RELEASE}", "zha-quirks==2.3.9", "zigpy==2.3.9"]}})
    requirements.write_text(REQUIREMENTS + "zigpy==2.4.1\n")
    assert run(monkeypatch, capsys, "--requirements", str(requirements)) == SAID
    # zigpy: zha's pin, not the test package's.
    assert requirements.read_text() == RAISED + "zigpy==2.4.2\n"


@pytest.mark.parametrize("zha_requires", [["zigpy==2.4.2"], ["zigpy==2.4.2", 'zha-quirks==9.9.9; extra == "testing"'],
                                          ["zigpy==2.4.2", "zha-quirks==9.9.9 ; 'testing' == extra"], ["zha-quirks==2.4.2,<3"], None])
def test_a_pin_the_release_does_not_pin_exactly_is_kept_and_named(files, monkeypatch, capsys, zha_requires):
    """pip would refuse zha-quirks 2.4.1 next to a zha that needs another: the line says so."""
    requirements, _ = files
    monkeypatch.setitem(NETWORK, component("zha"), manifest("zha==2.4.3"))
    monkeypatch.setitem(NETWORK, ZHA_URL, {"info": {"requires_dist": zha_requires}})
    out = run(monkeypatch, capsys, "--requirements", str(requirements))
    assert out.splitlines()[1:] == [
        f"- {requirements} keeps zha-quirks==2.4.1, which neither the components' manifests nor zha nor pytest-homeassistant pin exactly: fix it by hand"]
    assert requirements.read_text() == RAISED.replace("zha-quirks==2.4.2", "zha-quirks==2.4.1")


def test_pins_under_a_marker_are_not_taken(files, monkeypatch, capsys):
    """A pin that holds only under an environment marker is named, never written; the file's pin stays."""
    requirements, _ = files
    pygbl = "pygbl==1.2.1; python_version < '3.13'"
    monkeypatch.setitem(NETWORK, component("homeassistant_hardware"), manifest(
        "universal-silabs-flasher==1.3.1", "ha-silabs-firmware-client==0.4.0", pygbl, "winonly==1.0; sys_platform == 'win32'"))
    out = run(monkeypatch, capsys, "--requirements", str(requirements))
    assert out.splitlines()[1:] == [
        f"- {requirements} keeps pygbl==1.2.0: Home Assistant {RELEASE} pins it only under an environment marker ({pygbl}): fix it by hand",
        f"- {requirements} lacks winonly==1.0; sys_platform == 'win32', a requirement of Home Assistant {RELEASE} under an environment marker: add it by hand where it holds"]
    assert requirements.read_text() == RAISED


def test_two_different_pins_of_one_package_stop_it(files, monkeypatch, capsys):
    monkeypatch.setitem(NETWORK, ZHA_URL, {"info": {"requires_dist": ["zigpy==2.4.2", "Zigpy==2.4.3"]}})
    assert "two different pins of zigpy: 2.4.2 and 2.4.3" in str(refused(monkeypatch, capsys, files).code)


def test_extras_markers_and_other_spellings_in_the_release(files, monkeypatch, capsys):
    requirements, _ = files
    monkeypatch.setitem(NETWORK, component("usb"), manifest("aiousbwatcher==1.1.2", "serialx[cli]==1.15.2"))
    monkeypatch.setitem(NETWORK, component("homeassistant_hardware"), manifest(
        "Universal_Silabs.Flasher==1.3.1", "ha-silabs-firmware-client==0.4.0", "pygbl==1.2.0"))
    assert run(monkeypatch, capsys, "--requirements", str(requirements)) == SAID
    # The file keeps its own spelling.
    assert requirements.read_text() == RAISED


def test_the_test_packages_own_pins_count(files, monkeypatch, capsys):
    requirements, _ = files
    requirements.write_text(REQUIREMENTS + "pytest-timeout==1.3.0\n")
    assert run(monkeypatch, capsys, "--requirements", str(requirements)) == SAID
    assert requirements.read_text() == RAISED + "pytest-timeout==1.4.0\n"


def test_inline_comments_and_trailing_spaces_stay(files, monkeypatch, capsys):
    requirements, _ = files
    requirements.write_text(REQUIREMENTS.replace("zha==2.4.2\n", "zha==2.4.2  # the core of it  \n").replace("pygbl==1.2.0\n", "pygbl==1.2.0   \n"))
    assert run(monkeypatch, capsys, "--requirements", str(requirements)) == SAID
    assert requirements.read_text() == RAISED.replace("zha==2.4.3\n", "zha==2.4.3  # the core of it  \n").replace("pygbl==1.2.0\n", "pygbl==1.2.0   \n")


@pytest.mark.parametrize("line", ["serialx[cli]==1.15.1", 'pygbl==1.2.0;python_version<"3.15"', "pygbl==1.2.0#no comment", "-r other.txt",
                                  "zha>=2.4.2", "zha==2.4.2,<3", "--extra-index-url https://packages.example.invalid/simple"])
def test_a_line_it_does_not_understand_stops_it(files, monkeypatch, capsys, line):
    requirements, _ = files
    requirements.write_text(REQUIREMENTS + line + "\n")
    stop = refused(monkeypatch, capsys, files)
    assert f"{requirements}:12: {line!r} is no pin" in str(stop.code)


@pytest.mark.parametrize("hacs_text", ["{", "[]", None])
def test_nothing_is_written_when_hacs_json_cannot_be_read(files, monkeypatch, capsys, hacs_text):
    requirements, hacs = files
    if hacs_text is None:
        hacs.unlink()
    else:
        hacs.write_text(hacs_text)
    with pytest.raises((SystemExit, FileNotFoundError)):
        run(monkeypatch, capsys, "--requirements", str(requirements), "--hacs-json", str(hacs))
    assert requirements.read_text() == REQUIREMENTS
    assert capsys.readouterr().out == ""


@pytest.mark.skipif(os.geteuid() == 0, reason="root writes into read-only files and folders")
@pytest.mark.parametrize("locked", ["file", "folder"])
def test_nothing_is_written_when_one_file_cannot_be_written(files, monkeypatch, capsys, locked):
    requirements, hacs = files
    target = hacs if locked == "file" else hacs.parent
    mode = target.stat().st_mode
    target.chmod(0o444 if locked == "file" else 0o555)
    try:
        assert "nothing written" in str(refused(monkeypatch, capsys, files).code)
    finally:
        target.chmod(mode)


@pytest.mark.parametrize("harness", [None, {"info": {"requires_dist": ["homeassistant==2026.11.0"]}}, {"info": {"requires_dist": None}}])
def test_nothing_changes_without_the_test_package_of_the_release(files, monkeypatch, capsys, harness):
    """Home Assistant's own upload of the test package can fail or come late: the pins wait for it."""
    if harness is None:
        monkeypatch.delitem(NETWORK, harness_url())
    else:
        monkeypatch.setitem(NETWORK, harness_url(), harness)
    stop = refused(monkeypatch, capsys, files)
    assert stop.code == f"no pytest-homeassistant release pins homeassistant=={RELEASE} yet"


def test_without_options_it_prints_the_pins(monkeypatch, capsys):
    assert json.loads(run(monkeypatch, capsys)) == {"ha": RELEASE, "pins": dict(sorted(NEEDED.items())), "zha": FROM_ZHA,
                                                    "pytest-homeassistant": FROM_HARNESS, "marked": {}}


def test_the_real_requirements_file_round_trips():
    """tests_hacs/requirements.txt holds pins and comments only, names its release in the comment
    the tool rewrites and comes back unchanged from the pins it already has."""
    text = (ROOT / "tests_hacs" / "requirements.txt").read_text()
    found = {}
    for line in text.splitlines():
        if not pins_tool.FILE_OTHER.fullmatch(line):
            m = pins_tool.FILE_PIN.fullmatch(line)
            found[pins_tool.canonical(m.group(2))] = m.group(3)
    release = found[pins_tool.HARNESS]
    assert re.search(rf"pinned as in {re.escape(release)}\.$", text, re.MULTILINE)
    same = pins_tool.Pins(needed=found, zha={}, harness={}, marked={}, marked_needed=set())
    assert pins_tool.requirements_text(text, "requirements.txt", release, same) == (text, release, [])
