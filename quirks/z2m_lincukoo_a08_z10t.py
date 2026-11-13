"""Lincukoo A08-Z10T: Smart sound and flash siren.

Generated from the Zigbee2MQTT definition.
Data: zigbee-herdsman-converters, MIT, Copyright (c) 2018 Koen Kanters.
Status: generated, not verified on hardware.
Revision: bb75c37f
"""

import functools
import logging
import pathlib

import zhaquirks
from zha.quirks import DEVICE_REGISTRY, DeviceMatch
import zigpy.types as t
from zigpy.zcl import foundation

from zhaquirks.builder import (
    EntityPlatform,
    EntityType,
)
from zhaquirks.tuya import TUYA_CLUSTER_ID
from zhaquirks.tuya.builder import TuyaQuirkBuilder


class AlarmState(t.enum8):
    """alarm_state values (z2m)."""

    alarm_sound = 0x00
    alarm_light = 0x01
    alarm_sound_light = 0x02
    normal = 0x03


class AlarmVolume(t.enum8):
    """alarm_volume values (z2m)."""

    low = 0x00
    middle = 0x01
    high = 0x02
    mute = 0x03


class AlarmRingtone(t.enum8):
    """alarm_ringtone values (z2m)."""

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



_LOGGER = logging.getLogger(__name__)
_SHIPPED = pathlib.Path(zhaquirks.__file__).resolve().parent
_STEPPED_BACK: set = set()

# The Zigbee fingerprints (manufacturer, model) this quirk is for; None matches any manufacturer.
FINGERPRINTS = [('_TZE204_l4daccga', 'TS0601'), ('_TZE28C1000000_l4daccga', 'TS0601')]
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


def _upstream_first(device) -> bool:
    """Upstream first: step back for every device that a quirk shipped with ZHA matches.

    ZHA tries this custom quirk before the shipped ones under the same name. This check
    compares each device with the shipped quirks (name, endpoint signature, firmware range)
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


def no_builtin_quirk(device) -> bool:
    """The filter ZHA calls: _upstream_first, and a step back when that check fails.

    ZHA calls it while it loads its devices, where an error would stop ZHA as a whole (a
    newer ZHA may register entries this check does not know yet). Then this quirk steps
    back for the device instead, and the log says so once.
    """
    try:
        return _upstream_first(device)
    except Exception:
        if "check failed" not in _STEPPED_BACK:
            _STEPPED_BACK.add("check failed")
            _LOGGER.exception("custom quirk %s could not check a device; ZHA handles it without this quirk", __name__)
        return False


(
    TuyaQuirkBuilder()
    .applies_to('_TZE204_l4daccga', 'TS0601')
    .applies_to('_TZE28C1000000_l4daccga', 'TS0601')
    .tuya_dp_attribute(dp_id=1, attribute_name='alarm_state', type=AlarmState, access=foundation.ZCLAttributeAccess.Read | foundation.ZCLAttributeAccess.Write, converter=lambda x: AlarmState(int(x)), dp_converter=lambda x: int(x))
    .enum(attribute_name='alarm_state', enum_class=AlarmState, cluster_id=TUYA_CLUSTER_ID, entity_platform=EntityPlatform.SELECT, entity_type=EntityType.STANDARD, translation_key='alarm_state', fallback_name='Alarm state')
    .tuya_enum(dp_id=5, attribute_name='alarm_volume', enum_class=AlarmVolume, entity_type=EntityType.CONFIG, translation_key='alarm_volume', fallback_name='Alarm volume')
    .tuya_number(dp_id=7, type=t.uint32_t, attribute_name='alarm_time', min_value=0, max_value=100, step=1, unit='times', entity_type=EntityType.CONFIG, translation_key='alarm_time', fallback_name='Alarm time')
    .tuya_switch(dp_id=16, attribute_name='mute', entity_type=EntityType.STANDARD, translation_key='mute', fallback_name='Mute')
    .tuya_enum(dp_id=21, attribute_name='alarm_ringtone', enum_class=AlarmRingtone, entity_type=EntityType.CONFIG, translation_key='alarm_ringtone', fallback_name='Alarm ringtone')
    .skip_configuration()
    .filter(no_builtin_quirk)
    .add_to_registry()
)
