"""HOBEIAN ZG-204ZM: PIR 24Ghz human presence sensor.

Generated from the Zigbee2MQTT definition.
ZHA ships a quirk for _TZE200_2aaelwxk / TS0601, _TZE200_kb5noeto / TS0601 that decodes DP 122
differently, and a device test confirmed z2m (data/known-conflicts.toml: hobeian-zg-204zm-
dp122). These names get their own quirk instead of an alias; once a quirk shipped with ZHA
matches them, this file steps back.
Data: zigbee-herdsman-converters, MIT, Copyright (c) 2018 Koen Kanters.
Status: generated, not verified on hardware.
Revision: 2d87f28c
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


class MotionDetectionMode(t.enum8):
    """motion_detection_mode values (z2m)."""

    only_pir = 0x00
    pir_and_radar = 0x01
    only_radar = 0x02



_LOGGER = logging.getLogger(__name__)
_SHIPPED = pathlib.Path(zhaquirks.__file__).resolve().parent
_STEPPED_BACK: set = set()

# The Zigbee fingerprints (manufacturer, model) this quirk is for; None matches any manufacturer.
FINGERPRINTS = [('_TZE200_tyffvoij', 'TS0601'), ('_TZE200_yflzeeqj', 'TS0601')]
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
    .applies_to('_TZE200_tyffvoij', 'TS0601')
    .applies_to('_TZE200_yflzeeqj', 'TS0601')
    .tuya_dp(dp_id=1, ep_attribute=TuyaOccupancySensing.ep_attribute, attribute_name=OccupancySensing.AttributeDefs.occupancy.name, converter=lambda x: x == 1)
    .adds(TuyaOccupancySensing)
    .tuya_number(dp_id=2, type=t.uint32_t, attribute_name='static_detection_sensitivity', min_value=0, max_value=10, step=1, entity_type=EntityType.CONFIG, translation_key='static_detection_sensitivity', fallback_name='Static detection sensitivity')
    .tuya_number(dp_id=4, type=t.uint32_t, attribute_name='static_detection_distance', min_value=0, max_value=6, step=0.01, unit=UnitOfLength.METERS, multiplier=0.01, device_class=NumberDeviceClass.DISTANCE, entity_type=EntityType.CONFIG, translation_key='static_detection_distance', fallback_name='Static detection distance')
    .tuya_dp_attribute(dp_id=101, attribute_name='motion_state', type=MotionState, access=foundation.ZCLAttributeAccess.Read | foundation.ZCLAttributeAccess.Report, converter=lambda x: MotionState(int(x)))
    .enum(attribute_name='motion_state', enum_class=MotionState, cluster_id=TUYA_CLUSTER_ID, entity_platform=EntityPlatform.SENSOR, entity_type=EntityType.STANDARD, translation_key='motion_state', fallback_name='Motion state')
    .tuya_number(dp_id=102, type=t.uint32_t, attribute_name='fading_time', min_value=0, max_value=28800, step=1, unit=UnitOfTime.SECONDS, device_class=NumberDeviceClass.DURATION, entity_type=EntityType.CONFIG, translation_key='fading_time', fallback_name='Fading time')
    .tuya_illuminance(dp_id=106)
    .tuya_switch(dp_id=107, attribute_name='indicator', entity_type=EntityType.CONFIG, translation_key='indicator', fallback_name='Indicator')
    .tuya_battery(dp_id=121, scale=2)
    .tuya_enum(dp_id=122, attribute_name='motion_detection_mode', enum_class=MotionDetectionMode, entity_type=EntityType.CONFIG, translation_key='motion_detection_mode', fallback_name='Motion detection mode')
    .tuya_number(dp_id=123, type=t.uint32_t, attribute_name='motion_detection_sensitivity', min_value=0, max_value=10, step=1, entity_type=EntityType.CONFIG, translation_key='motion_detection_sensitivity', fallback_name='Motion detection sensitivity')
    .skip_configuration()
    .filter(no_builtin_quirk)
    .add_to_registry()
)
