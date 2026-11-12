"""What an offered quirk file changes against the copy on disk, read with ast (never executed).

The quirk files of this collection hold a fixed set of QuirkBuilder calls (guard.py METHODS).
Each entity call, Tuya helper and added entity cluster becomes one entity here, keyed the
way Home Assistant keys ZHA quirk entities: the platform, the endpoint and the unique id suffix (or the
attribute or command name). A changed platform is a new entity in Home Assistant, so it shows as one
(Removed and New): an automation that switches something cannot use a sensor. An entity that keeps its
platform and reads the same thing under another key (a renamed attribute or unique id suffix) is one
item, New ID, with any other change it brings: Home Assistant makes a new entity of it, automations
that use the old one need updating. What it reads comes from the file alone: the Tuya datapoint, or the
cluster id and attribute id from the cluster classes the file defines. A cluster id the file takes from
an imported class (such as XiaomiAqaraE1Cluster) or a plain call on TUYA_CLUSTER_ID stays unknown: a
rename there shows as Removed and New.

Everything else is code this reading cannot judge. The list never calls it harmless: it names the
modules a new version imports and the functions it calls (besides the QuirkBuilder methods) that the
copy on disk does not, so an os, subprocess or socket stands out.
"""

from __future__ import annotations

import ast
import dataclasses
import re

# QuirkBuilder calls that declare one entity, with the entity kind in plain words.
ENTITY_CALLS = {
    "sensor": "sensor",
    "binary_sensor": "binary sensor",
    "switch": "switch",
    "number": "number",
    "enum": "select",
    "write_attr_button": "button",
    "command_button": "button",
    "tuya_sensor": "sensor",
    "tuya_binary_sensor": "binary sensor",
    "tuya_switch": "switch",
    "tuya_number": "number",
    "tuya_enum": "select",
}
# entity_platform=EntityPlatform.<X> overrides the kind of the call.
PLATFORMS = {"SENSOR": "sensor", "BINARY_SENSOR": "binary sensor", "SWITCH": "switch", "NUMBER": "number", "SELECT": "select", "BUTTON": "button"}
# TuyaQuirkBuilder helpers that add one fixed entity (zhaquirks/tuya/builder): kind, name.
HELPERS = {
    "tuya_battery": ("sensor", "Battery"),
    "tuya_temperature": ("sensor", "Temperature"),
    "tuya_humidity": ("sensor", "Humidity"),
    "tuya_illuminance": ("sensor", "Illuminance"),
    "tuya_soil_moisture": ("sensor", "Soil moisture"),
    "tuya_co2": ("sensor", "CO2"),
    "tuya_pm25": ("sensor", "PM2.5"),
    "tuya_voc": ("sensor", "VOC"),
    "tuya_formaldehyde": ("sensor", "Formaldehyde"),
    "tuya_electrical_conductivity": ("sensor", "Electrical conductivity"),
    "tuya_metering": ("sensor", "Energy"),
    "tuya_contact": ("binary sensor", "Contact"),
    "tuya_gas": ("binary sensor", "Gas"),
    "tuya_smoke": ("binary sensor", "Smoke"),
    "tuya_vibration": ("binary sensor", "Vibration"),
    "tuya_ias": ("binary sensor", "Alarm"),
    "tuya_onoff": ("switch", "Switch"),
    "tuya_cover": ("cover", "Cover"),
}
# Clusters a quirk adds whose entities ZHA creates itself: kind, name. A class the file defines
# counts as the first of its bases found here.
ADDED_CLUSTERS = {
    "TuyaWindowCovering": ("cover", "Cover"),
    "TuyaThermostatV2": ("thermostat", "Thermostat"),
    "DeviceTemperatureCluster": ("sensor", "Device temperature"),
    "TuyaOccupancySensing": ("binary sensor", "Occupancy"),
    "MeteringCluster": ("sensor", "Energy"),
    "ElectricalMeasurementCluster": ("sensor", "Power"),
    "XiaomiPowerConfiguration": ("sensor", "Battery"),
}
# Which kind of change a keyword argument stands for.
LABELS = {
    "min_value": "range",
    "max_value": "range",
    "step": "range",
    "unit": "unit",
    "multiplier": "scale",
    "divisor": "scale",
    "scale": "scale",
    "converter": "scale",
    "dp_converter": "scale",
    "enum_class": "options",
    "on_value": "options",
    "off_value": "options",
    "force_inverted": "options",
    "invert_attribute_name": "options",
    "attribute_value": "options",
    "command_args": "options",
    "attribute_name": "data source",
    "command_name": "data source",
    "cluster_id": "data source",
    "cluster_type": "data source",
    "dp_id": "data source",
    "type": "data source",
    "entity_type": "category",
    "initially_disabled": "category",
    "device_class": "display",
    "state_class": "display",
    "mode": "display",
}
IGNORED = {"translation_key", "translation_placeholders", "fallback_name", "unique_id_suffix", "entity_platform", "endpoint_id"}
LIMIT = 10
# The docstring line with the file's status (gen_tuya.py, gen_zcl.py, gen_alias.py), e.g. "verified on hardware.".
STATUS_LINE = re.compile(rb"^Status: (.+)$", re.M)
# Names shown per line for button events, imports and calls.
SHOWN = 6


