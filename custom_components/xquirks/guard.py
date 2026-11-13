"""Refuse quirk files that hold anything but the shapes a quirk file of this collection may have.

ZHA imports a quirk file into Home Assistant, so its code runs there. This is the core of the
guard: the integration runs it on every file its change list would write, before the list and
again before the write. A file passes only when each of its statements has one of these shapes:

- the module docstring;
- the fixed code (the upstream-first guard with its imports, the alias registration,
  the energy helpers), equal node for node to the source text in fixed_code.json;
- `from X import Y` for a name in IMPORTS or a zigpy cluster class;
- a literal assignment of FINGERPRINTS, CLAIMED_ELSEWHERE, ALIASES or ENDPOINTS, checked as data
  also where it equals a statement of the fixed code (the templates hold empty values there);
- a class with a docstring, nested AttributeDefs and ServerCommandDefs classes of attribute and
  command definitions and the fixed Aqara methods (the file imports what they read); an enum class
  holds integer members the enum can carry, named so that no member stands for anything of the enum
  type (ENUM_MEMBER, ENUM_RESERVED); any other class holds only its data in its allowed
  shape (cluster_id, STRUCT_TAGS, the battery range, _CONSTANT_ATTRIBUTES: integers and
  float factors a cluster or a fixed method computes with) and fixed class statements (STRUCT_TARGETS);
- a QuirkBuilder or TuyaQuirkBuilder chain with the allowed methods (METHODS),
  with exactly one .filter(no_builtin_quirk), ending in add_to_registry().

No class or import takes a name the fixed code binds. Nothing but further chains follows the first
chain: add_to_registry() ran there, so a name bound below it would be unbound when ZHA calls the
quirk if a statement in between failed at import. A file with a chain binds every name the fixed
filter reads when ZHA calls it (FILTER_NEEDS): one missing would raise there, where nothing
catches it. So these names come only from the fixed code and the literals
checked as data, ENDPOINTS among them: every file with a chain has a runtime check.

What a file targets stays inside the manifest entry it is offered for (Targets): the builder's
fingerprints, applies_to, FINGERPRINTS and the fingerprints of ALIASES are literals among the
entry's fingerprints (a manufacturer wildcard only where the entry has it), each ALIASES group
lies inside one alias group of the entry, CLAIMED_ELSEWHERE (empty without one) equals the entry's
claimed_elsewhere, ENDPOINTS (the endpoints the runtime check needs, absent from an alias file)
equals the entry's endpoints. The filter variant that keeps the file for its exact names over ZHA's own quirk
(fixed code "take_over") stands in a file exactly when its entry has over_zha. The integration
keeps the entry's names as what an installed file claims: they cover what the file registers.
Without an entry a file is refused.

Values in classes and chains are literals, the names the file imports or defines and the
allowed attribute paths: cluster ids, attribute and command names, enum members,
zigpy types. Converters are `lambda x:` over arithmetic, comparisons and calls of a short list
(bool, int, str, t.Bool, the file's enum classes and helpers, TuyaCoverControl); a product is x
times a number literal, an integer one of at most MAX_FACTOR, one product per Tuya converter
(`converter=`) at most and none in an attribute_converter or dp_converter; other arithmetic has a
number literal on one side; a converter holds no list, tuple or set and x stands in a dict only as
the key looked up. Nothing else: no other statement, import, call, builtin or attribute, no dunder
name, no name bound twice, no coding declaration.

Standard library only, no Home Assistant import: it can be loaded by its path. fixed_code.json
ships with the integration, is parsed here with
the running Python (ast.dump differs between Python versions) and never comes from a content tag.
"""

from __future__ import annotations

import ast
import builtins
import hashlib
import json
import math
import pathlib
import re

HERE = pathlib.Path(__file__).resolve().parent
FIXED_CODE = "fixed_code.json"
# Reasons kept per refused file.
MAX_PROBLEMS = 20
# The largest integer a converter multiplies x by. A Tuya string or raw value has at most 255 bytes
# (zhaquirks reads its length as one byte), so a device that sends one where a number is meant makes
# a Tuya converter repeat it to at most 255 kB: it holds one product at most, no other arithmetic
# joins two such values and no container holds one (QuirkFile.converter, QuirkFile.expr). Only the
# Tuya converters (`converter=`) get such a value: an attribute_converter gets a ZCL attribute, which
# a device may send as a long string, a dp_converter the value written. Neither may hold a product.
# Quirk files stay below the limit: a larger integer scale is a float there (a string times a float
# raises); a climate datapoint that would need a larger factor is left out.
MAX_FACTOR = 1000

# What a quirk may do with a name it imports.
BUILDER = "builder"  # start a chain: QuirkBuilder(...)
DEFINITION = "definition"  # call it in a class body: ZCLAttributeDef(...)
MAPPING = "mapping"  # call it in a chain argument: DPToAttributeMapping(...)
CONVERTER = "converter"  # call it in a converter: TuyaCoverControl(...)
ENUM = "enum"  # read its members: EntityType.CONFIG
VALUE = "value"  # use the name itself: TUYA_CLUSTER_ID
CLUSTER = "cluster"  # a cluster class: base, added cluster, its ids and attribute names
ATTRIBUTE_DEFS = "attribute defs"  # the base of a nested AttributeDefs class
COMMAND_DEFS = "command defs"  # the base of a nested ServerCommandDefs class
FOUNDATION = "foundation"  # zigpy's foundation module: foundation.ZCLAttributeAccess.Read

