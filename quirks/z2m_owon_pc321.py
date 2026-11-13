"""OWON PC321: 3-Phase clamp power meter.

Generated from the Zigbee2MQTT definition.
Data: zigbee-herdsman-converters, MIT, Copyright (c) 2018 Koen Kanters.
Status: generated, not verified on hardware.
Revision: 5fc9b89c
"""

import functools
import logging
import pathlib

import zhaquirks
from zha.quirks import DEVICE_REGISTRY, DeviceMatch
import zigpy.types as t
from zigpy.zcl.foundation import ZCLAttributeDef
from zigpy.zcl.clusters.smartenergy import Metering

from zhaquirks.builder import (
    EntityType,
    NumberDeviceClass,
    PERCENTAGE,
    QuirkBuilder,
    SensorDeviceClass,
    SensorStateClass,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfTime,
)
from zhaquirks.clusters import CustomCluster


class SeMeteringCluster(CustomCluster, Metering):
    """Metering with the attributes z2m adds."""

    class AttributeDefs(Metering.AttributeDefs):
        """Attribute definitions."""

        owon_l1_phase_power = ZCLAttributeDef(id=0x2000, type=t.int24s, manufacturer_code=0x113C)
        owon_l2_phase_power = ZCLAttributeDef(id=0x2001, type=t.int24s, manufacturer_code=0x113C)
        owon_l3_phase_power = ZCLAttributeDef(id=0x2002, type=t.int24s, manufacturer_code=0x113C)
        owon_l1_phase_reactive_power = ZCLAttributeDef(id=0x2100, type=t.int24s, manufacturer_code=0x113C)
        owon_l2_phase_reactive_power = ZCLAttributeDef(id=0x2101, type=t.int24s, manufacturer_code=0x113C)
        owon_l3_phase_reactive_power = ZCLAttributeDef(id=0x2102, type=t.int24s, manufacturer_code=0x113C)
        owon_reactive_power_sum = ZCLAttributeDef(id=0x2103, type=t.int24s, manufacturer_code=0x113C)
        owon_l1_phase_voltage = ZCLAttributeDef(id=0x3000, type=t.uint24_t, manufacturer_code=0x113C)
        owon_l2_phase_voltage = ZCLAttributeDef(id=0x3001, type=t.uint24_t, manufacturer_code=0x113C)
        owon_l3_phase_voltage = ZCLAttributeDef(id=0x3002, type=t.uint24_t, manufacturer_code=0x113C)
        owon_l1_phase_current = ZCLAttributeDef(id=0x3100, type=t.uint24_t, manufacturer_code=0x113C)
        owon_l2_phase_current = ZCLAttributeDef(id=0x3101, type=t.uint24_t, manufacturer_code=0x113C)
        owon_l3_phase_current = ZCLAttributeDef(id=0x3102, type=t.uint24_t, manufacturer_code=0x113C)
        owon_current_sum = ZCLAttributeDef(id=0x3103, type=t.uint24_t, manufacturer_code=0x113C)
        owon_leakage_current = ZCLAttributeDef(id=0x3104, type=t.uint24_t, manufacturer_code=0x113C)
        owon_l1_energy = ZCLAttributeDef(id=0x4000, type=t.uint48_t, manufacturer_code=0x113C)
        owon_l2_energy = ZCLAttributeDef(id=0x4001, type=t.uint48_t, manufacturer_code=0x113C)
        owon_l3_energy = ZCLAttributeDef(id=0x4002, type=t.uint48_t, manufacturer_code=0x113C)
        owon_l1_reactive_energy = ZCLAttributeDef(id=0x4100, type=t.uint48_t, manufacturer_code=0x113C)
        owon_l2_reactive_energy = ZCLAttributeDef(id=0x4101, type=t.uint48_t, manufacturer_code=0x113C)
        owon_l3_reactive_energy = ZCLAttributeDef(id=0x4102, type=t.uint48_t, manufacturer_code=0x113C)
        owon_reactive_energy_sum = ZCLAttributeDef(id=0x4103, type=t.uint48_t, manufacturer_code=0x113C)
        owon_l1_power_factor = ZCLAttributeDef(id=0x4104, type=t.int8s, manufacturer_code=0x113C)
        owon_l2_power_factor = ZCLAttributeDef(id=0x4105, type=t.int8s, manufacturer_code=0x113C)
        owon_l3_power_factor = ZCLAttributeDef(id=0x4106, type=t.int8s, manufacturer_code=0x113C)
        owon_frequency = ZCLAttributeDef(id=0x5005, type=t.uint8_t, manufacturer_code=0x113C)
        owon_report_map = ZCLAttributeDef(id=0x1000, type=t.bitmap8, manufacturer_code=0x113C)
        owon_last_historical_record_time = ZCLAttributeDef(id=0x5000, type=t.uint32_t, manufacturer_code=0x113C)
        owon_oldest_historical_record_time = ZCLAttributeDef(id=0x5001, type=t.uint32_t, manufacturer_code=0x113C)
        owon_minimum_report_cycle = ZCLAttributeDef(id=0x5002, type=t.uint32_t, manufacturer_code=0x113C)
        owon_maximum_report_cycle = ZCLAttributeDef(id=0x5003, type=t.uint32_t, manufacturer_code=0x113C)
        owon_sent_historical_record_state = ZCLAttributeDef(id=0x5004, type=t.uint8_t, manufacturer_code=0x113C)
        owon_accumulative_energy_threshold = ZCLAttributeDef(id=0x5006, type=t.uint8_t, manufacturer_code=0x113C)
        owon_report_mode = ZCLAttributeDef(id=0x5007, type=t.uint8_t, manufacturer_code=0x113C)
        owon_percent_change_in_power = ZCLAttributeDef(id=0x5008, type=t.uint8_t, manufacturer_code=0x113C)



