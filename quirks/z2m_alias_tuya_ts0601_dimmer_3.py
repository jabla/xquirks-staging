"""Tuya TS0601_dimmer_3: 3 gang smart dimmer.

Generated from the Zigbee2MQTT definition.
Zigbee2MQTT treats these fingerprints as one device: an alias for the quirk ZHA ships for
_TZE200_vm1gyrso / TS0601.
Data: zigbee-herdsman-converters, MIT, Copyright (c) 2018 Koen Kanters.
Status: generated, not verified on hardware.
Revision: 015741b4
"""

import dataclasses
import functools
import logging
import pathlib

import zhaquirks
from zha.quirks import DEVICE_REGISTRY, DeviceMatch, ModelInfo, QuirkSource

_LOGGER = logging.getLogger(__name__)
_SHIPPED = pathlib.Path(zhaquirks.__file__).resolve().parent

# Per group: the shipped names whose registry entries are reused (targets) and the Zigbee
# fingerprints (manufacturer, model) that get them. FINGERPRINTS lists every name of the file.
ALIASES = [{'targets': [('_TZE200_vm1gyrso', 'TS0601')], 'fingerprints': [('_TZE204_znvwzxkq', 'TS0601'), ('_TZE200_vizxbhco', 'TS0601')]}]
FINGERPRINTS = [('_TZE204_znvwzxkq', 'TS0601'), ('_TZE200_vizxbhco', 'TS0601')]


@functools.cache
def _is_shipped(source: str | None) -> bool:
    return bool(source) and pathlib.Path(source).resolve().is_relative_to(_SHIPPED)


def register_alias(targets, fingerprints, shipped, listed) -> None:
    entries = []
    for target in targets:
        for entry in shipped:
            if ModelInfo(*target) in entry.device_match.applies_to and entry not in entries:
                entries.append(entry)
    if not entries:
        _LOGGER.warning("%s: ZHA ships no quirk for %s, alias not registered", __name__, targets)
        return
    names = tuple(ModelInfo(*fp) for fp in fingerprints if ModelInfo(*fp) not in listed)
    if not names:
        _LOGGER.warning("%s: ZHA ships quirks for %s, the alias is not needed", __name__, fingerprints)
        return
    # register() puts an entry first in its key: the last entry registered is tried first.
    # Every copy keeps its match filters, so a v1 signature still decides per device.
    for entry in reversed(entries):
        DEVICE_REGISTRY.register(
            dataclasses.replace(
                entry,
                device_match=dataclasses.replace(entry.device_match, applies_to=names),
                source=QuirkSource(module=__name__, file=__file__, line=None, label=f"alias of {entry.source.label}"),
            )
        )


def register_aliases() -> None:
    # Green Power quirks (zha 2.4) have no Zigbee names to alias.
    shipped = [e for e in DEVICE_REGISTRY if isinstance(e.device_match, DeviceMatch) and _is_shipped(getattr(e.source, "file", None))]
    listed = {info for e in shipped for info in e.device_match.applies_to}
    for group in ALIASES:
        register_alias(group["targets"], group["fingerprints"], shipped, listed)


register_aliases()
