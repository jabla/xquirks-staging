"""Tuya ZRF01: Zigbee RF cloner with 8 slots.

Generated from the Zigbee2MQTT definition.
Data: zigbee-herdsman-converters, MIT, Copyright (c) 2018 Koen Kanters.
Status: generated, not verified on hardware.
Revision: ba001fa8
"""

import functools
import logging
import pathlib

import zhaquirks
from zha.quirks import DEVICE_REGISTRY, DeviceMatch
import zigpy.types as t

from zhaquirks.builder import (
    EntityType,
)
from zhaquirks.tuya.builder import TuyaQuirkBuilder


class Button1(t.enum8):
    """button_1 values (z2m)."""

    Learn = 0x00
    Saved = 0x01
    Delete = 0x02


class Button2(t.enum8):
    """button_2 values (z2m)."""

    Learn = 0x00
    Saved = 0x01
    Delete = 0x02


class Button3(t.enum8):
    """button_3 values (z2m)."""

    Learn = 0x00
    Saved = 0x01
    Delete = 0x02


class Button4(t.enum8):
    """button_4 values (z2m)."""

    Learn = 0x00
    Saved = 0x01
    Delete = 0x02


class Button5(t.enum8):
    """button_5 values (z2m)."""

    Learn = 0x00
    Saved = 0x01
    Delete = 0x02


class Button6(t.enum8):
    """button_6 values (z2m)."""

    Learn = 0x00
    Saved = 0x01
    Delete = 0x02


class Button7(t.enum8):
    """button_7 values (z2m)."""

    Learn = 0x00
    Saved = 0x01
    Delete = 0x02


class Button8(t.enum8):
    """button_8 values (z2m)."""

    Learn = 0x00
    Saved = 0x01
    Delete = 0x02


class Start1(t.enum8):
    """start_1 values (z2m)."""

    Transmit = 0x00


class Start2(t.enum8):
    """start_2 values (z2m)."""

    Transmit = 0x00


class Start3(t.enum8):
    """start_3 values (z2m)."""

    Transmit = 0x00


class Start4(t.enum8):
    """start_4 values (z2m)."""

    Transmit = 0x00


class Start5(t.enum8):
    """start_5 values (z2m)."""

    Transmit = 0x00


class Start6(t.enum8):
    """start_6 values (z2m)."""

    Transmit = 0x00


class Start7(t.enum8):
    """start_7 values (z2m)."""

    Transmit = 0x00


class Start8(t.enum8):
    """start_8 values (z2m)."""

    Transmit = 0x00



_LOGGER = logging.getLogger(__name__)
_SHIPPED = pathlib.Path(zhaquirks.__file__).resolve().parent
_STEPPED_BACK: set = set()

# The Zigbee fingerprints (manufacturer, model) this quirk is for; None matches any manufacturer.
FINGERPRINTS = [('_TZE284_tdg4ckyh', 'TS0601')]
# Names that a model-only fingerprint would catch but Zigbee2MQTT gives to other devices.
CLAIMED_ELSEWHERE = set()
# The endpoints this quirk needs, each with the input clusters it puts there where Zigbee2MQTT names none.
ENDPOINTS = {1: (0xEF00,)}


@functools.cache
def _is_shipped(source: str | None) -> bool:
    return bool(source) and pathlib.Path(source).resolve().is_relative_to(_SHIPPED)


def _misfit(device) -> str | None:
    """Why the device does not fit ENDPOINTS, None when it does.

    The device needs every endpoint in ENDPOINTS. Zigbee2MQTT sends a cluster it names no endpoint
    for to the first endpoint that announces it, or to the device's first endpoint when none does:
    each cluster in ENDPOINTS must land there on the endpoint this quirk puts it on.
    """
    announced = {ep_id: endpoint.in_clusters for ep_id, endpoint in sorted(device.endpoints.items()) if ep_id}
    for ep_id, cluster_ids in ENDPOINTS.items():
        if ep_id not in announced:
            return f"it has no endpoint {ep_id}"
        for cluster_id in cluster_ids:
            first = next((other for other, clusters in announced.items() if cluster_id in clusters), None)
            if first is None and min(announced) != ep_id:
                return f"no endpoint has cluster 0x{cluster_id:04X} and the first endpoint is {min(announced)}, not {ep_id}"
            if first is not None and first != ep_id:
                return f"the first endpoint with cluster 0x{cluster_id:04X} is {first}, not {ep_id}"
    return None


def _shipped_quirk(device):
    """The registry entry of a quirk shipped with ZHA that matches the device, None without one."""
    for entry in DEVICE_REGISTRY:
        # Green Power quirks (zha 2.4) never apply to a Zigbee device and cannot match one.
        if not isinstance(entry.device_match, DeviceMatch):
            continue
        if _is_shipped(getattr(entry.source, "file", None)) and entry.device_match.matches(device):
            return entry
    return None


