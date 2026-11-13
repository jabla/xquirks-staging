"""HOBEIAN ZG-205ZL: 24Ghz/5.8GHz human presence sensor.

Generated from the Zigbee2MQTT definition.
Data: zigbee-herdsman-converters, MIT, Copyright (c) 2018 Koen Kanters.
Status: generated, not verified on hardware.
Revision: 76b7c788
"""

import functools
import logging
import pathlib

import zhaquirks
from zha.quirks import DEVICE_REGISTRY, DeviceMatch
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.measurement import OccupancySensing

from zhaquirks.builder import (
    EntityPlatform,
    EntityType,
    NumberDeviceClass,
    UnitOfLength,
    UnitOfTime,
)
from zhaquirks.tuya import TUYA_CLUSTER_ID
from zhaquirks.tuya.builder import TuyaQuirkBuilder
from zhaquirks.tuya.tuya_motion import TuyaOccupancySensing


class MotionState(t.enum8):
    """motion_state values (z2m)."""

    none = 0x00
    large = 0x01
    small = 0x02
    static = 0x03
    far = 0x04
    near = 0x05


class Mode(t.enum8):
    """mode values (z2m)."""

    arm = 0x00
    off = 0x01
    alarm = 0x02
    doorbell = 0x03


class AlarmVolume(t.enum8):
    """alarm_volume values (z2m)."""

    low = 0x00
    medium = 0x01
    high = 0x02
    mute = 0x03



_LOGGER = logging.getLogger(__name__)
_SHIPPED = pathlib.Path(zhaquirks.__file__).resolve().parent
_STEPPED_BACK: set = set()

# The Zigbee fingerprints (manufacturer, model) this quirk is for; None matches any manufacturer.
FINGERPRINTS = [('_TZE200_hl0ss9oa', 'TS0225'), ('ZGAF-205L', 'CK-BL702-MWS-01(7016)'), ('_TZE200_y4mdop0b', 'TS0225'), (None, 'ZG-205ZL')]
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
    .applies_to('_TZE200_hl0ss9oa', 'TS0225')
    .applies_to('ZGAF-205L', 'CK-BL702-MWS-01(7016)')
    .applies_to('_TZE200_y4mdop0b', 'TS0225')
    .applies_to(None, 'ZG-205ZL')
    .tuya_dp(dp_id=1, ep_attribute=TuyaOccupancySensing.ep_attribute, attribute_name=OccupancySensing.AttributeDefs.occupancy.name, converter=lambda x: x == 1)
    .adds(TuyaOccupancySensing)
    .tuya_illuminance(dp_id=20)
    .tuya_dp_attribute(dp_id=11, attribute_name='motion_state', type=MotionState, access=foundation.ZCLAttributeAccess.Read | foundation.ZCLAttributeAccess.Report, converter=lambda x: MotionState(int(x)))
    .enum(attribute_name='motion_state', enum_class=MotionState, cluster_id=TUYA_CLUSTER_ID, entity_platform=EntityPlatform.SENSOR, entity_type=EntityType.STANDARD, translation_key='motion_state', fallback_name='Motion state')
    .tuya_number(dp_id=12, type=t.uint32_t, attribute_name='fading_time', min_value=0, max_value=3600, step=1, unit=UnitOfTime.SECONDS, device_class=NumberDeviceClass.DURATION, entity_type=EntityType.CONFIG, translation_key='fading_time', fallback_name='Fading time')
    .tuya_number(dp_id=13, type=t.uint32_t, attribute_name='large_motion_detection_distance', min_value=0, max_value=10, step=0.01, unit=UnitOfLength.METERS, multiplier=0.01, device_class=NumberDeviceClass.DISTANCE, entity_type=EntityType.CONFIG, translation_key='z2m_large_motion_detection_distance', fallback_name='Large motion detection distance')
    .tuya_number(dp_id=15, type=t.uint32_t, attribute_name='large_motion_detection_sensitivity', min_value=0, max_value=10, step=1, entity_type=EntityType.CONFIG, translation_key='z2m_large_motion_detection_sensitivity', fallback_name='Large motion detection sensitivity')
    .tuya_number(dp_id=14, type=t.uint32_t, attribute_name='small_motion_detection_distance', min_value=0, max_value=6, step=0.01, unit=UnitOfLength.METERS, multiplier=0.01, device_class=NumberDeviceClass.DISTANCE, entity_type=EntityType.CONFIG, translation_key='small_motion_detection_distance', fallback_name='Small motion detection distance')
    .tuya_number(dp_id=16, type=t.uint32_t, attribute_name='small_motion_detection_sensitivity', min_value=0, max_value=10, step=1, entity_type=EntityType.CONFIG, translation_key='small_motion_detection_sensitivity', fallback_name='Small motion detection sensitivity')
    .tuya_number(dp_id=103, type=t.uint32_t, attribute_name='static_detection_distance', min_value=0, max_value=6, step=0.01, unit=UnitOfLength.METERS, multiplier=0.01, device_class=NumberDeviceClass.DISTANCE, entity_type=EntityType.CONFIG, translation_key='static_detection_distance', fallback_name='Static detection distance')
    .tuya_number(dp_id=104, type=t.uint32_t, attribute_name='static_detection_sensitivity', min_value=0, max_value=10, step=1, entity_type=EntityType.CONFIG, translation_key='static_detection_sensitivity', fallback_name='Static detection sensitivity')
    .tuya_enum(dp_id=105, attribute_name='mode', enum_class=Mode, entity_type=EntityType.CONFIG, translation_key='mode', fallback_name='Mode')
    .tuya_enum(dp_id=102, attribute_name='alarm_volume', enum_class=AlarmVolume, entity_type=EntityType.CONFIG, translation_key='alarm_volume', fallback_name='Alarm volume')
    .tuya_number(dp_id=101, type=t.uint32_t, attribute_name='alarm_time', min_value=1, max_value=60, step=1, unit=UnitOfLength.METERS, device_class=NumberDeviceClass.DISTANCE, entity_type=EntityType.CONFIG, translation_key='alarm_time', fallback_name='Alarm time')
    .tuya_switch(dp_id=24, attribute_name='light_mode', entity_type=EntityType.STANDARD, translation_key='light_mode', fallback_name='Light mode')
    .filter(no_builtin_quirk)
    .add_to_registry()
)
