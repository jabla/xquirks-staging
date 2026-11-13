"""HYSYIOT HS208Z: PIR 24Ghz human presence sensor.

Generated from the Zigbee2MQTT definition.
Data: zigbee-herdsman-converters, MIT, Copyright (c) 2018 Koen Kanters.
Status: generated, not verified on hardware.
Revision: a8507a26
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
    EntityPlatform,
    EntityType,
    NumberDeviceClass,
    PERCENTAGE,
    UnitOfLength,
    UnitOfTemperature,
    UnitOfTime,
)
from zhaquirks.tuya import TUYA_CLUSTER_ID
from zhaquirks.tuya.builder import TuyaQuirkBuilder


class BatteryState(t.enum8):
    """battery_state values (z2m)."""

    low = 0x00
    middle = 0x01
    high = 0x02


class PirSensitivity(t.enum8):
    """pir_sensitivity values (z2m)."""

    low = 0x00
    middle = 0x01
    high = 0x02


class MotionState(t.enum8):
    """motion_state values (z2m)."""

    none = 0x00
    move = 0x01
    Micro_move = 0x02
    static = 0x03


class TemperatureUnit(t.enum8):
    """temperature_unit values (z2m)."""

    celsius = 0x00
    fahrenheit = 0x01


class MotionDetectionMode(t.enum8):
    """motion_detection_mode values (z2m)."""

    pir_and_radar = 0x00
    pir_or_radar = 0x01
    only_radar = 0x02



_LOGGER = logging.getLogger(__name__)
_SHIPPED = pathlib.Path(zhaquirks.__file__).resolve().parent
_STEPPED_BACK: set = set()

# The Zigbee fingerprints (manufacturer, model) this quirk is for; None matches any manufacturer.
FINGERPRINTS = [('_TZD200_sjjp9bti', 'TS0202'), (None, 'HS208Z')]
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
    .applies_to('_TZD200_sjjp9bti', 'TS0202')
    .applies_to(None, 'HS208Z')
    .tuya_dp_attribute(dp_id=3, attribute_name='battery_state', type=BatteryState, access=foundation.ZCLAttributeAccess.Read | foundation.ZCLAttributeAccess.Report, converter=lambda x: BatteryState(int(x)))
    .enum(attribute_name='battery_state', enum_class=BatteryState, cluster_id=TUYA_CLUSTER_ID, entity_platform=EntityPlatform.SENSOR, entity_type=EntityType.STANDARD, translation_key='battery_state', fallback_name='Battery state')
    .tuya_dp_attribute(dp_id=9, attribute_name='pir_sensitivity', type=PirSensitivity, access=foundation.ZCLAttributeAccess.Read | foundation.ZCLAttributeAccess.Write, converter=lambda x: PirSensitivity(int(x)), dp_converter=lambda x: int(x))
    .enum(attribute_name='pir_sensitivity', enum_class=PirSensitivity, cluster_id=TUYA_CLUSTER_ID, entity_platform=EntityPlatform.SELECT, entity_type=EntityType.CONFIG, translation_key='pir_sensitivity', fallback_name='PIR sensitivity')
    .tuya_illuminance(dp_id=11)
    .tuya_number(dp_id=12, type=t.uint32_t, attribute_name='pir_delay', min_value=30, max_value=120, unit=UnitOfTime.SECONDS, device_class=NumberDeviceClass.DURATION, entity_type=EntityType.CONFIG, translation_key='pir_delay', fallback_name='PIR delay')
    .tuya_number(dp_id=101, type=t.uint32_t, attribute_name='light_sensor_time', min_value=1, max_value=60, entity_type=EntityType.CONFIG, translation_key='light_sensor_time', fallback_name='Light sensor time')
    .tuya_binary_sensor(dp_id=102, attribute_name='vibration', entity_type=EntityType.STANDARD, device_class=BinarySensorDeviceClass.VIBRATION, fallback_name='Vibration')
    .tuya_number(dp_id=103, type=t.uint32_t, attribute_name='detection_distance', min_value=1, max_value=500, unit=UnitOfLength.CENTIMETERS, device_class=NumberDeviceClass.DISTANCE, entity_type=EntityType.CONFIG, translation_key='detection_distance', fallback_name='Detection distance')
    .tuya_number(dp_id=104, type=t.uint32_t, attribute_name='static_sensitivity', min_value=1, max_value=10, entity_type=EntityType.CONFIG, translation_key='static_sensitivity', fallback_name='Static sensitivity')
    .tuya_dp_attribute(dp_id=105, attribute_name='motion_state', type=MotionState, access=foundation.ZCLAttributeAccess.Read | foundation.ZCLAttributeAccess.Report, converter=lambda x: MotionState(int(x)))
    .enum(attribute_name='motion_state', enum_class=MotionState, cluster_id=TUYA_CLUSTER_ID, entity_platform=EntityPlatform.SENSOR, entity_type=EntityType.STANDARD, translation_key='motion_state', fallback_name='Motion state')
    .tuya_number(dp_id=106, type=t.int32s, attribute_name='temperature_calibration', min_value=-4, max_value=4, step=0.5, unit=UnitOfTemperature.CELSIUS, multiplier=0.1, device_class=NumberDeviceClass.TEMPERATURE_DELTA, entity_type=EntityType.CONFIG, translation_key='temperature_calibration', fallback_name='Temperature calibration')
    .tuya_switch(dp_id=107, attribute_name='indicator', entity_type=EntityType.CONFIG, translation_key='indicator', fallback_name='Indicator')
    .tuya_number(dp_id=108, type=t.int32s, attribute_name='humidity_calibration', min_value=-10, max_value=10, unit=PERCENTAGE, entity_type=EntityType.CONFIG, translation_key='humidity_calibration', fallback_name='Humidity calibration')
    .tuya_enum(dp_id=109, attribute_name='temperature_unit', enum_class=TemperatureUnit, entity_type=EntityType.CONFIG, translation_key='temperature_unit', fallback_name='Temperature unit')
    .tuya_temperature(dp_id=110, scale=10)
    .tuya_humidity(dp_id=111, scale=100)
    .tuya_number(dp_id=112, type=t.uint32_t, attribute_name='vibration_sensitivity', min_value=1, max_value=100, entity_type=EntityType.CONFIG, translation_key='vibration_sensitivity', fallback_name='Vibration sensitivity')
    .tuya_number(dp_id=113, type=t.uint32_t, attribute_name='vibration_delay', min_value=1, max_value=1440, unit=UnitOfTime.SECONDS, device_class=NumberDeviceClass.DURATION, entity_type=EntityType.CONFIG, translation_key='vibration_delay', fallback_name='Vibration delay')
    .tuya_enum(dp_id=122, attribute_name='motion_detection_mode', enum_class=MotionDetectionMode, entity_type=EntityType.CONFIG, translation_key='motion_detection_mode', fallback_name='Motion detection mode')
    .tuya_number(dp_id=123, type=t.uint32_t, attribute_name='detection_sensitivity', min_value=1, max_value=10, entity_type=EntityType.CONFIG, translation_key='detection_sensitivity', fallback_name='Detection sensitivity')
    .filter(no_builtin_quirk)
    .add_to_registry()
)