def no_builtin_quirk(device) -> bool:
    """Upstream first: step back for every device that a quirk shipped with ZHA matches.

    ZHA tries this custom quirk before the shipped ones under the same name. This filter
    checks each device against the shipped quirks (name, endpoint signature, firmware range)
    and returns False when one matches, so ZHA falls through to the shipped quirk. Then it
    steps back for a device whose endpoints do not fit this quirk (ENDPOINTS).
    """
    if (device.manufacturer, device.model) in CLAIMED_ELSEWHERE:
        return False
    shipped = _shipped_quirk(device)
    if shipped is not None:
        if device.ieee not in _STEPPED_BACK:
            _STEPPED_BACK.add(device.ieee)
            _LOGGER.warning(
                "%s %s uses the quirk shipped with ZHA (%s); custom quirk %s is not needed for it",
                device.manufacturer, device.model, shipped.source.label, __name__,
            )
        return False
    misfit = _misfit(device)
    if misfit is not None:
        if (device.ieee, misfit) not in _STEPPED_BACK:
            _STEPPED_BACK.add((device.ieee, misfit))
            _LOGGER.warning(
                "%s %s does not fit custom quirk %s (%s); ZHA handles it without this quirk",
                device.manufacturer, device.model, __name__, misfit,
            )
        return False
    return True


(
    TuyaQuirkBuilder()
    .applies_to('_TZE284_tdg4ckyh', 'TS0601')
    .tuya_onoff(dp_id=117)
    .tuya_switch(dp_id=118, attribute_name='pack', entity_type=EntityType.STANDARD, translation_key='pack', fallback_name='Packet mode')
    .tuya_illuminance(dp_id=119)
    .tuya_enum(dp_id=101, attribute_name='button_1', enum_class=Button1, entity_type=EntityType.CONFIG, translation_key='button_1', fallback_name='Button 1 code learning')
    .tuya_enum(dp_id=102, attribute_name='button_2', enum_class=Button2, entity_type=EntityType.CONFIG, translation_key='button_2', fallback_name='Button 2 code learning')
    .tuya_enum(dp_id=103, attribute_name='button_3', enum_class=Button3, entity_type=EntityType.CONFIG, translation_key='button_3', fallback_name='Button 3 code learning')
    .tuya_enum(dp_id=104, attribute_name='button_4', enum_class=Button4, entity_type=EntityType.CONFIG, translation_key='button_4', fallback_name='Button 4 code learning')
    .tuya_enum(dp_id=105, attribute_name='button_5', enum_class=Button5, entity_type=EntityType.CONFIG, translation_key='button_5', fallback_name='Button 5 code learning')
    .tuya_enum(dp_id=106, attribute_name='button_6', enum_class=Button6, entity_type=EntityType.CONFIG, translation_key='button_6', fallback_name='Button 6 code learning')
    .tuya_enum(dp_id=107, attribute_name='button_7', enum_class=Button7, entity_type=EntityType.CONFIG, translation_key='button_7', fallback_name='Button 7 code learning')
    .tuya_enum(dp_id=108, attribute_name='button_8', enum_class=Button8, entity_type=EntityType.CONFIG, translation_key='button_8', fallback_name='Button 8 code learning')
    .tuya_enum(dp_id=109, attribute_name='start_1', enum_class=Start1, entity_type=EntityType.CONFIG, translation_key='start_1', fallback_name='Button 1 code transmit')
    .tuya_enum(dp_id=110, attribute_name='start_2', enum_class=Start2, entity_type=EntityType.CONFIG, translation_key='start_2', fallback_name='Button 2 code transmit')
    .tuya_enum(dp_id=111, attribute_name='start_3', enum_class=Start3, entity_type=EntityType.CONFIG, translation_key='start_3', fallback_name='Button 3 code transmit')
    .tuya_enum(dp_id=112, attribute_name='start_4', enum_class=Start4, entity_type=EntityType.CONFIG, translation_key='start_4', fallback_name='Button 4 code transmit')
    .tuya_enum(dp_id=113, attribute_name='start_5', enum_class=Start5, entity_type=EntityType.CONFIG, translation_key='start_5', fallback_name='Button 5 code transmit')
    .tuya_enum(dp_id=114, attribute_name='start_6', enum_class=Start6, entity_type=EntityType.CONFIG, translation_key='start_6', fallback_name='Button 6 code transmit')
    .tuya_enum(dp_id=115, attribute_name='start_7', enum_class=Start7, entity_type=EntityType.CONFIG, translation_key='start_7', fallback_name='Button 7 code transmit')
    .tuya_enum(dp_id=116, attribute_name='start_8', enum_class=Start8, entity_type=EntityType.CONFIG, translation_key='start_8', fallback_name='Button 8 code transmit')
    .skip_configuration()
    .filter(no_builtin_quirk)
    .add_to_registry()
)
