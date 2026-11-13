"""NEO NAS-PS10B2: Human presence sensor.

Generated from the Zigbee2MQTT definition.
ZHA ships a quirk for _TZE204_1youk3hj / TS0601 that decodes DP 102 differently, and a device
test confirmed z2m (data/known-conflicts.toml: neo-nas-ps10b2-dp102). These names get their own
quirk instead of an alias; once a quirk shipped with ZHA matches them, this file steps back.
Data: zigbee-herdsman-converters, MIT, Copyright (c) 2018 Koen Kanters.
Status: generated, not verified on hardware.
Revision: 3db7f96e
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
    SensorDeviceClass,
    SensorStateClass,
    UnitOfLength,
    UnitOfTime,
)
from zhaquirks.tuya import TUYA_CLUSTER_ID
from zhaquirks.tuya.builder import TuyaQuirkBuilder
from zhaquirks.tuya.tuya_motion import TuyaOccupancySensing


class HumanMotionState(t.enum8):
    """human_motion_state values (z2m)."""

    none = 0x00
    small = 0x01
    large = 0x02


class WorkMode(t.enum8):
    """work_mode values (z2m)."""

    manual = 0x00
    auto = 0x01


class LuxValue(t.enum8):
    """lux_value values (z2m)."""

    Lux_10 = 0x00
    Lux_20 = 0x01
    Lux_50 = 0x02
    Lux_24h = 0x03



_LOGGER = logging.getLogger(__name__)
_SHIPPED = pathlib.Path(zhaquirks.__file__).resolve().parent
_STEPPED_BACK: set = set()

# The Zigbee fingerprints (manufacturer, model) this quirk is for; None matches any manufacturer.
FINGERPRINTS = [('_TZE284_1youk3hj', 'TS0601'), ('_TZE28C1000000_1youk3hj', 'TS0601')]
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
    .applies_to('_TZE284_1youk3hj', 'TS0601')
    .applies_to('_TZE28C1000000_1youk3hj', 'TS0601')
    .tuya_dp(dp_id=1, ep_attribute=TuyaOccupancySensing.ep_attribute, attribute_name=OccupancySensing.AttributeDefs.occupancy.name, converter=lambda x: x == 1)
    .adds(TuyaOccupancySensing)
    .tuya_dp_attribute(dp_id=11, attribute_name='human_motion_state', type=HumanMotionState, access=foundation.ZCLAttributeAccess.Read | foundation.ZCLAttributeAccess.Report, converter=lambda x: HumanMotionState(int(x)))
    .enum(attribute_name='human_motion_state', enum_class=HumanMotionState, cluster_id=TUYA_CLUSTER_ID, entity_platform=EntityPlatform.SENSOR, entity_type=EntityType.STANDARD, translation_key='human_motion_state', fallback_name='Human motion state')
    .tuya_sensor(dp_id=19, attribute_name='dis_current', type=t.uint32_t, state_class=SensorStateClass.MEASUREMENT, device_class=SensorDeviceClass.DISTANCE, unit=UnitOfLength.CENTIMETERS, entity_type=EntityType.STANDARD, translation_key='dis_current', fallback_name='Current distance')
    .tuya_number(dp_id=13, type=t.uint32_t, attribute_name='motion_far_detection', min_value=150, max_value=600, step=75, unit=UnitOfLength.CENTIMETERS, device_class=NumberDeviceClass.DISTANCE, entity_type=EntityType.CONFIG, translation_key='motion_far_detection', fallback_name='Motion far detection')
    .tuya_number(dp_id=15, type=t.uint32_t, attribute_name='motion_sensitivity', min_value=0, max_value=7, step=1, entity_type=EntityType.CONFIG, translation_key='motion_sensitivity', fallback_name='Motion sensitivity')
    .tuya_number(dp_id=16, type=t.uint32_t, attribute_name='motionless_sensitivity', min_value=0, max_value=7, step=1, entity_type=EntityType.CONFIG, translation_key='z2m_motionless_sensitivity', fallback_name='Motionless sensitivity')
    .tuya_enum(dp_id=101, attribute_name='work_mode', enum_class=WorkMode, entity_type=EntityType.CONFIG, translation_key='work_mode', fallback_name='Work mode')
    .tuya_switch(dp_id=104, attribute_name='output_switch', entity_type=EntityType.STANDARD, translation_key='output_switch', fallback_name='Output switch')
    .tuya_number(dp_id=103, type=t.uint32_t, attribute_name='output_time', min_value=10, max_value=1800, unit=UnitOfTime.SECONDS, device_class=NumberDeviceClass.DURATION, entity_type=EntityType.CONFIG, translation_key='output_time', fallback_name='Output time')
    .tuya_switch(dp_id=105, attribute_name='led_switch', entity_type=EntityType.CONFIG, translation_key='led_switch', fallback_name='LED switch')
    .tuya_enum(dp_id=102, attribute_name='lux_value', enum_class=LuxValue, entity_type=EntityType.CONFIG, translation_key='lux_value', fallback_name='Lux value')
    # DP 12 (presence_time): a setting z2m decodes with its own code, not generated yet
    .skip_configuration()
    .filter(no_builtin_quirk)
    .add_to_registry()
)
