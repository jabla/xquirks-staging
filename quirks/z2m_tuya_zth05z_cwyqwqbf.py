"""Tuya ZTH05Z: Temperature and humidity sensor.

Generated from the Zigbee2MQTT definition.
Zigbee2MQTT lists these names with _TZE200_vvmbj46n / TS0601, _TZE200_w6n8jeuu / TS0601,
_TZE284_vvmbj46n / TS0601, but the quirk ZHA ships for those does not fit them (exposes differ).
These names get their own quirk instead of an alias; once a quirk shipped with ZHA matches them,
this file steps back.
Data: zigbee-herdsman-converters, MIT, Copyright (c) 2018 Koen Kanters.
Status: generated, not verified on hardware.
Revision: 6c40b800
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
    UnitOfTemperature,
    UnitOfTime,
)
from zhaquirks.tuya import TUYA_CLUSTER_ID
from zhaquirks.tuya.builder import TuyaQuirkBuilder


class BatteryState(t.enum8):
    """battery_state values (z2m)."""

    low = 0x00
    medium = 0x01
    high = 0x02


class TemperatureUnit(t.enum8):
    """temperature_unit values (z2m)."""

    celsius = 0x00
    fahrenheit = 0x01


class TemperatureAlarm(t.enum8):
    """temperature_alarm values (z2m)."""

    lower_alarm = 0x00
    upper_alarm = 0x01
    cancel = 0x02


class HumidityAlarm(t.enum8):
    """humidity_alarm values (z2m)."""

    lower_alarm = 0x00
    upper_alarm = 0x01
    cancel = 0x02



_LOGGER = logging.getLogger(__name__)
_SHIPPED = pathlib.Path(zhaquirks.__file__).resolve().parent
_STEPPED_BACK: set = set()

# The Zigbee fingerprints (manufacturer, model) this quirk is for; None matches any manufacturer.
FINGERPRINTS = [('_TZE284_cwyqwqbf', 'TS0601')]
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
    .applies_to('_TZE284_cwyqwqbf', 'TS0601')
    .tuya_temperature(dp_id=1, scale=10)
    .tuya_humidity(dp_id=2, scale=100)
    .tuya_dp_attribute(dp_id=3, attribute_name='battery_state', type=BatteryState, access=foundation.ZCLAttributeAccess.Read | foundation.ZCLAttributeAccess.Report, converter=lambda x: BatteryState(int(x)))
    .enum(attribute_name='battery_state', enum_class=BatteryState, cluster_id=TUYA_CLUSTER_ID, entity_platform=EntityPlatform.SENSOR, entity_type=EntityType.DIAGNOSTIC, translation_key='battery_state', fallback_name='Battery state')
    .tuya_enum(dp_id=9, attribute_name='temperature_unit', enum_class=TemperatureUnit, entity_type=EntityType.CONFIG, translation_key='temperature_unit', fallback_name='Temperature unit')
    .tuya_number(dp_id=10, type=t.int32s, attribute_name='max_temperature_alarm', min_value=-20, max_value=60, unit=UnitOfTemperature.CELSIUS, multiplier=0.1, device_class=NumberDeviceClass.TEMPERATURE, entity_type=EntityType.CONFIG, translation_key='max_temperature_alarm', fallback_name='Max temperature alarm')
    .tuya_number(dp_id=11, type=t.int32s, attribute_name='min_temperature_alarm', min_value=-20, max_value=60, unit=UnitOfTemperature.CELSIUS, multiplier=0.1, device_class=NumberDeviceClass.TEMPERATURE, entity_type=EntityType.CONFIG, translation_key='min_temperature_alarm', fallback_name='Min temperature alarm')
    .tuya_number(dp_id=12, type=t.uint32_t, attribute_name='max_humidity_alarm', min_value=0, max_value=100, unit=PERCENTAGE, entity_type=EntityType.CONFIG, translation_key='max_humidity_alarm', fallback_name='Max humidity alarm')
    .tuya_number(dp_id=13, type=t.uint32_t, attribute_name='min_humidity_alarm', min_value=0, max_value=100, unit=PERCENTAGE, entity_type=EntityType.CONFIG, translation_key='min_humidity_alarm', fallback_name='Min humidity alarm')
    .tuya_dp_attribute(dp_id=14, attribute_name='temperature_alarm', type=TemperatureAlarm, access=foundation.ZCLAttributeAccess.Read | foundation.ZCLAttributeAccess.Report, converter=lambda x: TemperatureAlarm(int(x)))
    .enum(attribute_name='temperature_alarm', enum_class=TemperatureAlarm, cluster_id=TUYA_CLUSTER_ID, entity_platform=EntityPlatform.SENSOR, entity_type=EntityType.STANDARD, translation_key='temperature_alarm', fallback_name='Temperature alarm')
    .tuya_dp_attribute(dp_id=15, attribute_name='humidity_alarm', type=HumidityAlarm, access=foundation.ZCLAttributeAccess.Read | foundation.ZCLAttributeAccess.Report, converter=lambda x: HumidityAlarm(int(x)))
    .enum(attribute_name='humidity_alarm', enum_class=HumidityAlarm, cluster_id=TUYA_CLUSTER_ID, entity_platform=EntityPlatform.SENSOR, entity_type=EntityType.STANDARD, translation_key='humidity_alarm', fallback_name='Humidity alarm')
    .tuya_number(dp_id=17, type=t.uint32_t, attribute_name='temperature_periodic_report', min_value=1, max_value=120, unit=UnitOfTime.MINUTES, device_class=NumberDeviceClass.DURATION, entity_type=EntityType.CONFIG, translation_key='temperature_periodic_report', fallback_name='Temperature periodic report')
    .tuya_number(dp_id=18, type=t.uint32_t, attribute_name='humidity_periodic_report', min_value=1, max_value=120, unit=UnitOfTime.MINUTES, device_class=NumberDeviceClass.DURATION, entity_type=EntityType.CONFIG, translation_key='humidity_periodic_report', fallback_name='Humidity periodic report')
    .tuya_number(dp_id=19, type=t.uint32_t, attribute_name='temperature_sensitivity', min_value=0.3, max_value=1, step=0.1, unit=UnitOfTemperature.CELSIUS, multiplier=0.1, device_class=NumberDeviceClass.TEMPERATURE, entity_type=EntityType.CONFIG, translation_key='temperature_sensitivity', fallback_name='Temperature sensitivity')
    .tuya_number(dp_id=20, type=t.uint32_t, attribute_name='humidity_sensitivity', min_value=3, max_value=10, step=1, unit=PERCENTAGE, entity_type=EntityType.CONFIG, translation_key='humidity_sensitivity', fallback_name='Humidity sensitivity')
    # DP 4 (battery): z2m exposes no entity for it, not generated
    # DP 23 (temperature_calibration): z2m exposes no entity for it, not generated
    # DP 24 (humidity_calibration): z2m exposes no entity for it, not generated
    .skip_configuration()
    .filter(no_builtin_quirk)
    .add_to_registry()
)