# The `from X import Y` a quirk file may hold, with what it may do with Y.
IMPORTS: dict[str, dict[str, str]] = {
    "zhaquirks.builder": {
        "QuirkBuilder": BUILDER,
        **dict.fromkeys(("EntityPlatform", "EntityType", "SensorStateClass", "SensorDeviceClass", "BinarySensorDeviceClass", "NumberDeviceClass"), ENUM),
        **dict.fromkeys(
            (
                "UnitOfElectricCurrent", "UnitOfElectricPotential", "UnitOfEnergy", "UnitOfFrequency", "UnitOfLength", "UnitOfPower",
                "UnitOfPressure", "UnitOfSoundPressure", "UnitOfTemperature", "UnitOfTime", "UnitOfVolume",
            ),
            ENUM,
        ),
        **dict.fromkeys(
            (
                "PERCENTAGE", "LIGHT_LUX", "SIGNAL_STRENGTH_DECIBELS", "CONCENTRATION_PARTS_PER_MILLION", "CONCENTRATION_PARTS_PER_BILLION",
                "CONCENTRATION_MICROGRAMS_PER_CUBIC_METER", "CONCENTRATION_MILLIGRAMS_PER_CUBIC_METER",
            ),
            VALUE,
        ),
    },
    "zhaquirks.tuya.builder": {"TuyaQuirkBuilder": BUILDER},
    "zhaquirks.tuya": {"TUYA_CLUSTER_ID": VALUE},
    "zhaquirks.tuya.mcu": {"DPToAttributeMapping": MAPPING, "TuyaCoverControl": CONVERTER, "TuyaMCUCluster": CLUSTER, "TuyaWindowCovering": CLUSTER},
    "zhaquirks.tuya.tuya_motion": {"TuyaOccupancySensing": CLUSTER},
    "zhaquirks.tuya.tuya_trv": {"TuyaThermostatV2": CLUSTER},
    "zhaquirks": {"LocalDataCluster": CLUSTER},
    "zhaquirks.clusters": {"CustomCluster": CLUSTER},
    "zhaquirks.const": dict.fromkeys(
        (*(f"BUTTON_{n}" for n in range(1, 9)), "COMMAND", "COMMAND_HOLD", "COMMAND_SINGLE", "COMMAND_DOUBLE", "COMMAND_TRIPLE", "COMMAND_RELEASE"), VALUE
    ),
    "zhaquirks.xiaomi": dict.fromkeys(("XiaomiAqaraE1Cluster", "DeviceTemperatureCluster", "XiaomiPowerConfiguration", "ElectricalMeasurementCluster", "MeteringCluster"), CLUSTER),
    "zhaquirks.xiaomi.aqara.opple_remote": {"MultistateInputCluster": CLUSTER},
    "zigpy.profiles.zha": {"DeviceType": ENUM},
    "zigpy.zcl": {"foundation": FOUNDATION},
    "zigpy.zcl.foundation": {"ZCLAttributeDef": DEFINITION, "ZCLCommandDef": DEFINITION, "BaseAttributeDefs": ATTRIBUTE_DEFS, "BaseCommandDefs": COMMAND_DEFS, "Direction": ENUM},
    "zigpy.zcl.clusters.hvac": {"RunningState": ENUM},
}
# Any class of these modules is a cluster (gen_zcl imports zigpy's class of a standard cluster).
CLUSTER_MODULES = frozenset(
    f"zigpy.zcl.clusters.{name}"
    for name in ("closures", "general", "greenpower", "homeautomation", "hvac", "lighting", "lightlink", "measurement", "protocol", "security", "smartenergy")
)
# The builder methods a chain may call, by builder (every chain also calls the filter).
_SHARED = ("applies_to", "adds", "binary_sensor", "enum", "filter", "sensor", "switch", "add_to_registry")
METHODS = {
    "QuirkBuilder": frozenset((*_SHARED, "replaces", "number", "write_attr_button", "command_button", "device_automation_triggers")),
    "TuyaQuirkBuilder": frozenset(
        (
            *_SHARED, "replaces_endpoint", "skip_configuration", "tuya_attribute", "tuya_binary_sensor", "tuya_cover", "tuya_dp", "tuya_dp_attribute",
            "tuya_dp_multi", "tuya_enum", "tuya_illuminance", "tuya_number", "tuya_onoff", "tuya_sensor", "tuya_switch",
            # gen_tuya.STANDARD_NUMERIC
            "tuya_battery", "tuya_co2", "tuya_humidity", "tuya_soil_moisture", "tuya_temperature",
        )
    ),
}
# The keywords whose value is a converter lambda (and nothing else).
CONVERTER_KEYWORDS = frozenset({"converter", "dp_converter", "attribute_converter"})
# zigpy types a quirk names as t.X (gen_zcl.ZCL_TYPES and COMMAND_TYPES, gen_tuya's attribute types).
TYPE_NAMES = frozenset(
    {"Bool", "uint8_t", "uint16_t", "uint24_t", "uint32_t", "uint48_t", "int8s", "int16s", "int24s", "int32s", "enum8", "enum16", "bitmap8", "bitmap16", "Single",
     "CharacterString", "LVBytes"}
)
ENUM_BASES = ("enum8", "enum16")
# t.List[t.uint8_t]: herdsman's LIST_UINT8 command parameter.
TYPE_LISTS = ("List",)
# Enums nested in a cluster class: Thermostat.SystemMode.Heat.
CLUSTER_ENUMS = frozenset({"SystemMode"})
# The cluster attribute a dict may spread: {**TuyaThermostatV2._CONSTANT_ATTRIBUTES, ...}.
SPREAD = "_CONSTANT_ATTRIBUTES"
# The data a cluster class holds besides the fixed class statements (STRUCT_TARGETS, the outage
# cluster's), each in its one allowed shape: the cluster or a fixed method computes
# with it and a device value, so a string or a sequence there would repeat a report's value, an
# empty battery range would divide by zero. The Aqara struct tags with the key the Xiaomi base
# routes each one under (gen_zcl.METER_TAGS), each with a float factor (a sequence times a float raises).
STRUCT_TAG_KEYS = {149: "consumption", 150: "voltage", 151: "current", 152: "power"}
# The battery range of zhaquirks' XiaomiPowerConfiguration in mV (gen_zcl: z2m's range).
VOLTS = ("MIN_VOLTS_MV", "MAX_VOLTS_MV")
VOLTS_RANGE = range(1000, 5001)
# The values of _CONSTANT_ATTRIBUTES: setpoint limits in 0.01 °C, a current multiplier and divisor.
CONSTANT_RANGE = range(-0x8000, 0x10000)
# Names an enum member must not take: what zigpy's t.enum8 and t.enum16 (and an Enum member) have,
# which zigpy and the converters call (a test keeps it complete). Names that start
# with an underscore (_missing_, _order_) are refused anyway.
ENUM_RESERVED = frozenset({
    "as_integer_ratio", "bit_count", "bit_length", "bits", "conjugate", "denominator", "deserialize", "from_bits", "from_bytes", "imag",
    "is_integer", "max_value", "min_value", "mro", "name", "numerator", "real", "serialize", "to_bytes", "value",
})
BUILTINS = frozenset({"bool", "int", "str"})
TYPE_CALLS = frozenset({"Bool"})
NESTED = {"AttributeDefs": ATTRIBUTE_DEFS, "ServerCommandDefs": COMMAND_DEFS}
# The fixed function every chain filters with, exactly once.
FILTER = "no_builtin_quirk"
# What the fixed filter and its helpers read (and their module statements bind): a file with a chain
# binds each of them, so the filter cannot raise NameError inside ZHA's device lookup.
FILTER_NEEDS = frozenset({
    "functools", "logging", "pathlib", "zhaquirks", "DEVICE_REGISTRY", "DeviceMatch", "_LOGGER", "_SHIPPED", "_STEPPED_BACK",
    "FINGERPRINTS", "CLAIMED_ELSEWHERE", "ENDPOINTS", "_is_shipped", "_shipped_quirk", "_misfit", "_upstream_first", FILTER,
})
# The fingerprints a builder takes when it starts its chain (gen_zcl: QuirkBuilder(manufacturer, model)).
ROOT_ARGS = {"QuirkBuilder": 2, "TuyaQuirkBuilder": 0}
# The module-level literals the templates fill with data.
LITERALS = frozenset({"FINGERPRINTS", "CLAIMED_ELSEWHERE", "ALIASES", "ENDPOINTS"})