@dataclasses.dataclass(frozen=True)
class Entity:
    key: str
    kind: str
    name: str
    params: tuple[tuple[str, str], ...]
    # The call that declares it: a QuirkBuilder method, or adds:<class> for an added cluster.
    call: str = ""
    # What it reads or sends, as far as the file says (_Reader.feature); None when it does not.
    feature: tuple[object, ...] | None = None


@dataclasses.dataclass(frozen=True)
class Inventory:
    entities: dict[str, Entity]
    events: dict[str, str]
    code: str
    # The modules the file imports and the functions it calls besides the QuirkBuilder methods.
    imports: frozenset[str] = frozenset()
    calls: frozenset[str] = frozenset()


@dataclasses.dataclass(frozen=True)
class Summary:
    new: list[Entity]
    removed: list[Entity]
    changed: list[tuple[Entity, list[str]]]
    events_added: list[str]
    events_removed: list[str]
    # No entity or button event changed, but the code did.
    internal: bool
    cosmetic: bool
    imports_added: list[str] = dataclasses.field(default_factory=list)
    calls_added: list[str] = dataclasses.field(default_factory=list)
    # The new Status line when it differs from the old one (verified on hardware, for example).
    status: str | None = None
    # (old, new): entities that keep their platform and read the same thing under another key in Home
    # Assistant.
    new_id: list[tuple[Entity, Entity]] = dataclasses.field(default_factory=list)

    def items(self) -> list[str]:
        # New imports and calls first: they must never end up behind the LIMIT.
        out = [f"{label}: {_names(names)}" for label, names in (("New imports", self.imports_added), ("New function calls", self.calls_added)) if names]
        if self.status:
            out.append(f"Status now: {plain(self.status)}")
        out += [f"New: {plain(e.name)} ({e.kind})" for e in self.new]
        out += [f"Removed: {plain(e.name)} ({e.kind})" for e in self.removed]
        out += [_new_id(old, new) for old, new in self.new_id]
        out += [f"Changed: {plain(e.name)} ({e.kind}): {', '.join(labels)}" for e, labels in self.changed]
        for label, events in (("New button events", self.events_added), ("Removed button events", self.events_removed)):
            if events:
                out.append(f"{label}: {_names(events)}")
        if self.internal:
            out.append("No entity added, removed or changed: other code differs")
        if self.cosmetic:
            out.append("No functional change: only comments and the file header differ")
        return out

    def as_dict(self) -> dict:
        return {
            "new": [f"{e.name} ({e.kind})" for e in self.new],
            "removed": [f"{e.name} ({e.kind})" for e in self.removed],
            "new_id": [_rekeyed(old, new, str) for old, new in self.new_id],
            "changed": {f"{e.name} ({e.kind})": labels for e, labels in self.changed},
            "button_events_added": self.events_added,
            "button_events_removed": self.events_removed,
            "imports_added": self.imports_added,
            "calls_added": self.calls_added,
            "other_code_only": self.internal,
            "comments_only": self.cosmetic,
            "status": self.status,
        }