_LOGGER = logging.getLogger(__name__)
_SHIPPED = pathlib.Path(zhaquirks.__file__).resolve().parent
_STEPPED_BACK: set = set()

# The Zigbee fingerprints (manufacturer, model) this quirk is for; None matches any manufacturer.
FINGERPRINTS = [(None, 'PC321')]
# Names that a model-only fingerprint would catch but Zigbee2MQTT gives to other devices.
CLAIMED_ELSEWHERE = set()
# The endpoints this quirk needs, each with the input clusters it puts there where Zigbee2MQTT names none.
ENDPOINTS = {1: (0x0702,)}


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
    QuirkBuilder(None, 'PC321')
    .replaces(SeMeteringCluster)
    .number(attribute_name=SeMeteringCluster.AttributeDefs.owon_minimum_report_cycle.name, cluster_id=SeMeteringCluster.cluster_id, min_value=1, max_value=3600, unit=UnitOfTime.SECONDS, device_class=NumberDeviceClass.DURATION, entity_type=EntityType.CONFIG, translation_key='min_report_cycle', fallback_name='Min report cycle')
    .number(attribute_name=SeMeteringCluster.AttributeDefs.owon_maximum_report_cycle.name, cluster_id=SeMeteringCluster.cluster_id, min_value=1, max_value=3600, unit=UnitOfTime.SECONDS, device_class=NumberDeviceClass.DURATION, entity_type=EntityType.CONFIG, translation_key='max_report_cycle', fallback_name='Max report cycle')
    .number(attribute_name=SeMeteringCluster.AttributeDefs.owon_percent_change_in_power.name, cluster_id=SeMeteringCluster.cluster_id, min_value=1, max_value=100, unit=PERCENTAGE, entity_type=EntityType.CONFIG, translation_key='percent_change_in_power', fallback_name='Percent change in power')
    .sensor(attribute_name=SeMeteringCluster.AttributeDefs.owon_reactive_power_sum.name, cluster_id=SeMeteringCluster.cluster_id, state_class=SensorStateClass.MEASUREMENT, unit='VAR', entity_type=EntityType.STANDARD, translation_key='power_reactive', fallback_name='Power reactive')
    .sensor(attribute_name=SeMeteringCluster.AttributeDefs.owon_l1_phase_voltage.name, cluster_id=SeMeteringCluster.cluster_id, divisor=10, state_class=SensorStateClass.MEASUREMENT, device_class=SensorDeviceClass.VOLTAGE, unit=UnitOfElectricPotential.VOLT, entity_type=EntityType.STANDARD, translation_key='voltage_l1', fallback_name='Voltage L1')
    .sensor(attribute_name=SeMeteringCluster.AttributeDefs.owon_l2_phase_voltage.name, cluster_id=SeMeteringCluster.cluster_id, divisor=10, state_class=SensorStateClass.MEASUREMENT, device_class=SensorDeviceClass.VOLTAGE, unit=UnitOfElectricPotential.VOLT, entity_type=EntityType.STANDARD, translation_key='voltage_l2', fallback_name='Voltage L2')
    .sensor(attribute_name=SeMeteringCluster.AttributeDefs.owon_l3_phase_voltage.name, cluster_id=SeMeteringCluster.cluster_id, divisor=10, state_class=SensorStateClass.MEASUREMENT, device_class=SensorDeviceClass.VOLTAGE, unit=UnitOfElectricPotential.VOLT, entity_type=EntityType.STANDARD, translation_key='voltage_l3', fallback_name='Voltage L3')
    .sensor(attribute_name=SeMeteringCluster.AttributeDefs.owon_l1_phase_current.name, cluster_id=SeMeteringCluster.cluster_id, divisor=1000, state_class=SensorStateClass.MEASUREMENT, device_class=SensorDeviceClass.CURRENT, unit=UnitOfElectricCurrent.AMPERE, entity_type=EntityType.STANDARD, translation_key='current_l1', fallback_name='Current L1')
    .sensor(attribute_name=SeMeteringCluster.AttributeDefs.owon_l2_phase_current.name, cluster_id=SeMeteringCluster.cluster_id, divisor=1000, state_class=SensorStateClass.MEASUREMENT, device_class=SensorDeviceClass.CURRENT, unit=UnitOfElectricCurrent.AMPERE, entity_type=EntityType.STANDARD, translation_key='current_l2', fallback_name='Current L2')
    .sensor(attribute_name=SeMeteringCluster.AttributeDefs.owon_l3_phase_current.name, cluster_id=SeMeteringCluster.cluster_id, divisor=1000, state_class=SensorStateClass.MEASUREMENT, device_class=SensorDeviceClass.CURRENT, unit=UnitOfElectricCurrent.AMPERE, entity_type=EntityType.STANDARD, translation_key='current_l3', fallback_name='Current L3')
    .sensor(attribute_name=SeMeteringCluster.AttributeDefs.owon_l1_energy.name, cluster_id=SeMeteringCluster.cluster_id, divisor=1000, state_class=SensorStateClass.TOTAL_INCREASING, device_class=SensorDeviceClass.ENERGY, unit=UnitOfEnergy.KILO_WATT_HOUR, entity_type=EntityType.STANDARD, translation_key='energy_l1', fallback_name='Energy L1')
    .sensor(attribute_name=SeMeteringCluster.AttributeDefs.owon_l2_energy.name, cluster_id=SeMeteringCluster.cluster_id, divisor=1000, state_class=SensorStateClass.TOTAL_INCREASING, device_class=SensorDeviceClass.ENERGY, unit=UnitOfEnergy.KILO_WATT_HOUR, entity_type=EntityType.STANDARD, translation_key='energy_l2', fallback_name='Energy L2')
    .sensor(attribute_name=SeMeteringCluster.AttributeDefs.owon_l3_energy.name, cluster_id=SeMeteringCluster.cluster_id, divisor=1000, state_class=SensorStateClass.TOTAL_INCREASING, device_class=SensorDeviceClass.ENERGY, unit=UnitOfEnergy.KILO_WATT_HOUR, entity_type=EntityType.STANDARD, translation_key='energy_l3', fallback_name='Energy L3')
    .sensor(attribute_name=SeMeteringCluster.AttributeDefs.owon_l1_reactive_energy.name, cluster_id=SeMeteringCluster.cluster_id, divisor=1000, state_class=SensorStateClass.MEASUREMENT, unit='kVArh', entity_type=EntityType.STANDARD, translation_key='reactive_energy_l1', fallback_name='Reactive energy L1')
    .sensor(attribute_name=SeMeteringCluster.AttributeDefs.owon_l2_reactive_energy.name, cluster_id=SeMeteringCluster.cluster_id, divisor=1000, state_class=SensorStateClass.MEASUREMENT, unit='kVArh', entity_type=EntityType.STANDARD, translation_key='reactive_energy_l2', fallback_name='Reactive energy L2')
    .sensor(attribute_name=SeMeteringCluster.AttributeDefs.owon_l3_reactive_energy.name, cluster_id=SeMeteringCluster.cluster_id, divisor=1000, state_class=SensorStateClass.MEASUREMENT, unit='kVArh', entity_type=EntityType.STANDARD, translation_key='reactive_energy_l3', fallback_name='Reactive energy L3')
    .sensor(attribute_name=SeMeteringCluster.AttributeDefs.owon_l1_phase_power.name, cluster_id=SeMeteringCluster.cluster_id, state_class=SensorStateClass.MEASUREMENT, device_class=SensorDeviceClass.POWER, unit=UnitOfPower.WATT, entity_type=EntityType.STANDARD, translation_key='power_l1', fallback_name='Power L1')
    .sensor(attribute_name=SeMeteringCluster.AttributeDefs.owon_l2_phase_power.name, cluster_id=SeMeteringCluster.cluster_id, state_class=SensorStateClass.MEASUREMENT, device_class=SensorDeviceClass.POWER, unit=UnitOfPower.WATT, entity_type=EntityType.STANDARD, translation_key='power_l2', fallback_name='Power L2')
    .sensor(attribute_name=SeMeteringCluster.AttributeDefs.owon_l3_phase_power.name, cluster_id=SeMeteringCluster.cluster_id, state_class=SensorStateClass.MEASUREMENT, device_class=SensorDeviceClass.POWER, unit=UnitOfPower.WATT, entity_type=EntityType.STANDARD, translation_key='power_l3', fallback_name='Power L3')
    .sensor(attribute_name=SeMeteringCluster.AttributeDefs.owon_l1_phase_reactive_power.name, cluster_id=SeMeteringCluster.cluster_id, state_class=SensorStateClass.MEASUREMENT, unit='VAr', entity_type=EntityType.STANDARD, translation_key='reactive_power_l1', fallback_name='Reactive power L1')
    .sensor(attribute_name=SeMeteringCluster.AttributeDefs.owon_l2_phase_reactive_power.name, cluster_id=SeMeteringCluster.cluster_id, state_class=SensorStateClass.MEASUREMENT, unit='VAr', entity_type=EntityType.STANDARD, translation_key='reactive_power_l2', fallback_name='Reactive power L2')
    .sensor(attribute_name=SeMeteringCluster.AttributeDefs.owon_l3_phase_reactive_power.name, cluster_id=SeMeteringCluster.cluster_id, state_class=SensorStateClass.MEASUREMENT, unit='VAr', entity_type=EntityType.STANDARD, translation_key='reactive_power_l3', fallback_name='Reactive power L3')
    .sensor(attribute_name=SeMeteringCluster.AttributeDefs.owon_l1_power_factor.name, cluster_id=SeMeteringCluster.cluster_id, divisor=100, state_class=SensorStateClass.MEASUREMENT, unit=PERCENTAGE, entity_type=EntityType.STANDARD, translation_key='power_factor_l1', fallback_name='Power factor L1')
    .sensor(attribute_name=SeMeteringCluster.AttributeDefs.owon_l2_power_factor.name, cluster_id=SeMeteringCluster.cluster_id, divisor=100, state_class=SensorStateClass.MEASUREMENT, unit=PERCENTAGE, entity_type=EntityType.STANDARD, translation_key='power_factor_l2', fallback_name='Power factor L2')
    .sensor(attribute_name=SeMeteringCluster.AttributeDefs.owon_l3_power_factor.name, cluster_id=SeMeteringCluster.cluster_id, divisor=100, state_class=SensorStateClass.MEASUREMENT, unit=PERCENTAGE, entity_type=EntityType.STANDARD, translation_key='power_factor_l3', fallback_name='Power factor L3')
    # current: z2m's own code, not generated
    # power: standard clusters or z2m's own code, not generated
    # energy: standard clusters or z2m's own code, not generated
    # reactive_energy: z2m's own code, not generated
    # clear_metering: standard clusters or z2m's own code, not generated
    .filter(no_builtin_quirk)
    .add_to_registry()
)