# Where a value stands; the imported callables each place may call.
CHAIN, LAMBDA, CLASS = "chain", "lambda", "class"
CALLS = {CHAIN: MAPPING, LAMBDA: CONVERTER, CLASS: DEFINITION}
OPERATORS = {CHAIN: (ast.BitOr,), LAMBDA: (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv), CLASS: ()}
CMPOPS = (ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE)

MEMBER = re.compile(r"[A-Z][A-Za-z0-9_]*")
# An enum member's name in a class of the file: a letter first, or (as ZHA's own quirks name an option
# that starts with a digit) an underscore and a digit, never an Enum hook such as _missing_ or _order_.
ENUM_MEMBER = re.compile(r"[A-Za-z][A-Za-z0-9_]*|_[0-9](?:[A-Za-z0-9_]*[A-Za-z0-9])?")
NAME = re.compile(r"[A-Za-z][A-Za-z0-9_]*")
CLASS_NAME = re.compile(r"[A-Z][A-Za-z0-9_]*")
# A coding declaration (PEP 263) on one of the first two lines.
CODING = re.compile(rb"^[ \t\f]*#.*?coding[:=]")
LINE_BREAK = re.compile(rb"\r\n|\r|\n")


class Refused(Exception):
    def __init__(self, node: ast.AST, reason: str) -> None:
        super().__init__(reason)
        self.node = node
        self.reason = reason


# The layout of a content tag this release reads: manifest.json, hacs.json and the file layout.
# Raise it when one of them changes in a way an older release would misread: it is part of the
# guard identity, so older releases skip the tags of the new layout. The fields of
# data/withdrawn.toml (file, revision, reason) never change: every release reads them from a newer tag.
FORMAT = 1


def identity(guard_source: bytes, fixed_source: bytes) -> str:
    """The guard a content tag names in its content.json: the sha256 of FORMAT, this file and
    fixed_code.json as the release ships them. Another guard reads the tag's files otherwise."""
    return hashlib.sha256(f"{FORMAT}\n".encode() + hashlib.sha256(guard_source).digest() + hashlib.sha256(fixed_source).digest()).hexdigest()


def bound_names(stmt: ast.stmt) -> list[str]:
    """The module-level names a statement binds: imports, classes, functions, assignments."""
    if isinstance(stmt, (ast.Import, ast.ImportFrom)):
        return [a.asname or a.name.partition(".")[0] if isinstance(stmt, ast.Import) else a.asname or a.name for a in stmt.names]
    if isinstance(stmt, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
        return [stmt.name]
    if isinstance(stmt, (ast.Assign, ast.AnnAssign)):
        targets = stmt.targets if isinstance(stmt, ast.Assign) else [stmt.target]
        return [n.id for t in targets for n in (t.elts if isinstance(t, ast.Tuple) else [t]) if isinstance(n, ast.Name)]
    return []


def free_names(function: ast.FunctionDef) -> frozenset[str]:
    """The module-level names a function reads: loaded in it, bound nowhere in it, no builtin."""
    bound = {node.arg for node in ast.walk(function) if isinstance(node, ast.arg)}
    bound |= {node.id for node in ast.walk(function) if isinstance(node, ast.Name) and not isinstance(node.ctx, ast.Load)}
    loaded = {node.id for node in ast.walk(function) if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load)}
    return frozenset(loaded - bound - set(dir(builtins)))


def _int_in(node: ast.expr, allowed: range) -> bool:
    """An integer literal (a negative one too, no bool) inside the range."""
    negative = isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub)
    if negative:
        node = node.operand
    if not (isinstance(node, ast.Constant) and type(node.value) is int):
        return False
    return (-node.value if negative else node.value) in allowed


def _struct_tag(key: ast.expr | None, value: ast.expr) -> bool:
    """149: ('consumption', 1.0): a tag of STRUCT_TAG_KEYS, the key routed for it and a finite float
    factor above 0 and at most MAX_FACTOR."""
    if not (isinstance(key, ast.Constant) and type(key.value) is int and key.value in STRUCT_TAG_KEYS):
        return False
    if not (isinstance(value, ast.Tuple) and len(value.elts) == 2):
        return False
    routed, factor_node = value.elts
    return (isinstance(routed, ast.Constant) and routed.value == STRUCT_TAG_KEYS[key.value] and isinstance(factor_node, ast.Constant)
            and type(factor_node.value) is float and math.isfinite(factor_node.value) and 0 < factor_node.value <= MAX_FACTOR)


class Fixed:
    """The fixed code, parsed with the running Python from its source text: module
    statements, the methods of the Aqara cluster class, the helpers a converter may call."""

    def __init__(self, sources: object) -> None:
        if not isinstance(sources, dict) or not all(isinstance(sources.get(key), list) and all(isinstance(text, str) for text in sources[key]) for key in ("module", "helpers", "class", "take_over")):
            raise ValueError("fixed code: module, helpers, class and take_over must be lists of source texts")
        helpers = [stmt for text in sources["helpers"] for stmt in ast.parse(text).body]
        statements = [stmt for key in ("module", "take_over") for text in sources[key] for stmt in ast.parse(text).body] + helpers
        module = frozenset(ast.dump(stmt) for text in sources["module"] for stmt in ast.parse(text).body) | {ast.dump(stmt) for stmt in helpers}
        # The statements only a file that takes devices over from ZHA's own quirk holds.
        self.take_over = frozenset(ast.dump(stmt) for text in sources["take_over"] for stmt in ast.parse(text).body) - module
        self.module = module | self.take_over
        class_statements = [stmt for text in sources["class"] for stmt in ast.parse(text).body[0].body]
        self.methods = frozenset(ast.dump(stmt) for stmt in class_statements)
        # What each fixed method reads from the module: a file that holds the method imports each one.
        self.reads = {ast.dump(stmt): free_names(stmt) for stmt in class_statements if isinstance(stmt, ast.FunctionDef)}
        self.helpers = frozenset(stmt.name for stmt in helpers if isinstance(stmt, ast.FunctionDef))
        # The module-level names the fixed code binds: no class or import of a file takes one.
        self.names = frozenset(name for stmt in statements for name in bound_names(stmt))


def _pair(value: object) -> tuple[str | None, str] | None:
    """A fingerprint (manufacturer or None, model) as the manifest holds it, None for anything else."""
    if isinstance(value, (list, tuple)) and len(value) == 2 and (value[0] is None or isinstance(value[0], str)) and isinstance(value[1], str):
        return (value[0], value[1])
    return None