def plain(value: str) -> str:
    """A string as plain text in markdown: no emphasis, link, image or HTML of its own."""
    return re.sub(r"([\\`*_\[\]<>#|])", r"\\\1", value)


def _rekeyed(old: Entity, new: Entity, text=plain) -> str:
    """An entity under a new key: its name and platform, the old name when it changed, the other changes."""
    was = f", was {text(old.name)}" if old.name != new.name else ""
    # The name shows as "was"; the attribute or command name is what gave it the new key.
    labels = [label for label in _labels(old, new) if label not in ("name", "data source")]
    also = f", also changed: {', '.join(labels)}" if labels else ""
    return f"{text(new.name)} ({new.kind}{was}){also}"


def _new_id(old: Entity, new: Entity) -> str:
    return f"New ID: {_rekeyed(old, new)}: automations that use it need updating"


def _names(names: list[str]) -> str:
    shown = ", ".join(plain(name) for name in names[:SHOWN])
    return shown + (f" and {len(names) - SHOWN} more" if len(names) > SHOWN else "")


def _identifier(node: ast.AST | None) -> str | None:
    """The attribute or command a call names: a string, or the X of Cluster.AttributeDefs.X.name."""
    if node is None:
        return None
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.Attribute) and node.attr == "name" and isinstance(node.value, ast.Attribute):
        return node.value.attr
    return ast.unparse(node)


def _literal(node: ast.AST | None, default: object = None) -> object:
    if node is None:
        return default
    try:
        return ast.literal_eval(node)
    except ValueError:
        return ast.unparse(node)


def _number(node: ast.AST | None) -> int | None:
    """An int literal (0xFC11), None for anything else."""
    if isinstance(node, ast.Constant) and isinstance(node.value, int) and not isinstance(node.value, bool):
        return node.value
    return None


def _assigns(statement: ast.stmt, name: str) -> bool:
    """The statement assigns to a plain name: name = ... or name: type = ..."""
    if isinstance(statement, ast.Assign):
        return any(isinstance(target, ast.Name) and target.id == name for target in statement.targets)
    return isinstance(statement, ast.AnnAssign) and isinstance(statement.target, ast.Name) and statement.target.id == name


def _base_names(cls: ast.ClassDef) -> list[str]:
    return [base.id if isinstance(base, ast.Name) else base.attr for base in cls.bases if isinstance(base, (ast.Name, ast.Attribute))]


def _attribute_def_id(node: ast.AST | None) -> int | None:
    """The id of a ZCLAttributeDef(id=0x..., ...) call."""
    if not (isinstance(node, ast.Call) and _callee(node.func).endswith("ZCLAttributeDef")):
        return None
    for keyword in node.keywords:
        if keyword.arg == "id":
            return _number(keyword.value)
    return _number(node.args[0]) if node.args else None


def _humane(value: str) -> str:
    return value.replace("_", " ").strip().capitalize() or value


def _strip_docstrings(tree: ast.Module) -> ast.Module:
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)) and node.body:
            first = node.body[0]
            if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) and isinstance(first.value.value, str):
                node.body = node.body[1:] or [ast.Pass()]
    return tree


