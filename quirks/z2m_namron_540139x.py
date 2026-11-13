"""Namron 540139X: Panel heater 400/600/800/1000 W.

Generated from the Zigbee2MQTT definition.
Data: zigbee-herdsman-converters, MIT, Copyright (c) 2018 Koen Kanters.
Status: generated, not verified on hardware.
Revision: 8d9d478b
"""

import functools
import logging
import pathlib

import zhaquirks
from zha.quirks import DEVICE_REGISTRY, DeviceMatch
import zigpy.types as t
from zigpy.zcl.foundation import ZCLAttributeDef
from zigpy.zcl.clusters.hvac import Thermostat
from zigpy.zcl.clusters.hvac import UserInterface

from zhaquirks.builder import (
    EntityType,
    NumberDeviceClass,
    QuirkBuilder,
    UnitOfTemperature,
)
from zhaquirks.clusters import CustomCluster


class HvacThermostatCluster(CustomCluster, Thermostat):
    """Thermostat with the attributes z2m adds."""

    class AttributeDefs(Thermostat.AttributeDefs):
        """Attribute definitions."""

        operate_display_brightness = ZCLAttributeDef(id=0x1000, type=t.enum8, manufacturer_code=0x1224)
        display_auto_off = ZCLAttributeDef(id=0x1001, type=t.enum8, manufacturer_code=0x1224)
        floor_sensor_type = ZCLAttributeDef(id=0x1002, type=t.enum8, manufacturer_code=0x1224)
        control_type = ZCLAttributeDef(id=0x1003, type=t.enum8, manufacturer_code=0x1224)
        power_up_status = ZCLAttributeDef(id=0x1004, type=t.enum8, manufacturer_code=0x1224)
        floor_sensor_calibration = ZCLAttributeDef(id=0x1005, type=t.int8s, manufacturer_code=0x1224)
        dry_time = ZCLAttributeDef(id=0x1006, type=t.uint8_t, manufacturer_code=0x1224)
        mode_after_dry = ZCLAttributeDef(id=0x1007, type=t.enum8, manufacturer_code=0x1224)
        temperature_display = ZCLAttributeDef(id=0x1008, type=t.enum8, manufacturer_code=0x1224)
        window_open_check2 = ZCLAttributeDef(id=0x1009, type=t.uint8_t, manufacturer_code=0x1224)
        hysterersis = ZCLAttributeDef(id=0x100A, type=t.uint8_t, manufacturer_code=0x1224)
        window_open = ZCLAttributeDef(id=0x100B, type=t.enum8, manufacturer_code=0x1224)
        adaptive_function = ZCLAttributeDef(id=0x100C, type=t.enum8, manufacturer_code=0x1224)
        alarm_air_temp_over_value = ZCLAttributeDef(id=0x2001, type=t.uint8_t, manufacturer_code=0x1224)
        away_mode_set = ZCLAttributeDef(id=0x2002, type=t.enum8, manufacturer_code=0x1224)
        pid_kp = ZCLAttributeDef(id=0x2006, type=t.uint16_t, manufacturer_code=0x1224)
        pid_kd = ZCLAttributeDef(id=0x2007, type=t.uint16_t, manufacturer_code=0x1224)
        pid_ki = ZCLAttributeDef(id=0x2008, type=t.uint16_t, manufacturer_code=0x1224)
        control_method = ZCLAttributeDef(id=0x2009, type=t.enum8, manufacturer_code=0x1224)
        window_open_check = ZCLAttributeDef(id=0x8000, type=t.Bool, manufacturer_code=None)
        anti_frost = ZCLAttributeDef(id=0x8001, type=t.Bool, manufacturer_code=None)
        window_state = ZCLAttributeDef(id=0x8002, type=t.Bool, access="r", manufacturer_code=None)
        work_days = ZCLAttributeDef(id=0x8003, type=t.enum8, access="r", manufacturer_code=0x1224)
        sensor_mode = ZCLAttributeDef(id=0x8004, type=t.enum8, manufacturer_code=None)
        display_active_backlight = ZCLAttributeDef(id=0x8005, type=t.uint8_t, manufacturer_code=0x1224)
        fault = ZCLAttributeDef(id=0x8006, type=t.enum8, access="r", manufacturer_code=0x1224)
        backlight_onoff = ZCLAttributeDef(id=0x8009, type=t.Bool, manufacturer_code=0x1224)
        time_sync = ZCLAttributeDef(id=0x800A, type=t.Bool, manufacturer_code=0x1224)
        device_time = ZCLAttributeDef(id=0x800B, type=t.uint32_t, manufacturer_code=0x1224)
        abs_min_heat_setpoint_limit_f = ZCLAttributeDef(id=0x800C, type=t.int16s, manufacturer_code=0x1224)
        abs_max_heat_setpoint_limit_f = ZCLAttributeDef(id=0x800D, type=t.int16s, manufacturer_code=0x1224)
        abs_min_cool_setpoint_limit_f = ZCLAttributeDef(id=0x800E, type=t.int16s, manufacturer_code=0x1224)
        abs_max_cool_setpoint_limit_f = ZCLAttributeDef(id=0x800F, type=t.int16s, manufacturer_code=0x1224)
        occupied_cooling_setpoint_f = ZCLAttributeDef(id=0x8010, type=t.int16s, manufacturer_code=0x1224)
        occupied_heating_setpoint_f = ZCLAttributeDef(id=0x8011, type=t.int16s, manufacturer_code=0x1224)
        local_temperature_f = ZCLAttributeDef(id=0x8012, type=t.int16s, manufacturer_code=0x1224)
        holiday_temp_set = ZCLAttributeDef(id=0x8013, type=t.int16s, manufacturer_code=0x1224)
        holiday_temp_set_f = ZCLAttributeDef(id=0x801B, type=t.int16s, manufacturer_code=0x1224)
        regulation_mode = ZCLAttributeDef(id=0x801C, type=t.enum8, manufacturer_code=0x1224)
        regulator_percentage = ZCLAttributeDef(id=0x801D, type=t.int16s, manufacturer_code=0x1224)
        summer_winter_switch = ZCLAttributeDef(id=0x801E, type=t.Bool, manufacturer_code=0x1224)
        vacation_mode = ZCLAttributeDef(id=0x801F, type=t.Bool, manufacturer_code=0x1224)
        vacation_start_date = ZCLAttributeDef(id=0x8020, type=t.uint32_t, manufacturer_code=0x1224)
        vacation_end_date = ZCLAttributeDef(id=0x8021, type=t.uint32_t, manufacturer_code=0x1224)
        auto_time = ZCLAttributeDef(id=0x8022, type=t.Bool, manufacturer_code=0x1224)
        boost_time_set = ZCLAttributeDef(id=0x8023, type=t.enum8, manufacturer_code=0x1224)
        boost_time_remaining = ZCLAttributeDef(id=0x8024, type=t.uint8_t, access="r", manufacturer_code=0x1224)
        display_auto_off2 = ZCLAttributeDef(id=0x8029, type=t.enum8, manufacturer_code=0x1224)


