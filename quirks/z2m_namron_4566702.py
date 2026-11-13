"""Namron 4566702: Zigbee Edge Thermostat.

Generated from the Zigbee2MQTT definition.
Data: zigbee-herdsman-converters, MIT, Copyright (c) 2018 Koen Kanters.
Status: generated, not verified on hardware.
Revision: 7f742ee7
"""

import functools
import logging
import pathlib

import zhaquirks
from zha.quirks import DEVICE_REGISTRY, DeviceMatch
import zigpy.types as t
from zigpy.zcl.foundation import ZCLAttributeDef
from zigpy.zcl.clusters.hvac import Thermostat

from zhaquirks.builder import (
    EntityPlatform,
    EntityType,
    NumberDeviceClass,
    PERCENTAGE,
    QuirkBuilder,
    SensorDeviceClass,
    SensorStateClass,
    UnitOfTime,
)
from zhaquirks.clusters import CustomCluster


class HvacThermostatCluster(CustomCluster, Thermostat):
    """Thermostat with the attributes z2m adds."""

    class AttributeDefs(Thermostat.AttributeDefs):
        """Attribute definitions."""

        sensor_mode = ZCLAttributeDef(id=0x8004, type=t.enum8, manufacturer_code=None)
        frost = ZCLAttributeDef(id=0x8001, type=t.Bool, manufacturer_code=None)
        window_open_check = ZCLAttributeDef(id=0x8000, type=t.Bool, manufacturer_code=None)
        panel_brightness = ZCLAttributeDef(id=0x8005, type=t.uint8_t, manufacturer_code=None)
        screen_on_time = ZCLAttributeDef(id=0x8029, type=t.enum8, manufacturer_code=None)
        countdown_set = ZCLAttributeDef(id=0x8023, type=t.enum8, manufacturer_code=None)
        vacation_mode = ZCLAttributeDef(id=0x801F, type=t.Bool, manufacturer_code=None)
        auto_time = ZCLAttributeDef(id=0x8022, type=t.Bool, manufacturer_code=None)
        regulator_percentage = ZCLAttributeDef(id=0x801D, type=t.int16s, manufacturer_code=None)
        regulator_cycle = ZCLAttributeDef(id=0x8007, type=t.uint8_t, access="r", manufacturer_code=None)
        week_program = ZCLAttributeDef(id=0x8003, type=t.enum8, access="r", manufacturer_code=None)
        window_state = ZCLAttributeDef(id=0x8002, type=t.Bool, access="r", manufacturer_code=None)


class WeekProgram(t.enum8):
    """week_program values (z2m)."""

    mon_fri_sat_sun = 0x00
    mon_sat_sun = 0x01
    no_time_off = 0x02
    time_off = 0x03


class WindowState(t.enum8):
    """window_state values (z2m)."""

    closed = 0x00
    open = 0x01


class SensorMode(t.enum8):
    """sensor_mode values (z2m)."""

    air = 0x00
    floor = 0x01
    air_floor = 0x02
    external = 0x03
    external_floor = 0x04
    floor_percent = 0x05
    regulator = 0x06


class ScreenOnTime(t.enum8):
    """screen_on_time values (z2m)."""

    always_on = 0x00
    Time_10s = 0x01
    Time_30s = 0x02
    Time_60s = 0x03



_LOGGER = logging.getLogger(__name__)
_SHIPPED = pathlib.Path(zhaquirks.__file__).resolve().parent
_STEPPED_BACK: set = set()

