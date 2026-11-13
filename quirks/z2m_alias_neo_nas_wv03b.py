"""NEO NAS-WV03B: Smart sprinkler timer with measurements.

Generated from the Zigbee2MQTT definition.
Zigbee2MQTT treats these fingerprints as one device: an alias for the quirk ZHA ships for
_TZE204_rzrrjkz2 / TS0601, _TZE204_z7a2jmyy / TS0601.
Zigbee2MQTT decodes some datapoints differently from that quirk; check them on the device:
- DP 3: enum: ZHA has no member for wire 3 (z2m on_manual_app), wire 4 (z2m on_manual_button)
- DP 9: scale: ZHA shows 16.6667 x z2m's value (wire 3600: z2m 3.6, ZHA 60)
- DP 9: scale: ZHA shows 4.40287 x z2m's value (wire 3600: z2m 3.6, ZHA 15.8503)
- DP 15: scale: ZHA shows 1000 x z2m's value (wire 3600: z2m 3.6, ZHA 3600)
- DP 15: scale: ZHA shows 264.172 x z2m's value (wire 3600: z2m 3.6, ZHA 951.019)
- DP 102: unit: the same number, z2m in gal, ZHA in L
- DP 108: unit: the same number, z2m in gal, ZHA in L
Data: zigbee-herdsman-converters, MIT, Copyright (c) 2018 Koen Kanters.
Status: generated, not verified on hardware.
Revision: f0f238ea
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
ALIASES = [{'targets': [('_TZE204_rzrrjkz2', 'TS0601')], 'fingerprints': [('_TZE284_rzrrjkz2', 'TS0601'), ('_TZE284_uab532m0', 'TS0601'), ('_TZE204_nnhwcvbk', 'TS0601'), ('_TZE284_nnhwcvbk', 'TS0601'), ('_TZE204_4fblxpma', 'TS0601'), ('_TZE284_4fblxpma', 'TS0601')]}, {'targets': [('_TZE204_z7a2jmyy', 'TS0601')], 'fingerprints': [('_TZE284_z7a2jmyy', 'TS0601')]}]
FINGERPRINTS = [('_TZE284_rzrrjkz2', 'TS0601'), ('_TZE284_uab532m0', 'TS0601'), ('_TZE204_nnhwcvbk', 'TS0601'), ('_TZE284_nnhwcvbk', 'TS0601'), ('_TZE204_4fblxpma', 'TS0601'), ('_TZE284_4fblxpma', 'TS0601'), ('_TZE284_z7a2jmyy', 'TS0601')]


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