class TemperatureDisplayMode(t.enum8):
    """temperature_display_mode values (z2m)."""

    celsius = 0x00
    fahrenheit = 0x01


class DisplayAutoOff(t.enum8):
    """display_auto_off values (z2m)."""

    deactivated = 0x00
    activated = 0x01


class PowerUpStatus(t.enum8):
    """power_up_status values (z2m)."""

    manual = 0x00
    last_state = 0x01



_LOGGER = logging.getLogger(__name__)
_SHIPPED = pathlib.Path(zhaquirks.__file__).resolve().parent
_STEPPED_BACK: set = set()

# The Zigbee fingerprints (manufacturer, model) this quirk is for; None matches any manufacturer.
FINGERPRINTS = [(None, '5401392'), (None, '5401396'), (None, '5401393'), (None, '5401397'), (None, '5401394'), (None, '5401398'), (None, '5401395'), (None, '5401399')]
# Names that a model-only fingerprint would catch but Zigbee2MQTT gives to other devices.
CLAIMED_ELSEWHERE = set()
# The endpoints this quirk needs, each with the input clusters it puts there where Zigbee2MQTT names none.
ENDPOINTS = {1: (0x0201, 0x0204)}


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
    QuirkBuilder(None, '5401392')
    .applies_to(None, '5401396')
    .applies_to(None, '5401393')
    .applies_to(None, '5401397')
    .applies_to(None, '5401394')
    .applies_to(None, '5401398')
    .applies_to(None, '5401395')
    .applies_to(None, '5401399')
    .replaces(HvacThermostatCluster)
    .enum(attribute_name=UserInterface.AttributeDefs.temperature_display_mode.name, cluster_id=UserInterface.cluster_id, enum_class=TemperatureDisplayMode, entity_type=EntityType.CONFIG, translation_key='temperature_display_mode', fallback_name='Temperature display mode')
    .number(attribute_name=HvacThermostatCluster.AttributeDefs.hysterersis.name, cluster_id=HvacThermostatCluster.cluster_id, min_value=0.5, max_value=2, step=0.1, unit=UnitOfTemperature.CELSIUS, multiplier=0.1, device_class=NumberDeviceClass.TEMPERATURE_DELTA, entity_type=EntityType.STANDARD, translation_key='hysterersis', fallback_name='Hysterersis')
    .number(attribute_name=HvacThermostatCluster.AttributeDefs.operate_display_brightness.name, cluster_id=HvacThermostatCluster.cluster_id, min_value=1, max_value=7, step=1, entity_type=EntityType.STANDARD, translation_key='display_brightnesss', fallback_name='Display brightnesss')
    .enum(attribute_name=HvacThermostatCluster.AttributeDefs.display_auto_off.name, cluster_id=HvacThermostatCluster.cluster_id, enum_class=DisplayAutoOff, entity_type=EntityType.STANDARD, translation_key='display_auto_off', fallback_name='Display auto off')
    .enum(attribute_name=HvacThermostatCluster.AttributeDefs.power_up_status.name, cluster_id=HvacThermostatCluster.cluster_id, enum_class=PowerUpStatus, entity_type=EntityType.STANDARD, translation_key='power_up_status', fallback_name='Power up status')
    .switch(attribute_name=HvacThermostatCluster.AttributeDefs.window_open_check2.name, cluster_id=HvacThermostatCluster.cluster_id, entity_type=EntityType.CONFIG, translation_key='z2m_window_detection', fallback_name='Window detection')
    .binary_sensor(attribute_name=HvacThermostatCluster.AttributeDefs.window_open.name, cluster_id=HvacThermostatCluster.cluster_id, entity_type=EntityType.DIAGNOSTIC, translation_key='window_open', fallback_name='Window open')
    # power: standard clusters or z2m's own code, not generated
    # current: standard clusters or z2m's own code, not generated
    # voltage: standard clusters or z2m's own code, not generated
    # energy: standard clusters or z2m's own code, not generated
    # climate: standard clusters, ZHA's own entities
    # child_lock: standard clusters, ZHA's own entities
    .filter(no_builtin_quirk)
    .add_to_registry()
)
