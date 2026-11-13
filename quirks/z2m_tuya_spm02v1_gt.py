"""Tuya SPM02V1-GT: Smart energy monitor for 3P+N system.

Generated from the Zigbee2MQTT definition.
Data: zigbee-herdsman-converters, MIT, Copyright (c) 2018 Koen Kanters.
Status: generated, not verified on hardware.
Revision: 0cbd313f
"""

import functools
import logging
import pathlib

import zhaquirks
from zha.quirks import DEVICE_REGISTRY, DeviceMatch
import zigpy.types as t
from zigpy.zcl import foundation

from zhaquirks.builder import (
    EntityType,
    NumberDeviceClass,
    PERCENTAGE,
    SensorDeviceClass,
    SensorStateClass,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfFrequency,
    UnitOfPower,
    UnitOfTime,
)
from zhaquirks.tuya import TUYA_CLUSTER_ID
from zhaquirks.tuya.builder import TuyaQuirkBuilder
from zhaquirks.tuya.mcu import DPToAttributeMapping, TuyaMCUCluster


def _be(data, start: int, width: int) -> int:
    """The unsigned big-endian number in data[start:start + width] of a Tuya RAW datapoint."""
    return int.from_bytes(bytes(data[start : start + width]), "big")


def _power_24(value: int) -> int:
    """24-bit power as z2m decodes it: 0x800000 to 0x99999a count down from 0x99999a (an
    offset encoding), values above are two's complement."""
    if value > 0x99999A:
        return value - 0x1000000
    if value >= 0x800000:
        return value - 0x99999A
    return value



_LOGGER = logging.getLogger(__name__)
_SHIPPED = pathlib.Path(zhaquirks.__file__).resolve().parent
_STEPPED_BACK: set = set()

