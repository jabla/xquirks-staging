"""Heat Decor HD-T1000: Floor thermostat.

Generated from the Zigbee2MQTT definition.
Data: zigbee-herdsman-converters, MIT, Copyright (c) 2018 Koen Kanters.
Status: generated, not verified on hardware.
Revision: 8f32119f
"""

import functools
import logging
import pathlib

import zhaquirks
from zha.quirks import DEVICE_REGISTRY, DeviceMatch
import zigpy.types as t
from zigpy.zcl.clusters.hvac import RunningState, Thermostat

from zhaquirks.builder import (
    EntityType,
    NumberDeviceClass,
    UnitOfTemperature,
    UnitOfTime,
)
from zhaquirks.tuya.builder import TuyaQuirkBuilder
from zhaquirks.tuya.tuya_trv import TuyaThermostatV2


class Z2mThermostat(TuyaThermostatV2):
    """Tuya thermostat with the setpoint range z2m gives (absolute limits 5 to 35 °C)."""

    _CONSTANT_ATTRIBUTES = {
        **TuyaThermostatV2._CONSTANT_ATTRIBUTES,
        Thermostat.AttributeDefs.abs_min_heat_setpoint_limit.id: 500,
        Thermostat.AttributeDefs.abs_max_heat_setpoint_limit.id: 3500,
    }


class WorkMode(t.enum8):
    """work_mode values (z2m)."""

    manual = 0x00
    schedule = 0x01



_LOGGER = logging.getLogger(__name__)
_SHIPPED = pathlib.Path(zhaquirks.__file__).resolve().parent
_STEPPED_BACK: set = set()

# The Zigbee fingerprints (manufacturer, model) this quirk is for; None matches any manufacturer.
FINGERPRINTS = [('_TZE200_spyvfeti', 'TS0601')]
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
    .applies_to('_TZE200_spyvfeti', 'TS0601')
    .tuya_dp(dp_id=24, ep_attribute=Z2mThermostat.ep_attribute, attribute_name=Thermostat.AttributeDefs.local_temperature.name, converter=lambda x: x * 10)
    .tuya_dp(dp_id=16, ep_attribute=Z2mThermostat.ep_attribute, attribute_name=Thermostat.AttributeDefs.occupied_heating_setpoint.name, converter=lambda x: x * 10, dp_converter=lambda x: x // 10)
    .tuya_dp(dp_id=1, ep_attribute=Z2mThermostat.ep_attribute, attribute_name=Thermostat.AttributeDefs.system_mode.name, converter=lambda x: {True: Thermostat.SystemMode.Heat, False: Thermostat.SystemMode.Off}[bool(x)], dp_converter=lambda x: {Thermostat.SystemMode.Heat: True, Thermostat.SystemMode.Off: False}[x])
    .tuya_dp(dp_id=3, ep_attribute=Z2mThermostat.ep_attribute, attribute_name=Thermostat.AttributeDefs.running_state.name, converter=lambda x: {0: RunningState.Heat_State_On, 1: RunningState.Idle}[int(x)])
    .adds(Z2mThermostat)
    .tuya_enum(dp_id=2, attribute_name='work_mode', enum_class=WorkMode, entity_type=EntityType.CONFIG, translation_key='work_mode', fallback_name='Work mode')
    .tuya_switch(dp_id=10, attribute_name='frost_protection', entity_type=EntityType.CONFIG, translation_key='frost_protection', fallback_name='Frost protection')
    .tuya_switch(dp_id=8, attribute_name='window_detection', entity_type=EntityType.CONFIG, translation_key='z2m_window_detection', fallback_name='Window detection')
    .tuya_number(dp_id=19, type=t.uint32_t, attribute_name='max_air_temperature', min_value=35, max_value=95, step=0.5, unit=UnitOfTemperature.CELSIUS, multiplier=0.1, device_class=NumberDeviceClass.TEMPERATURE, entity_type=EntityType.CONFIG, translation_key='max_air_temperature', fallback_name='Max air temperature')
    .tuya_number(dp_id=27, type=t.int32s, attribute_name='local_temperature_calibration', min_value=-9, max_value=9, step=1, unit=UnitOfTemperature.CELSIUS, device_class=NumberDeviceClass.TEMPERATURE_DELTA, entity_type=EntityType.CONFIG, translation_key='z2m_local_temperature_calibration', fallback_name='Local temperature calibration')
    .tuya_switch(dp_id=40, attribute_name='child_lock', entity_type=EntityType.CONFIG, translation_key='child_lock', fallback_name='Child lock')
    .tuya_number(dp_id=101, type=t.uint32_t, attribute_name='max_floor_temperature', min_value=5, max_value=60, step=0.5, unit=UnitOfTemperature.CELSIUS, multiplier=0.1, device_class=NumberDeviceClass.TEMPERATURE, entity_type=EntityType.CONFIG, translation_key='max_floor_temperature', fallback_name='Max floor temperature')
    .tuya_number(dp_id=102, type=t.uint32_t, attribute_name='deadzone_temperature', min_value=0.5, max_value=5, step=0.5, unit=UnitOfTemperature.CELSIUS, multiplier=0.1, device_class=NumberDeviceClass.TEMPERATURE_DELTA, entity_type=EntityType.CONFIG, translation_key='deadzone_temperature', fallback_name='Deadzone temperature')
    .tuya_number(dp_id=104, type=t.uint32_t, attribute_name='window_detection_time', min_value=2, max_value=30, step=1, unit=UnitOfTime.MINUTES, device_class=NumberDeviceClass.DURATION, entity_type=EntityType.CONFIG, translation_key='window_detection_time', fallback_name='Window detection time')
    .tuya_number(dp_id=105, type=t.uint32_t, attribute_name='window_detection_temperature', min_value=2, max_value=4, step=1, unit=UnitOfTemperature.CELSIUS, device_class=NumberDeviceClass.TEMPERATURE, entity_type=EntityType.CONFIG, translation_key='window_detection_temperature', fallback_name='Window detection temperature')
    .tuya_number(dp_id=106, type=t.uint32_t, attribute_name='window_detection_recovery_time', min_value=10, max_value=60, step=1, unit=UnitOfTime.MINUTES, device_class=NumberDeviceClass.DURATION, entity_type=EntityType.CONFIG, translation_key='window_detection_recovery_time', fallback_name='Window detection recovery time')
    .skip_configuration()
    .filter(no_builtin_quirk)
    .add_to_registry()
)
