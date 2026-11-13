"""Lincukoo EZCP04: Smart air quality monitor (CO2+PM2.5).

Generated from the Zigbee2MQTT definition.
Data: zigbee-herdsman-converters, MIT, Copyright (c) 2018 Koen Kanters.
Status: generated, not verified on hardware.
Revision: 0debfb8a
"""

import functools
import logging
import pathlib

import zhaquirks
from zha.quirks import DEVICE_REGISTRY, DeviceMatch
import zigpy.types as t
from zigpy.zcl import foundation

from zhaquirks.builder import (
    CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
    CONCENTRATION_PARTS_PER_MILLION,
    EntityPlatform,
    EntityType,
    SensorStateClass,
)
from zhaquirks.tuya import TUYA_CLUSTER_ID
from zhaquirks.tuya.builder import TuyaQuirkBuilder


class AlarmState(t.enum8):
    """alarm_state values (z2m)."""

    normal = 0x00
    alarm_co2 = 0x01
    alarm_pm25 = 0x02


class AlarmRingtone(t.enum8):
    """alarm_ringtone values (z2m)."""

    mute = 0x00
    ringtone_1 = 0x01
    ringtone_2 = 0x02
    ringtone_3 = 0x03


class TemperatureUnitConvert(t.enum8):
    """temperature_unit_convert values (z2m)."""

    celsius = 0x00
    fahrenheit = 0x01



_LOGGER = logging.getLogger(__name__)
_SHIPPED = pathlib.Path(zhaquirks.__file__).resolve().parent
_STEPPED_BACK: set = set()

# The Zigbee fingerprints (manufacturer, model) this quirk is for; None matches any manufacturer.
FINGERPRINTS = [('_TZE204_fpwtjlfh', 'TS0601'), ('_TZE28C1000000_fpwtjlfh', 'TS0601')]
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
    .applies_to('_TZE204_fpwtjlfh', 'TS0601')
    .applies_to('_TZE28C1000000_fpwtjlfh', 'TS0601')
    .tuya_dp_attribute(dp_id=1, attribute_name='alarm_state', type=AlarmState, access=foundation.ZCLAttributeAccess.Read | foundation.ZCLAttributeAccess.Report, converter=lambda x: AlarmState(int(x)))
    .enum(attribute_name='alarm_state', enum_class=AlarmState, cluster_id=TUYA_CLUSTER_ID, entity_platform=EntityPlatform.SENSOR, entity_type=EntityType.STANDARD, translation_key='alarm_state', fallback_name='Alarm state')
    .tuya_co2(dp_id=2, scale=1e-06)
    .tuya_enum(dp_id=6, attribute_name='alarm_ringtone', enum_class=AlarmRingtone, entity_type=EntityType.CONFIG, translation_key='alarm_ringtone', fallback_name='Alarm ringtone')
    .tuya_temperature(dp_id=18, scale=10)
    .tuya_humidity(dp_id=19, scale=100)
    .tuya_number(dp_id=26, type=t.uint32_t, attribute_name='co2_alarm_value', min_value=1000, max_value=10000, step=100, unit=CONCENTRATION_PARTS_PER_MILLION, entity_type=EntityType.CONFIG, translation_key='co2_alarm_value', fallback_name='CO2 alarm value')
    .tuya_enum(dp_id=31, attribute_name='temperature_unit_convert', enum_class=TemperatureUnitConvert, entity_type=EntityType.CONFIG, translation_key='temperature_unit_convert', fallback_name='Temperature unit convert')
    .tuya_sensor(dp_id=20, attribute_name='pm25', type=t.uint32_t, state_class=SensorStateClass.MEASUREMENT, unit=CONCENTRATION_MICROGRAMS_PER_CUBIC_METER, entity_type=EntityType.STANDARD, translation_key='pm25', fallback_name='PM2.5')
    .tuya_number(dp_id=101, type=t.uint32_t, attribute_name='pm25_alarm_value', min_value=10, max_value=1000, step=10, unit='ug/m3', entity_type=EntityType.CONFIG, translation_key='pm25_alarm_value', fallback_name='PM2.5 alarm value')
    .skip_configuration()
    .filter(no_builtin_quirk)
    .add_to_registry()
)
