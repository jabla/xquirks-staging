"""CTM Lyng mTouch_One: mTouch One OP, touch thermostat.

Generated from the Zigbee2MQTT definition.
Data: zigbee-herdsman-converters, MIT, Copyright (c) 2018 Koen Kanters.
Status: generated, not verified on hardware.
Revision: 9edb5133
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
    EntityType,
    NumberDeviceClass,
    PERCENTAGE,
    QuirkBuilder,
    SensorDeviceClass,
    SensorStateClass,
    UnitOfPower,
    UnitOfTemperature,
)
from zhaquirks.clusters import CustomCluster


class HvacThermostatCluster(CustomCluster, Thermostat):
    """Thermostat with the attributes z2m adds."""

    class AttributeDefs(Thermostat.AttributeDefs):
        """Attribute definitions."""

        ctm_load = ZCLAttributeDef(id=0x0401, type=t.uint16_t, manufacturer_code=None)
        ctm_display_text = ZCLAttributeDef(id=0x0402, type=t.CharacterString, manufacturer_code=None)
        ctm_sensor = ZCLAttributeDef(id=0x0403, type=t.enum8, manufacturer_code=None)
        ctm_regulator_mode = ZCLAttributeDef(id=0x0405, type=t.Bool, manufacturer_code=None)
        ctm_power_status = ZCLAttributeDef(id=0x0406, type=t.Bool, manufacturer_code=None)
        ctm_mean_power = ZCLAttributeDef(id=0x0408, type=t.uint16_t, access="r", manufacturer_code=None)
        ctm_floor_temp = ZCLAttributeDef(id=0x0409, type=t.int16s, access="r", manufacturer_code=None)
        ctm_night_switching = ZCLAttributeDef(id=0x0411, type=t.Bool, manufacturer_code=None)
        ctm_frost_guard = ZCLAttributeDef(id=0x0412, type=t.Bool, manufacturer_code=None)
        ctm_child_lock = ZCLAttributeDef(id=0x0413, type=t.Bool, manufacturer_code=None)
        ctm_max_floor_temp = ZCLAttributeDef(id=0x0414, type=t.uint8_t, manufacturer_code=None)
        ctm_relay_state = ZCLAttributeDef(id=0x0415, type=t.Bool, access="r", manufacturer_code=None)
        ctm_regulator_setpoint = ZCLAttributeDef(id=0x0420, type=t.uint8_t, manufacturer_code=None)
        ctm_regulation_mode = ZCLAttributeDef(id=0x0421, type=t.uint8_t, manufacturer_code=None)
        ctm_operation_mode = ZCLAttributeDef(id=0x0422, type=t.uint8_t, manufacturer_code=None)
        ctm_max_floor_guard = ZCLAttributeDef(id=0x0423, type=t.Bool, manufacturer_code=None)
        ctm_weekly_timer = ZCLAttributeDef(id=0x0424, type=t.Bool, manufacturer_code=None)
        ctm_frost_guard_setpoint = ZCLAttributeDef(id=0x0425, type=t.uint8_t, manufacturer_code=None)
        ctm_external_temp = ZCLAttributeDef(id=0x0426, type=t.int16s, access="r", manufacturer_code=None)
        ctm_external_sensor_source = ZCLAttributeDef(id=0x0428, type=t.uint16_t, manufacturer_code=None)
        ctm_air_temp = ZCLAttributeDef(id=0x0429, type=t.int16s, access="r", manufacturer_code=None)
        ctm_floor_sensor_error = ZCLAttributeDef(id=0x042B, type=t.Bool, access="r", manufacturer_code=None)
        ctm_air_sensor_error = ZCLAttributeDef(id=0x042C, type=t.Bool, access="r", manufacturer_code=None)



_LOGGER = logging.getLogger(__name__)
_SHIPPED = pathlib.Path(zhaquirks.__file__).resolve().parent
_STEPPED_BACK: set = set()

# The Zigbee fingerprints (manufacturer, model) this quirk is for; None matches any manufacturer.
FINGERPRINTS = [(None, 'mTouch One')]
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
    QuirkBuilder(None, 'mTouch One')
    .replaces(HvacThermostatCluster)
    .switch(attribute_name=HvacThermostatCluster.AttributeDefs.ctm_child_lock.name, cluster_id=HvacThermostatCluster.cluster_id, entity_type=EntityType.STANDARD, translation_key='child_lock', fallback_name='Child lock')
    .number(attribute_name=HvacThermostatCluster.AttributeDefs.ctm_load.name, cluster_id=HvacThermostatCluster.cluster_id, min_value=0, max_value=3600, unit=UnitOfPower.WATT, device_class=NumberDeviceClass.POWER, entity_type=EntityType.STANDARD, translation_key='load', fallback_name='Load')
    .switch(attribute_name=HvacThermostatCluster.AttributeDefs.ctm_regulator_mode.name, cluster_id=HvacThermostatCluster.cluster_id, entity_type=EntityType.STANDARD, translation_key='regulator_mode', fallback_name='Regulator mode')
    .sensor(attribute_name=HvacThermostatCluster.AttributeDefs.ctm_mean_power.name, cluster_id=HvacThermostatCluster.cluster_id, state_class=SensorStateClass.MEASUREMENT, device_class=SensorDeviceClass.POWER, unit=UnitOfPower.WATT, entity_type=EntityType.STANDARD, translation_key='mean_power', fallback_name='Mean power')
    .sensor(attribute_name=HvacThermostatCluster.AttributeDefs.ctm_floor_temp.name, cluster_id=HvacThermostatCluster.cluster_id, divisor=100, state_class=SensorStateClass.MEASUREMENT, device_class=SensorDeviceClass.TEMPERATURE, unit=UnitOfTemperature.CELSIUS, entity_type=EntityType.STANDARD, translation_key='floor_temp', fallback_name='Floor temp')
    .switch(attribute_name=HvacThermostatCluster.AttributeDefs.ctm_frost_guard.name, cluster_id=HvacThermostatCluster.cluster_id, entity_type=EntityType.STANDARD, translation_key='frost_guard', fallback_name='Frost guard')
    .number(attribute_name=HvacThermostatCluster.AttributeDefs.ctm_regulator_setpoint.name, cluster_id=HvacThermostatCluster.cluster_id, min_value=1, max_value=99, unit=PERCENTAGE, entity_type=EntityType.STANDARD, translation_key='regulator_setpoint', fallback_name='Regulator setpoint')
    .sensor(attribute_name=HvacThermostatCluster.AttributeDefs.ctm_air_temp.name, cluster_id=HvacThermostatCluster.cluster_id, divisor=100, state_class=SensorStateClass.MEASUREMENT, device_class=SensorDeviceClass.TEMPERATURE, unit=UnitOfTemperature.CELSIUS, entity_type=EntityType.STANDARD, translation_key='air_temp', fallback_name='Air temp')
    # climate: standard clusters, ZHA's own entities
    # display_text: z2m's own code, not generated
    .filter(no_builtin_quirk)
    .add_to_registry()
)
