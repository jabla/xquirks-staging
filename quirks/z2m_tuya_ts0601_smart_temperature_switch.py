"""Tuya TS0601_smart_temperature_switch: Smart temperature switch with manual and automatic modes: heating & cooling.

Generated from the Zigbee2MQTT definition.
Data: zigbee-herdsman-converters, MIT, Copyright (c) 2018 Koen Kanters.
Status: generated, not verified on hardware; corrected by devices/tuya_ts0601_smart_temperature_switch.toml.
Revision: d4449a55
"""

import functools
import logging
import pathlib

import zhaquirks
from zha.quirks import DEVICE_REGISTRY, DeviceMatch
import zigpy.types as t

from zhaquirks.builder import (
    EntityType,
    NumberDeviceClass,
    SensorDeviceClass,
    SensorStateClass,
    UnitOfTemperature,
    UnitOfTime,
)
from zhaquirks.tuya.builder import TuyaQuirkBuilder


class WorkMode(t.enum8):
    """work_mode values (z2m)."""

    heating = 0x00
    cooling = 0x02


class TemperatureUnit(t.enum8):
    """temperature_unit values (z2m)."""

    celsius = 0x00
    fahrenheit = 0x01



_LOGGER = logging.getLogger(__name__)
_SHIPPED = pathlib.Path(zhaquirks.__file__).resolve().parent
_STEPPED_BACK: set = set()

# The Zigbee fingerprints (manufacturer, model) this quirk is for; None matches any manufacturer.
FINGERPRINTS = [('_TZE284_roujjevx', 'TS0601')]
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
    .applies_to('_TZE284_roujjevx', 'TS0601')
    .tuya_onoff(dp_id=2)
    .tuya_number(dp_id=4, type=t.uint32_t, attribute_name='countdown', min_value=0, max_value=86400, step=1, unit=UnitOfTime.SECONDS, device_class=NumberDeviceClass.DURATION, entity_type=EntityType.CONFIG, translation_key='countdown', fallback_name='Countdown')
    .tuya_enum(dp_id=8, attribute_name='work_mode', enum_class=WorkMode, entity_type=EntityType.CONFIG, translation_key='work_mode', fallback_name='Work mode')
    .tuya_switch(dp_id=9, attribute_name='autowork', entity_type=EntityType.CONFIG, translation_key='autowork', fallback_name='Autowork')
    .tuya_enum(dp_id=20, attribute_name='temperature_unit', enum_class=TemperatureUnit, entity_type=EntityType.CONFIG, translation_key='temperature_unit', fallback_name='Temperature unit')
    .tuya_number(dp_id=21, type=t.int32s, attribute_name='temperature_f_setpoint', min_value=-4, max_value=221, step=0.5, unit=UnitOfTemperature.FAHRENHEIT, multiplier=0.1, device_class=NumberDeviceClass.TEMPERATURE, entity_type=EntityType.CONFIG, translation_key='temperature_f_setpoint', fallback_name='Temperature f setpoint')
    .tuya_number(dp_id=22, type=t.int32s, attribute_name='temperature_c_setpoint', min_value=-20, max_value=102, step=0.5, unit=UnitOfTemperature.CELSIUS, multiplier=0.1, device_class=NumberDeviceClass.TEMPERATURE, entity_type=EntityType.CONFIG, translation_key='temperature_c_setpoint', fallback_name='Temperature c setpoint')
    .tuya_sensor(dp_id=27, attribute_name='temperature_c', type=t.uint32_t, divisor=10, state_class=SensorStateClass.MEASUREMENT, device_class=SensorDeviceClass.TEMPERATURE, unit=UnitOfTemperature.CELSIUS, entity_type=EntityType.DIAGNOSTIC, translation_key='temperature_c', fallback_name='Temperature c')
    .tuya_sensor(dp_id=28, attribute_name='temperature_f', type=t.uint32_t, divisor=10, state_class=SensorStateClass.MEASUREMENT, device_class=SensorDeviceClass.TEMPERATURE, unit=UnitOfTemperature.FAHRENHEIT, entity_type=EntityType.DIAGNOSTIC, translation_key='temperature_f', fallback_name='Temperature f')
    .tuya_number(dp_id=29, type=t.uint32_t, attribute_name='temperature_range', min_value=1, max_value=9, step=0.5, multiplier=0.1, entity_type=EntityType.CONFIG, translation_key='temperature_range', fallback_name='Temperature range')
    .tuya_number(dp_id=30, type=t.int32s, attribute_name='temperature_calibration', min_value=-9, max_value=9, step=1, unit=UnitOfTemperature.FAHRENHEIT, device_class=NumberDeviceClass.TEMPERATURE_DELTA, entity_type=EntityType.CONFIG, translation_key='temperature_calibration', fallback_name='Temperature calibration')
    .tuya_number(dp_id=55, type=t.uint32_t, attribute_name='cooling_delay', min_value=0, max_value=10, step=1, unit=UnitOfTime.MINUTES, device_class=NumberDeviceClass.DURATION, entity_type=EntityType.CONFIG, translation_key='cooling_delay', fallback_name='Cooling delay')
    .tuya_switch(dp_id=56, attribute_name='cooling_delay_switch', entity_type=EntityType.CONFIG, translation_key='cooling_delay_switch', fallback_name='Cooling delay switch')
    # DP 7 (schedules): z2m class custom (handles Buffers), not generated
    .skip_configuration()
    .filter(no_builtin_quirk)
    .add_to_registry()
)