class _Reader:
    def __init__(self, tree: ast.Module) -> None:
        self.classes = {node.name: node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)}
        # The module's own classes: every cluster class has a nested AttributeDefs of the same name.
        self.top = {node.name: node for node in tree.body if isinstance(node, ast.ClassDef)}

    def feature(self, method: str, kwargs: dict[str, ast.AST], endpoint: object) -> tuple[object, ...] | None:
        """What an entity call reads or sends, from the file alone: the endpoint and datapoint of a Tuya
        call; the endpoint, cluster id and attribute id of an attribute (with the value a write button
        writes); the endpoint, cluster id and command of a command button. None when the file does not
        say, for example for a cluster it does not define."""
        if method.startswith("tuya_"):
            dp = _number(kwargs.get("dp_id"))
            return ("dp", endpoint, dp) if dp is not None else None
        cluster = self.cluster_id(kwargs.get("cluster_id"))
        if cluster is None:
            return None
        if method == "command_button":
            command = _identifier(kwargs.get("command_name"))
            return ("command", endpoint, cluster, command) if command else None
        attribute = self.attribute_id(kwargs.get("attribute_name"))
        if attribute is None:
            return None
        if method == "write_attr_button":
            value = kwargs.get("attribute_value")
            return ("write", endpoint, cluster, attribute, ast.unparse(value) if value is not None else None)
        return ("attribute", endpoint, cluster, attribute)

    def cluster_id(self, node: ast.AST | None) -> int | None:
        """The cluster id an entity call names: a number, or the cluster_id of a class the file defines
        (through the bases it defines)."""
        if (value := _number(node)) is not None:
            return value
        if isinstance(node, ast.Attribute) and node.attr == "cluster_id" and isinstance(node.value, ast.Name):
            return self._cluster_id(node.value.id, frozenset())
        return None

    def _cluster_id(self, name: str, seen: frozenset[str]) -> int | None:
        cls = self.top.get(name)
        if cls is None or name in seen:
            return None
        for statement in cls.body:
            if _assigns(statement, "cluster_id") and (value := _number(statement.value)) is not None:
                return value
        for base in _base_names(cls):
            if (found := self._cluster_id(base, seen | {name})) is not None:
                return found
        return None

    def attribute_id(self, node: ast.AST | None) -> int | None:
        """The id of the attribute an entity call names as Cluster.AttributeDefs.<name>.name, from the
        AttributeDefs of a class the file defines (through the bases it defines)."""
        if not (
            isinstance(node, ast.Attribute)
            and node.attr == "name"
            and isinstance(node.value, ast.Attribute)
            and isinstance(node.value.value, ast.Attribute)
            and node.value.value.attr == "AttributeDefs"
            and isinstance(node.value.value.value, ast.Name)
        ):
            return None
        return self._attribute_id(node.value.value.value.id, node.value.attr, frozenset())

    def _attribute_id(self, name: str, attribute: str, seen: frozenset[str]) -> int | None:
        cls = self.top.get(name)
        if cls is None or name in seen:
            return None
        seen = seen | {name}
        for defs in (statement for statement in cls.body if isinstance(statement, ast.ClassDef) and statement.name == "AttributeDefs"):
            for statement in defs.body:
                if _assigns(statement, attribute):
                    return _attribute_def_id(statement.value)
            # class AttributeDefs(Other.AttributeDefs): the attributes of Other.
            for base in defs.bases:
                if isinstance(base, ast.Attribute) and base.attr == "AttributeDefs" and isinstance(base.value, ast.Name):
                    if (found := self._attribute_id(base.value.id, attribute, seen)) is not None:
                        return found
        for base in _base_names(cls):
            if (found := self._attribute_id(base, attribute, seen)) is not None:
                return found
        return None

    def enum_members(self, node: ast.AST) -> str:
        """An enum class the file defines, as its members and values (so new options show)."""
        cls = self.classes.get(node.id) if isinstance(node, ast.Name) else None
        if cls is None:
            return ast.unparse(node)
        members = [ast.unparse(item) for item in cls.body if isinstance(item, ast.Assign)]
        return "; ".join(members)

    def class_source(self, name: str) -> str:
        cls = self.classes.get(name)
        return ast.dump(_strip_docstrings(ast.Module(body=[cls], type_ignores=[]))) if cls else name

    def added(self, name: str, seen: frozenset[str] = frozenset()) -> tuple[str, str] | None:
        """The entity an added cluster class brings: a known class or one the file derives from it."""
        if name in ADDED_CLUSTERS:
            return ADDED_CLUSTERS[name]
        cls = self.classes.get(name)
        if cls is None or name in seen:
            return None
        for base in cls.bases:
            base_name = base.id if isinstance(base, ast.Name) else base.attr if isinstance(base, ast.Attribute) else None
            if base_name and (found := self.added(base_name, seen | {name})):
                return found
        return None


