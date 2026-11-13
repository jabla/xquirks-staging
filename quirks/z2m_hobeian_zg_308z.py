"""HOBEIAN ZG-308Z: Water valve.

Generated from the Zigbee2MQTT definition.
Data: zigbee-herdsman-converters, MIT, Copyright (c) 2018 Koen Kanters.
Status: generated, not verified on hardware.
Revision: f641c3f9
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
    SensorDeviceClass,
    SensorStateClass,
    UnitOfTime,
)
from zhaquirks.tuya import TUYA_CLUSTER_ID
from zhaquirks.tuya.builder import TuyaQuirkBuilder


class ValveStatus(t.enum8):
    """valve_status values (z2m)."""

    auto = 0x00
    manual = 0x01
    idle = 0x02


class WeatherDelay(t.enum8):
    """weather_delay values (z2m)."""

    cancel = 0x00
    hour_12h = 0x01
    hour_24h = 0x02
    hour_48h = 0x03
    hour_72h = 0x04


class CurrentWeather(t.enum8):
    """current_weather values (z2m)."""

    sunny = 0x00
    clear = 0x01
    cloud = 0x02
    cloudy = 0x03
    rainy = 0x04
    snow = 0x05
    fog = 0x06


class WeatherStatus(t.enum8):
    """weather_status values (z2m)."""

    sunny = 0x00
    cloudy = 0x01
    rainy = 0x02
    snow = 0x03
    null = 0x04



_LOGGER = logging.getLogger(__name__)
_SHIPPED = pathlib.Path(zhaquirks.__file__).resolve().parent
_STEPPED_BACK: set = set()

# The Zigbee fingerprints (manufacturer, model) this quirk is for; None matches any manufacturer.
FINGERPRINTS = [(None, 'ZG-308Z'), ('HOBEIAN', 'ZG-308Z')]
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
    .applies_to(None, 'ZG-308Z')
    .applies_to('HOBEIAN', 'ZG-308Z')
    .tuya_switch(dp_id=1, attribute_name='switch', entity_type=EntityType.STANDARD, translation_key='z2m_switch', fallback_name='Switch')
    .tuya_dp_attribute(dp_id=12, attribute_name='valve_status', type=ValveStatus, access=foundation.ZCLAttributeAccess.Read | foundation.ZCLAttributeAccess.Report, converter=lambda x: ValveStatus(int(x)))
    .enum(attribute_name='valve_status', enum_class=ValveStatus, cluster_id=TUYA_CLUSTER_ID, entity_platform=EntityPlatform.SENSOR, entity_type=EntityType.STANDARD, translation_key='valve_status', fallback_name='Valve status')
    .tuya_number(dp_id=11, type=t.uint32_t, attribute_name='countdown', min_value=0, max_value=86400, unit=UnitOfTime.SECONDS, device_class=NumberDeviceClass.DURATION, entity_type=EntityType.CONFIG, translation_key='countdown', fallback_name='Countdown')
    .tuya_sensor(dp_id=15, attribute_name='valve_duration', type=t.uint32_t, state_class=SensorStateClass.MEASUREMENT, device_class=SensorDeviceClass.DURATION, unit=UnitOfTime.SECONDS, entity_type=EntityType.STANDARD, translation_key='z2m_valve_duration', fallback_name='Valve duration')
    .tuya_sensor(dp_id=9, attribute_name='total_irrigation_duration', type=t.uint32_t, state_class=SensorStateClass.MEASUREMENT, device_class=SensorDeviceClass.DURATION, unit=UnitOfTime.SECONDS, entity_type=EntityType.STANDARD, translation_key='total_irrigation_duration', fallback_name='Total irrigation duration')
    .tuya_dp_attribute(dp_id=10, attribute_name='weather_delay', type=WeatherDelay, access=foundation.ZCLAttributeAccess.Read | foundation.ZCLAttributeAccess.Write, converter=lambda x: WeatherDelay(int(x)), dp_converter=lambda x: int(x))
    .enum(attribute_name='weather_delay', enum_class=WeatherDelay, cluster_id=TUYA_CLUSTER_ID, entity_platform=EntityPlatform.SELECT, entity_type=EntityType.CONFIG, translation_key='weather_delay', fallback_name='Weather delay')
    .tuya_dp_attribute(dp_id=13, attribute_name='current_weather', type=CurrentWeather, access=foundation.ZCLAttributeAccess.Read | foundation.ZCLAttributeAccess.Write, converter=lambda x: CurrentWeather(int(x)), dp_converter=lambda x: int(x))
    .enum(attribute_name='current_weather', enum_class=CurrentWeather, cluster_id=TUYA_CLUSTER_ID, entity_platform=EntityPlatform.SELECT, entity_type=EntityType.CONFIG, translation_key='current_weather', fallback_name='Current weather')
    .tuya_dp_attribute(dp_id=101, attribute_name='weather_status', type=WeatherStatus, access=foundation.ZCLAttributeAccess.Read | foundation.ZCLAttributeAccess.Report, converter=lambda x: WeatherStatus(int(x)))
    .enum(attribute_name='weather_status', enum_class=WeatherStatus, cluster_id=TUYA_CLUSTER_ID, entity_platform=EntityPlatform.SENSOR, entity_type=EntityType.STANDARD, translation_key='weather_status', fallback_name='Weather status')
    .tuya_switch(dp_id=14, attribute_name='weather_onoff', entity_type=EntityType.CONFIG, translation_key='weather_onoff', fallback_name='Weather onoff')
    .tuya_binary_sensor(dp_id=102, attribute_name='get_weather', entity_type=EntityType.STANDARD, translation_key='get_weather', fallback_name='Get weather')
    .tuya_battery(dp_id=7, scale=2)
    .skip_configuration()
    .filter(no_builtin_quirk)
    .add_to_registry()
)