# The Zigbee fingerprints (manufacturer, model) this quirk is for; None matches any manufacturer.
FINGERPRINTS = [('_TZE204_wjk6rurm', 'TS0601'), ('_TZE284_wjk6rurm', 'TS0601'), ('_TZE200_wjk6rurm', 'TS0601')]
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
    TuyaQuirkBuilder()
    .applies_to('_TZE204_wjk6rurm', 'TS0601')
    .applies_to('_TZE284_wjk6rurm', 'TS0601')
    .applies_to('_TZE200_wjk6rurm', 'TS0601')
    .tuya_sensor(dp_id=1, attribute_name='energy', type=t.uint32_t, divisor=100, state_class=SensorStateClass.TOTAL_INCREASING, device_class=SensorDeviceClass.ENERGY, unit=UnitOfEnergy.KILO_WATT_HOUR, entity_type=EntityType.STANDARD, fallback_name='Energy')
    .tuya_sensor(dp_id=23, attribute_name='produced_energy', type=t.uint32_t, divisor=100, state_class=SensorStateClass.TOTAL_INCREASING, device_class=SensorDeviceClass.ENERGY, unit=UnitOfEnergy.KILO_WATT_HOUR, entity_type=EntityType.STANDARD, translation_key='produced_energy', fallback_name='Produced energy')
    .tuya_attribute(dp_id=6, attribute_name='voltage_a', type=t.uint32_t, access=foundation.ZCLAttributeAccess.Read | foundation.ZCLAttributeAccess.Report)
    .tuya_attribute(dp_id=255, attribute_name='current_a', type=t.uint32_t, access=foundation.ZCLAttributeAccess.Read | foundation.ZCLAttributeAccess.Report)
    .tuya_attribute(dp_id=254, attribute_name='power_a', type=t.int32s, access=foundation.ZCLAttributeAccess.Read | foundation.ZCLAttributeAccess.Report)
    .tuya_dp_multi(dp_id=6, attribute_mapping=[DPToAttributeMapping(ep_attribute=TuyaMCUCluster.ep_attribute, attribute_name='voltage_a', converter=lambda x: _be(x, 0, 2)), DPToAttributeMapping(ep_attribute=TuyaMCUCluster.ep_attribute, attribute_name='current_a', converter=lambda x: _be(x, 2, 3)), DPToAttributeMapping(ep_attribute=TuyaMCUCluster.ep_attribute, attribute_name='power_a', converter=lambda x: _power_24(_be(x, 5, 3)))])
    .sensor(attribute_name='voltage_a', cluster_id=TUYA_CLUSTER_ID, divisor=10, state_class=SensorStateClass.MEASUREMENT, device_class=SensorDeviceClass.VOLTAGE, unit=UnitOfElectricPotential.VOLT, entity_type=EntityType.STANDARD, translation_key='voltage_a', fallback_name='Voltage a')
    .sensor(attribute_name='current_a', cluster_id=TUYA_CLUSTER_ID, divisor=1000, state_class=SensorStateClass.MEASUREMENT, device_class=SensorDeviceClass.CURRENT, unit=UnitOfElectricCurrent.AMPERE, entity_type=EntityType.STANDARD, translation_key='current_a', fallback_name='Current a')
    .sensor(attribute_name='power_a', cluster_id=TUYA_CLUSTER_ID, state_class=SensorStateClass.MEASUREMENT, device_class=SensorDeviceClass.POWER, unit=UnitOfPower.WATT, entity_type=EntityType.STANDARD, translation_key='power_a', fallback_name='Power a')
    .tuya_attribute(dp_id=7, attribute_name='voltage_b', type=t.uint32_t, access=foundation.ZCLAttributeAccess.Read | foundation.ZCLAttributeAccess.Report)
    .tuya_attribute(dp_id=253, attribute_name='current_b', type=t.uint32_t, access=foundation.ZCLAttributeAccess.Read | foundation.ZCLAttributeAccess.Report)
    .tuya_attribute(dp_id=252, attribute_name='power_b', type=t.int32s, access=foundation.ZCLAttributeAccess.Read | foundation.ZCLAttributeAccess.Report)
    .tuya_dp_multi(dp_id=7, attribute_mapping=[DPToAttributeMapping(ep_attribute=TuyaMCUCluster.ep_attribute, attribute_name='voltage_b', converter=lambda x: _be(x, 0, 2)), DPToAttributeMapping(ep_attribute=TuyaMCUCluster.ep_attribute, attribute_name='current_b', converter=lambda x: _be(x, 2, 3)), DPToAttributeMapping(ep_attribute=TuyaMCUCluster.ep_attribute, attribute_name='power_b', converter=lambda x: _power_24(_be(x, 5, 3)))])
    .sensor(attribute_name='voltage_b', cluster_id=TUYA_CLUSTER_ID, divisor=10, state_class=SensorStateClass.MEASUREMENT, device_class=SensorDeviceClass.VOLTAGE, unit=UnitOfElectricPotential.VOLT, entity_type=EntityType.STANDARD, translation_key='voltage_b', fallback_name='Voltage b')
    .sensor(attribute_name='current_b', cluster_id=TUYA_CLUSTER_ID, divisor=1000, state_class=SensorStateClass.MEASUREMENT, device_class=SensorDeviceClass.CURRENT, unit=UnitOfElectricCurrent.AMPERE, entity_type=EntityType.STANDARD, translation_key='current_b', fallback_name='Current b')
    .sensor(attribute_name='power_b', cluster_id=TUYA_CLUSTER_ID, state_class=SensorStateClass.MEASUREMENT, device_class=SensorDeviceClass.POWER, unit=UnitOfPower.WATT, entity_type=EntityType.STANDARD, translation_key='power_b', fallback_name='Power b')
    .tuya_attribute(dp_id=8, attribute_name='voltage_c', type=t.uint32_t, access=foundation.ZCLAttributeAccess.Read | foundation.ZCLAttributeAccess.Report)
    .tuya_attribute(dp_id=251, attribute_name='current_c', type=t.uint32_t, access=foundation.ZCLAttributeAccess.Read | foundation.ZCLAttributeAccess.Report)
    .tuya_attribute(dp_id=250, attribute_name='power_c', type=t.int32s, access=foundation.ZCLAttributeAccess.Read | foundation.ZCLAttributeAccess.Report)
    .tuya_dp_multi(dp_id=8, attribute_mapping=[DPToAttributeMapping(ep_attribute=TuyaMCUCluster.ep_attribute, attribute_name='voltage_c', converter=lambda x: _be(x, 0, 2)), DPToAttributeMapping(ep_attribute=TuyaMCUCluster.ep_attribute, attribute_name='current_c', converter=lambda x: _be(x, 2, 3)), DPToAttributeMapping(ep_attribute=TuyaMCUCluster.ep_attribute, attribute_name='power_c', converter=lambda x: _power_24(_be(x, 5, 3)))])
    .sensor(attribute_name='voltage_c', cluster_id=TUYA_CLUSTER_ID, divisor=10, state_class=SensorStateClass.MEASUREMENT, device_class=SensorDeviceClass.VOLTAGE, unit=UnitOfElectricPotential.VOLT, entity_type=EntityType.STANDARD, translation_key='voltage_c', fallback_name='Voltage c')
    .sensor(attribute_name='current_c', cluster_id=TUYA_CLUSTER_ID, divisor=1000, state_class=SensorStateClass.MEASUREMENT, device_class=SensorDeviceClass.CURRENT, unit=UnitOfElectricCurrent.AMPERE, entity_type=EntityType.STANDARD, translation_key='current_c', fallback_name='Current c')
    .sensor(attribute_name='power_c', cluster_id=TUYA_CLUSTER_ID, state_class=SensorStateClass.MEASUREMENT, device_class=SensorDeviceClass.POWER, unit=UnitOfPower.WATT, entity_type=EntityType.STANDARD, translation_key='power_c', fallback_name='Power c')
    .tuya_sensor(dp_id=29, attribute_name='power', type=t.uint32_t, state_class=SensorStateClass.MEASUREMENT, device_class=SensorDeviceClass.POWER, unit=UnitOfPower.WATT, entity_type=EntityType.STANDARD, fallback_name='Power')
    .tuya_sensor(dp_id=32, attribute_name='ac_frequency', type=t.uint32_t, divisor=100, state_class=SensorStateClass.MEASUREMENT, device_class=SensorDeviceClass.FREQUENCY, unit=UnitOfFrequency.HERTZ, entity_type=EntityType.STANDARD, translation_key='ac_frequency', fallback_name='AC frequency')
    .tuya_sensor(dp_id=50, attribute_name='power_factor', type=t.uint32_t, state_class=SensorStateClass.MEASUREMENT, unit=PERCENTAGE, entity_type=EntityType.STANDARD, translation_key='power_factor', fallback_name='Power factor')
    .tuya_switch(dp_id=101, attribute_name='device_locating', entity_type=EntityType.CONFIG, translation_key='device_locating', fallback_name='Device locating')
    .tuya_number(dp_id=102, type=t.uint32_t, attribute_name='update_frequency', min_value=30, max_value=3600, unit=UnitOfTime.SECONDS, device_class=NumberDeviceClass.DURATION, entity_type=EntityType.CONFIG, translation_key='update_frequency', fallback_name='Update frequency')
    .tuya_sensor(dp_id=108, attribute_name='power_factor_a', type=t.uint32_t, state_class=SensorStateClass.MEASUREMENT, unit=PERCENTAGE, entity_type=EntityType.STANDARD, translation_key='power_factor_a', fallback_name='Power factor a')
    .tuya_sensor(dp_id=53, attribute_name='energy_a', type=t.uint32_t, divisor=100, state_class=SensorStateClass.TOTAL_INCREASING, device_class=SensorDeviceClass.ENERGY, unit=UnitOfEnergy.KILO_WATT_HOUR, entity_type=EntityType.STANDARD, translation_key='energy_a', fallback_name='Energy a')
    .tuya_sensor(dp_id=57, attribute_name='energy_produced_a', type=t.uint32_t, divisor=100, state_class=SensorStateClass.TOTAL_INCREASING, device_class=SensorDeviceClass.ENERGY, unit=UnitOfEnergy.KILO_WATT_HOUR, entity_type=EntityType.STANDARD, translation_key='energy_produced_a', fallback_name='Energy produced a')
    .tuya_sensor(dp_id=117, attribute_name='power_factor_b', type=t.uint32_t, state_class=SensorStateClass.MEASUREMENT, unit=PERCENTAGE, entity_type=EntityType.STANDARD, translation_key='power_factor_b', fallback_name='Power factor b')
    .tuya_sensor(dp_id=54, attribute_name='energy_b', type=t.uint32_t, divisor=100, state_class=SensorStateClass.TOTAL_INCREASING, device_class=SensorDeviceClass.ENERGY, unit=UnitOfEnergy.KILO_WATT_HOUR, entity_type=EntityType.STANDARD, translation_key='energy_b', fallback_name='Energy b')
    .tuya_sensor(dp_id=58, attribute_name='energy_produced_b', type=t.uint32_t, divisor=100, state_class=SensorStateClass.TOTAL_INCREASING, device_class=SensorDeviceClass.ENERGY, unit=UnitOfEnergy.KILO_WATT_HOUR, entity_type=EntityType.STANDARD, translation_key='energy_produced_b', fallback_name='Energy produced b')
    .tuya_sensor(dp_id=126, attribute_name='power_factor_c', type=t.uint32_t, state_class=SensorStateClass.MEASUREMENT, unit=PERCENTAGE, entity_type=EntityType.STANDARD, translation_key='power_factor_c', fallback_name='Power factor c')
    .tuya_sensor(dp_id=55, attribute_name='energy_c', type=t.uint32_t, divisor=100, state_class=SensorStateClass.TOTAL_INCREASING, device_class=SensorDeviceClass.ENERGY, unit=UnitOfEnergy.KILO_WATT_HOUR, entity_type=EntityType.STANDARD, translation_key='energy_c', fallback_name='Energy c')
    .tuya_sensor(dp_id=59, attribute_name='energy_produced_c', type=t.uint32_t, divisor=100, state_class=SensorStateClass.TOTAL_INCREASING, device_class=SensorDeviceClass.ENERGY, unit=UnitOfEnergy.KILO_WATT_HOUR, entity_type=EntityType.STANDARD, translation_key='energy_produced_c', fallback_name='Energy produced c')
    .skip_configuration()
    .filter(no_builtin_quirk)
    .add_to_registry()
)
