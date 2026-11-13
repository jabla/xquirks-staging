"""Plugwise 170-01: Emma Wired Pro / Emma Wireless.

Generated from the Zigbee2MQTT definition.
Data: zigbee-herdsman-converters, MIT, Copyright (c) 2018 Koen Kanters.
Status: generated, not verified on hardware.
Revision: bd3d2ff8
"""

import functools
import logging
import pathlib

import zhaquirks
from zha.quirks import DEVICE_REGISTRY, DeviceMatch
import zigpy.types as t
from zigpy.zcl.foundation import ZCLAttributeDef
from zigpy.zcl.clusters.general import PowerConfiguration
from zigpy.zcl.clusters.hvac import Thermostat

from zhaquirks.builder import (
    EntityType,
    NumberDeviceClass,
    QuirkBuilder,
    SensorDeviceClass,
    SensorStateClass,
    UnitOfTemperature,
    UnitOfTime,
)
from zhaquirks.clusters import CustomCluster


class GenPowerCfgCluster(CustomCluster, PowerConfiguration):
    """PowerConfiguration with the attributes z2m adds."""

    class AttributeDefs(PowerConfiguration.AttributeDefs):
        """Attribute definitions."""

        plugwise_battery_type = ZCLAttributeDef(id=0x007F, type=t.enum8, manufacturer_code=0x1172)


class HvacThermostatCluster(CustomCluster, Thermostat):
    """Thermostat with the attributes z2m adds."""

    class AttributeDefs(Thermostat.AttributeDefs):
        """Attribute definitions."""

        plugwise_valve_position = ZCLAttributeDef(id=0x4001, type=t.uint8_t, manufacturer_code=None)
        plugwise_current_heating_setpoint = ZCLAttributeDef(id=0x4003, type=t.int16s, access="r", manufacturer_code=None)
        plugwise_t_diff = ZCLAttributeDef(id=0x4008, type=t.int16s, access="r", manufacturer_code=None)
        plugwise_push_force = ZCLAttributeDef(id=0x4012, type=t.uint32_t, manufacturer_code=None)
        plugwise_radio_strength = ZCLAttributeDef(id=0x4014, type=t.Bool, manufacturer_code=None)
        plugwise_external_heat_demand = ZCLAttributeDef(id=0xF000, type=t.uint16_t, manufacturer_code=0x1172)
        plugwise_external_heat_demand_timeout = ZCLAttributeDef(id=0xF001, type=t.uint16_t, manufacturer_code=0x1172)
        plugwise_boiler_water_temp = ZCLAttributeDef(id=0xF002, type=t.int16s, access="r", manufacturer_code=0x1172)
        plugwise_dhw_temp = ZCLAttributeDef(id=0xF003, type=t.int16s, access="r", manufacturer_code=0x1172)
        plugwise_return_water_temp = ZCLAttributeDef(id=0xF004, type=t.int16s, access="r", manufacturer_code=0x1172)
        plugwise_application_fault_code = ZCLAttributeDef(id=0xF005, type=t.bitmap8, access="r", manufacturer_code=0x1172)
        plugwise_oem_fault_code = ZCLAttributeDef(id=0xF006, type=t.uint8_t, access="r", manufacturer_code=0x1172)
        plugwise_max_dhw_setpoint = ZCLAttributeDef(id=0xF007, type=t.int16s, manufacturer_code=0x1172)
        plugwise_max_boiler_setpoint = ZCLAttributeDef(id=0xF008, type=t.int16s, manufacturer_code=0x1172)


class BatteryType(t.enum8):
    """battery_type values (z2m)."""

    alkaline = 0x00
    nimh = 0x01



_LOGGER = logging.getLogger(__name__)
_SHIPPED = pathlib.Path(zhaquirks.__file__).resolve().parent
_STEPPED_BACK: set = set()