def inventory(content: bytes) -> Inventory | None:
    """The entities and button events a quirk file declares; None when unreadable."""
    try:
        text = content.decode("utf-8")
        tree = ast.parse(text)
    except (UnicodeDecodeError, SyntaxError, ValueError, RecursionError, MemoryError):
        return None
    try:
        return _inventory(tree)
    except RecursionError:
        return None


def _callee(node: ast.AST) -> str:
    """How a call names its function: a dotted name, (...) for the part that is another expression."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return f"{_callee(node.value)}.{node.attr}"
    return "(...)"


def _chain(statement: ast.stmt) -> list[ast.Call]:
    """The calls of a QuirkBuilder(...).x(...).add_to_registry() statement, empty for any other statement."""
    node = statement.value if isinstance(statement, ast.Expr) else None
    found = []
    while isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
        found.append(node)
        node = node.func.value
    if isinstance(node, ast.Call) and _callee(node.func).endswith("QuirkBuilder"):
        return [*found, node]
    return []


def _code_names(tree: ast.Module) -> tuple[frozenset[str], frozenset[str]]:
    """The modules the file imports and the functions it calls (decorators included) besides the
    calls of its QuirkBuilder chains."""
    chain = {id(call) for statement in tree.body for call in _chain(statement)}
    imports, calls = set(), set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports |= {alias.name for alias in node.names}
        elif isinstance(node, ast.ImportFrom):
            imports.add("." * node.level + (node.module or ""))
        elif isinstance(node, ast.Call) and id(node) not in chain:
            calls.add(_callee(node.func))
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            calls |= {_callee(decorator) for decorator in node.decorator_list if not isinstance(decorator, ast.Call)}
    return frozenset(imports), frozenset(calls)


def _inventory(tree: ast.Module) -> Inventory:
    reader = _Reader(tree)
    entities: dict[str, Entity] = {}
    events: dict[str, str] = {}
    imports, called = _code_names(tree)
    calls = sorted(
        (node for node in ast.walk(tree) if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)),
        key=lambda node: (node.func.end_lineno or 0, node.func.end_col_offset or 0),
    )
    for call in calls:
        method = call.func.attr
        kwargs = {kw.arg: kw.value for kw in call.keywords if kw.arg}
        endpoint = _literal(kwargs.get("endpoint_id"), 1)
        if method in ENTITY_CALLS:
            kind = ENTITY_CALLS[method]
            platform = kwargs.get("entity_platform")
            if isinstance(platform, ast.Attribute) and platform.attr in PLATFORMS:
                kind = PLATFORMS[platform.attr]
            ident = _literal(kwargs.get("unique_id_suffix")) or _identifier(kwargs.get("attribute_name") or kwargs.get("command_name"))
            name = _literal(kwargs.get("fallback_name")) or _humane(str(ident or method))
            params = []
            for key, value in sorted(kwargs.items()):
                if key in IGNORED:
                    continue
                if key == "enum_class":
                    params.append((key, reader.enum_members(value)))
                elif key in ("attribute_name", "command_name"):
                    params.append((key, str(_identifier(value))))
                else:
                    params.append((key, ast.unparse(value)))
            key = f"{kind}:{endpoint}:{ident}"
            entities[key] = Entity(key, kind, str(name), tuple(params), method, reader.feature(method, kwargs, endpoint))
        elif method in HELPERS:
            kind, name = HELPERS[method]
            key = f"{kind}:{endpoint}" if kind in ("cover", "thermostat") else f"{kind}:{endpoint}:{method}"
            params = tuple((k, ast.unparse(v)) for k, v in sorted(kwargs.items()) if k not in IGNORED)
            entities[key] = Entity(key, kind, name, params, method)
        elif method == "adds" and call.args:
            target = call.args[0]
            cls = target.id if isinstance(target, ast.Name) else target.attr if isinstance(target, ast.Attribute) else None
            found = reader.added(cls) if cls else None
            if found:
                kind, name = found
                key = f"{kind}:{endpoint}" if kind in ("cover", "thermostat") else f"{kind}:{endpoint}:{cls}"
                entities[key] = Entity(key, kind, name, (("settings", reader.class_source(cls)),), f"adds:{cls}")
        elif method == "device_automation_triggers" and call.args and isinstance(call.args[0], ast.Dict):
            for trigger, command in zip(call.args[0].keys, call.args[0].values):
                if trigger is not None:
                    events[_event(trigger)] = ast.unparse(command)
    code = ast.dump(_strip_docstrings(tree))
    return Inventory(entities, events, code, imports, called)


def _event(node: ast.AST) -> str:
    """A device trigger key (type, subtype) as "button 1: single"."""
    parts = node.elts if isinstance(node, ast.Tuple) else [node]
    words = []
    for part in parts:
        if isinstance(part, ast.Constant):
            words.append(str(part.value).replace("_", " "))
        else:
            words.append(ast.unparse(part).removeprefix("COMMAND_").replace("_", " ").lower())
    return f"{words[1]}: {words[0]}" if len(words) == 2 else " ".join(words)


def summarize(old: bytes, new: bytes) -> Summary | None:
    """New, removed and changed entities from old to new; None when either file cannot be read."""
    before, after = inventory(old), inventory(new)
    if before is None or after is None:
        return None
    added = [after.entities[k] for k in after.entities if k not in before.entities]
    removed = [before.entities[k] for k in before.entities if k not in after.entities]
    new_id = _pairs(removed, added)
    paired = {entity.key for pair in new_id for entity in pair}
    added = [e for e in added if e.key not in paired]
    removed = [e for e in removed if e.key not in paired]
    changed = []
    for key, entity in after.entities.items():
        previous = before.entities.get(key)
        if previous is None:
            continue
        labels = _labels(previous, entity)
        if labels:
            changed.append((entity, labels))
    events_added = [e for e in after.events if e not in before.events]
    events_removed = [e for e in before.events if e not in after.events]
    differs = bool(added or removed or new_id or changed or events_added or events_removed)
    internal = not differs and before.code != after.code
    cosmetic = not differs and before.code == after.code and old != new
    imports, calls = sorted(after.imports - before.imports), sorted(after.calls - before.calls)
    status = _status(new)
    return Summary(added, removed, changed, events_added, events_removed, internal, cosmetic, imports, calls, status if status != _status(old) else None, new_id)


def _pairs(removed: list[Entity], added: list[Entity]) -> list[tuple[Entity, Entity]]:
    """(old, new) for each platform and feature that exactly one removed and exactly one new entity have:
    the same thing under another key in Home Assistant. Another platform stays Removed and New; a
    feature several of them share stays unpaired."""

    def by_feature(entities: list[Entity]) -> dict[tuple[object, ...], list[Entity]]:
        found: dict[tuple[object, ...], list[Entity]] = {}
        for entity in entities:
            if entity.feature is not None:
                found.setdefault((entity.kind, *entity.feature), []).append(entity)
        return found

    before, after = by_feature(removed), by_feature(added)
    return [(old[0], after[feature][0]) for feature, old in before.items() if len(old) == 1 and len(after.get(feature, ())) == 1]


def _status(content: bytes) -> str | None:
    found = STATUS_LINE.search(content)
    return found.group(1).decode("utf-8", "replace").strip() if found else None


def _labels(old: Entity, new: Entity) -> list[str]:
    labels = []
    if old.name != new.name:
        labels.append("name")
    before, after = dict(old.params), dict(new.params)
    for key in sorted(set(before) | set(after)):
        if before.get(key) == after.get(key):
            continue
        label = LABELS.get(key, "settings")
        if label not in labels:
            labels.append(label)
    return labels


def render(summary: Summary | None) -> str:
    """Markdown for a dialog: a short heading and at most LIMIT bullets; empty when nothing to say."""
    if summary is None:
        return ""
    items = summary.items()
    if not items:
        return ""
    shown = items[:LIMIT]
    if len(items) > LIMIT:
        shown.append(f"and {len(items) - LIMIT} more (all of them in the diagnostics)")
    return "**Changes:**\n\n" + "\n".join(f"- {item}" for item in shown) + "\n\n"
