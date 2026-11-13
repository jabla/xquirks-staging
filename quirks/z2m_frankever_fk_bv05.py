"""FrankEver FK-BV05: Zigbee smart water valve with flow meter and temperature sensor.

Generated from the Zigbee2MQTT definition.
Data: zigbee-herdsman-converters, MIT, Copyright (c) 2018 Koen Kanters.
Status: generated, not verified on hardware.
Revision: 8c0f3ae1
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
    NumberDeviceClass,
    PERCENTAGE,
    SensorDeviceClass,
    SensorStateClass,
    UnitOfTemperature,
    UnitOfTime,
    UnitOfVolume,
)
from zhaquirks.tuya import TUYA_CLUSTER_ID
from zhaquirks.tuya.builder import TuyaQuirkBuilder


class WeatherDelay(t.enum8):
    """weather_delay values (z2m)."""

    cancel = 0x00
    Delay_24h = 0x01
    Delay_48h = 0x02
    Delay_72h = 0x03


class WaterLeakageState(t.enum8):
    """water_leakage_state values (z2m)."""

    water_leakage_yes = 0x00
    water_leakage_no = 0x01


class PowerOffState(t.enum8):
    """power_off_state values (z2m)."""

    off = 0x00
    on = 0x01
    maintain = 0x02



_LOGGER = logging.getLogger(__name__)
_SHIPPED = pathlib.Path(zhaquirks.__file__).resolve().parent
_STEPPED_BACK: set = set()

# The Zigbee fingerprints (manufacturer, model) this quirk is for; None matches any manufacturer.
FINGERPRINTS = [('_TZE200_nbqnmkee', 'TS0601')]
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
    .applies_to('_TZE200_nbqnmkee', 'TS0601')
    .tuya_onoff(dp_id=1)
    .tuya_number(dp_id=2, type=t.uint32_t, attribute_name='threshold', min_value=0, max_value=100, step=10, unit=PERCENTAGE, entity_type=EntityType.CONFIG, translation_key='threshold', fallback_name='Threshold')
    .tuya_sensor(dp_id=3, attribute_name='position', type=t.uint32_t, state_class=SensorStateClass.MEASUREMENT, unit=PERCENTAGE, entity_type=EntityType.STANDARD, translation_key='z2m_position', fallback_name='Position')
    .tuya_binary_sensor(dp_id=4, attribute_name='fault', entity_type=EntityType.DIAGNOSTIC, translation_key='fault', fallback_name='Fault')
    .tuya_sensor(dp_id=5, attribute_name='water_consumed_last', type=t.uint32_t, divisor=10, state_class=SensorStateClass.MEASUREMENT, unit=UnitOfVolume.LITERS, entity_type=EntityType.STANDARD, translation_key='water_consumed_last', fallback_name='Water consumed last')
    .tuya_sensor(dp_id=6, attribute_name='water_consumed', type=t.uint32_t, state_class=SensorStateClass.MEASUREMENT, unit=UnitOfVolume.LITERS, entity_type=EntityType.STANDARD, translation_key='water_consumed', fallback_name='Water consumed')
    .tuya_enum(dp_id=10, attribute_name='weather_delay', enum_class=WeatherDelay, entity_type=EntityType.CONFIG, translation_key='weather_delay', fallback_name='Weather delay')
    .tuya_number(dp_id=11, type=t.uint32_t, attribute_name='countdown', min_value=0, max_value=86400, unit=UnitOfTime.SECONDS, device_class=NumberDeviceClass.DURATION, entity_type=EntityType.CONFIG, translation_key='countdown', fallback_name='Countdown')
    .tuya_sensor(dp_id=22, attribute_name='water_temperature', type=t.uint32_t, state_class=SensorStateClass.MEASUREMENT, device_class=SensorDeviceClass.TEMPERATURE, unit=UnitOfTemperature.CELSIUS, entity_type=EntityType.STANDARD, translation_key='water_temperature', fallback_name='Water temperature')
    .tuya_dp_attribute(dp_id=101, attribute_name='water_leakage_state', type=WaterLeakageState, access=foundation.ZCLAttributeAccess.Read | foundation.ZCLAttributeAccess.Report, converter=lambda x: WaterLeakageState(int(x)))
    .enum(attribute_name='water_leakage_state', enum_class=WaterLeakageState, cluster_id=TUYA_CLUSTER_ID, entity_platform=EntityPlatform.SENSOR, entity_type=EntityType.STANDARD, translation_key='water_leakage_state', fallback_name='Water leakage state')
    .tuya_switch(dp_id=102, attribute_name='single_irrigation_switch', entity_type=EntityType.STANDARD, translation_key='single_irrigation_switch', fallback_name='Single irrigation switch')
    .tuya_number(dp_id=103, type=t.uint32_t, attribute_name='single_irrigation_set', min_value=0, max_value=1000, unit=UnitOfVolume.LITERS, entity_type=EntityType.CONFIG, translation_key='single_irrigation_set', fallback_name='Single irrigation set')
    .tuya_switch(dp_id=104, attribute_name='day_irrigation_switch', entity_type=EntityType.STANDARD, translation_key='day_irrigation_switch', fallback_name='Day irrigation switch')
    .tuya_number(dp_id=105, type=t.uint32_t, attribute_name='day_irrigation_set', min_value=0, max_value=1000, unit=UnitOfVolume.LITERS, entity_type=EntityType.CONFIG, translation_key='day_irrigation_set', fallback_name='Day irrigation set')
    .tuya_switch(dp_id=106, attribute_name='water_volume_alarm_switch', entity_type=EntityType.CONFIG, translation_key='water_volume_alarm_switch', fallback_name='Water volume alarm switch')
    .tuya_number(dp_id=107, type=t.uint32_t, attribute_name='water_volume_alarm_set', min_value=0, max_value=1000, unit=UnitOfVolume.LITERS, entity_type=EntityType.CONFIG, translation_key='water_volume_alarm_set', fallback_name='Water volume alarm set')
    .tuya_switch(dp_id=108, attribute_name='water_temp_alarm_switch', entity_type=EntityType.CONFIG, translation_key='water_temp_alarm_switch', fallback_name='Water temp alarm switch')
    .tuya_number(dp_id=109, type=t.uint32_t, attribute_name='water_temp_alarm_max', min_value=0, max_value=120, unit=UnitOfTemperature.CELSIUS, device_class=NumberDeviceClass.TEMPERATURE, entity_type=EntityType.CONFIG, translation_key='water_temp_alarm_max', fallback_name='Water temp alarm max')
    .tuya_enum(dp_id=110, attribute_name='power_off_state', enum_class=PowerOffState, entity_type=EntityType.CONFIG, translation_key='power_off_state', fallback_name='Power off state')
    .tuya_switch(dp_id=112, attribute_name='creep_switch', entity_type=EntityType.CONFIG, translation_key='creep_switch', fallback_name='Creep switch')
    .tuya_number(dp_id=113, type=t.uint32_t, attribute_name='water_temp_alarm_min', min_value=0, max_value=120, unit=UnitOfTemperature.CELSIUS, device_class=NumberDeviceClass.TEMPERATURE, entity_type=EntityType.CONFIG, translation_key='water_temp_alarm_min', fallback_name='Water temp alarm min')
    .tuya_binary_sensor(dp_id=114, attribute_name='water_temp_alarm', entity_type=EntityType.STANDARD, translation_key='water_temp_alarm', fallback_name='Water temp alarm')
    .tuya_binary_sensor(dp_id=115, attribute_name='water_volume_alarm', entity_type=EntityType.STANDARD, translation_key='water_volume_alarm', fallback_name='Water volume alarm')
    .skip_configuration()
    .filter(no_builtin_quirk)
    .add_to_registry()
)