def _pairs(value: object) -> frozenset[tuple[str | None, str]] | None:
    pairs = [_pair(item) for item in value] if isinstance(value, list) else [None]
    return None if None in pairs else frozenset(pairs)


def _uint(value: object, low: int, high: int) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and low <= value <= high


def endpoint_map(value: object, keys: type) -> dict[int, tuple[int, ...]] | None:
    """Endpoint id (1 to 254) -> sorted distinct input cluster ids, as the manifest holds them: keys
    of type int in ascending order in a file's ENDPOINTS (the runtime check reports the first misfit
    in that order), decimal strings in a manifest entry's endpoints; None for anything else."""
    if not isinstance(value, dict) or not value:
        return None
    if keys is int and (not all(_uint(key, 1, 254) for key in value) or list(value) != sorted(value)):
        return None
    out = {}
    for key, ids in value.items():
        if keys is str:
            if not (isinstance(key, str) and key.isascii() and key.isdigit() and str(int(key)) == key):
                return None
            key = int(key)
        if not _uint(key, 1, 254) or not isinstance(ids, (tuple if keys is int else list)):
            return None
        if not all(_uint(i, 0, 0xFFFF) for i in ids) or list(ids) != sorted(set(ids)):
            return None
        out[key] = tuple(ids)
    return out


class Targets:
    """What a manifest entry lets its file target: the entry's fingerprints, the names it leaves to
    other devices (claimed_elsewhere), its alias groups (shipped targets with the fingerprints
    that get them) and whether it takes its exact names over from ZHA's own quirk (over_zha)."""

    def __init__(self, fingerprints: frozenset, groups: tuple[tuple[frozenset, frozenset], ...], claimed: frozenset = frozenset(), takes_over: bool = False,
                 endpoints: dict[int, tuple[int, ...]] | None = None) -> None:
        self.fingerprints = fingerprints
        self.groups = groups
        self.claimed = claimed
        self.takes_over = takes_over
        self.endpoints = endpoints
        # For caches: verdicts depend on the content and on these.
        self.key = repr((sorted(fingerprints, key=repr), [(sorted(t, key=repr), sorted(f, key=repr)) for t, f in groups], sorted(claimed, key=repr), takes_over,
                         sorted((endpoints or {}).items())))

    @classmethod
    def of(cls, entry: object) -> Targets | None:
        """The targets of a manifest entry; None without an entry or when its fingerprints, target
        or alias groups are not in the shape the manifest holds."""
        if not isinstance(entry, dict) or (fingerprints := _pairs(entry.get("fingerprints"))) is None:
            return None
        if (claimed := _pairs(entry.get("claimed_elsewhere", []))) is None:
            return None
        endpoints = None
        if entry.get("endpoints") is not None and (endpoints := endpoint_map(entry["endpoints"], str)) is None:
            return None
        over_zha = entry.get("over_zha")
        if over_zha is not None and not (
            isinstance(over_zha, dict) and set(over_zha) == {"adds", "zha_only"}
            and all(isinstance(names, list) and all(isinstance(name, str) for name in names) for names in over_zha.values())
        ):
            return None
        groups = []
        if entry.get("aliases") is not None:
            if not isinstance(entry["aliases"], list):
                return None
            for group in entry["aliases"]:
                if not isinstance(group, dict) or (targets := _pairs(group.get("targets"))) is None or (members := _pairs(group.get("fingerprints"))) is None:
                    return None
                groups.append((targets, members))
        elif entry.get("target") is not None:
            if (target := _pair(entry["target"])) is None:
                return None
            groups.append((frozenset({target}), fingerprints))
        return cls(fingerprints, tuple(groups), claimed, over_zha is not None, endpoints)


class Guard:
    """The guard as a release ships it: its identity and its fixed code."""

    def __init__(self, guard_source: bytes, fixed_source: bytes) -> None:
        self.id = identity(guard_source, fixed_source)
        self.fixed = Fixed(json.loads(fixed_source))

    @classmethod
    def load(cls, folder: pathlib.Path = HERE) -> Guard:
        """This file and fixed_code.json next to it (blocking I/O)."""
        return cls((folder / pathlib.Path(__file__).name).read_bytes(), (folder / FIXED_CODE).read_bytes())

    def problems(self, content: bytes, targets: Targets | None = None) -> tuple[str, ...]:
        """Why the guard refuses a quirk file offered with these targets ("line N: reason", at most
        MAX_PROBLEMS); empty when it passes. Without targets it is refused."""
        return tuple(f"line {line}: {reason}" for line, reason in check_quirk(content, self.fixed, targets)[:MAX_PROBLEMS])


def docstring(stmt: ast.stmt) -> bool:
    return isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant) and isinstance(stmt.value.value, str)


def literal(node: ast.expr) -> bool:
    """A literal: constants and the containers of constants that ast.literal_eval reads."""
    if isinstance(node, ast.Constant):
        return True
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
        return isinstance(node.operand, ast.Constant) and type(node.operand.value) in (int, float)
    if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        return all(literal(e) for e in node.elts)
    if isinstance(node, ast.Dict):
        return all(k is not None and literal(k) for k in node.keys) and all(literal(v) for v in node.values)
    return False


def number(node: ast.expr) -> bool:
    """A number literal: 10, 0.5, -3."""
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
        node = node.operand
    return isinstance(node, ast.Constant) and type(node.value) in (int, float)


def factor(node: ast.expr) -> bool:
    """A number literal a converter may multiply x by: any float (a string times a float raises) or
    an integer of at most MAX_FACTOR."""
    if not number(node):
        return False
    value = (node.operand if isinstance(node, ast.UnaryOp) else node).value
    return type(value) is float or abs(value) <= MAX_FACTOR


def literal_assignment(stmt: ast.stmt) -> bool:
    """NAME = literal, or NAME, NAME = literal."""
    if not isinstance(stmt, ast.Assign) or len(stmt.targets) != 1:
        return False
    target = stmt.targets[0]
    names = target.elts if isinstance(target, ast.Tuple) else [target]
    return all(isinstance(n, ast.Name) and not n.id.startswith("__") for n in names) and literal(stmt.value)


def dotted(node: ast.expr) -> str | None:
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        return ".".join([node.id, *reversed(parts)])
    return None


def _short(node: ast.AST) -> str:
    text = ast.unparse(node)
    return text if len(text) <= 80 else text[:77] + "..."


def kind_of(module: str, name: str) -> str:
    """What a quirk may do with `from module import name`; "" for a name it may not import."""
    found = IMPORTS.get(module, {}).get(name)
    if found:
        return found
    return CLUSTER if module in CLUSTER_MODULES and CLASS_NAME.fullmatch(name) else ""


