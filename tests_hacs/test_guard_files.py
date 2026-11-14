"""The guard on quirk files: what it refuses and what it passes, on frozen copies of real quirk files
(fixtures/) under their manifest entries (fixtures/manifest.json). Every payload is code no quirk
file holds, a target outside the file's manifest entry or a name the filter reads bound otherwise
than by the fixed code."""

from __future__ import annotations

import ast
import json
import re
import sys
from pathlib import Path

import pytest

from .integration import FOLDER, guard

FIXTURES = Path(__file__).resolve().parent / "fixtures"
# The guard as this release ships it: guard.py with its fixed_code.json.
SHIPPED = guard.Guard.load()
# File name -> manifest entry of each frozen file: what it may target.
FROZEN = {Path(entry["file"]).name: entry for entry in json.loads((FIXTURES / "manifest.json").read_text()).values() if entry.get("file")}
FIXED_CODE = json.loads((FOLDER / guard.FIXED_CODE).read_text())


def targets(name: str, **changes) -> object:
    """The targets of a frozen file's manifest entry, with changed fields."""
    return guard.Targets.of({**FROZEN[name], **changes})


def frozen(name: str) -> str:
    return (FIXTURES / f"{name}.txt").read_text()


def test_guard_needs_the_standard_library_only():
    """guard.py imports the standard library only: it runs without Home Assistant or other packages."""
    tree = ast.parse((FOLDER / "guard.py").read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            assert node.level == 0 and node.module.split(".")[0] in {*sys.stdlib_module_names, "__future__"}, node.module
        elif isinstance(node, ast.Import):
            assert all(alias.name.split(".")[0] in sys.stdlib_module_names for alias in node.names)


def test_cluster_modules_are_the_ones_zigpys_standard_clusters_come_from():
    import zigpy.zcl

    assert guard.CLUSTER_MODULES == {cls.__module__ for cluster_id, cls in zigpy.zcl.Cluster._registry.items() if cluster_id < 0xFC00}


# What the tables leave out: each payload is code no quirk file holds.

TUYA, ZCL, METER = "z2m_tuya_ts0105.py", "z2m_bosch_bsen_w.py", "z2m_moes_zm6lt1.py"
AQARA = "z2m_aqara_qbcz15lm.py"
CHAIN_END = "    .add_to_registry()\n"
# Class data a cluster or a fixed method computes with a device value: the Aqara helper multiplies a
# struct value by its STRUCT_TAGS factor, the Xiaomi base divides by the battery range.
STRUCT = "STRUCT_TAGS = {149: ('consumption', 1.0), "
XIAOMI = "from zhaquirks.xiaomi import DeviceTemperatureCluster, ElectricalMeasurementCluster, MeteringCluster, XiaomiAqaraE1Cluster\n"
XIAOMI_BATTERY = XIAOMI.replace("XiaomiAqaraE1Cluster", "XiaomiAqaraE1Cluster, XiaomiPowerConfiguration")
BATTERY = (
    "class StructPowerConfiguration(XiaomiPowerConfiguration):\n"
    '    """Battery from the voltage in the Aqara struct, over z2m\'s range."""\n\n'
    "{values}\n\n"
)


def battery(values: str) -> tuple[str, str, str]:
    """A payload that adds the battery class with these values to the Aqara file."""
    return (AQARA, XIAOMI + "\n\n", XIAOMI_BATTERY + "\n\n" + BATTERY.format(values=values))


ZCL_SENSOR = (
    ".sensor(attribute_name=BoschWaterAlarmCluster.AttributeDefs.alarm_on_motion.name, cluster_id=BoschWaterAlarmCluster.cluster_id, "
    "attribute_converter=lambda x: {converter}, fallback_name='Motion')"
)
PAYLOADS = {
    "plain import": (TUYA, "import functools\n", "import functools\nimport zigpy\n"),
    "import of a name no quirk file imports": (TUYA, "from zhaquirks.tuya.builder import TuyaQuirkBuilder\n",
                                                     "from zhaquirks.tuya.builder import TuyaQuirkBuilder\nfrom zhaquirks.tuya import TuyaLocalCluster\n"),
    "import of a lowercase name from a cluster module": (TUYA, "import functools\n", "import functools\nfrom zigpy.zcl.clusters.general import foundation\n"),
    "import from another zigpy module": (TUYA, "import functools\n", "import functools\nfrom zigpy.zcl.clusters.manufacturer_specific import ManufacturerSpecificCluster\n"),
    "builder method no quirk file calls": (TUYA, CHAIN_END, "    .friendly_name(model='Other', manufacturer='Someone')\n" + CHAIN_END),
    "tuya method on QuirkBuilder": (ZCL, CHAIN_END, "    .tuya_dp(dp_id=1)\n" + CHAIN_END),
    "another filter": (TUYA, ".filter(no_builtin_quirk)", ".filter(lambda device: True)"),
    "add_to_registry with an argument": (TUYA, ".add_to_registry()", ".add_to_registry(1)"),
    "lambda outside a converter": (TUYA, "fallback_name='State')\n    .filter", "fallback_name=lambda x: 'State')\n    .filter"),
    "converter of two arguments": (METER, "converter=lambda x: _be(x, 2, 2)", "converter=lambda x, y: _be(x, 2, 2)"),
    "converter with another argument name": (METER, "converter=lambda x: _be(x, 2, 2)", "converter=lambda data: _be(data, 2, 2)"),
    "converter reading an attribute of its value": (METER, "converter=lambda x: _be(x, 2, 2)", "converter=lambda x: x.real"),
    "converter that is a class": (METER, "converter=lambda x: OnlineState(int(x))", "converter=OnlineState"),
    "converter calling a builtin": (METER, "converter=lambda x: _be(x, 2, 2)", "converter=lambda x: len(x)"),
    "converter calling a definition": (METER, "converter=lambda x: _be(x, 2, 2)", "converter=lambda x: DPToAttributeMapping(x)"),
    "converter repeating a string": (METER, "converter=lambda x: _be(x, 2, 2)", "converter=lambda x: x * 'x'"),
    "converter repeating its value as text": (METER, "converter=lambda x: _be(x, 2, 2)", "converter=lambda x: str(x) * x"),
    "converter repeating a list": (METER, "converter=lambda x: _be(x, 2, 2)", "converter=lambda x: [0] * x"),
    "converter repeating a tuple": (METER, "converter=lambda x: _be(x, 2, 2)", "converter=lambda x: (x,) * x"),
    "converter repeating a looked-up string": (METER, "converter=lambda x: _be(x, 2, 2)", "converter=lambda x: {1: 'a'}[x] * x"),
    "converter repeating a conditional string": (METER, "converter=lambda x: _be(x, 2, 2)", "converter=lambda x: ('a' if x else 'b') * x"),
    "converter repeating its value as text by a number": (METER, "converter=lambda x: _be(x, 2, 2)", "converter=lambda x: str(x) * 100000000"),
    "converter repeating by its value as a number": (METER, "converter=lambda x: _be(x, 2, 2)", "converter=lambda x: x * int(x)"),
    "converter multiplying by a large integer": (METER, "converter=lambda x: _be(x, 2, 2)", "converter=lambda x: x * 10000000"),
    "converter chaining products": (METER, "converter=lambda x: _be(x, 2, 2)", "converter=lambda x: x * 1000 * 1000"),
    "converter multiplying arithmetic over x": (METER, "converter=lambda x: _be(x, 2, 2)", "converter=lambda x: (x + x) * 1000"),
    "converter multiplying a literal by x": (METER, "converter=lambda x: _be(x, 2, 2)", "converter=lambda x: 1000 * x"),
    # A string from the device repeated by each product: one product per converter, nothing joins
    # or collects such values (else 255 bytes times 1000 times the number of products).
    "converter summing products": (METER, "converter=lambda x: _be(x, 2, 2)", "converter=lambda x: x * 1000 + x * 1000"),
    "converter joining its value twice": (METER, "converter=lambda x: _be(x, 2, 2)", "converter=lambda x: x + x"),
    "converter with a product in each branch": (METER, "converter=lambda x: _be(x, 2, 2)", "converter=lambda x: x * 1000 if x else x * 1000"),
    "converter calling with two products": (METER, "converter=lambda x: _be(x, 2, 2)", "converter=lambda x: int(x * 1000, x * 1000)"),
    "converter holding a tuple of products": (METER, "converter=lambda x: _be(x, 2, 2)", "converter=lambda x: (x * 1000, x)"),
    # Only a Tuya value is at most 255 bytes: an attribute_converter gets a ZCL attribute (a long string
    # from the device), a dp_converter the value written. No quirk file has a product in either.
    "product in an attribute_converter": (ZCL, CHAIN_END, f"    {ZCL_SENSOR.format(converter='x * 1000')}\n" + CHAIN_END),
    "product in a dp_converter": (METER, "converter=lambda x: _be(x, 2, 2))", "converter=lambda x: _be(x, 2, 2), dp_converter=lambda x: x * 10)"),
    "converter holding a list": (METER, "converter=lambda x: _be(x, 2, 2)", "converter=lambda x: [x]"),
    "converter holding a set": (METER, "converter=lambda x: _be(x, 2, 2)", "converter=lambda x: {x}"),
    "converter with x in the values of a dict": (METER, "converter=lambda x: _be(x, 2, 2)", "converter=lambda x: {0: x * 1000, 1: 0}[x]"),
    "converter with x in the keys of a dict": (METER, "converter=lambda x: _be(x, 2, 2)", "converter=lambda x: {x: 0}[0]"),
    "converter with and/or": (METER, "converter=lambda x: _be(x, 2, 2)", "converter=lambda x: x and _be(x, 2, 2)"),
    "converter looking up in a name": (METER, "converter=lambda x: _be(x, 2, 2)", "converter=lambda x: TUYA_CLUSTER_ID[x]"),
    "converter as a cluster method": (METER, "converter=lambda x: _be(x, 2, 2)", "converter=TuyaMCUCluster.handle_cluster_request"),
    "cluster attribute no quirk file reads": (METER, "ep_attribute=TuyaMCUCluster.ep_attribute, attribute_name='voltage'",
                                                    "ep_attribute=TuyaMCUCluster.endpoint, attribute_name='voltage'"),
    "enum attribute in lower case": (TUYA, "entity_type=EntityType.STANDARD, translation_key='state_l3'", "entity_type=EntityType.mro, translation_key='state_l3'"),
    "foundation attribute": (METER, "access=foundation.ZCLAttributeAccess.Read | foundation.ZCLAttributeAccess.Report)\n    .tuya_attribute(dp_id=255",
                             "access=foundation.ZCLHeader)\n    .tuya_attribute(dp_id=255"),
    "zigpy name outside the types": (METER, "attribute_name='voltage', type=t.uint32_t", "attribute_name='voltage', type=t.basic"),
    "enum member the class does not have": (METER, "converter=lambda x: OnlineState(int(x))", "converter=lambda x: OnlineState.mro"),
    "enum class called outside a converter": (METER, "enum_class=OnlineState,", "enum_class=OnlineState(1),"),
    "bare builtin": (TUYA, "fallback_name='State')\n    .filter", "fallback_name=str)\n    .filter"),
    "call in a chain": (TUYA, "fallback_name='State')\n    .filter", "fallback_name=str(1))\n    .filter"),
    "lambda in a class body": (ZCL, '        """Attribute definitions."""\n', '        """Attribute definitions."""\n\n        handle = lambda x: x\n'),
    "operator in a class body": (ZCL, "cluster_id = 0xFCAC", "cluster_id = 0xFCAC | t.uint8_t"),
    "name in a class body": (ZCL, "cluster_id = 0xFCAC", "cluster_id = CustomCluster"),
    "call in a class body": (ZCL, "cluster_id = 0xFCAC", "cluster_id = int('0xFCAC', 16)"),
    "class on a builder": (METER, "class OnlineState(t.enum8):", "class OnlineState(TuyaQuirkBuilder, t.enum8):"),
    "class on a class of the file": (AQARA, "class StructElectricalMeasurement(ElectricalMeasurementCluster):", "class StructElectricalMeasurement(ManuSpecificLumiCluster):"),
    "class without a base": (METER, "class OnlineState(t.enum8):", "class OnlineState:"),
    "nested class in a nested class": (ZCL, '        """Attribute definitions."""\n', '        """Attribute definitions."""\n\n        class AttributeDefs(BaseAttributeDefs):\n            x = 1\n'),
    "spread of another attribute": (AQARA, "**ElectricalMeasurementCluster._CONSTANT_ATTRIBUTES", "**ElectricalMeasurementCluster.__dict__"),
    "spread of a file class": (AQARA, "**ElectricalMeasurementCluster._CONSTANT_ATTRIBUTES", "**StructElectricalMeasurement._CONSTANT_ATTRIBUTES"),
    # A string or a sequence as a factor repeats the device's value (a uint32 struct value: gigabytes).
    "struct factor as a string": (AQARA, STRUCT, "STRUCT_TAGS = {149: ('consumption', 'A'), "),
    "struct factor as a tuple": (AQARA, STRUCT, "STRUCT_TAGS = {149: ('consumption', (1,)), "),
    "struct factor as a large integer": (AQARA, STRUCT, "STRUCT_TAGS = {149: ('consumption', 1000000000), "),
    "struct factor as an integer": (AQARA, STRUCT, "STRUCT_TAGS = {149: ('consumption', 1), "),
    "struct factor above MAX_FACTOR": (AQARA, STRUCT, "STRUCT_TAGS = {149: ('consumption', 1001.0), "),
    "struct factor of zero": (AQARA, STRUCT, "STRUCT_TAGS = {149: ('consumption', 0.0), "),
    "struct tag under another key": (AQARA, STRUCT, "STRUCT_TAGS = {149: ('power', 1.0), "),
    "struct tag no quirk file has": (AQARA, STRUCT, "STRUCT_TAGS = {5: ('consumption', 1.0), "),
    "struct tags spread": (AQARA, STRUCT, "STRUCT_TAGS = {**ElectricalMeasurementCluster._CONSTANT_ATTRIBUTES, "),
    "struct target of another kind": (AQARA, '"consumption": "smartenergy_metering",', '"consumption": 5,'),
    "class value no quirk file sets": (AQARA, "    STRUCT_TAGS = {", "    manufacturer_id_override = 0x1234\n    STRUCT_TAGS = {"),
    "constant attribute as text": (AQARA, "ac_current_divisor.id: 1000,", "ac_current_divisor.id: '1000',"),
    "constant attribute keyed by its name": (AQARA, "ac_current_divisor.id: 1000,", "ac_current_divisor.name: 1000,"),
    "constant attribute out of range": (AQARA, "ac_current_divisor.id: 1000,", "ac_current_divisor.id: 100000,"),
    "cluster_id as text": (ZCL, "cluster_id = 0xFCAC", "cluster_id = '0xFCAC'"),
    "cluster_id out of range": (ZCL, "cluster_id = 0xFCAC", "cluster_id = 0x1FCAC"),
    "enum member as text": (METER, "    offline = 0x00\n", "    offline = 'offline'\n"),
    "enum member beyond enum8": (METER, "    offline = 0x00\n", "    offline = 0x100\n"),
    "attribute definition as a value": (ZCL, '        """Attribute definitions."""\n', '        """Attribute definitions."""\n\n        extra = 1\n'),
    # An empty or upside-down battery range divides by zero or goes negative on every battery report.
    "battery range of one value": battery("    MIN_VOLTS_MV = 3000\n    MAX_VOLTS_MV = 3000"),
    "battery range upside down": battery("    MIN_VOLTS_MV = 3000\n    MAX_VOLTS_MV = 2850"),
    "battery range with one end": battery("    MIN_VOLTS_MV = 3100"),
    "battery voltage out of range": battery("    MIN_VOLTS_MV = 500\n    MAX_VOLTS_MV = 3000"),
    "battery voltage as text": battery("    MIN_VOLTS_MV = '2850'\n    MAX_VOLTS_MV = 3000"),
    # zigpy calls _missing_ for a value without a member, serialize on a write: a member must not stand in.
    "enum member named like an enum hook": (METER, "    offline = 0x00\n", "    _missing_ = 0x00\n"),
    "enum member named like an enum method": (METER, "    offline = 0x00\n", "    serialize = 0x00\n"),
    "enum member named mro": (METER, "    offline = 0x00\n", "    mro = 0x00\n"),
    # A statement after add_to_registry(): an import that fails there leaves what follows unbound.
    "import after the chain": (TUYA, CHAIN_END + ")\n", CHAIN_END + ")\n\nfrom zigpy.zcl.clusters.general import NoSuchClusterAnywhere\n"),
    "class after the chain": (METER, CHAIN_END + ")\n", CHAIN_END + ")\n\n\nclass Late(t.enum8):\n    a = 0x00\n"),
    "module literal no quirk file has": (TUYA, "FINGERPRINTS = ", "EXTRA = 1\nFINGERPRINTS = "),
    "a fixed name bound to a literal": (TUYA, "_SHIPPED = pathlib.Path(zhaquirks.__file__).resolve().parent", "_SHIPPED = '/'"),
    "coding declaration": (TUYA, '"""Tuya TS0105', '# -*- coding: utf-7 -*-\n"""Tuya TS0105'),
    "coding declaration after a byte order mark": (TUYA, '"""Tuya TS0105', '\ufeff# coding: utf-8\n"""Tuya TS0105'),
    "coding declaration on the second line": (TUYA, '"""Tuya TS0105', '#!/usr/bin/env python3\n# vim: set fileencoding=latin-1 :\n"""Tuya TS0105'),
}


# .prevent_default_entity_creation: literal keywords of their kind only, the cluster always named.
HIDE_CALL = "    .prevent_default_entity_creation({})\n"
HIDE_PASSES = {
    "a ZCL default entity of a stand-in cluster": (TUYA, "endpoint_id=1, cluster_id=0x0406, unique_id_suffix='pir_o_to_u_delay'"),
    "the cluster of an imported stand-in": (METER, "endpoint_id=1, cluster_id=TuyaMCUCluster.cluster_id, unique_id_suffix='pir_u_to_o_delay'"),
    "a cluster on every endpoint": (TUYA, "cluster_id=0x0406"),
    "a suffix with an endpoint and a cluster in it": (TUYA, "cluster_id=0x0402, unique_id_suffix='1-1794'"),
}
HIDE_REFUSED = {
    # No ZCL file needs it: only the Tuya builder may call it.
    "on QuirkBuilder": (ZCL, "endpoint_id=1, cluster_id=BoschWaterAlarmCluster.cluster_id"),
    "no arguments": (TUYA, ""),
    "no cluster": (TUYA, "endpoint_id=1"),
    "only a suffix": (TUYA, "unique_id_suffix='pir_o_to_u_delay'"),
    "a positional argument": (TUYA, "1, cluster_id=0x0406"),
    "a filter function": (TUYA, "cluster_id=0x0406, function=lambda entity: True"),
    "the upstream filter as a function": (TUYA, "cluster_id=0x0406, function=no_builtin_quirk"),
    "a cluster type": (TUYA, "cluster_id=0x0406, cluster_type=1"),
    "spread keywords": (TUYA, "cluster_id=0x0406, **{'endpoint_id': 1}"),
    "endpoint zero": (TUYA, "endpoint_id=0, cluster_id=0x0406"),
    "endpoint 255": (TUYA, "endpoint_id=255, cluster_id=0x0406"),
    "endpoint as text": (TUYA, "endpoint_id='1', cluster_id=0x0406"),
    "endpoint as a bool": (TUYA, "endpoint_id=True, cluster_id=0x0406"),
    "endpoint computed": (TUYA, "endpoint_id=0 | 1, cluster_id=0x0406"),
    "cluster as text": (TUYA, "cluster_id='0x0406'"),
    "cluster out of range": (TUYA, "cluster_id=0x10000"),
    "negative cluster": (TUYA, "cluster_id=-1"),
    "cluster as a float": (TUYA, "cluster_id=1030.0"),
    "cluster of an enum of the file": (METER, "cluster_id=OnlineState.cluster_id"),
    "cluster of a builder": (METER, "cluster_id=TuyaQuirkBuilder.cluster_id"),
    "cluster of a module": (METER, "cluster_id=zhaquirks.cluster_id"),
    "another attribute of a cluster": (METER, "cluster_id=TuyaMCUCluster.ep_attribute"),
    "a cluster class itself": (METER, "cluster_id=TuyaMCUCluster"),
    "a value of the file": (METER, "cluster_id=TUYA_CLUSTER_ID"),
    "suffix as a number": (TUYA, "cluster_id=0x0406, unique_id_suffix=1794"),
    "empty suffix": (TUYA, "cluster_id=0x0406, unique_id_suffix=''"),
    "suffix with a space": (TUYA, "cluster_id=0x0406, unique_id_suffix='pir delay'"),
    "suffix with a dot": (TUYA, "cluster_id=0x0406, unique_id_suffix='../x'"),
    "suffix too long": (TUYA, f"cluster_id=0x0406, unique_id_suffix='{'a' * 65}'"),
    "suffix as bytes": (TUYA, "cluster_id=0x0406, unique_id_suffix=b'pir'"),
    "suffix as an f-string": (TUYA, "cluster_id=0x0406, unique_id_suffix=f'pir{1}'"),
    "suffix computed": (TUYA, "cluster_id=0x0406, unique_id_suffix='pir' + '_delay'"),
}


@pytest.mark.parametrize(("name", "arguments"), HIDE_PASSES.values(), ids=HIDE_PASSES)
def test_integration_guard_passes_hiding_default_entities(name, arguments):
    text = frozen(name).replace(CHAIN_END, HIDE_CALL.format(arguments) + CHAIN_END, 1)
    assert SHIPPED.problems(text.encode(), targets(name)) == ()


@pytest.mark.parametrize(("name", "arguments"), HIDE_REFUSED.values(), ids=HIDE_REFUSED)
def test_integration_guard_refuses_other_ways_of_hiding_entities(name, arguments):
    text = frozen(name)
    assert SHIPPED.problems(text.encode(), targets(name)) == ()
    problems = SHIPPED.problems(text.replace(CHAIN_END, HIDE_CALL.format(arguments) + CHAIN_END, 1).encode(), targets(name))
    assert problems and any(guard.HIDE in problem or "** in a call" in problem for problem in problems), problems


def test_hiding_takes_the_keywords_of_both_builders():
    """The pinned zha-quirks: both builders have the method (the guard allows it on the Tuya one), with each keyword the guard allows as a
    keyword-only parameter that takes the kind the guard checks for."""
    import inspect

    from zhaquirks.builder import QuirkBuilder
    from zhaquirks.tuya.builder import TuyaQuirkBuilder

    assert guard.HIDE in guard.METHODS["TuyaQuirkBuilder"] and guard.HIDE not in guard.METHODS["QuirkBuilder"]
    for builder in (QuirkBuilder, TuyaQuirkBuilder):
        parameters = inspect.signature(getattr(builder, guard.HIDE)).parameters
        assert all(parameters[name].kind is inspect.Parameter.KEYWORD_ONLY for name in guard.HIDE_KEYWORDS)
        assert {name: parameters[name].annotation for name in guard.HIDE_KEYWORDS} == {"endpoint_id": "int | None", "cluster_id": "int | None", "unique_id_suffix": "str | None"}
    # What the call leaves in the quirk: a filter of exactly these values, ZHA hides the entities it matches.
    built = TuyaQuirkBuilder("_TZE200_aaaa", "TS0601").prevent_default_entity_creation(endpoint_id=1, cluster_id=0x0406, unique_id_suffix="pir_o_to_u_delay")
    (entity_filter,) = built.disabled_default_entities
    assert (entity_filter.endpoint_id, entity_filter.cluster_id, entity_filter.unique_id_suffix, entity_filter.function, entity_filter.cluster_type) == (1, 0x0406, "pir_o_to_u_delay", None, None)


@pytest.mark.parametrize(("name", "old", "new"), PAYLOADS.values(), ids=PAYLOADS)
def test_integration_guard_refuses(name, old, new):
    text = frozen(name)
    assert SHIPPED.problems(text.encode(), targets(name)) == ()
    assert old in text
    assert SHIPPED.problems(text.replace(old, new, 1).encode(), targets(name))


def test_the_battery_class_with_a_range_passes():
    _, old, new = battery("    MIN_VOLTS_MV = 2850\n    MAX_VOLTS_MV = 3000")
    assert SHIPPED.problems(frozen(AQARA).replace(old, new, 1).encode(), targets(AQARA)) == ()


def test_enum_member_names_the_guard_refuses_cover_zigpys_enum_types():
    import zigpy.types as t

    # ZHA's own quirks name an option that starts with a digit so; quirk files keep those names.
    assert all(guard.ENUM_MEMBER.fullmatch(name) for name in ("_4_anti_flicker", "_10", "Quick", "offline"))
    assert not any(guard.ENUM_MEMBER.fullmatch(name) for name in ("_missing_", "_order_", "_4_", "__init__", "_value_"))
    assert {name for cls in (t.enum8, t.enum16) for name in dir(cls) if not name.startswith("_")} <= guard.ENUM_RESERVED


def test_a_fixed_method_needs_what_it_reads_imported():
    """_handle_attribute_event reads ElectricalMeasurement when ZHA calls it: without that import
    every struct report on an endpoint with the electrical measurement cluster raises NameError."""
    text = frozen(AQARA)
    start = text.index("class StructElectricalMeasurement(")
    end = text.index("\n\n\n", start) + 3
    imported = "from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement\n"
    cut = (text[:start] + text[end:]).replace(imported, "", 1).replace("    .adds(StructElectricalMeasurement)\n", "", 1)
    assert "ElectricalMeasurement.AttributeDefs.rms_current" in cut
    problems = SHIPPED.problems(cut.encode(), targets(AQARA))
    assert any("method _handle_attribute_event reads ElectricalMeasurement" in problem for problem in problems), problems
    foundation_import = "from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef\n"
    assert SHIPPED.problems(cut.replace(foundation_import, foundation_import + imported, 1).encode(), targets(AQARA)) == ()


# The products quirk files hold (a scale, a scale and an offset, a thermostat factor), negative and
# float literals included, pass.
@pytest.mark.parametrize("product", ["x * 10", "x * 0.1", "x * -0.5", "x * 1e-05", "x * 0.1 + -40", "x * 2 + 0.5", "x * 1000", "x * -1000"])
def test_integration_guard_passes_the_products_of_quirk_files(product):
    text = frozen(METER).replace("converter=lambda x: _be(x, 2, 2)", f"converter=lambda x: {product}", 1)
    assert SHIPPED.problems(text.encode(), targets(METER)) == ()


# What quirk files hold there passes: a scale in an attribute_converter, a floor division in a
# dp_converter.
def test_integration_guard_passes_the_zcl_and_write_converters_of_quirk_files():
    zcl = frozen(ZCL).replace(CHAIN_END, f"    {ZCL_SENSOR.format(converter='x / 1000')}\n" + CHAIN_END, 1)
    assert SHIPPED.problems(zcl.encode(), targets(ZCL)) == ()
    meter = frozen(METER).replace("converter=lambda x: _be(x, 2, 2))", "converter=lambda x: _be(x, 2, 2), dp_converter=lambda x: x // 10)", 1)
    assert SHIPPED.problems(meter.encode(), targets(METER)) == ()


# What a file targets stays inside its manifest entry (the offer names those devices).

ALIAS, ALIAS_GROUPS = "z2m_alias_moes_zc_hm.py", "z2m_alias_neo_nas_wv03b.py"
FILTER = "    .filter(no_builtin_quirk)\n"
TARGET_PAYLOADS = {
    "chain without the filter": (TUYA, FILTER, "", "without exactly one .filter(no_builtin_quirk)"),
    "chain with two filters": (TUYA, FILTER, FILTER * 2, "without exactly one .filter(no_builtin_quirk)"),
    "applies_to outside the entry": (TUYA, ".applies_to('Tuya', 'TS0105')", ".applies_to('Tuya', 'TS0106')", "targets ('Tuya', 'TS0106'), which its manifest entry does not list"),
    "undeclared manufacturer wildcard": (METER, ".applies_to('_TZE284_2fnssffc', 'TS0601')\n", ".applies_to('_TZE284_2fnssffc', 'TS0601')\n    .applies_to(None, 'TS0601')\n",
                                         "targets (None, 'TS0601') (a manufacturer wildcard)"),
    "builder fingerprint outside the entry": (ZCL, "QuirkBuilder(None, 'RBSH-WS-ZB-EU')", "QuirkBuilder(None, 'RBSH-WS-ZB-EX')", "targets (None, 'RBSH-WS-ZB-EX')"),
    "QuirkBuilder without its fingerprint": (ZCL, "QuirkBuilder(None, 'RBSH-WS-ZB-EU')", "QuirkBuilder()", "QuirkBuilder with other arguments"),
    "TuyaQuirkBuilder with a fingerprint": (METER, "TuyaQuirkBuilder()", "TuyaQuirkBuilder('_TZE284_2fnssffc', 'TS0601')", "TuyaQuirkBuilder with other arguments"),
    "target as keywords": (METER, ".applies_to('_TZE284_2fnssffc', 'TS0601')", ".applies_to(manufacturer='_TZE284_2fnssffc', model='TS0601')", "no literal (manufacturer, model)"),
    "target the guard cannot read": (METER, ".applies_to('_TZE284_2fnssffc', 'TS0601')", ".applies_to(TUYA_CLUSTER_ID, 'TS0601')", "no literal (manufacturer, model)"),
    "manufacturer-only target": (METER, ".applies_to('_TZE284_2fnssffc', 'TS0601')", ".applies_to('_TZE284_2fnssffc', None)", "no literal (manufacturer, model)"),
    "FINGERPRINTS outside the entry": (TUYA, "FINGERPRINTS = [(None, 'TS0105'), ('Tuya', 'TS0105')]", "FINGERPRINTS = [(None, 'TS0105'), ('Tuya', 'TS0105'), ('X', 'Y')]",
                                       "targets ('X', 'Y')"),
    "FINGERPRINTS of another shape": (TUYA, "FINGERPRINTS = [(None, 'TS0105'), ('Tuya', 'TS0105')]", "FINGERPRINTS = [[None, 'TS0105']]", "FINGERPRINTS other than"),
    "alias onto a wildcard (review)": (ALIAS, "'fingerprints': [('JM720ES-EF-3.0', 'TS0601')]", "'fingerprints': [('JM720ES-EF-3.0', 'TS0601'), (None, 'TS0601')]",
                                       "targets (None, 'TS0601') (a manufacturer wildcard)"),
    "alias onto another device": (ALIAS, "'fingerprints': [('JM720ES-EF-3.0', 'TS0601')]", "'fingerprints': [('VICTIM_MFR', 'VICTIM_MODEL')]", "targets ('VICTIM_MFR', 'VICTIM_MODEL')"),
    "alias of another shipped quirk": (ALIAS, "'targets': [('_TZE200_hr0tdd47', 'TS0601')]", "'targets': [('_TZE204_victim', 'TS0601')]", "an alias group outside"),
    "alias name moved into another group": (ALIAS_GROUPS, "'fingerprints': [('_TZE284_z7a2jmyy', 'TS0601')]", "'fingerprints': [('_TZE284_z7a2jmyy', 'TS0601'), ('_TZE284_rzrrjkz2', 'TS0601')]",
                                            "an alias group outside"),
    "ALIASES of another shape": (ALIAS, "'targets': [('_TZE200_hr0tdd47', 'TS0601')]", "'targets': [['_TZE200_hr0tdd47', 'TS0601']]", "an ALIASES group other than"),
    "FINGERPRINTS that do not evaluate": (TUYA, "FINGERPRINTS = [(None, 'TS0105'), ('Tuya', 'TS0105')]", "FINGERPRINTS = [{[1]: 2}]", "a literal that does not evaluate"),
    "ALIASES with another key": (ALIAS, "'targets': [('_TZE200_hr0tdd47', 'TS0601')]", "'filters': [], 'targets': [('_TZE200_hr0tdd47', 'TS0601')]", "ALIASES other than"),
    # The integration reads what an installed file claims from its manifest entry.
    "CLAIMED_ELSEWHERE with fewer names than the entry": (TUYA, "CLAIMED_ELSEWHERE = {('_TZE600_ogyg1y6b', 'TS0105')}", "CLAIMED_ELSEWHERE = set()",
                                                          "CLAIMED_ELSEWHERE other than its manifest entry's claimed_elsewhere"),
    "CLAIMED_ELSEWHERE with more names than the entry": (TUYA, "CLAIMED_ELSEWHERE = {('_TZE600_ogyg1y6b', 'TS0105')}", "CLAIMED_ELSEWHERE = {('_TZE600_ogyg1y6b', 'TS0105'), ('Tuya', 'TS0105')}",
                                                         "CLAIMED_ELSEWHERE other than its manifest entry's claimed_elsewhere"),
    "CLAIMED_ELSEWHERE left out": (TUYA, "CLAIMED_ELSEWHERE = {('_TZE600_ogyg1y6b', 'TS0105')}\n", "", "CLAIMED_ELSEWHERE other than its manifest entry's claimed_elsewhere"),
    "CLAIMED_ELSEWHERE with a manufacturer wildcard": (TUYA, "CLAIMED_ELSEWHERE = {('_TZE600_ogyg1y6b', 'TS0105')}", "CLAIMED_ELSEWHERE = {(None, 'TS0105')}",
                                                       "CLAIMED_ELSEWHERE other than a set of (manufacturer, model)"),
}


@pytest.mark.parametrize(("name", "old", "new", "reason"), TARGET_PAYLOADS.values(), ids=TARGET_PAYLOADS)
def test_integration_guard_keeps_targets_inside_the_manifest_entry(name, old, new, reason):
    text = frozen(name)
    assert SHIPPED.problems(text.encode(), targets(name)) == ()
    assert old in text
    problems = SHIPPED.problems(text.replace(old, new, 1).encode(), targets(name))
    assert any(reason in problem for problem in problems), problems


def test_targets_come_from_the_manifest_entry():
    data = frozen(METER).encode()
    wildcard = data.replace(b".applies_to('_TZE284_2fnssffc', 'TS0601')\n", b".applies_to('_TZE284_2fnssffc', 'TS0601')\n    .applies_to(None, 'TS0601')\n", 1)
    # A wildcard the entry declares is fine; the file's own FINGERPRINTS decide nothing.
    assert SHIPPED.problems(wildcard, targets(METER, fingerprints=[["_TZE284_2fnssffc", "TS0601"], [None, "TS0601"]])) == ()
    assert SHIPPED.problems(data, targets(METER, fingerprints=[["_TZE284_2fnssffc", "TS0602"]]))
    # An alias needs the entry's target: another one, none, or groups that do not hold it refuse it.
    alias = frozen(ALIAS).encode()
    assert SHIPPED.problems(alias, targets(ALIAS, target=["_TZE200_other", "TS0601"]))
    assert SHIPPED.problems(alias, targets(ALIAS, target=None))
    assert SHIPPED.problems(alias, targets(ALIAS, aliases=[{"targets": [["_TZE200_hr0tdd47", "TS0601"]], "fingerprints": []}]))
    # An entry the guard cannot read is no entry: the file is refused.
    for broken in ({"fingerprints": "all"}, {"fingerprints": [["a"]]}, {"target": "x"}, {"aliases": {}}, {"aliases": [{"targets": [["a", "b"]]}]}):
        assert targets(ALIAS, **broken) is None
    assert SHIPPED.problems(alias) == ("line 1: no manifest entry to compare its targets with",)


# The payloads of the guard bypass review, as files a content tag could ship.

NO_FILTER = '''"""VICTIM override.

Generated from the Zigbee2MQTT definition (zigbee-herdsman-converters 1.0, zha-device-handlers abc).
Data: zigbee-herdsman-converters, MIT, Copyright (c) 2018 Koen Kanters.
Status: generated, not verified on hardware.
Revision: 00000000
"""

import functools
import logging
import pathlib

import zhaquirks
from zha.quirks import DEVICE_REGISTRY

from zhaquirks.builder import QuirkBuilder
from zhaquirks.clusters import CustomCluster


_LOGGER = logging.getLogger(__name__)
_SHIPPED = pathlib.Path(zhaquirks.__file__).resolve().parent
_STEPPED_BACK: set = set()

FINGERPRINTS = [('_TZE204_victim', 'TS0601')]
CLAIMED_ELSEWHERE = set()


class HijackCluster(CustomCluster):
    """Attacker cluster swapped onto the victim device; declarative only."""

    cluster_id = 61184
    ep_attribute = "hijack"


(
    QuirkBuilder('_TZE204_victim', 'TS0601')
    .replaces(HijackCluster)
    .add_to_registry()
)
'''


def test_review_payloads_are_refused():
    """Even with a manifest entry written for them: a chain without the upstream-first filter, an
    alias onto a manufacturer wildcard the entry does not declare."""
    victim = guard.Targets.of({"fingerprints": [["_TZE204_victim", "TS0601"]]})
    assert any("without exactly one .filter(no_builtin_quirk)" in p for p in SHIPPED.problems(NO_FILTER.encode(), victim))
    alias = frozen(ALIAS).replace(
        "ALIASES = [{'targets': [('_TZE200_hr0tdd47', 'TS0601')], 'fingerprints': [('JM720ES-EF-3.0', 'TS0601')]}]",
        "ALIASES = [{'targets': [('_TZE200_hr0tdd47', 'TS0601')], 'fingerprints': [('VICTIM_MFR', 'VICTIM_MODEL'), (None, 'TS0601')]}]",
    ).replace("FINGERPRINTS = [('JM720ES-EF-3.0', 'TS0601')]", "FINGERPRINTS = [('VICTIM_MFR', 'VICTIM_MODEL')]")
    offered = guard.Targets.of({"fingerprints": [["VICTIM_MFR", "VICTIM_MODEL"]], "target": ["_TZE200_hr0tdd47", "TS0601"]})
    assert SHIPPED.problems(alias.encode(), offered) == (
        "line 24: targets (None, 'TS0601') (a manufacturer wildcard), which its manifest entry does not list",
        "line 24: an alias group outside the targets and fingerprints of its manifest entry",
    )


def test_problems_name_the_line_and_stay_short():
    text = frozen(TUYA).replace("dp_id=3,", "dp_id=__import__('os').system('x' * 1000),", 1)
    problems = SHIPPED.problems(text.encode(), targets(TUYA))
    line = next(n for n, row in enumerate(text.splitlines(), 1) if "__import__" in row)
    assert problems and problems[0].startswith(f"line {line}: ")
    assert all(len(problem) < 200 for problem in problems)


def test_unparsable_and_deep_files_are_refused():
    assert SHIPPED.problems(b"(\n", targets(TUYA))
    assert SHIPPED.problems(b"\x00", targets(TUYA))
    assert SHIPPED.problems("x = 1\n".encode("utf-16"), targets(TUYA))
    deep = frozen(TUYA).replace("dp_id=3,", "dp_id=" + "-" * 100000 + "3,", 1)
    assert SHIPPED.problems(deep.encode(), targets(TUYA))


ENDPOINTS_FILE = "z2m_moes_zm6lt1.py"


def test_endpoints_must_equal_the_entrys():
    """The runtime check's ENDPOINTS is the entry's endpoints: the integration offers the file only to
    devices that fit them."""
    text = frozen(ENDPOINTS_FILE)
    assert re.search(r"^ENDPOINTS = ", text, re.M)
    assert SHIPPED.problems(text.encode(), targets(ENDPOINTS_FILE)) == ()
    changed = re.sub(r"^ENDPOINTS = .*$", "ENDPOINTS = {2: (0x0006,)}", text, flags=re.M)
    assert any("ENDPOINTS other than its manifest entry's endpoints" in p for p in SHIPPED.problems(changed.encode(), targets(ENDPOINTS_FILE)))
    assert SHIPPED.problems(changed.encode(), targets(ENDPOINTS_FILE, endpoints={"2": [6]})) == ()


@pytest.mark.parametrize("literal", ["{1: [6]}", "{0: (6,)}", "{1: (6, 6)}", "{1: (7, 6)}", "{1: (True,)}", "{'1': (6,)}", "{1: (70000,)}", "{255: ()}", "dict(a=1)"])
def test_endpoints_in_another_shape_are_refused(literal):
    changed = re.sub(r"^ENDPOINTS = .*$", f"ENDPOINTS = {literal}", frozen(ENDPOINTS_FILE), flags=re.M)
    assert SHIPPED.problems(changed.encode(), targets(ENDPOINTS_FILE))


@pytest.mark.parametrize("bad", [{"1": [7, 6]}, {"0": [6]}, {"01": [6]}, {1: [6]}, {"1": "6"}, {"1": [True]}, {}])
def test_an_entry_with_endpoints_in_another_shape_has_no_targets(bad):
    assert guard.Targets.of({**FROZEN[ENDPOINTS_FILE], "endpoints": bad}) is None


TUYA_IMPORT = "from zhaquirks.tuya import TUYA_CLUSTER_ID\n"
CLUSTER_IMPORT = TUYA_IMPORT + "from zigpy.zcl.clusters.general import OnOff\n"
STAND_IN = '(OnOff):\n    """A cluster class in place of the name."""\n'
FROZEN_FINGERPRINTS = "FINGERPRINTS = [('_TZE284_2fnssffc', 'TS0601')]\n"
FROZEN_ENDPOINTS = "ENDPOINTS = {1: (0xEF00,)}\n"
TAKE_OVER = {"over_zha": {"adds": [], "zha_only": []}}


def filter_of(text: str) -> str:
    """The filter's part of the fixed code: the check it calls, then the filter."""
    return text[text.index("def _upstream_first("):]


# The take-over filter in place of the plain one (both from fixed_code.json), as a file whose entry has
# over_zha holds it.
TO_TAKE_OVER = (filter_of(next(text for text in FIXED_CODE["module"] if "def _upstream_first(" in text)), filter_of(FIXED_CODE["take_over"][0]))
# Names the filter reads, bound otherwise than by the fixed code or a literal checked as data: each
# passed the guard before and made the filter raise inside ZHA's device lookup. (replacements, entry changes)
STAND_INS = {
    "CLAIMED_ELSEWHERE as a class": ([("CLAIMED_ELSEWHERE = set()\n", "class CLAIMED_ELSEWHERE" + STAND_IN), (TUYA_IMPORT, CLUSTER_IMPORT)], {}),
    "FINGERPRINTS as a class": ([(FROZEN_FINGERPRINTS, "class FINGERPRINTS" + STAND_IN), (TUYA_IMPORT, CLUSTER_IMPORT)], {}),
    "ENDPOINTS as a class": ([(FROZEN_ENDPOINTS, "class ENDPOINTS" + STAND_IN), (TUYA_IMPORT, CLUSTER_IMPORT)], {"endpoints": None}),
    "DEVICE_REGISTRY and DeviceMatch as classes": ([
        ("from zha.quirks import DEVICE_REGISTRY, DeviceMatch\n", ""), (TUYA_IMPORT, CLUSTER_IMPORT),
        ("\n_LOGGER = ", "\nclass DEVICE_REGISTRY" + STAND_IN + "\n\nclass DeviceMatch" + STAND_IN + "\n_LOGGER = "),
    ], {}),
    "FINGERPRINTS imported from a cluster module": ([(FROZEN_FINGERPRINTS, ""), (TUYA_IMPORT, TUYA_IMPORT + "from zigpy.zcl.clusters.general import FINGERPRINTS\n")], {}),
    # Placeholder strings, as an unfilled alias file holds them: a string where the take-over filter
    # looks a pair up.
    "FINGERPRINTS as a placeholder string": ([TO_TAKE_OVER, (FROZEN_FINGERPRINTS, "FINGERPRINTS = '[]'\n")], TAKE_OVER),
    "ALIASES as a placeholder string": ([("CLAIMED_ELSEWHERE = set()\n", "CLAIMED_ELSEWHERE = set()\nALIASES = '[]'\n")], {}),
    # An empty value: no runtime check, the integration would offer the file to every device.
    "ENDPOINTS empty": ([(FROZEN_ENDPOINTS, "ENDPOINTS = {}\n")], {"endpoints": None}),
    "ENDPOINTS with endpoints out of order": ([(FROZEN_ENDPOINTS, "ENDPOINTS = {5: (), 1: (0xEF00,)}\n")], {"endpoints": {"1": [0xEF00], "5": []}}),
}


@pytest.mark.parametrize(("replacements", "changes"), STAND_INS.values(), ids=STAND_INS)
def test_names_the_filter_reads_come_from_the_fixed_code_and_checked_literals(replacements, changes):
    text = frozen(ENDPOINTS_FILE)
    entry = {key: value for key, value in {**FROZEN[ENDPOINTS_FILE], **changes}.items() if value is not None}
    if "over_zha" in changes:
        # The file with the take-over filter passes.
        assert SHIPPED.problems(text.replace(*TO_TAKE_OVER, 1).encode(), guard.Targets.of(entry)) == ()
    changed = text
    for old, new in replacements:
        assert old in changed
        changed = changed.replace(old, new, 1)
    assert SHIPPED.problems(changed.encode(), guard.Targets.of(entry))


def test_names_the_filter_reads_are_bound_before_the_first_chain():
    """The chain registers the quirk when it runs: an import that fails below it (a cluster class the
    installed zigpy lacks) would leave the names bound after it unbound when ZHA calls the filter."""
    text = frozen(ENDPOINTS_FILE)
    start, end = text.index("\n_LOGGER = logging.getLogger(__name__)"), text.index("\n\n\n@functools.cache")
    block, rest = text[start:end], text[:start] + text[end:]
    chain_end = rest.index(CHAIN_END + ")\n") + len(CHAIN_END) + 2
    moved = rest[:chain_end] + "\nfrom zigpy.zcl.clusters.general import NoSuchCluster\n" + block + "\n"
    problems = SHIPPED.problems(moved.encode(), targets(ENDPOINTS_FILE))
    assert any("bound before the first builder chain" in p and "FINGERPRINTS" in p and "_LOGGER" in p for p in problems), problems
    assert not any("bound before" in p for p in SHIPPED.problems(text.encode(), targets(ENDPOINTS_FILE)))


@pytest.mark.parametrize("cut", ["ENDPOINTS", "CLAIMED_ELSEWHERE", "_misfit", "_is_shipped"])
def test_a_file_without_a_name_its_filter_reads_is_refused(cut):
    """The fixed filter reads these names when ZHA calls it: a file without one would raise there,
    where nothing catches it; also when its entry has no endpoints to compare with."""
    text = frozen(ENDPOINTS_FILE)
    if cut in ("ENDPOINTS", "CLAIMED_ELSEWHERE"):
        changed = re.sub(rf"^{cut} = .*\n", "", text, flags=re.M)
    else:
        start = text.index(f"\ndef {cut}(") if cut == "_misfit" else text.index("\n@functools.cache\ndef _is_shipped(")
        changed = text[:start] + text[text.index("\n\n\ndef ", start + 1):]
    assert changed != text
    problems = SHIPPED.problems(changed.encode(), targets(ENDPOINTS_FILE, endpoints=None))
    assert any(f"the filter needs {cut}" in p or (cut in p and "the filter needs" in p) for p in problems), problems


# Code a payload may hide in a value: the review's payloads and code no quirk file holds.

PAYLOAD = "__import__('os').environ.get('XQ_MARK') and open(__import__('os').environ['XQ_MARK'], 'w').write('payload ran on import')"
BOSCH, TS0105 = "z2m_bosch_bsen_w.py", "z2m_tuya_ts0105.py"
DOCS = '        """Attribute definitions."""\n'
# (quirk file, text to replace, replacement): code no quirk file holds.
QUIRK_PAYLOADS = {
    "review: zcl attribute type": (BOSCH, DOCS, f"{DOCS}        # spare 0x7777: BITMAP64\n        {PAYLOAD}\n        #, attribute only\n"),
    "review: tuya datapoint": (TS0105, "dp_id=3,", f"dp_id=[{PAYLOAD}, 3][1],"),
    "import os": (TS0105, "import functools\n", "import functools\nimport os\n"),
    "import from os": (TS0105, "import functools\n", "import functools\nfrom os import system\n"),
    "import under another name": (TS0105, "import functools\n", "import functools\nfrom zhaquirks import setup as QuirkBuilder\n"),
    "exec": (TS0105, "dp_id=3,", "dp_id=exec('x'),"),
    "eval in a lambda": (TS0105, "dp_id=3,", "dp_id=3, converter=lambda x: eval(x),"),
    "dunder attribute": (TS0105, "dp_id=3,", "dp_id=(3).__class__,"),
    "call through an imported module": (TS0105, "dp_id=3,", "dp_id=pathlib.Path('/tmp/x').write_text('y'),"),
    "power": (TS0105, "dp_id=3,", "dp_id=9 ** 9 ** 9,"),
    "comprehension": (TS0105, "dp_id=3,", "dp_id=[x for x in ()],"),
    "module-level call": (TS0105, ".add_to_registry()\n)\n", ".add_to_registry()\n)\nprint('x')\n"),
    "chain that registers nothing": (TS0105, ".add_to_registry()", ".skip_configuration()"),
    "method in a cluster": (BOSCH, DOCS, f"{DOCS}\n        def evil(self):\n            return 1\n"),
    "metaclass": (BOSCH, "(CustomCluster):", "(CustomCluster, metaclass=type):"),
    "base class from an imported module": (BOSCH, "(CustomCluster):", "(logging.FileHandler):"),
    "class standing in for an import": (TS0105, "\n\n(\n    TuyaQuirkBuilder()", "\n\nclass TuyaQuirkBuilder(t.enum8):\n    x = 1\n\n\n(\n    TuyaQuirkBuilder()"),
    "module value in a chain": (TS0105, "dp_id=3,", "dp_id=_LOGGER.disabled,"),
}


@pytest.mark.parametrize(("name", "old", "new"), QUIRK_PAYLOADS.values(), ids=QUIRK_PAYLOADS)
def test_integration_guard_refuses_code(name, old, new):
    """The files at the user's end, as the integration downloads them."""
    text = frozen(name)
    assert SHIPPED.problems(text.encode(), targets(name)) == ()
    assert old in text
    assert SHIPPED.problems(text.replace(old, new, 1).encode(), targets(name))
