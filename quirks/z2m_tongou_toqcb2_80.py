"""Tongou TOQCB2-80: Smart circuit breaker.

Generated from the Zigbee2MQTT definition.
Data: zigbee-herdsman-converters, MIT, Copyright (c) 2018 Koen Kanters.
Status: generated, not verified on hardware.
Revision: 1913bbb0
"""

import functools
import logging
import pathlib

import zhaquirks
from zha.quirks import DEVICE_REGISTRY, DeviceMatch
import zigpy.types as t
from zigpy.zcl import foundation

from zhaquirks.builder import (
    EntityPlatform,
    EntityType,
    NumberDeviceClass,
    SensorDeviceClass,
    SensorStateClass,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfTemperature,
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


class OverVoltageSetting(t.enum8):
    """over_voltage_setting values (z2m)."""

    closed = 0x00
    alarm = 0x01
    trip = 0x02


class UnderVoltageSetting(t.enum8):
    """under_voltage_setting values (z2m)."""

    closed = 0x00
    alarm = 0x01
    trip = 0x02


class OverCurrentSetting(t.enum8):
    """over_current_setting values (z2m)."""

    closed = 0x00
    alarm = 0x01
    trip = 0x02


class OverPowerSetting(t.enum8):
    """over_power_setting values (z2m)."""

    closed = 0x00
    alarm = 0x01
    trip = 0x02


class TemperatureSetting(t.enum8):
    """temperature_setting values (z2m)."""

    closed = 0x00
    alarm = 0x01
    trip = 0x02


class LastEvent(t.enum8):
    """last_event values (z2m)."""

    normal = 0x00
    trip_over_current = 0x01
    trip_over_power = 0x02
    trip_over_temperature = 0x03
    trip_voltage_1 = 0x04
    trip_voltage_2 = 0x05
    alarm_over_current = 0x06
    alarm_over_power = 0x07
    alarm_over_temperature = 0x08
    alarm_voltage_1 = 0x09
    alarm_voltage_2 = 0x0A
    remote_on = 0x0B
    remote_off = 0x0C
    manual_on = 0x0D
    manual_off = 0x0E
    value_15 = 0x0F
    value_16 = 0x10
    factory_reset = 0x11



_LOGGER = logging.getLogger(__name__)
_SHIPPED = pathlib.Path(zhaquirks.__file__).resolve().parent
_STEPPED_BACK: set = set()

# The Zigbee fingerprints (manufacturer, model) this quirk is for; None matches any manufacturer.
FINGERPRINTS = [('_TZE284_q22avxbv', 'TS0601'), ('_TZE204_q22avxbv', 'TS0601'), ('_TZE204_mrffaamu', 'TS0601'), ('_TZE204_tzreobvu', 'TS0601'), ('_TZE284_mrffaamu', 'TS0601'), ('_TZE284_tzreobvu', 'TS0601'), ('_TZE284_9xstqowh', 'TS0601'), ('_TZE284_kv1nvirl', 'TS0601'), ('_TZE284_lyqazpe6', 'TS0601'), ('_TZE204_lyqazpe6', 'TS0601')]
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
    .applies_to('_TZE284_q22avxbv', 'TS0601')
    .applies_to('_TZE204_q22avxbv', 'TS0601')
    .applies_to('_TZE204_mrffaamu', 'TS0601')
    .applies_to('_TZE204_tzreobvu', 'TS0601')
    .applies_to('_TZE284_mrffaamu', 'TS0601')
    .applies_to('_TZE284_tzreobvu', 'TS0601')
    .applies_to('_TZE284_9xstqowh', 'TS0601')
    .applies_to('_TZE284_kv1nvirl', 'TS0601')
    .applies_to('_TZE284_lyqazpe6', 'TS0601')
    .applies_to('_TZE204_lyqazpe6', 'TS0601')
    .tuya_sensor(dp_id=1, attribute_name='energy', type=t.uint32_t, divisor=100, state_class=SensorStateClass.TOTAL_INCREASING, device_class=SensorDeviceClass.ENERGY, unit=UnitOfEnergy.KILO_WATT_HOUR, entity_type=EntityType.STANDARD, fallback_name='Energy')
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
    .tuya_onoff(dp_id=16)
    .tuya_enum(dp_id=102, attribute_name='over_voltage_setting', enum_class=OverVoltageSetting, entity_type=EntityType.CONFIG, translation_key='over_voltage_setting', fallback_name='Over voltage setting')
    .tuya_enum(dp_id=103, attribute_name='under_voltage_setting', enum_class=UnderVoltageSetting, entity_type=EntityType.CONFIG, translation_key='under_voltage_setting', fallback_name='Under voltage setting')
    .tuya_enum(dp_id=104, attribute_name='over_current_setting', enum_class=OverCurrentSetting, entity_type=EntityType.CONFIG, translation_key='over_current_setting', fallback_name='Over current setting')
    .tuya_enum(dp_id=105, attribute_name='over_power_setting', enum_class=OverPowerSetting, entity_type=EntityType.CONFIG, translation_key='over_power_setting', fallback_name='Over power setting')
    .tuya_enum(dp_id=107, attribute_name='temperature_setting', enum_class=TemperatureSetting, entity_type=EntityType.CONFIG, translation_key='temperature_setting', fallback_name='Temperature setting')
    .tuya_dp_attribute(dp_id=110, attribute_name='last_event', type=LastEvent, access=foundation.ZCLAttributeAccess.Read | foundation.ZCLAttributeAccess.Report, converter=lambda x: LastEvent(int(x)))
    .enum(attribute_name='last_event', enum_class=LastEvent, cluster_id=TUYA_CLUSTER_ID, entity_platform=EntityPlatform.SENSOR, entity_type=EntityType.STANDARD, translation_key='last_event', fallback_name='Last event')
    .tuya_switch(dp_id=112, attribute_name='clear_fault', entity_type=EntityType.CONFIG, translation_key='clear_fault', fallback_name='Clear fault')
    .tuya_switch(dp_id=113, attribute_name='factory_reset', entity_type=EntityType.CONFIG, translation_key='factory_reset', fallback_name='Factory reset')
    .tuya_number(dp_id=114, type=t.uint32_t, attribute_name='current_threshold', min_value=1, max_value=63, step=1, unit=UnitOfElectricCurrent.AMPERE, device_class=NumberDeviceClass.CURRENT, entity_type=EntityType.CONFIG, translation_key='current_threshold', fallback_name='Current threshold')
    .tuya_number(dp_id=115, type=t.uint32_t, attribute_name='over_voltage_threshold', min_value=245, max_value=295, step=1, unit=UnitOfElectricPotential.VOLT, device_class=NumberDeviceClass.VOLTAGE, entity_type=EntityType.CONFIG, translation_key='over_voltage_threshold', fallback_name='Over voltage threshold')
    .tuya_number(dp_id=116, type=t.uint32_t, attribute_name='under_voltage_threshold', min_value=145, max_value=220, step=1, unit=UnitOfElectricPotential.VOLT, device_class=NumberDeviceClass.VOLTAGE, entity_type=EntityType.CONFIG, translation_key='under_voltage_threshold', fallback_name='Under voltage threshold')
    .tuya_number(dp_id=118, type=t.int32s, attribute_name='temperature_threshold', min_value=-40, max_value=100, step=1, unit=UnitOfTemperature.CELSIUS, multiplier=0.1, device_class=NumberDeviceClass.TEMPERATURE, entity_type=EntityType.CONFIG, translation_key='temperature_threshold', fallback_name='Temperature threshold')
    .tuya_number(dp_id=119, type=t.uint32_t, attribute_name='over_power_threshold', min_value=200, max_value=20000, step=100, unit=UnitOfPower.WATT, device_class=NumberDeviceClass.POWER, entity_type=EntityType.CONFIG, translation_key='over_power_threshold', fallback_name='Over power threshold')
    .tuya_temperature(dp_id=131, scale=10)
    # DP 3: z2m reads nothing from it
    # DP 4: z2m reads nothing from it
    .skip_configuration()
    .filter(no_builtin_quirk)
    .add_to_registry()
)
