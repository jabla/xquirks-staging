"""SONOFF TRV-ZBT: Zigbee thermostatic radiator valve.

Generated from the Zigbee2MQTT definition.
Entity names follow ZHA's own quirk for this device where it shows the same feature.
Data: zigbee-herdsman-converters, MIT, Copyright (c) 2018 Koen Kanters.
Status: verified on hardware.
Revision: 5ff97812
"""

import functools
import logging
import pathlib

import zhaquirks
from zha.quirks import DEVICE_REGISTRY, DeviceMatch
import zigpy.types as t
from zigpy.zcl.foundation import BaseAttributeDefs, BaseCommandDefs, Direction, ZCLAttributeDef, ZCLCommandDef

from zhaquirks.builder import (
    EntityType,
    NumberDeviceClass,
    PERCENTAGE,
    QuirkBuilder,
    SensorDeviceClass,
    SensorStateClass,
    UnitOfElectricPotential,
    UnitOfTemperature,
)
from zhaquirks.clusters import CustomCluster


class CustomSonoffTrvzbtCluster(CustomCluster):
    """customSonoffTrvzbt (z2m custom cluster)."""

    cluster_id = 0xFC11

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        child_lock = ZCLAttributeDef(id=0x0000, type=t.Bool, manufacturer_code=None)
        fault_code = ZCLAttributeDef(id=0x0010, type=t.uint32_t, access="r", manufacturer_code=None)
        screen_direction = ZCLAttributeDef(id=0x0021, type=t.uint8_t, manufacturer_code=None)
        open_window = ZCLAttributeDef(id=0x6000, type=t.Bool, manufacturer_code=None)
        frost_protection_temperature = ZCLAttributeDef(id=0x6002, type=t.int16s, manufacturer_code=None)
        idle_steps = ZCLAttributeDef(id=0x6003, type=t.uint16_t, access="r", manufacturer_code=None)
        closing_steps = ZCLAttributeDef(id=0x6004, type=t.uint16_t, access="r", manufacturer_code=None)
        valve_opening_limit_voltage = ZCLAttributeDef(id=0x6005, type=t.uint16_t, access="r", manufacturer_code=None)
        valve_closing_limit_voltage = ZCLAttributeDef(id=0x6006, type=t.uint16_t, access="r", manufacturer_code=None)
        valve_motor_running_voltage = ZCLAttributeDef(id=0x6007, type=t.uint16_t, access="r", manufacturer_code=None)
        valve_opening_degree = ZCLAttributeDef(id=0x600B, type=t.uint8_t, manufacturer_code=None)
        valve_closing_degree = ZCLAttributeDef(id=0x600C, type=t.uint8_t, manufacturer_code=None)
        external_temperature_input = ZCLAttributeDef(id=0x600D, type=t.int16s, manufacturer_code=None)
        temperature_sensor_select = ZCLAttributeDef(id=0x600E, type=t.uint8_t, manufacturer_code=None)
        temperature_trigger_of_valve_opening = ZCLAttributeDef(id=0x6011, type=t.int16s, manufacturer_code=None)
        temperature_control_mode = ZCLAttributeDef(id=0x6013, type=t.enum8, manufacturer_code=None)
        temporary_mode = ZCLAttributeDef(id=0x6014, type=t.uint8_t, manufacturer_code=None)
        temporary_mode_time = ZCLAttributeDef(id=0x6015, type=t.uint32_t, manufacturer_code=None)
        temporary_mode_temp = ZCLAttributeDef(id=0x6016, type=t.int16s, manufacturer_code=None)
        low_battery_valve_state = ZCLAttributeDef(id=0x601C, type=t.uint8_t, manufacturer_code=None)
        weekly_schedule_active_num = ZCLAttributeDef(id=0x601D, type=t.uint8_t, manufacturer_code=None)
        # remote_attribute_linkage 0x601E: ARRAY, attribute only
        # hvac_message_notification 0x6030: ARRAY, attribute only
        heat_percentage_hour = ZCLAttributeDef(id=0x6033, type=t.uint8_t, access="r", manufacturer_code=None)
        motor_travel_calibration = ZCLAttributeDef(id=0x6036, type=t.Bool, manufacturer_code=None)
        motor_travel_calibration_status = ZCLAttributeDef(id=0x6037, type=t.uint8_t, access="r", manufacturer_code=None)

    class ServerCommandDefs(BaseCommandDefs):
        """Command definitions (z2m's commands this cluster lacks)."""

        bluetooth_pairing = ZCLCommandDef(id=0x10, schema={'data': t.List[t.uint8_t]}, direction=Direction.Client_to_Server, manufacturer_code=None)