class QuirkFile:
    """The allowlist applied to one parsed quirk file."""

    def __init__(self, tree: ast.Module, fixed: Fixed) -> None:
        self.tree = tree
        self.fixed = fixed
        # What the file targets, as read: (node, fingerprint) of builders, applies_to, FINGERPRINTS
        # and ALIASES; (node, targets, fingerprints) of each ALIASES group.
        self.aims: list[tuple[ast.AST, tuple[str | None, str]]] = []
        self.alias_groups: list[tuple[ast.AST, frozenset, frozenset]] = []
        # CLAIMED_ELSEWHERE as read (empty without one): the names the file leaves to other devices.
        self.claimed: frozenset = frozenset()
        # ENDPOINTS as read (None without one): what the runtime check needs on the device.
        self.endpoints: dict[int, tuple[int, ...]] | None = None
        # A builder chain with the filter: the file must bind FILTER_NEEDS before its first chain.
        self.filtered = False
        self.first_chain: int | None = None  # the index of the first chain statement
        # The filter variant that keeps the file for its exact names over ZHA's own quirk.
        self.takes_over = False
        self.imported: dict[str, str] = {}  # from-imported name -> its kind ("" when only the fixed code uses it)
        self.modules: dict[str, str] = {}  # name of a plain import -> module
        self.classes: dict[str, ast.ClassDef] = {}
        # The file's enum classes (bases t.enum8, t.enum16) -> their members.
        self.enums: dict[str, set[str]] = {}
        self.functions: set[str] = set()
        self.values: set[str] = set()
        # Each name is bound once: a class must not stand in for an imported QuirkBuilder.
        self.twice: list[tuple[ast.stmt, str]] = []
        # Name -> the index of the statement that binds it.
        self.where: dict[str, int] = {}
        for index, stmt in enumerate(tree.body):
            names = bound_names(stmt)
            if isinstance(stmt, ast.ImportFrom):
                self.imported.update({a.asname or a.name: "" if a.asname else kind_of(stmt.module or "", a.name) for a in stmt.names})
            elif isinstance(stmt, ast.Import):
                self.modules.update({a.asname or a.name: a.name for a in stmt.names})
            elif isinstance(stmt, ast.ClassDef):
                self.classes[stmt.name] = stmt
            elif isinstance(stmt, ast.FunctionDef):
                self.functions.add(stmt.name)
            elif isinstance(stmt, (ast.Assign, ast.AnnAssign)):
                self.values.update(names)
            self.twice += [(stmt, name) for name in names if name in self.where]
            for name in names:
                self.where.setdefault(name, index)
        self.bound = frozenset(self.where)
        for name, node in self.classes.items():
            if node.bases and all(self.zigpy_type(base, ENUM_BASES) for base in node.bases):
                self.enums[name] = {s.targets[0].id for s in node.body if isinstance(s, ast.Assign) and len(s.targets) == 1 and isinstance(s.targets[0], ast.Name)}

    def problems(self, targets: Targets | None) -> list[tuple[ast.AST, str]]:
        out = [(stmt, f"name {name} bound twice") for stmt, name in self.twice]
        for index, stmt in enumerate(self.tree.body):
            try:
                self.statement(stmt, index)
            except Refused as refused:
                out.append((refused.node, refused.reason))
        if self.filtered:
            if missing := FILTER_NEEDS - self.bound:
                out.append((self.tree, f"the filter needs {', '.join(sorted(missing))}, which the file does not define"))
            # add_to_registry() ran once the first chain did: a statement after it that fails at import
            # would leave a name bound below it unbound when ZHA calls the filter.
            if late := sorted(name for name in FILTER_NEEDS & self.bound if self.where[name] > self.first_chain):
                out.append((self.tree, f"the filter needs {', '.join(late)} bound before the first builder chain"))
        return out + self.targeting(targets)

    def targeting(self, targets: Targets | None) -> list[tuple[ast.AST, str]]:
        """What the file targets outside the manifest entry it is offered for."""
        if targets is None:
            return [(self.tree, "no manifest entry to compare its targets with")]
        out = []
        for node, pair in self.aims:
            if pair not in targets.fingerprints:
                wildcard = " (a manufacturer wildcard)" if pair[0] is None else ""
                out.append((node, f"targets {_quoted(pair)}{wildcard}, which its manifest entry does not list"))
        for node, group_targets, members in self.alias_groups:
            if not any(group_targets <= allowed and members <= names for allowed, names in targets.groups):
                out.append((node, "an alias group outside the targets and fingerprints of its manifest entry"))
        if self.claimed != targets.claimed:
            # The integration reads what an installed file claims from the entry it was written for.
            out.append((self.tree, "CLAIMED_ELSEWHERE other than its manifest entry's claimed_elsewhere"))
        if self.endpoints != targets.endpoints:
            # The integration offers a file only to devices that fit its entry's endpoints.
            out.append((self.tree, "ENDPOINTS other than its manifest entry's endpoints"))
        if self.takes_over != targets.takes_over:
            # The integration offers a file over ZHA's own quirk only where its entry says so.
            out.append((self.tree, "takes devices over from ZHA's own quirk, which its manifest entry does not say" if self.takes_over
                        else "its manifest entry says it takes devices over from ZHA's own quirk, its filter does not"))
        return out

    def aim(self, node: ast.AST, values: list[ast.expr]) -> None:
        """A fingerprint written as two arguments: literal (manufacturer or None, model)."""
        if len(values) != 2 or not all(isinstance(v, ast.Constant) for v in values) or (pair := _pair([v.value for v in values])) is None:
            raise Refused(node, "a target that is no literal (manufacturer, model)")
        self.aims.append((node, pair))

    def literal_targets(self, stmt: ast.Assign) -> None:
        """FINGERPRINTS, CLAIMED_ELSEWHERE, ENDPOINTS and ALIASES as the templates write them."""
        try:
            name, value = stmt.targets[0].id, ast.literal_eval(stmt.value)
        except (ValueError, TypeError, SyntaxError, MemoryError, RecursionError) as error:
            raise Refused(stmt, f"a literal that does not evaluate ({type(error).__name__})") from None
        if name == "FINGERPRINTS":
            if not isinstance(value, list) or not all(isinstance(item, tuple) and _pair(item) for item in value):
                raise Refused(stmt, "FINGERPRINTS other than a list of (manufacturer, model)")
            self.aims += [(stmt, _pair(item)) for item in value]
        elif name == "CLAIMED_ELSEWHERE":
            if not isinstance(value, (set, list)) or not all(isinstance(item, tuple) and _pair(item) and item[0] is not None for item in value):
                raise Refused(stmt, "CLAIMED_ELSEWHERE other than a set of (manufacturer, model)")
            self.claimed = frozenset(_pair(item) for item in value)
        elif name == "ENDPOINTS":
            if (endpoints := endpoint_map(value, int)) is None:
                raise Refused(stmt, "ENDPOINTS other than ascending endpoint ids with sorted tuples of cluster ids")
            self.endpoints = endpoints
        elif name == "ALIASES":
            if not isinstance(value, list) or not all(isinstance(group, dict) and set(group) == {"targets", "fingerprints"} for group in value):
                raise Refused(stmt, "ALIASES other than a list of {targets, fingerprints}")
            for group in value:
                if not all(isinstance(items, list) and all(isinstance(item, tuple) for item in items) for items in group.values()):
                    raise Refused(stmt, "an ALIASES group other than lists of (manufacturer, model)")
                group_targets, members = _pairs(group["targets"]), _pairs(group["fingerprints"])
                if group_targets is None or members is None:
                    raise Refused(stmt, "an ALIASES group other than lists of (manufacturer, model)")
                self.alias_groups.append((stmt, group_targets, members))
                self.aims += [(stmt, pair) for pair in members]

    def zigpy_type(self, node: ast.expr, names) -> bool:
        """t.X with X in names, t being zigpy.types."""
        parts = (dotted(node) or "").split(".")
        return len(parts) == 2 and parts[0] == "t" and self.modules.get("t") == "zigpy.types" and parts[1] in names

    def statement(self, stmt: ast.stmt, index: int) -> None:
        if index == 0 and docstring(stmt):
            return
        # add_to_registry() ran once the first chain did: a statement after it that fails at import
        # (an import of a name the module lacks) would leave what it binds unbound when ZHA calls the
        # quirk (the filter, a fixed method, a converter's helper). Chains come last.
        if self.first_chain is not None and not (isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call)):
            raise Refused(stmt, f"{type(stmt).__name__} statement after the first builder chain")
        if literal_assignment(stmt) and isinstance(stmt.targets[0], ast.Name) and stmt.targets[0].id in LITERALS:
            # Data, also where it equals a template statement: the filter reads these values.
            return self.literal_targets(stmt)
        if (dumped := ast.dump(stmt)) in self.fixed.module:
            self.takes_over |= dumped in self.fixed.take_over
            return  # the fixed code
        if isinstance(stmt, ast.Import):
            raise Refused(stmt, "import " + ", ".join(a.name + (f" as {a.asname}" if a.asname else "") for a in stmt.names))
        if isinstance(stmt, ast.ImportFrom):
            if stmt.level or not stmt.module:
                raise Refused(stmt, f"import from {'.' * stmt.level}{stmt.module or ''}")
            for alias in stmt.names:
                if alias.asname or not kind_of(stmt.module, alias.name):
                    raise Refused(stmt, f"import of {alias.name}{' as ' + alias.asname if alias.asname else ''} from {stmt.module}")
                if alias.name in self.reserved:
                    raise Refused(stmt, f"import of {alias.name}, a name the fixed code binds")
        elif isinstance(stmt, ast.ClassDef):
            self.class_def(stmt)
        elif isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
            if self.first_chain is None:
                self.first_chain = index
            self.chain(stmt.value)
        else:
            raise Refused(stmt, f"{type(stmt).__name__} statement")

    @property
    def reserved(self) -> frozenset[str]:
        """The names only the fixed code and the literals checked as data bind."""
        return self.fixed.names | FILTER_NEEDS | LITERALS

    def class_def(self, node: ast.ClassDef, nested: bool = False) -> None:
        if node.decorator_list or node.keywords or getattr(node, "type_params", None):
            raise Refused(node, f"class {node.name} with decorators, keywords or type parameters")
        if not CLASS_NAME.fullmatch(node.name):
            raise Refused(node, f"class name {node.name}")
        if not nested and node.name in self.reserved:
            raise Refused(node, f"class {node.name}, a name the fixed code binds")
        if nested and node.name not in NESTED:
            raise Refused(node, f"nested class {node.name}")
        if not node.bases:
            raise Refused(node, f"class {node.name} without a base")
        for base in node.bases:
            if not (self.nested_base(base, node.name) if nested else self.base(base)):
                raise Refused(base, f"base class {_short(base)}")
        values: dict[str, ast.Assign] = {}
        for index, stmt in enumerate(node.body):
            if index == 0 and docstring(stmt):
                continue
            if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Name) and not stmt.targets[0].id.startswith("__"):
                if nested:
                    # A member of AttributeDefs or ServerCommandDefs: a definition.
                    if not isinstance(stmt.value, ast.Call):
                        raise Refused(stmt, f"{stmt.targets[0].id} in {node.name} other than a definition")
                    self.expr(stmt.value, CLASS)
                elif node.name in self.enums:
                    self.enum_member(stmt, node)
                else:
                    self.class_value(stmt, node)
                    values[stmt.targets[0].id] = stmt
            elif isinstance(stmt, ast.ClassDef) and not nested:
                self.class_def(stmt, nested=True)
            elif isinstance(stmt, ast.FunctionDef) and not nested and (dumped := ast.dump(stmt)) in self.fixed.methods:
                # The Aqara helpers: what one reads from the module (ElectricalMeasurement), the file imports.
                if missing := sorted(name for name in self.fixed.reads.get(dumped, ()) if not self.imported.get(name)):
                    raise Refused(stmt, f"method {stmt.name} reads {', '.join(missing)}, which the file does not import")
            else:
                raise Refused(stmt, f"{type(stmt).__name__} statement in class {node.name}")
        if set(VOLTS) & set(values):
            low, high = (values.get(name) for name in VOLTS)
            if low is None or high is None or not low.value.value < high.value.value:
                raise Refused(node, f"class {node.name}: {VOLTS[0]} below {VOLTS[1]}, both or neither")

    def enum_member(self, stmt: ast.Assign, node: ast.ClassDef) -> None:
        """An enum member: a name ENUM_MEMBER allows that stands for nothing of the enum type
        (ENUM_RESERVED: _missing_ or serialize would replace what zigpy calls), an integer the enum
        holds (t.enum8: 0 to 255, t.enum16: 0 to 65535)."""
        name = stmt.targets[0].id
        if not ENUM_MEMBER.fullmatch(name) or name in ENUM_RESERVED:
            raise Refused(stmt, f"enum member name {name}")
        bits = 8 if any(self.zigpy_type(base, ("enum8",)) for base in node.bases) else 16
        if not _int_in(stmt.value, range(1 << bits)):
            raise Refused(stmt, f"enum member {name} other than an integer from 0 to {(1 << bits) - 1}")

    def class_value(self, stmt: ast.Assign, node: ast.ClassDef) -> None:
        """A value of a cluster class: data in its allowed shape, else a fixed class
        statement (STRUCT_TARGETS, the outage cluster's ep_attribute and _VALID_ATTRIBUTES)."""
        name, value = stmt.targets[0].id, stmt.value
        if name == "cluster_id":
            if not _int_in(value, range(0x10000)):
                raise Refused(stmt, "cluster_id other than an integer from 0 to 0xFFFF")
        elif name == "STRUCT_TAGS":
            if not (isinstance(value, ast.Dict) and value.keys and all(_struct_tag(k, v) for k, v in zip(value.keys, value.values, strict=True))):
                raise Refused(stmt, "STRUCT_TAGS other than Aqara struct tags with their key and a float factor")
        elif name in VOLTS:
            if not _int_in(value, VOLTS_RANGE):
                raise Refused(stmt, f"{name} other than an integer from {VOLTS_RANGE.start} to {VOLTS_RANGE.stop - 1}")
        elif name == SPREAD:
            self.constant_attributes(stmt)
        elif ast.dump(stmt) not in self.fixed.methods:
            raise Refused(stmt, f"{name} in class {node.name}")

    def constant_attributes(self, stmt: ast.Assign) -> None:
        """{**Cluster._CONSTANT_ATTRIBUTES, Cluster.AttributeDefs.name.id: 1000}: integer values."""
        if not isinstance(stmt.value, ast.Dict):
            raise Refused(stmt, f"{SPREAD} other than a dict")
        for key, item in zip(stmt.value.keys, stmt.value.values, strict=True):
            if key is None:
                if not isinstance(item, ast.Attribute):
                    raise Refused(item, f"** other than a cluster's {SPREAD}")
                self.attribute(item, spread=True)
                continue
            if not _int_in(key, range(0x10000)):
                if not (isinstance(key, ast.Attribute) and key.attr == "id"):
                    raise Refused(key, f"{SPREAD} key other than an attribute id")
                self.attribute(key)
            if not _int_in(item, CONSTANT_RANGE):
                raise Refused(item, f"{SPREAD} value other than an integer from {CONSTANT_RANGE.start} to {CONSTANT_RANGE.stop - 1}")

    def base(self, node: ast.expr) -> bool:
        """The base of a class: an imported cluster class or t.enum8, t.enum16."""
        if isinstance(node, ast.Name):
            return self.imported.get(node.id) == CLUSTER
        return self.zigpy_type(node, ENUM_BASES)

    def nested_base(self, node: ast.expr, nested: str) -> bool:
        """The base of a nested AttributeDefs or ServerCommandDefs: zigpy's base or that of an imported cluster class."""
        if isinstance(node, ast.Name):
            return self.imported.get(node.id) == NESTED[nested]
        parts = (dotted(node) or "").split(".")
        return len(parts) == 2 and parts[1] == nested and self.imported.get(parts[0]) == CLUSTER

    def chain(self, node: ast.Call) -> None:
        """QuirkBuilder(...).method(...)....add_to_registry()."""
        calls = []
        while isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            calls.append(node)
            node = node.func.value
        root = node
        if not (isinstance(root, ast.Call) and isinstance(root.func, ast.Name) and self.imported.get(root.func.id) == BUILDER):
            raise Refused(root, "a module-level call that is no builder chain")
        if not calls or calls[0].func.attr != "add_to_registry" or calls[0].args or calls[0].keywords:
            raise Refused(root, "a builder chain that does not end in add_to_registry()")
        for call in calls:
            if call.func.attr not in METHODS[root.func.id]:
                raise Refused(call, f"builder method {call.func.attr}")
            if call.func.attr == "filter" and not (
                len(call.args) == 1 and not call.keywords and isinstance(call.args[0], ast.Name) and call.args[0].id == FILTER and FILTER in self.functions
            ):
                raise Refused(call, f"filter other than {FILTER}")
        # Upstream first: every chain has the filter that steps back for a shipped quirk.
        if sum(call.func.attr == "filter" for call in calls) != 1:
            raise Refused(root, f"a builder chain without exactly one .filter({FILTER})")
        self.filtered = True
        # Its fingerprints: the builder's own (QuirkBuilder only) and each applies_to.
        if root.keywords or len(root.args) != ROOT_ARGS[root.func.id]:
            raise Refused(root, f"{root.func.id} with other arguments than allowed")
        if root.args:
            self.aim(root, root.args)
        for call in calls:
            if call.func.attr == "applies_to":
                if call.keywords:
                    raise Refused(call, "a target that is no literal (manufacturer, model)")
                self.aim(call, call.args)
        for call in [root, *calls]:
            self.arguments(call, CHAIN)

    def arguments(self, call: ast.Call, where: str) -> None:
        for arg in call.args:
            self.expr(arg, where)
        for keyword in call.keywords:
            if keyword.arg is None:
                raise Refused(call, "** in a call")
            if where == CHAIN and keyword.arg in CONVERTER_KEYWORDS:
                self.converter(keyword.value, keyword.arg)
            else:
                self.expr(keyword.value, where)

    def converter(self, node: ast.expr, keyword: str) -> None:
        """lambda x: ... over what a converter may use (keyword: the one it is passed as)."""
        if not isinstance(node, ast.Lambda):
            raise Refused(node, "a converter other than lambda x: ...")
        args = node.args
        if args.posonlyargs or args.vararg or args.kwonlyargs or args.kwarg or args.defaults or [a.arg for a in args.args] != ["x"]:
            raise Refused(node, "a converter other than lambda x: ...")
        self.expr(node.body, LAMBDA)
        # Each product may repeat x (a string from the device) up to MAX_FACTOR times: one of them only,
        # in a Tuya converter only (MAX_FACTOR).
        products = sum(isinstance(n, ast.BinOp) and isinstance(n.op, ast.Mult) for n in ast.walk(node.body))
        if keyword != "converter" and products:
            raise Refused(node, f"a product in {keyword}")
        if products > 1:
            raise Refused(node, "a converter with more than one product")

    def callee(self, func: ast.expr, where: str) -> bool:
        """Whether a call of func is allowed here: an imported callable of this place; in a
        converter also the casts, t.Bool, the file's enum classes and helpers."""
        if isinstance(func, ast.Name):
            name = func.id
            if name in self.imported:
                return self.imported[name] == CALLS[where]
            if where != LAMBDA:
                return False
            if name in BUILTINS:
                return name not in self.bound
            return name in self.enums or (name in self.functions and name in self.fixed.helpers)
        return where == LAMBDA and self.zigpy_type(func, TYPE_CALLS)

    def name(self, node: ast.Name, where: str) -> None:
        name = node.id
        if where == LAMBDA and name == "x":
            return
        # Module-level values (FINGERPRINTS, _LOGGER) and the plain imports serve only the fixed code.
        if where == CHAIN and (self.imported.get(name) in (VALUE, CLUSTER) or name in self.classes or (name == FILTER and name in self.functions)):
            return
        raise Refused(node, f"name {name}")

    def attribute(self, node: ast.Attribute, spread: bool = False) -> None:
        """An allowed attribute path."""
        parts: list[str] = []
        root: ast.expr = node
        while isinstance(root, ast.Attribute):
            parts.insert(0, root.attr)
            root = root.value
        if isinstance(root, ast.Name) and self.path(root.id, parts, spread):
            return
        raise Refused(node, f"attribute {_short(node)}")

    def path(self, root: str, parts: list[str], spread: bool) -> bool:
        kind = self.imported.get(root)
        if spread:
            return kind == CLUSTER and parts == [SPREAD]
        if root == "t" and self.modules.get("t") == "zigpy.types":
            return len(parts) == 1 and parts[0] in TYPE_NAMES
        if kind == ENUM:
            return len(parts) == 1 and MEMBER.fullmatch(parts[0]) is not None
        if kind == FOUNDATION:
            return len(parts) == 2 and parts[0] == "ZCLAttributeAccess" and MEMBER.fullmatch(parts[1]) is not None
        if root in self.enums:
            return len(parts) == 1 and parts[0] in self.enums[root] and not parts[0].startswith("_")
        if kind == CLUSTER or root in self.classes:
            match parts:
                case ["cluster_id"] | ["ep_attribute"]:
                    return True
                case ["AttributeDefs", attribute, "name" | "id"] | ["ServerCommandDefs", attribute, "name"]:
                    return NAME.fullmatch(attribute) is not None
                case [nested, member] if nested in CLUSTER_ENUMS:
                    return MEMBER.fullmatch(member) is not None
        return False

    def expr(self, node: ast.expr, where: str) -> None:
        """A value in a builder chain, a converter or a class body."""
        match node:
            case ast.Constant():
                return None
            case ast.Name():
                return self.name(node, where)
            case ast.Attribute():
                return self.attribute(node)
            case ast.UnaryOp(op=op, operand=operand):
                if isinstance(op, (ast.USub, ast.UAdd)) and isinstance(operand, ast.Constant) and type(operand.value) in (int, float):
                    return None
                if isinstance(op, ast.Not) and where == LAMBDA:
                    return self.expr(operand, where)
                raise Refused(node, f"operator {type(op).__name__}")
            case ast.BinOp(left=left, op=op, right=right):
                if not isinstance(op, OPERATORS[where]):
                    raise Refused(node, f"operator {type(op).__name__}")
                if isinstance(left, ast.Constant) and isinstance(right, ast.Constant):
                    raise Refused(node, "arithmetic on two constants")
                # Numbers only: a string or bytes would turn a device value into a long repetition.
                if any(isinstance(side, ast.Constant) and type(side.value) not in (int, float) for side in (left, right)):
                    raise Refused(node, "arithmetic on something other than a number")
                # A product is x times a number literal, as gen_tuya writes it. Anything else could be
                # a sequence the product repeats (str(x), a list, a tuple, a looked-up or conditional
                # value) or a count the device chooses (x * int(x)). x itself is a string when the
                # device says so (the Tuya type byte, up to 255 bytes): the literal bounds that
                # repetition, so an integer one stays small and a product never chains.
                if isinstance(op, ast.Mult) and not (isinstance(left, ast.Name) and left.id == "x" and factor(right)):
                    raise Refused(node, f"a product other than x times a number literal of at most {MAX_FACTOR}")
                # x + x, x * 1000 + x: two values from the device joined, a sequence grows with each one.
                if where == LAMBDA and not isinstance(op, ast.Mult) and not (number(left) or number(right)):
                    raise Refused(node, "arithmetic without a number literal on one side")
                self.expr(left, where)
                return self.expr(right, where)
            case ast.Compare(left=left, ops=ops, comparators=comparators) if where == LAMBDA:
                if not all(isinstance(op, CMPOPS) for op in ops):
                    raise Refused(node, "comparison operator")
                for value in (left, *comparators):
                    self.expr(value, where)
                return None
            case ast.IfExp(test=test, body=body, orelse=orelse) if where == LAMBDA:
                for value in (test, body, orelse):
                    self.expr(value, where)
                return None
            case ast.Subscript(value=ast.Dict() as value, slice=index) if where == LAMBDA:
                # {wire: value}[x]
                self.expr(value, where)
                return self.expr(index, where)
            case ast.Subscript(value=value, slice=index) if where == CLASS and self.zigpy_type(value, TYPE_LISTS):
                # t.List[t.uint8_t]
                if not self.zigpy_type(index, TYPE_NAMES):
                    raise Refused(node, f"list of {_short(index)}")
                return None
            case ast.List(elts=elts) | ast.Tuple(elts=elts) | ast.Set(elts=elts):
                if where == LAMBDA:
                    # Each item would be computed: many products, each up to MAX_FACTOR times x.
                    raise Refused(node, f"a {type(node).__name__.lower()} in a converter")
                for value in elts:
                    self.expr(value, where)
                return None
            case ast.Dict(keys=keys, values=values):
                if where == LAMBDA and any(isinstance(n, ast.Name) and n.id == "x" for item in (*keys, *values) if item is not None for n in ast.walk(item)):
                    # {wire: value}[x]: every value is computed before the lookup.
                    raise Refused(node, "x in a dict of a converter (only as the key looked up)")
                for key, value in zip(keys, values, strict=True):
                    if key is None:
                        if where != CLASS or not isinstance(value, ast.Attribute):
                            raise Refused(node, f"** other than a cluster's {SPREAD}")
                        self.attribute(value, spread=True)
                        continue
                    self.expr(key, where)
                    self.expr(value, where)
                return None
            case ast.Call(func=func):
                if not self.callee(func, where):
                    raise Refused(node, f"call of {_short(func)}")
                return self.arguments(node, where)
        raise Refused(node, f"{type(node).__name__} expression")


