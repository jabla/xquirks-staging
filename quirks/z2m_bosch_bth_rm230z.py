"""Bosch BTH-RM230Z: Room thermostat II 230V.

Generated from the Zigbee2MQTT definition.
Entity names follow ZHA's own quirk for this device where it shows the same feature.
Data: zigbee-herdsman-converters, MIT, Copyright (c) 2018 Koen Kanters.
Status: generated, not verified on hardware.
Revision: 3c1a1423
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
    PERCENTAGE,
    QuirkBuilder,
    SensorDeviceClass,
    SensorStateClass,
    UnitOfTemperature,
    UnitOfTime,
)
from zhaquirks.clusters import CustomCluster


class HvacThermostatCluster(CustomCluster, Thermostat):
    """Thermostat with the attributes z2m adds."""

    class AttributeDefs(Thermostat.AttributeDefs):
        """Attribute definitions."""

        operating_mode = ZCLAttributeDef(id=0x4007, type=t.enum8, manufacturer_code=0x1209)
        heating_demand = ZCLAttributeDef(id=0x4020, type=t.enum8, manufacturer_code=0x1209)
        valve_adapt_status = ZCLAttributeDef(id=0x4022, type=t.enum8, manufacturer_code=0x1209)
        humidity_alarm_led = ZCLAttributeDef(id=0x4023, type=t.enum8, manufacturer_code=0x1209)
        unknown_attribute0 = ZCLAttributeDef(id=0x4025, type=t.enum8, manufacturer_code=0x1209)
        remote_temperature = ZCLAttributeDef(id=0x4040, type=t.int16s, manufacturer_code=0x1209)
        unknown_attribute1 = ZCLAttributeDef(id=0x4041, type=t.enum8, manufacturer_code=0x1209)
        window_open_mode = ZCLAttributeDef(id=0x4042, type=t.enum8, manufacturer_code=0x1209)
        boost_heating = ZCLAttributeDef(id=0x4043, type=t.enum8, manufacturer_code=0x1209)
        cable_sensor_temperature = ZCLAttributeDef(id=0x4052, type=t.int16s, manufacturer_code=0x1209)
        valve_type = ZCLAttributeDef(id=0x4060, type=t.enum8, manufacturer_code=0x1209)
        unknown_attribute2 = ZCLAttributeDef(id=0x4061, type=t.enum8, manufacturer_code=0x1209)
        cable_sensor_mode = ZCLAttributeDef(id=0x4062, type=t.enum8, manufacturer_code=0x1209)
        heater_type = ZCLAttributeDef(id=0x4063, type=t.enum8, manufacturer_code=0x1209)
        error_state = ZCLAttributeDef(id=0x5000, type=t.bitmap8, manufacturer_code=0x1209)
        automatic_valve_adapt = ZCLAttributeDef(id=0x5010, type=t.enum8, manufacturer_code=0x1209)


class HvacUserInterfaceCfgCluster(CustomCluster, UserInterface):
    """UserInterface with the attributes z2m adds."""

    class AttributeDefs(UserInterface.AttributeDefs):
        """Attribute definitions."""

        display_orientation = ZCLAttributeDef(id=0x400B, type=t.uint8_t, manufacturer_code=0x1209)
        activity_led = ZCLAttributeDef(id=0x4033, type=t.enum8, manufacturer_code=0x1209)
        displayed_temperature = ZCLAttributeDef(id=0x4039, type=t.enum8, manufacturer_code=0x1209)
        display_switch_on_duration = ZCLAttributeDef(id=0x403A, type=t.enum8, manufacturer_code=0x1209)
        display_brightness = ZCLAttributeDef(id=0x403B, type=t.enum8, manufacturer_code=0x1209)


class OperatingMode(t.enum8):
    """operating_mode values (ZHA's quirk)."""

    Schedule = 0x00
    Manual = 0x01
    Pause = 0x05


class HeaterType(t.enum8):
    """heater_type values (ZHA's quirk)."""

    UnderfloorHeating = 0x00
    Boiler = 0x01
    Radiator = 0x02
    CentralHeating = 0x03


class ValveType(t.enum8):
    """valve_type values (ZHA's quirk)."""

    NormallyClosed = 0x00
    NormallyOpen = 0x01


class CableSensorMode(t.enum8):
    """cable_sensor_mode values (ZHA's quirk)."""

    NotUsed = 0x00
    WithoutRegulation = 0xB0
    WithRegulation = 0xB1


class ActivityLed(t.enum8):
    """activity_led values (ZHA's quirk)."""

    Off = 0x00
    Normal = 0x01
    On = 0x02



_LOGGER = logging.getLogger(__name__)
_SHIPPED = pathlib.Path(zhaquirks.__file__).resolve().parent
_STEPPED_BACK: set = set()

# The Zigbee fingerprints (manufacturer, model) this quirk is for; None matches any manufacturer.
FINGERPRINTS = [(None, 'RBSH-RTH0-ZB-EU'), ('Bosch', 'RBSH-RTH0-ZB-EU')]
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
    QuirkBuilder(None, 'RBSH-RTH0-ZB-EU')
    .applies_to('Bosch', 'RBSH-RTH0-ZB-EU')
    .replaces(HvacUserInterfaceCfgCluster)
    .replaces(HvacThermostatCluster)
    .enum(attribute_name=HvacThermostatCluster.AttributeDefs.operating_mode.name, cluster_id=HvacThermostatCluster.cluster_id, enum_class=OperatingMode, entity_type=EntityType.CONFIG, translation_key='operating_mode', fallback_name='Operating mode', unique_id_suffix='operating_mode')
    .enum(attribute_name=HvacThermostatCluster.AttributeDefs.heater_type.name, cluster_id=HvacThermostatCluster.cluster_id, enum_class=HeaterType, entity_type=EntityType.CONFIG, translation_key='heater_type', fallback_name='Heater type', unique_id_suffix='heater_type')
    .enum(attribute_name=HvacThermostatCluster.AttributeDefs.valve_type.name, cluster_id=HvacThermostatCluster.cluster_id, enum_class=ValveType, entity_type=EntityType.CONFIG, translation_key='actuator_type', fallback_name='Actuator type', unique_id_suffix='actuator_type')
    .enum(attribute_name=HvacThermostatCluster.AttributeDefs.cable_sensor_mode.name, cluster_id=HvacThermostatCluster.cluster_id, enum_class=CableSensorMode, entity_type=EntityType.CONFIG, translation_key='sensor_connection', fallback_name='Sensor connection', unique_id_suffix='sensor_connection')
    .sensor(attribute_name=HvacThermostatCluster.AttributeDefs.cable_sensor_temperature.name, cluster_id=HvacThermostatCluster.cluster_id, divisor=100, state_class=SensorStateClass.MEASUREMENT, device_class=SensorDeviceClass.TEMPERATURE, unit=UnitOfTemperature.CELSIUS, entity_type=EntityType.STANDARD, translation_key='external_temperature', fallback_name='External temperature', unique_id_suffix='external_temperature')
    .switch(attribute_name=HvacThermostatCluster.AttributeDefs.window_open_mode.name, cluster_id=HvacThermostatCluster.cluster_id, entity_type=EntityType.STANDARD, translation_key='window_open', fallback_name='Window open', unique_id_suffix='window_open')
    .switch(attribute_name=HvacThermostatCluster.AttributeDefs.boost_heating.name, cluster_id=HvacThermostatCluster.cluster_id, entity_type=EntityType.STANDARD, translation_key='boost_heating', fallback_name='Boost heating', unique_id_suffix='boost_heating')
    .number(attribute_name=HvacUserInterfaceCfgCluster.AttributeDefs.display_brightness.name, cluster_id=HvacUserInterfaceCfgCluster.cluster_id, min_value=0, max_value=100, step=10, unit=PERCENTAGE, multiplier=10.0, entity_type=EntityType.CONFIG, translation_key='display_brightness', fallback_name='Display brightness')
    .number(attribute_name=HvacUserInterfaceCfgCluster.AttributeDefs.display_switch_on_duration.name, cluster_id=HvacUserInterfaceCfgCluster.cluster_id, min_value=5, max_value=30, unit=UnitOfTime.SECONDS, device_class=NumberDeviceClass.DURATION, entity_type=EntityType.CONFIG, translation_key='display_on_time', fallback_name='Display on-time', unique_id_suffix='display_on_time')
    .enum(attribute_name=HvacUserInterfaceCfgCluster.AttributeDefs.activity_led.name, cluster_id=HvacUserInterfaceCfgCluster.cluster_id, enum_class=ActivityLed, entity_type=EntityType.CONFIG, translation_key='valve_status_led', fallback_name='Valve status LED', unique_id_suffix='valve_status_led')
    .switch(attribute_name=HvacThermostatCluster.AttributeDefs.humidity_alarm_led.name, cluster_id=HvacThermostatCluster.cluster_id, on_value=7, off_value=6, entity_type=EntityType.CONFIG, translation_key='humidity_alarm_led', fallback_name='Humidity alarm LED')
    # setpoint_change_source: standard clusters, ZHA's own entities
    # child_lock: standard clusters, ZHA's own entities
    # climate: standard clusters, ZHA's own entities
    # humidity: standard clusters, ZHA's own entities
    # error_state: z2m's own code, not generated
    .filter(no_builtin_quirk)
    .add_to_registry()
)
