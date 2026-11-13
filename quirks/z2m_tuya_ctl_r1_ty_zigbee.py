"""Tuya CTL-R1-TY-Zigbee: 24G radar human presence motion sensor..

Generated from the Zigbee2MQTT definition.
Data: zigbee-herdsman-converters, MIT, Copyright (c) 2018 Koen Kanters.
Status: generated, not verified on hardware.
Revision: 7deabeb3
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
    EntityType,
    LIGHT_LUX,
    NumberDeviceClass,
    PERCENTAGE,
    UnitOfLength,
    UnitOfTime,
)
from zhaquirks.tuya import TUYA_CLUSTER_ID
from zhaquirks.tuya.builder import TuyaQuirkBuilder
from zhaquirks.tuya.tuya_motion import TuyaOccupancySensing


class IndicatorLight(t.enum8):
    """indicator_light values (z2m)."""

    presence = 0x00
    off = 0x01
    on = 0x02


class DetectionMethod(t.enum8):
    """detection_method values (z2m)."""

    only_move = 0x00
    exist_move = 0x01



_LOGGER = logging.getLogger(__name__)
_SHIPPED = pathlib.Path(zhaquirks.__file__).resolve().parent
_STEPPED_BACK: set = set()

# The Zigbee fingerprints (manufacturer, model) this quirk is for; None matches any manufacturer.
FINGERPRINTS = [('_TZE204_e9ajs4ft', 'TS0601')]
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
    .applies_to('_TZE204_e9ajs4ft', 'TS0601')
    .tuya_dp(dp_id=1, ep_attribute=TuyaOccupancySensing.ep_attribute, attribute_name=OccupancySensing.AttributeDefs.occupancy.name, converter=lambda x: x == 1)
    .adds(TuyaOccupancySensing)
    .tuya_number(dp_id=2, type=t.uint32_t, attribute_name='presence_sensitivity', min_value=0, max_value=100, step=1, unit=PERCENTAGE, entity_type=EntityType.CONFIG, translation_key='presence_sensitivity', fallback_name='Presence sensitivity')
    .tuya_number(dp_id=4, type=t.uint32_t, attribute_name='detection_range', min_value=1.5, max_value=4.5, step=0.1, unit=UnitOfLength.METERS, multiplier=0.1, device_class=NumberDeviceClass.DISTANCE, entity_type=EntityType.CONFIG, translation_key='z2m_detection_range', fallback_name='Detection range')
    .tuya_illuminance(dp_id=101)
    .tuya_number(dp_id=102, type=t.uint32_t, attribute_name='illuminance_treshold_max', min_value=0, max_value=2000, step=1, unit=LIGHT_LUX, device_class=NumberDeviceClass.ILLUMINANCE, entity_type=EntityType.CONFIG, translation_key='illuminance_treshold_max', fallback_name='Illuminance treshold max')
    .tuya_number(dp_id=103, type=t.uint32_t, attribute_name='illuminance_treshold_min', min_value=0, max_value=2000, step=1, unit=LIGHT_LUX, device_class=NumberDeviceClass.ILLUMINANCE, entity_type=EntityType.CONFIG, translation_key='illuminance_treshold_min', fallback_name='Illuminance treshold min')
    .tuya_number(dp_id=104, type=t.uint32_t, attribute_name='detection_delay', min_value=1, max_value=600, step=1, unit=UnitOfTime.SECONDS, device_class=NumberDeviceClass.DURATION, entity_type=EntityType.CONFIG, translation_key='detection_delay', fallback_name='Detection delay')
    .tuya_dp_attribute(dp_id=109, attribute_name='presence_illuminance_switch', type=t.Bool, access=foundation.ZCLAttributeAccess.Read | foundation.ZCLAttributeAccess.Report, converter=lambda x: x == 1)
    .binary_sensor(attribute_name='presence_illuminance_switch', cluster_id=TUYA_CLUSTER_ID, entity_type=EntityType.STANDARD, translation_key='presence_illuminance_switch', fallback_name='Presence illuminance switch')
    .tuya_binary_sensor(dp_id=105, attribute_name='light_switch', entity_type=EntityType.STANDARD, translation_key='z2m_light_switch', fallback_name='Light switch')
    .tuya_dp_attribute(dp_id=106, attribute_name='light_linkage', type=t.Bool, access=foundation.ZCLAttributeAccess.Read | foundation.ZCLAttributeAccess.Report, converter=lambda x: x == 1)
    .binary_sensor(attribute_name='light_linkage', cluster_id=TUYA_CLUSTER_ID, entity_type=EntityType.STANDARD, translation_key='light_linkage', fallback_name='Light linkage')
    .tuya_enum(dp_id=107, attribute_name='indicator_light', enum_class=IndicatorLight, entity_type=EntityType.CONFIG, translation_key='indicator_light', fallback_name='Indicator light')
    .tuya_enum(dp_id=108, attribute_name='detection_method', enum_class=DetectionMethod, entity_type=EntityType.CONFIG, translation_key='detection_method', fallback_name='Detection method')
    # DP 113 (find_switch): z2m exposes no entity for it, not generated
    .skip_configuration()
    .filter(no_builtin_quirk)
    .add_to_registry()
)