# The Zigbee fingerprints (manufacturer, model) this quirk is for; None matches any manufacturer.
FINGERPRINTS = [(None, '170-01')]
# Names that a model-only fingerprint would catch but Zigbee2MQTT gives to other devices.
CLAIMED_ELSEWHERE = set()
# The endpoints this quirk needs, each with the input clusters it puts there where Zigbee2MQTT names none.
ENDPOINTS = {1: (0x0001, 0x0201)}


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
    QuirkBuilder(None, '170-01')
    .replaces(HvacThermostatCluster)
    .replaces(GenPowerCfgCluster)
    .sensor(attribute_name=HvacThermostatCluster.AttributeDefs.plugwise_oem_fault_code.name, cluster_id=HvacThermostatCluster.cluster_id, entity_type=EntityType.STANDARD, translation_key='oem_fault_code', fallback_name='Oem fault code')
    .number(attribute_name=HvacThermostatCluster.AttributeDefs.min_cool_setpoint_limit.name, cluster_id=HvacThermostatCluster.cluster_id, min_value=0, max_value=30, step=0.5, unit=UnitOfTemperature.CELSIUS, multiplier=0.01, device_class=NumberDeviceClass.TEMPERATURE, entity_type=EntityType.CONFIG, translation_key='min_cool_setpoint_limit', fallback_name='Min cool setpoint limit')
    .number(attribute_name=HvacThermostatCluster.AttributeDefs.max_cool_setpoint_limit.name, cluster_id=HvacThermostatCluster.cluster_id, min_value=0, max_value=30, step=0.5, unit=UnitOfTemperature.CELSIUS, multiplier=0.01, device_class=NumberDeviceClass.TEMPERATURE, entity_type=EntityType.CONFIG, translation_key='max_cool_setpoint_limit', fallback_name='Max cool setpoint limit')
    .sensor(attribute_name=HvacThermostatCluster.AttributeDefs.outdoor_temperature.name, cluster_id=HvacThermostatCluster.cluster_id, divisor=100, state_class=SensorStateClass.MEASUREMENT, device_class=SensorDeviceClass.TEMPERATURE, unit=UnitOfTemperature.CELSIUS, entity_type=EntityType.STANDARD, translation_key='outdoor_temperature', fallback_name='Outdoor temperature')
    .sensor(attribute_name=HvacThermostatCluster.AttributeDefs.plugwise_dhw_temp.name, cluster_id=HvacThermostatCluster.cluster_id, divisor=100, state_class=SensorStateClass.MEASUREMENT, device_class=SensorDeviceClass.TEMPERATURE, unit=UnitOfTemperature.CELSIUS, entity_type=EntityType.STANDARD, translation_key='dhw_temperature', fallback_name='Dhw temperature')
    .sensor(attribute_name=HvacThermostatCluster.AttributeDefs.plugwise_return_water_temp.name, cluster_id=HvacThermostatCluster.cluster_id, divisor=100, state_class=SensorStateClass.MEASUREMENT, device_class=SensorDeviceClass.TEMPERATURE, unit=UnitOfTemperature.CELSIUS, entity_type=EntityType.STANDARD, translation_key='return_water_temperature', fallback_name='Return water temperature')
    .sensor(attribute_name=HvacThermostatCluster.AttributeDefs.plugwise_boiler_water_temp.name, cluster_id=HvacThermostatCluster.cluster_id, divisor=100, state_class=SensorStateClass.MEASUREMENT, device_class=SensorDeviceClass.TEMPERATURE, unit=UnitOfTemperature.CELSIUS, entity_type=EntityType.STANDARD, translation_key='boiler_water_temperature', fallback_name='Boiler water temperature')
    .number(attribute_name=HvacThermostatCluster.AttributeDefs.plugwise_external_heat_demand.name, cluster_id=HvacThermostatCluster.cluster_id, min_value=0, max_value=90, step=0.01, unit=UnitOfTemperature.CELSIUS, multiplier=0.01, device_class=NumberDeviceClass.TEMPERATURE, entity_type=EntityType.STANDARD, translation_key='external_heat_demand', fallback_name='External heat demand')
    .number(attribute_name=HvacThermostatCluster.AttributeDefs.plugwise_external_heat_demand_timeout.name, cluster_id=HvacThermostatCluster.cluster_id, min_value=300, max_value=3600, step=1, unit=UnitOfTime.SECONDS, device_class=NumberDeviceClass.DURATION, entity_type=EntityType.CONFIG, translation_key='external_heat_demand_timeout', fallback_name='External heat demand timeout')
    .number(attribute_name=HvacThermostatCluster.AttributeDefs.plugwise_max_dhw_setpoint.name, cluster_id=HvacThermostatCluster.cluster_id, min_value=0, max_value=100, step=0.01, unit=UnitOfTemperature.CELSIUS, multiplier=0.01, device_class=NumberDeviceClass.TEMPERATURE, entity_type=EntityType.CONFIG, translation_key='max_dhw_setpoint', fallback_name='Max dhw setpoint')
    .number(attribute_name=HvacThermostatCluster.AttributeDefs.plugwise_max_boiler_setpoint.name, cluster_id=HvacThermostatCluster.cluster_id, min_value=0, max_value=100, step=0.01, unit=UnitOfTemperature.CELSIUS, multiplier=0.01, device_class=NumberDeviceClass.TEMPERATURE, entity_type=EntityType.CONFIG, translation_key='max_boiler_setpoint', fallback_name='Max boiler setpoint')
    .enum(attribute_name=GenPowerCfgCluster.AttributeDefs.plugwise_battery_type.name, cluster_id=GenPowerCfgCluster.cluster_id, enum_class=BatteryType, entity_type=EntityType.CONFIG, translation_key='battery_type', fallback_name='Battery type')
    # application_fault_status: z2m numeric with own fromZigbee converter, not generated
    # min_heat_setpoint_limit: standard clusters, ZHA's own entities
    # max_heat_setpoint_limit: standard clusters, ZHA's own entities
    # boiler_setpoint: standard clusters, ZHA's own entities
    # battery: standard clusters, ZHA's own entities
    # keypad_lockout: standard clusters, ZHA's own entities
    # product_variant: standard clusters, ZHA's own entities
    # temperature: standard clusters, ZHA's own entities
    # climate: standard clusters, ZHA's own entities
    # humidity: standard clusters, ZHA's own entities
    .filter(no_builtin_quirk)
    .add_to_registry()
)