class ScreenDirection(t.enum8):
    """screen_direction values (z2m)."""

    Direction_0 = 0x00
    Direction_90 = 0x01
    Direction_180 = 0x02
    Direction_270 = 0x03


class TemperatureSensorSelect(t.enum8):
    """temperature_sensor_select values (z2m)."""

    local_temperature = 0x00
    remote_temperature = 0x01
    remote_source_offline = 0x02


class LowBatteryValveState(t.enum8):
    """low_battery_valve_state values (z2m)."""

    close = 0x00
    open_30 = 0x1E



_LOGGER = logging.getLogger(__name__)
_SHIPPED = pathlib.Path(zhaquirks.__file__).resolve().parent
_STEPPED_BACK: set = set()

# The Zigbee fingerprints (manufacturer, model) this quirk is for; None matches any manufacturer.
FINGERPRINTS = [(None, 'TRV-ZBT'), ('SONOFF', 'TRV-ZBT')]
# Names that a model-only fingerprint would catch but Zigbee2MQTT gives to other devices.
CLAIMED_ELSEWHERE = set()
# The endpoints this quirk needs, each with the input clusters it puts there where Zigbee2MQTT names none.
ENDPOINTS = {1: (0xFC11,)}


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

    Except for the exact names in FINGERPRINTS: ZHA's own quirk for them shows fewer features
    than this file (compared when the file was built), so this quirk stays for them.
    """
    if (device.manufacturer, device.model) in CLAIMED_ELSEWHERE:
        return False
    shipped = None if device.manufacturer is not None and (device.manufacturer, device.model) in FINGERPRINTS else _shipped_quirk(device)
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
    QuirkBuilder(None, 'TRV-ZBT')
    .applies_to('SONOFF', 'TRV-ZBT')
    .replaces(CustomSonoffTrvzbtCluster)
    .enum(attribute_name=CustomSonoffTrvzbtCluster.AttributeDefs.screen_direction.name, cluster_id=CustomSonoffTrvzbtCluster.cluster_id, enum_class=ScreenDirection, entity_type=EntityType.CONFIG, translation_key='screen_direction', fallback_name='Screen direction')
    .switch(attribute_name=CustomSonoffTrvzbtCluster.AttributeDefs.child_lock.name, cluster_id=CustomSonoffTrvzbtCluster.cluster_id, entity_type=EntityType.CONFIG, translation_key='child_lock', fallback_name='Child lock', unique_id_suffix='child_lock')
    .switch(attribute_name=CustomSonoffTrvzbtCluster.AttributeDefs.open_window.name, cluster_id=CustomSonoffTrvzbtCluster.cluster_id, entity_type=EntityType.CONFIG, translation_key='open_window', fallback_name='Open window', unique_id_suffix='open_window')
    .number(attribute_name=CustomSonoffTrvzbtCluster.AttributeDefs.frost_protection_temperature.name, cluster_id=CustomSonoffTrvzbtCluster.cluster_id, min_value=5, max_value=15, step=0.5, unit=UnitOfTemperature.CELSIUS, multiplier=0.01, device_class=NumberDeviceClass.TEMPERATURE, entity_type=EntityType.CONFIG, translation_key='frost_protection_temperature', fallback_name='Frost protection temperature', unique_id_suffix='frost_protection_temperature')
    .enum(attribute_name=CustomSonoffTrvzbtCluster.AttributeDefs.temperature_sensor_select.name, cluster_id=CustomSonoffTrvzbtCluster.cluster_id, enum_class=TemperatureSensorSelect, entity_type=EntityType.STANDARD, translation_key='temperature_sensor_select', fallback_name='Temperature sensor')
    .number(attribute_name=CustomSonoffTrvzbtCluster.AttributeDefs.external_temperature_input.name, cluster_id=CustomSonoffTrvzbtCluster.cluster_id, min_value=0, max_value=99.9, step=0.1, unit=UnitOfTemperature.CELSIUS, multiplier=0.01, device_class=NumberDeviceClass.TEMPERATURE, entity_type=EntityType.CONFIG, translation_key='external_temperature_sensor_value', fallback_name='External temperature sensor value', unique_id_suffix='external_temperature_sensor_value')
    .sensor(attribute_name=CustomSonoffTrvzbtCluster.AttributeDefs.idle_steps.name, cluster_id=CustomSonoffTrvzbtCluster.cluster_id, entity_type=EntityType.DIAGNOSTIC, translation_key='idle_steps', fallback_name='Idle steps')
    .sensor(attribute_name=CustomSonoffTrvzbtCluster.AttributeDefs.closing_steps.name, cluster_id=CustomSonoffTrvzbtCluster.cluster_id, entity_type=EntityType.DIAGNOSTIC, translation_key='closing_steps', fallback_name='Closing steps')
    .sensor(attribute_name=CustomSonoffTrvzbtCluster.AttributeDefs.valve_opening_limit_voltage.name, cluster_id=CustomSonoffTrvzbtCluster.cluster_id, state_class=SensorStateClass.MEASUREMENT, device_class=SensorDeviceClass.VOLTAGE, unit=UnitOfElectricPotential.MILLIVOLT, entity_type=EntityType.DIAGNOSTIC, translation_key='valve_opening_limit_voltage', fallback_name='Valve opening limit voltage')
    .sensor(attribute_name=CustomSonoffTrvzbtCluster.AttributeDefs.valve_closing_limit_voltage.name, cluster_id=CustomSonoffTrvzbtCluster.cluster_id, state_class=SensorStateClass.MEASUREMENT, device_class=SensorDeviceClass.VOLTAGE, unit=UnitOfElectricPotential.MILLIVOLT, entity_type=EntityType.DIAGNOSTIC, translation_key='valve_closing_limit_voltage', fallback_name='Valve closing limit voltage')
    .sensor(attribute_name=CustomSonoffTrvzbtCluster.AttributeDefs.valve_motor_running_voltage.name, cluster_id=CustomSonoffTrvzbtCluster.cluster_id, state_class=SensorStateClass.MEASUREMENT, device_class=SensorDeviceClass.VOLTAGE, unit=UnitOfElectricPotential.MILLIVOLT, entity_type=EntityType.DIAGNOSTIC, translation_key='valve_motor_running_voltage', fallback_name='Valve motor running voltage')
    .number(attribute_name=CustomSonoffTrvzbtCluster.AttributeDefs.valve_opening_degree.name, cluster_id=CustomSonoffTrvzbtCluster.cluster_id, min_value=0, max_value=100, step=1, unit=PERCENTAGE, entity_type=EntityType.CONFIG, translation_key='valve_opening_degree', fallback_name='Valve opening degree', unique_id_suffix='valve_opening_degree')
    .number(attribute_name=CustomSonoffTrvzbtCluster.AttributeDefs.valve_closing_degree.name, cluster_id=CustomSonoffTrvzbtCluster.cluster_id, min_value=0, max_value=100, step=1, unit=PERCENTAGE, entity_type=EntityType.CONFIG, translation_key='valve_closing_degree', fallback_name='Valve closing degree', unique_id_suffix='valve_closing_degree')
    .number(attribute_name=CustomSonoffTrvzbtCluster.AttributeDefs.temperature_trigger_of_valve_opening.name, cluster_id=CustomSonoffTrvzbtCluster.cluster_id, min_value=-1, max_value=-0.2, step=0.2, unit=UnitOfTemperature.CELSIUS, multiplier=0.01, device_class=NumberDeviceClass.TEMPERATURE_DELTA, entity_type=EntityType.CONFIG, translation_key='temperature_control_accuracy', fallback_name='Temperature control accuracy', unique_id_suffix='temperature_control_accuracy')
    .switch(attribute_name=CustomSonoffTrvzbtCluster.AttributeDefs.temperature_control_mode.name, cluster_id=CustomSonoffTrvzbtCluster.cluster_id, on_value=2, off_value=1, entity_type=EntityType.CONFIG, translation_key='adaptive_mode', fallback_name='Adaptive mode', unique_id_suffix='temperature_control_mode')
    .enum(attribute_name=CustomSonoffTrvzbtCluster.AttributeDefs.low_battery_valve_state.name, cluster_id=CustomSonoffTrvzbtCluster.cluster_id, enum_class=LowBatteryValveState, entity_type=EntityType.CONFIG, translation_key='low_battery_valve_state', fallback_name='Low battery valve state')
    .sensor(attribute_name=CustomSonoffTrvzbtCluster.AttributeDefs.heat_percentage_hour.name, cluster_id=CustomSonoffTrvzbtCluster.cluster_id, state_class=SensorStateClass.MEASUREMENT, unit=PERCENTAGE, entity_type=EntityType.DIAGNOSTIC, translation_key='heat_percentage_hour', fallback_name='Heat percentage hour')
    .write_attr_button(attribute_name=CustomSonoffTrvzbtCluster.AttributeDefs.motor_travel_calibration.name, cluster_id=CustomSonoffTrvzbtCluster.cluster_id, attribute_value=0, entity_type=EntityType.CONFIG, translation_key='valve_travel_calibration', fallback_name='Valve travel calibration')
    .command_button(command_name=CustomSonoffTrvzbtCluster.ServerCommandDefs.bluetooth_pairing.name, cluster_id=CustomSonoffTrvzbtCluster.cluster_id, command_args=((3, 1, 1),), entity_type=EntityType.STANDARD, translation_key='bluetooth_pairing_start', fallback_name='Bluetooth pairing (start)', unique_id_suffix='bluetooth_pairing_start')
    .command_button(command_name=CustomSonoffTrvzbtCluster.ServerCommandDefs.bluetooth_pairing.name, cluster_id=CustomSonoffTrvzbtCluster.cluster_id, command_args=((3, 1, 2),), entity_type=EntityType.STANDARD, translation_key='bluetooth_pairing_stop', fallback_name='Bluetooth pairing (stop)', unique_id_suffix='bluetooth_pairing_stop')
    # battery: standard clusters, ZHA's own entities
    # fault_status: z2m's own code, not generated
    # temporary_mode_mode: z2m's own code, not generated
    # temporary_mode_duration: z2m's own code, not generated
    # temporary_mode_target_temperature: z2m's own code, not generated
    # schedule_active_group: z2m's own code, not generated
    # schedule_group_to_edit: z2m's own code, not generated
    # weekly_schedule_sunday: z2m's own code, not generated
    # weekly_schedule_monday: z2m's own code, not generated
    # weekly_schedule_tuesday: z2m's own code, not generated
    # weekly_schedule_wednesday: z2m's own code, not generated
    # weekly_schedule_thursday: z2m's own code, not generated
    # weekly_schedule_friday: z2m's own code, not generated
    # weekly_schedule_saturday: z2m's own code, not generated
    # remote_temperature_linkage: z2m's own code, not generated
    # remote_setpoint_temperature: z2m's own code, not generated
    # open_window_detected: z2m's own code, not generated
    # motor_travel_calibration_status: z2m's own code, not generated
    # bluetooth_pairing_status: z2m's own code, not generated
    # read_temperature_control_history: z2m's own code, not generated
    # temperature_control_history: z2m's own code, not generated
    # climate: standard clusters, ZHA's own entities
    .filter(no_builtin_quirk)
    .add_to_registry()
)
