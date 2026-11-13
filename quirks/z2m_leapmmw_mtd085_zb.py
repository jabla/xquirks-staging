"""LeapMMW MTD085-ZB: Human presence sensor.

Generated from the Zigbee2MQTT definition.
Data: zigbee-herdsman-converters, MIT, Copyright (c) 2018 Koen Kanters.
Status: generated, not verified on hardware.
Revision: c5d08472
"""

import functools
import logging
import pathlib

import zhaquirks
from zha.quirks import DEVICE_REGISTRY, DeviceMatch
import zigpy.types as t

from zhaquirks.builder import (
    EntityType,
    LIGHT_LUX,
    NumberDeviceClass,
    PERCENTAGE,
    SensorDeviceClass,
    SensorStateClass,
    UnitOfLength,
    UnitOfTime,
)
from zhaquirks.tuya.builder import TuyaQuirkBuilder


class DebugMode(t.enum8):
    """debug_mode values (z2m)."""

    OFF = 0x00
    ON = 0x01


class ScenePreset(t.enum8):
    """scene_preset values (z2m)."""

    Custom = 0x00
    Toilet = 0x01
    Kitchen = 0x02
    Hallway = 0x03
    Bedroom = 0x04
    Livingroom = 0x05
    Meetingroom = 0x06
    Default = 0x07


class Sensor(t.enum8):
    """sensor values (z2m)."""

    on = 0x00
    occupied = 0x01
    unoccupied = 0x02


class StatusIndication(t.enum8):
    """status_indication values (z2m)."""

    OFF = 0x00
    ON = 0x01


class DistanceReportMode(t.enum8):
    """distance_report_mode values (z2m)."""

    Normal = 0x00
    Occupancy_detection = 0x01



_LOGGER = logging.getLogger(__name__)
_SHIPPED = pathlib.Path(zhaquirks.__file__).resolve().parent
_STEPPED_BACK: set = set()

# The Zigbee fingerprints (manufacturer, model) this quirk is for; None matches any manufacturer.
FINGERPRINTS = [('_TZ321C_fkzihax8', 'TS0225'), ('_TZ321C_4slreunp', 'TS0225')]
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
    .applies_to('_TZ321C_fkzihax8', 'TS0225')
    .applies_to('_TZ321C_4slreunp', 'TS0225')
    .tuya_number(dp_id=101, type=t.uint32_t, attribute_name='entry_sensitivity', min_value=10, max_value=100, step=10, unit=PERCENTAGE, entity_type=EntityType.CONFIG, translation_key='entry_sensitivity', fallback_name='Entry sensitivity')
    .tuya_number(dp_id=102, type=t.uint32_t, attribute_name='entry_distance', min_value=0, max_value=8, step=0.1, unit=UnitOfLength.METERS, multiplier=0.01, device_class=NumberDeviceClass.DISTANCE, entity_type=EntityType.CONFIG, translation_key='entry_distance', fallback_name='Entry distance')
    .tuya_number(dp_id=103, type=t.uint32_t, attribute_name='departure_delay', min_value=5, max_value=7200, step=1, unit=UnitOfTime.SECONDS, device_class=NumberDeviceClass.DURATION, entity_type=EntityType.CONFIG, translation_key='departure_delay', fallback_name='Departure delay')
    .tuya_number(dp_id=104, type=t.uint32_t, attribute_name='entry_filter_time', min_value=0, max_value=0.5, step=0.05, unit=UnitOfTime.SECONDS, multiplier=0.01, device_class=NumberDeviceClass.DURATION, entity_type=EntityType.CONFIG, translation_key='entry_filter_time', fallback_name='Entry filter time')
    .tuya_number(dp_id=105, type=t.uint32_t, attribute_name='block_time', min_value=0, max_value=10, step=0.1, unit=UnitOfTime.SECONDS, multiplier=0.1, device_class=NumberDeviceClass.DURATION, entity_type=EntityType.CONFIG, translation_key='block_time', fallback_name='Block time')
    .tuya_sensor(dp_id=107, attribute_name='illuminance', type=t.uint32_t, divisor=10, state_class=SensorStateClass.MEASUREMENT, device_class=SensorDeviceClass.ILLUMINANCE, unit=LIGHT_LUX, entity_type=EntityType.STANDARD, fallback_name='Illuminance')
    .tuya_enum(dp_id=108, attribute_name='debug_mode', enum_class=DebugMode, entity_type=EntityType.CONFIG, translation_key='debug_mode', fallback_name='Debug mode')
    .tuya_sensor(dp_id=109, attribute_name='debug_distance', type=t.uint32_t, divisor=100, state_class=SensorStateClass.MEASUREMENT, device_class=SensorDeviceClass.DISTANCE, unit=UnitOfLength.METERS, entity_type=EntityType.STANDARD, translation_key='debug_distance', fallback_name='Debug distance')
    .tuya_sensor(dp_id=110, attribute_name='debug_countdown', type=t.uint32_t, state_class=SensorStateClass.MEASUREMENT, device_class=SensorDeviceClass.DURATION, unit=UnitOfTime.SECONDS, entity_type=EntityType.STANDARD, translation_key='debug_countdown', fallback_name='Debug countdown')
    .tuya_enum(dp_id=111, attribute_name='scene_preset', enum_class=ScenePreset, entity_type=EntityType.CONFIG, translation_key='scene_preset', fallback_name='Scene preset')
    .tuya_enum(dp_id=112, attribute_name='sensor', enum_class=Sensor, entity_type=EntityType.CONFIG, translation_key='sensor', fallback_name='Sensor')
    .tuya_enum(dp_id=114, attribute_name='status_indication', enum_class=StatusIndication, entity_type=EntityType.CONFIG, translation_key='status_indication', fallback_name='Status indication')
    .tuya_number(dp_id=115, type=t.uint32_t, attribute_name='radar_sensitivity', min_value=10, max_value=100, step=10, unit=PERCENTAGE, entity_type=EntityType.CONFIG, translation_key='radar_sensitivity', fallback_name='Radar sensitivity')
    .tuya_number(dp_id=116, type=t.uint32_t, attribute_name='shield_range', min_value=0, max_value=8, step=0.1, unit=UnitOfLength.METERS, multiplier=0.01, device_class=NumberDeviceClass.DISTANCE, entity_type=EntityType.CONFIG, translation_key='shield_range', fallback_name='Shield range')
    .tuya_number(dp_id=117, type=t.uint32_t, attribute_name='detection_range', min_value=0, max_value=8, step=0.1, unit=UnitOfLength.METERS, multiplier=0.01, device_class=NumberDeviceClass.DISTANCE, entity_type=EntityType.CONFIG, translation_key='z2m_detection_range', fallback_name='Detection range')
    .tuya_sensor(dp_id=119, attribute_name='target_distance', type=t.uint32_t, divisor=100, state_class=SensorStateClass.MEASUREMENT, device_class=SensorDeviceClass.DISTANCE, unit=UnitOfLength.METERS, entity_type=EntityType.STANDARD, translation_key='target_distance', fallback_name='Target distance')
    .tuya_enum(dp_id=120, attribute_name='distance_report_mode', enum_class=DistanceReportMode, entity_type=EntityType.CONFIG, translation_key='distance_report_mode', fallback_name='Distance report mode')
    # DP 113 (cline): z2m exposes no entity for it, not generated
    # DP 118 (equipment_status): z2m exposes no entity for it, not generated
    .filter(no_builtin_quirk)
    .add_to_registry()
)
