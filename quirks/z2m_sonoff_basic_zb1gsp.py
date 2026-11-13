"""SONOFF BASIC-ZB1GSP: Zigbee smart plug with power monitoring.

Generated from the Zigbee2MQTT definition.
Entity names follow zha-device-handlers#5033 (open pull request for this device).
Data: zigbee-herdsman-converters, MIT, Copyright (c) 2018 Koen Kanters.
Status: generated, not verified on hardware.
Revision: 415c6132
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
    QuirkBuilder,
    SensorDeviceClass,
    SensorStateClass,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfPower,
)
from zhaquirks.clusters import CustomCluster


class CustomClusterEwelinkCluster(CustomCluster):
    """customClusterEwelink (z2m custom cluster)."""

    cluster_id = 0xFC11

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        network_led = ZCLAttributeDef(id=0x0001, type=t.Bool, manufacturer_code=None)
        fault_code = ZCLAttributeDef(id=0x0010, type=t.uint32_t, access="r", manufacturer_code=None)
        limits_of_threshold_value = ZCLAttributeDef(id=0x7003, type=t.CharacterString, manufacturer_code=None)
        ac_current_current_value = ZCLAttributeDef(id=0x7004, type=t.uint32_t, access="r", manufacturer_code=None)
        ac_current_voltage_value = ZCLAttributeDef(id=0x7005, type=t.uint32_t, access="r", manufacturer_code=None)
        ac_current_power_value = ZCLAttributeDef(id=0x7006, type=t.uint32_t, access="r", manufacturer_code=None)
        outlet_control_protect = ZCLAttributeDef(id=0x7007, type=t.uint8_t, manufacturer_code=None)
        daily_forward_energy = ZCLAttributeDef(id=0x7009, type=t.uint32_t, access="r", manufacturer_code=None)
        monthly_forward_energy = ZCLAttributeDef(id=0x700A, type=t.uint32_t, access="r", manufacturer_code=None)
        energy_yesterday = ZCLAttributeDef(id=0x700B, type=t.uint32_t, access="r", manufacturer_code=None)
        ac_current_max_overload_enable = ZCLAttributeDef(id=0x700C, type=t.uint8_t, manufacturer_code=None)
        ac_current_max_overload = ZCLAttributeDef(id=0x700D, type=t.uint32_t, manufacturer_code=None)
        ac_voltage_max_overload_enable = ZCLAttributeDef(id=0x700E, type=t.uint8_t, manufacturer_code=None)
        ac_voltage_max_overload = ZCLAttributeDef(id=0x700F, type=t.uint32_t, manufacturer_code=None)
        ac_power_max_overload_enable = ZCLAttributeDef(id=0x7010, type=t.uint8_t, manufacturer_code=None)
        ac_power_max_overload = ZCLAttributeDef(id=0x7011, type=t.uint32_t, manufacturer_code=None)
        total_energy_consumption = ZCLAttributeDef(id=0x701E, type=t.uint32_t, access="r", manufacturer_code=None)
        daily_reverse_energy = ZCLAttributeDef(id=0x7018, type=t.uint32_t, access="r", manufacturer_code=None)
        monthly_reverse_energy = ZCLAttributeDef(id=0x7019, type=t.uint32_t, access="r", manufacturer_code=None)
        total_reverse_energy = ZCLAttributeDef(id=0x701F, type=t.uint32_t, access="r", manufacturer_code=None)

    class ServerCommandDefs(BaseCommandDefs):
        """Command definitions (z2m's commands this cluster lacks)."""

        clear_history = ZCLCommandDef(id=0x0C, schema={'device_type': t.uint8_t, 'device_length': t.uint8_t, 'event_type': t.uint8_t}, direction=Direction.Client_to_Server, manufacturer_code=None)



_LOGGER = logging.getLogger(__name__)
_SHIPPED = pathlib.Path(zhaquirks.__file__).resolve().parent
_STEPPED_BACK: set = set()

# The Zigbee fingerprints (manufacturer, model) this quirk is for; None matches any manufacturer.
FINGERPRINTS = [(None, 'BASIC-ZB1GSP')]
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
    QuirkBuilder(None, 'BASIC-ZB1GSP')
    .replaces(CustomClusterEwelinkCluster)
    .switch(attribute_name=CustomClusterEwelinkCluster.AttributeDefs.network_led.name, cluster_id=CustomClusterEwelinkCluster.cluster_id, entity_type=EntityType.CONFIG, translation_key='network_led', fallback_name='Network LED')
    .sensor(attribute_name=CustomClusterEwelinkCluster.AttributeDefs.ac_current_voltage_value.name, cluster_id=CustomClusterEwelinkCluster.cluster_id, divisor=1000, state_class=SensorStateClass.MEASUREMENT, device_class=SensorDeviceClass.VOLTAGE, unit=UnitOfElectricPotential.VOLT, entity_type=EntityType.STANDARD, fallback_name='Voltage')
    .sensor(attribute_name=CustomClusterEwelinkCluster.AttributeDefs.daily_forward_energy.name, cluster_id=CustomClusterEwelinkCluster.cluster_id, divisor=1000, state_class=SensorStateClass.TOTAL_INCREASING, device_class=SensorDeviceClass.ENERGY, unit=UnitOfEnergy.KILO_WATT_HOUR, entity_type=EntityType.STANDARD, translation_key='daily_forward_energy', fallback_name='Daily forward energy')
    .sensor(attribute_name=CustomClusterEwelinkCluster.AttributeDefs.daily_reverse_energy.name, cluster_id=CustomClusterEwelinkCluster.cluster_id, divisor=1000, entity_type=EntityType.STANDARD, translation_key='daily_reverse_energy', fallback_name='Daily reverse energy')
    .sensor(attribute_name=CustomClusterEwelinkCluster.AttributeDefs.monthly_forward_energy.name, cluster_id=CustomClusterEwelinkCluster.cluster_id, divisor=1000, state_class=SensorStateClass.TOTAL_INCREASING, device_class=SensorDeviceClass.ENERGY, unit=UnitOfEnergy.KILO_WATT_HOUR, entity_type=EntityType.STANDARD, translation_key='monthly_forward_energy', fallback_name='Monthly forward energy')
    .sensor(attribute_name=CustomClusterEwelinkCluster.AttributeDefs.monthly_reverse_energy.name, cluster_id=CustomClusterEwelinkCluster.cluster_id, divisor=1000, entity_type=EntityType.STANDARD, translation_key='monthly_reverse_energy', fallback_name='Monthly reverse energy')
    .sensor(attribute_name=CustomClusterEwelinkCluster.AttributeDefs.energy_yesterday.name, cluster_id=CustomClusterEwelinkCluster.cluster_id, divisor=1000, state_class=SensorStateClass.TOTAL_INCREASING, device_class=SensorDeviceClass.ENERGY, unit=UnitOfEnergy.KILO_WATT_HOUR, entity_type=EntityType.STANDARD, translation_key='energy_yesterday', fallback_name='Energy yesterday')
    .sensor(attribute_name=CustomClusterEwelinkCluster.AttributeDefs.total_energy_consumption.name, cluster_id=CustomClusterEwelinkCluster.cluster_id, divisor=1000, state_class=SensorStateClass.TOTAL_INCREASING, device_class=SensorDeviceClass.ENERGY, unit=UnitOfEnergy.KILO_WATT_HOUR, entity_type=EntityType.STANDARD, translation_key='total_energy', fallback_name='Total energy')
    .sensor(attribute_name=CustomClusterEwelinkCluster.AttributeDefs.total_reverse_energy.name, cluster_id=CustomClusterEwelinkCluster.cluster_id, divisor=1000, entity_type=EntityType.STANDARD, translation_key='total_reverse_energy', fallback_name='Total reverse energy')
    .switch(attribute_name=CustomClusterEwelinkCluster.AttributeDefs.outlet_control_protect.name, cluster_id=CustomClusterEwelinkCluster.cluster_id, entity_type=EntityType.CONFIG, translation_key='outlet_control_protect', fallback_name='Outlet control protect')
    .switch(attribute_name=CustomClusterEwelinkCluster.AttributeDefs.ac_current_max_overload_enable.name, cluster_id=CustomClusterEwelinkCluster.cluster_id, entity_type=EntityType.CONFIG, translation_key='ac_current_max_overload_enable', fallback_name='AC current max overload enable')
    .number(attribute_name=CustomClusterEwelinkCluster.AttributeDefs.ac_current_max_overload.name, cluster_id=CustomClusterEwelinkCluster.cluster_id, min_value=0.1, max_value=32, step=0.1, unit=UnitOfElectricCurrent.AMPERE, multiplier=0.001, device_class=NumberDeviceClass.CURRENT, entity_type=EntityType.CONFIG, translation_key='ac_current_max_overload', fallback_name='AC current max overload')
    .switch(attribute_name=CustomClusterEwelinkCluster.AttributeDefs.ac_voltage_max_overload_enable.name, cluster_id=CustomClusterEwelinkCluster.cluster_id, entity_type=EntityType.CONFIG, translation_key='ac_voltage_max_overload_enable', fallback_name='AC voltage max overload enable')
    .number(attribute_name=CustomClusterEwelinkCluster.AttributeDefs.ac_voltage_max_overload.name, cluster_id=CustomClusterEwelinkCluster.cluster_id, min_value=85, max_value=277, step=1, unit=UnitOfElectricPotential.VOLT, multiplier=0.001, device_class=NumberDeviceClass.VOLTAGE, entity_type=EntityType.CONFIG, translation_key='ac_voltage_max_overload', fallback_name='AC voltage max overload')
    .switch(attribute_name=CustomClusterEwelinkCluster.AttributeDefs.ac_power_max_overload_enable.name, cluster_id=CustomClusterEwelinkCluster.cluster_id, entity_type=EntityType.CONFIG, translation_key='ac_power_max_overload_enable', fallback_name='AC power max overload enable')
    .number(attribute_name=CustomClusterEwelinkCluster.AttributeDefs.ac_power_max_overload.name, cluster_id=CustomClusterEwelinkCluster.cluster_id, min_value=10, max_value=7680, step=1, unit=UnitOfPower.WATT, multiplier=0.001, device_class=NumberDeviceClass.POWER, entity_type=EntityType.CONFIG, translation_key='ac_power_max_overload', fallback_name='AC power max overload')
    .command_button(command_name=CustomClusterEwelinkCluster.ServerCommandDefs.clear_history.name, cluster_id=CustomClusterEwelinkCluster.cluster_id, command_args=(2, 1, 0), entity_type=EntityType.STANDARD, initially_disabled=True, translation_key='clear_history', fallback_name='Clear history', unique_id_suffix='clear_history')
    # power: z2m numeric with own fromZigbee converter, not generated
    # current: z2m numeric with own fromZigbee converter, not generated
    # switch: standard clusters, ZHA's own entities
    # power_on_behavior: standard clusters, ZHA's own entities
    # inching_control_set: z2m's own code, not generated
    .filter(no_builtin_quirk)
    .add_to_registry()
)
