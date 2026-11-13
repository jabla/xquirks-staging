"""Tuya SDM02V1-GT: Smart energy monitor for 2P+N system.

Generated from the Zigbee2MQTT definition.
Data: zigbee-herdsman-converters, MIT, Copyright (c) 2018 Koen Kanters.
Status: generated, not verified on hardware.
Revision: 13a13dfa
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
FINGERPRINTS = [('_TZE204_x8diwkqb', 'TS0601'), ('_TZE284_x8diwkqb', 'TS0601'), ('_TZE200_x8diwkqb', 'TS0601')]
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
    .applies_to('_TZE204_x8diwkqb', 'TS0601')
    .applies_to('_TZE284_x8diwkqb', 'TS0601')
    .applies_to('_TZE200_x8diwkqb', 'TS0601')
    .tuya_sensor(dp_id=1, attribute_name='energy', type=t.uint32_t, divisor=100, state_class=SensorStateClass.TOTAL_INCREASING, device_class=SensorDeviceClass.ENERGY, unit=UnitOfEnergy.KILO_WATT_HOUR, entity_type=EntityType.STANDARD, fallback_name='Energy')
    .tuya_attribute(dp_id=6, attribute_name='voltage_l1', type=t.uint32_t, access=foundation.ZCLAttributeAccess.Read | foundation.ZCLAttributeAccess.Report)
    .tuya_attribute(dp_id=255, attribute_name='current_l1', type=t.uint32_t, access=foundation.ZCLAttributeAccess.Read | foundation.ZCLAttributeAccess.Report)
    .tuya_attribute(dp_id=254, attribute_name='power_l1', type=t.int32s, access=foundation.ZCLAttributeAccess.Read | foundation.ZCLAttributeAccess.Report)
    .tuya_dp_multi(dp_id=6, attribute_mapping=[DPToAttributeMapping(ep_attribute=TuyaMCUCluster.ep_attribute, attribute_name='voltage_l1', converter=lambda x: _be(x, 0, 2)), DPToAttributeMapping(ep_attribute=TuyaMCUCluster.ep_attribute, attribute_name='current_l1', converter=lambda x: _be(x, 2, 3)), DPToAttributeMapping(ep_attribute=TuyaMCUCluster.ep_attribute, attribute_name='power_l1', converter=lambda x: _power_24(_be(x, 5, 3)))])
    .sensor(attribute_name='voltage_l1', cluster_id=TUYA_CLUSTER_ID, divisor=10, state_class=SensorStateClass.MEASUREMENT, device_class=SensorDeviceClass.VOLTAGE, unit=UnitOfElectricPotential.VOLT, entity_type=EntityType.STANDARD, translation_key='voltage_l1', fallback_name='Voltage L1')
    .sensor(attribute_name='current_l1', cluster_id=TUYA_CLUSTER_ID, divisor=1000, state_class=SensorStateClass.MEASUREMENT, device_class=SensorDeviceClass.CURRENT, unit=UnitOfElectricCurrent.AMPERE, entity_type=EntityType.STANDARD, translation_key='current_l1', fallback_name='Current L1')
    .sensor(attribute_name='power_l1', cluster_id=TUYA_CLUSTER_ID, state_class=SensorStateClass.MEASUREMENT, device_class=SensorDeviceClass.POWER, unit=UnitOfPower.WATT, entity_type=EntityType.STANDARD, translation_key='power_l1', fallback_name='Power L1')
    .tuya_attribute(dp_id=7, attribute_name='voltage_l2', type=t.uint32_t, access=foundation.ZCLAttributeAccess.Read | foundation.ZCLAttributeAccess.Report)
    .tuya_attribute(dp_id=253, attribute_name='current_l2', type=t.uint32_t, access=foundation.ZCLAttributeAccess.Read | foundation.ZCLAttributeAccess.Report)
    .tuya_attribute(dp_id=252, attribute_name='power_l2', type=t.int32s, access=foundation.ZCLAttributeAccess.Read | foundation.ZCLAttributeAccess.Report)
    .tuya_dp_multi(dp_id=7, attribute_mapping=[DPToAttributeMapping(ep_attribute=TuyaMCUCluster.ep_attribute, attribute_name='voltage_l2', converter=lambda x: _be(x, 0, 2)), DPToAttributeMapping(ep_attribute=TuyaMCUCluster.ep_attribute, attribute_name='current_l2', converter=lambda x: _be(x, 2, 3)), DPToAttributeMapping(ep_attribute=TuyaMCUCluster.ep_attribute, attribute_name='power_l2', converter=lambda x: _power_24(_be(x, 5, 3)))])
    .sensor(attribute_name='voltage_l2', cluster_id=TUYA_CLUSTER_ID, divisor=10, state_class=SensorStateClass.MEASUREMENT, device_class=SensorDeviceClass.VOLTAGE, unit=UnitOfElectricPotential.VOLT, entity_type=EntityType.STANDARD, translation_key='voltage_l2', fallback_name='Voltage L2')
    .sensor(attribute_name='current_l2', cluster_id=TUYA_CLUSTER_ID, divisor=1000, state_class=SensorStateClass.MEASUREMENT, device_class=SensorDeviceClass.CURRENT, unit=UnitOfElectricCurrent.AMPERE, entity_type=EntityType.STANDARD, translation_key='current_l2', fallback_name='Current L2')
    .sensor(attribute_name='power_l2', cluster_id=TUYA_CLUSTER_ID, state_class=SensorStateClass.MEASUREMENT, device_class=SensorDeviceClass.POWER, unit=UnitOfPower.WATT, entity_type=EntityType.STANDARD, translation_key='power_l2', fallback_name='Power L2')
    .tuya_sensor(dp_id=23, attribute_name='produced_energy', type=t.uint32_t, divisor=100, state_class=SensorStateClass.TOTAL_INCREASING, device_class=SensorDeviceClass.ENERGY, unit=UnitOfEnergy.KILO_WATT_HOUR, entity_type=EntityType.STANDARD, translation_key='produced_energy', fallback_name='Produced energy')
    .tuya_sensor(dp_id=29, attribute_name='power', type=t.uint32_t, state_class=SensorStateClass.MEASUREMENT, device_class=SensorDeviceClass.POWER, unit=UnitOfPower.WATT, entity_type=EntityType.STANDARD, fallback_name='Power')
    .tuya_sensor(dp_id=32, attribute_name='ac_frequency', type=t.uint32_t, divisor=100, state_class=SensorStateClass.MEASUREMENT, device_class=SensorDeviceClass.FREQUENCY, unit=UnitOfFrequency.HERTZ, entity_type=EntityType.STANDARD, translation_key='ac_frequency', fallback_name='AC frequency')
    .tuya_sensor(dp_id=50, attribute_name='power_factor', type=t.uint32_t, state_class=SensorStateClass.MEASUREMENT, unit=PERCENTAGE, entity_type=EntityType.STANDARD, translation_key='power_factor', fallback_name='Power factor')
    .tuya_sensor(dp_id=53, attribute_name='energy_l1', type=t.uint32_t, divisor=100, state_class=SensorStateClass.TOTAL_INCREASING, device_class=SensorDeviceClass.ENERGY, unit=UnitOfEnergy.KILO_WATT_HOUR, entity_type=EntityType.STANDARD, translation_key='energy_l1', fallback_name='Energy L1')
    .tuya_sensor(dp_id=54, attribute_name='energy_l2', type=t.uint32_t, divisor=100, state_class=SensorStateClass.TOTAL_INCREASING, device_class=SensorDeviceClass.ENERGY, unit=UnitOfEnergy.KILO_WATT_HOUR, entity_type=EntityType.STANDARD, translation_key='energy_l2', fallback_name='Energy L2')
    .tuya_sensor(dp_id=57, attribute_name='energy_produced_l1', type=t.uint32_t, divisor=100, state_class=SensorStateClass.TOTAL_INCREASING, device_class=SensorDeviceClass.ENERGY, unit=UnitOfEnergy.KILO_WATT_HOUR, entity_type=EntityType.STANDARD, translation_key='energy_produced_l1', fallback_name='Energy produced L1')
    .tuya_sensor(dp_id=58, attribute_name='energy_produced_l2', type=t.uint32_t, divisor=100, state_class=SensorStateClass.TOTAL_INCREASING, device_class=SensorDeviceClass.ENERGY, unit=UnitOfEnergy.KILO_WATT_HOUR, entity_type=EntityType.STANDARD, translation_key='energy_produced_l2', fallback_name='Energy produced L2')
    .tuya_switch(dp_id=101, attribute_name='device_locating', entity_type=EntityType.CONFIG, translation_key='device_locating', fallback_name='Device locating')
    .tuya_number(dp_id=102, type=t.uint32_t, attribute_name='update_frequency', min_value=5, max_value=3600, unit=UnitOfTime.SECONDS, device_class=NumberDeviceClass.DURATION, entity_type=EntityType.CONFIG, translation_key='update_frequency', fallback_name='Update frequency')
    .tuya_sensor(dp_id=108, attribute_name='power_factor_l1', type=t.uint32_t, state_class=SensorStateClass.MEASUREMENT, unit=PERCENTAGE, entity_type=EntityType.STANDARD, translation_key='power_factor_l1', fallback_name='Power factor L1')
    .tuya_sensor(dp_id=117, attribute_name='power_factor_l2', type=t.uint32_t, state_class=SensorStateClass.MEASUREMENT, unit=PERCENTAGE, entity_type=EntityType.STANDARD, translation_key='power_factor_l2', fallback_name='Power factor L2')
    .skip_configuration()
    .filter(no_builtin_quirk)
    .add_to_registry()
)
