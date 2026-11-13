"""HOBEIAN ZG-228Z: Vibration alarm.

Generated from the Zigbee2MQTT definition.
Data: zigbee-herdsman-converters, MIT, Copyright (c) 2018 Koen Kanters.
Status: generated, not verified on hardware.
Revision: 5eed9e9a
"""

import functools
import logging
import pathlib

import zhaquirks
from zha.quirks import DEVICE_REGISTRY, DeviceMatch
import zigpy.types as t
from zigpy.zcl import foundation

from zhaquirks.builder import (
    BinarySensorDeviceClass,
    EntityType,
    NumberDeviceClass,
    UnitOfTime,
)
from zhaquirks.tuya import TUYA_CLUSTER_ID
from zhaquirks.tuya.builder import TuyaQuirkBuilder


class VibrationSiren(t.enum8):
    """vibration_siren values (z2m)."""

    OFF = 0x00
    ON = 0x01


class Alarm(t.enum8):
    """alarm values (z2m)."""

    beep = 0x00
    ring = 0x01
    stop = 0x02


class AlarmVolume(t.enum8):
    """alarm_volume values (z2m)."""

    low = 0x00
    middle = 0x01
    high = 0x02
    mute = 0x03


class AlarmRing(t.enum8):
    """alarm_ring values (z2m)."""

    mute = 0x00
    beep = 0x01
    music = 0x02



_LOGGER = logging.getLogger(__name__)
_SHIPPED = pathlib.Path(zhaquirks.__file__).resolve().parent
_STEPPED_BACK: set = set()

# The Zigbee fingerprints (manufacturer, model) this quirk is for; None matches any manufacturer.
FINGERPRINTS = [(None, 'ZG-228Z'), ('HOBEIAN', 'ZG-228Z')]
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
    .applies_to(None, 'ZG-228Z')
    .applies_to('HOBEIAN', 'ZG-228Z')
    .tuya_dp_attribute(dp_id=1, attribute_name='vibration', type=t.Bool, access=foundation.ZCLAttributeAccess.Read | foundation.ZCLAttributeAccess.Report, converter=lambda x: x == 1)
    .binary_sensor(attribute_name='vibration', cluster_id=TUYA_CLUSTER_ID, entity_type=EntityType.STANDARD, device_class=BinarySensorDeviceClass.VIBRATION, fallback_name='Vibration')
    .tuya_enum(dp_id=101, attribute_name='vibration_siren', enum_class=VibrationSiren, entity_type=EntityType.CONFIG, translation_key='vibration_siren', fallback_name='Vibration siren')
    .tuya_enum(dp_id=105, attribute_name='alarm', enum_class=Alarm, entity_type=EntityType.STANDARD, translation_key='alarm', fallback_name='Alarm')
    .tuya_switch(dp_id=102, attribute_name='muffling', entity_type=EntityType.STANDARD, translation_key='muffling', fallback_name='Muffling')
    .tuya_battery(dp_id=4, scale=2)
    .tuya_number(dp_id=106, type=t.uint32_t, attribute_name='alarm_time', min_value=0, max_value=1800, step=1, unit=UnitOfTime.SECONDS, device_class=NumberDeviceClass.DURATION, entity_type=EntityType.CONFIG, translation_key='alarm_time', fallback_name='Alarm time')
    .tuya_number(dp_id=6, type=t.uint32_t, attribute_name='sensitivity', min_value=1, max_value=50, step=1, entity_type=EntityType.CONFIG, translation_key='sensitivity', fallback_name='Sensitivity')
    .tuya_enum(dp_id=103, attribute_name='alarm_volume', enum_class=AlarmVolume, entity_type=EntityType.CONFIG, translation_key='alarm_volume', fallback_name='Alarm volume')
    .tuya_enum(dp_id=104, attribute_name='alarm_ring', enum_class=AlarmRing, entity_type=EntityType.CONFIG, translation_key='alarm_ring', fallback_name='Alarm ring')
    .skip_configuration()
    .filter(no_builtin_quirk)
    .add_to_registry()
)