# The Zigbee fingerprints (manufacturer, model) this quirk is for; None matches any manufacturer.
FINGERPRINTS = [(None, '4566702'), (None, '4566703'), (None, '4512783'), (None, '4512784')]
# Names that a model-only fingerprint would catch but Zigbee2MQTT gives to other devices.
CLAIMED_ELSEWHERE = set()
# The endpoints this quirk needs, each with the input clusters it puts there where Zigbee2MQTT names none.
ENDPOINTS = {1: (0x0201,)}


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
    QuirkBuilder(None, '4566702')
    .applies_to(None, '4566703')
    .applies_to(None, '4512783')
    .applies_to(None, '4512784')
    .replaces(HvacThermostatCluster)
    .number(attribute_name=HvacThermostatCluster.AttributeDefs.regulator_percentage.name, cluster_id=HvacThermostatCluster.cluster_id, min_value=0, max_value=100, step=1, unit=PERCENTAGE, entity_type=EntityType.STANDARD, translation_key='regulator_percentage', fallback_name='Regulator percentage')
    .sensor(attribute_name=HvacThermostatCluster.AttributeDefs.regulator_cycle.name, cluster_id=HvacThermostatCluster.cluster_id, state_class=SensorStateClass.MEASUREMENT, device_class=SensorDeviceClass.DURATION, unit=UnitOfTime.MINUTES, entity_type=EntityType.STANDARD, translation_key='regulator_cycle', fallback_name='Regulator cycle')
    .enum(attribute_name=HvacThermostatCluster.AttributeDefs.week_program.name, cluster_id=HvacThermostatCluster.cluster_id, enum_class=WeekProgram, entity_platform=EntityPlatform.SENSOR, entity_type=EntityType.STANDARD, translation_key='week_program', fallback_name='Week program')
    .enum(attribute_name=HvacThermostatCluster.AttributeDefs.window_state.name, cluster_id=HvacThermostatCluster.cluster_id, enum_class=WindowState, entity_platform=EntityPlatform.SENSOR, entity_type=EntityType.STANDARD, translation_key='window_state', fallback_name='Window state')
    .enum(attribute_name=HvacThermostatCluster.AttributeDefs.sensor_mode.name, cluster_id=HvacThermostatCluster.cluster_id, enum_class=SensorMode, entity_type=EntityType.STANDARD, translation_key='sensor_mode', fallback_name='Sensor mode')
    .switch(attribute_name=HvacThermostatCluster.AttributeDefs.frost.name, cluster_id=HvacThermostatCluster.cluster_id, entity_type=EntityType.STANDARD, translation_key='frost', fallback_name='Frost')
    .switch(attribute_name=HvacThermostatCluster.AttributeDefs.window_open_check.name, cluster_id=HvacThermostatCluster.cluster_id, entity_type=EntityType.STANDARD, translation_key='window_open_check', fallback_name='Window open check')
    .number(attribute_name=HvacThermostatCluster.AttributeDefs.panel_brightness.name, cluster_id=HvacThermostatCluster.cluster_id, min_value=1, max_value=100, unit=PERCENTAGE, entity_type=EntityType.STANDARD, translation_key='panel_brightness', fallback_name='Panel brightness')
    .enum(attribute_name=HvacThermostatCluster.AttributeDefs.screen_on_time.name, cluster_id=HvacThermostatCluster.cluster_id, enum_class=ScreenOnTime, entity_type=EntityType.STANDARD, translation_key='screen_on_time', fallback_name='Screen on time')
    .number(attribute_name=HvacThermostatCluster.AttributeDefs.countdown_set.name, cluster_id=HvacThermostatCluster.cluster_id, min_value=0, max_value=120, step=5, unit=UnitOfTime.MINUTES, multiplier=5.0, device_class=NumberDeviceClass.DURATION, entity_type=EntityType.STANDARD, translation_key='countdown_set', fallback_name='Countdown set')
    .switch(attribute_name=HvacThermostatCluster.AttributeDefs.vacation_mode.name, cluster_id=HvacThermostatCluster.cluster_id, entity_type=EntityType.STANDARD, translation_key='vacation_mode', fallback_name='Vacation mode')
    .switch(attribute_name=HvacThermostatCluster.AttributeDefs.auto_time.name, cluster_id=HvacThermostatCluster.cluster_id, entity_type=EntityType.STANDARD, translation_key='auto_time', fallback_name='Auto time')
    # countdown_left: z2m numeric with scale function, not generated
    # switch: standard clusters, ZHA's own entities
    # humidity: standard clusters, ZHA's own entities
    # power: standard clusters, ZHA's own entities
    # current: standard clusters, ZHA's own entities
    # energy: standard clusters, ZHA's own entities
    # climate: standard clusters, ZHA's own entities
    # occupied_cooling_setpoint: standard clusters, ZHA's own entities
    # programming_operation_mode: standard cluster, no ZHA entity, not generated
    # thermostat_mode: standard clusters or z2m's own code, not generated
    # week_program_schedule: standard clusters or z2m's own code, not generated
    # keypad_lockout: standard clusters, ZHA's own entities
    # temperature_display_mode: standard cluster, no ZHA entity, not generated
    # vacation_start: standard clusters or z2m's own code, not generated
    # vacation_end: standard clusters or z2m's own code, not generated
    # holiday_temp_set: standard clusters or z2m's own code, not generated
    # max_heat_temp: standard clusters or z2m's own code, not generated
    # sync_time: standard clusters or z2m's own code, not generated
    # clock_last_synced: standard clusters or z2m's own code, not generated
    # fault: standard clusters or z2m's own code, not generated
    # firmware_version: standard cluster, no ZHA entity, not generated
    # firmware_date: standard cluster, no ZHA entity, not generated
    # abs_min_heat_setpoint_limit: standard cluster, no ZHA entity, not generated
    # abs_max_heat_setpoint_limit: standard cluster, no ZHA entity, not generated
    .filter(no_builtin_quirk)
    .add_to_registry()
)