def _quoted(pair: tuple[str | None, str]) -> str:
    text = repr(pair)
    return text if len(text) <= 80 else text[:77] + "..."


def check_quirk(source: str | bytes, fixed: Fixed, targets: Targets | None) -> list[tuple[int, str]]:
    """(line, reason) for every statement of a quirk file outside the allowlist and every target
    outside its manifest entry's (Targets.of; None refuses the file); empty when it passes. Bytes
    are parsed as Python imports them."""
    raw = source.encode() if isinstance(source, str) else source
    # Quirk files have none; another encoding could make the file read differently.
    if any(CODING.match(line) for line in LINE_BREAK.split(raw.removeprefix(b"\xef\xbb\xbf"), maxsplit=2)[:2]):
        return [(1, "coding declaration")]
    try:
        tree = ast.parse(source)
        return [(getattr(node, "lineno", 1), reason) for node, reason in QuirkFile(tree, fixed).problems(targets)]
    except SyntaxError as error:
        return [(error.lineno or 0, f"does not parse: {error.msg}")]
    except (ValueError, RecursionError, MemoryError) as error:
        return [(0, f"does not parse: {type(error).__name__}")]
    except Exception as error:  # noqa: BLE001 - a file the guard cannot judge is refused, never a crash
        return [(0, f"cannot be checked: {type(error).__name__}")]
