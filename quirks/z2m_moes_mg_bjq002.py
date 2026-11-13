"""Moes MG-BJQ002: Plug-in smart siren alarm with RGB night light.

Generated from the Zigbee2MQTT definition.
Data: zigbee-herdsman-converters, MIT, Copyright (c) 2018 Koen Kanters.
Status: generated, not verified on hardware.
Revision: 691d2d09
"""

import functools
import logging
import pathlib

import zhaquirks
from zha.quirks import DEVICE_REGISTRY, DeviceMatch
import zigpy.types as t

from zhaquirks.builder import (
    EntityType,
    NumberDeviceClass,
    UnitOfTime,
)
from zhaquirks.tuya.builder import TuyaQuirkBuilder


class Alarm(t.enum8):
    """alarm values (z2m)."""

    sound = 0x00
    light = 0x01
    sound_light = 0x02
    off = 0x03


class Volume(t.enum8):
    """volume values (z2m)."""

    low = 0x00
    medium = 0x01
    high = 0x02
    mute = 0x03


class Ringtone(t.enum8):
    """ringtone values (z2m)."""

    ringtone_1 = 0x00
    ringtone_2 = 0x01
    ringtone_3 = 0x02
    ringtone_4 = 0x03
    ringtone_5 = 0x04
    ringtone_6 = 0x05
    ringtone_7 = 0x06
    ringtone_8 = 0x07
    ringtone_9 = 0x08
    ringtone_10 = 0x09
    ringtone_11 = 0x0A
    ringtone_12 = 0x0B
    ringtone_13 = 0x0C
    ringtone_14 = 0x0D
    ringtone_15 = 0x0E
    ringtone_16 = 0x0F
    ringtone_17 = 0x10
    ringtone_18 = 0x11
    ringtone_19 = 0x12
    ringtone_20 = 0x13
    ringtone_21 = 0x14
    ringtone_22 = 0x15
    ringtone_23 = 0x16
    ringtone_24 = 0x17
    ringtone_25 = 0x18
    ringtone_26 = 0x19
    ringtone_27 = 0x1A
    ringtone_28 = 0x1B
    ringtone_29 = 0x1C
    ringtone_30 = 0x1D
    ringtone_31 = 0x1E
    ringtone_32 = 0x1F


class LightMode(t.enum8):
    """light_mode values (z2m)."""

    rainbow = 0x00
    red_flash = 0x01
    night_light = 0x02



_LOGGER = logging.getLogger(__name__)
_SHIPPED = pathlib.Path(zhaquirks.__file__).resolve().parent
_STEPPED_BACK: set = set()

# The Zigbee fingerprints (manufacturer, model) this quirk is for; None matches any manufacturer.
FINGERPRINTS = [('_TZE20C_tjz9ad5g', 'TS0601')]
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
    .applies_to('_TZE20C_tjz9ad5g', 'TS0601')
    .tuya_enum(dp_id=1, attribute_name='alarm', enum_class=Alarm, entity_type=EntityType.STANDARD, translation_key='alarm', fallback_name='Alarm')
    .tuya_enum(dp_id=5, attribute_name='volume', enum_class=Volume, entity_type=EntityType.CONFIG, translation_key='volume', fallback_name='Volume')
    .tuya_number(dp_id=7, type=t.uint32_t, attribute_name='duration', min_value=1, max_value=1800, step=1, unit=UnitOfTime.SECONDS, device_class=NumberDeviceClass.DURATION, entity_type=EntityType.CONFIG, fallback_name='Duration')
    .tuya_enum(dp_id=21, attribute_name='ringtone', enum_class=Ringtone, entity_type=EntityType.CONFIG, translation_key='ringtone', fallback_name='Ringtone')
    .tuya_switch(dp_id=22, attribute_name='night_light', entity_type=EntityType.STANDARD, translation_key='night_light', fallback_name='Night light')
    .tuya_enum(dp_id=23, attribute_name='light_mode', enum_class=LightMode, entity_type=EntityType.CONFIG, translation_key='light_mode', fallback_name='Light mode')
    .skip_configuration()
    .filter(no_builtin_quirk)
    .add_to_registry()
)
