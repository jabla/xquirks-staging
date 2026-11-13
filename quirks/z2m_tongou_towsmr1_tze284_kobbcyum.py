"""Tongou TOWSMR1: Single-phase multifunction RCBO (DIN Module).

Generated from the Zigbee2MQTT definition.
Data: zigbee-herdsman-converters, MIT, Copyright (c) 2018 Koen Kanters.
Status: generated, not verified on hardware.
Revision: 95654a1c
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


class Event(t.enum8):
    """event values (z2m)."""

    normal = 0x00
    over_current_trip = 0x01
    over_power_trip = 0x02
    high_temp_trip = 0x03
    over_voltage_trip = 0x04
    under_voltage_trip = 0x05
    over_current_alarm = 0x06
    over_power_alarm = 0x07
    high_temp_alarm = 0x08
    over_voltage_alarm = 0x09
    under_voltage_alarm = 0x0A
    remote_on = 0x0B
    remote_off = 0x0C
    manual_on = 0x0D
    manual_off = 0x0E
    leakage_trip = 0x0F
    leakage_alarm = 0x10
    restore_default = 0x11
    automatic_closing = 0x12
    electricity_shortage = 0x13
    electricity_shortage_alarm = 0x14
    timing_switch_on = 0x15
    timing_switch_off = 0x16


class OverVoltageSetting(t.enum8):
    """over_voltage_setting values (z2m)."""

    Ignore = 0x00
    Alarm = 0x01
    Trip = 0x02


class UnderVoltageSetting(t.enum8):
    """under_voltage_setting values (z2m)."""

    Ignore = 0x00
    Alarm = 0x01
    Trip = 0x02


class OverPowerSetting(t.enum8):
    """over_power_setting values (z2m)."""

    Ignore = 0x00
    Alarm = 0x01
    Trip = 0x02


class TemperatureSetting(t.enum8):
    """temperature_setting values (z2m)."""

    Ignore = 0x00
    Alarm = 0x01
    Trip = 0x02



_LOGGER = logging.getLogger(__name__)
_SHIPPED = pathlib.Path(zhaquirks.__file__).resolve().parent
_STEPPED_BACK: set = set()

# The Zigbee fingerprints (manufacturer, model) this quirk is for; None matches any manufacturer.
FINGERPRINTS = [('_TZE284_kobbcyum', 'TS0601'), ('_TZE284_hecsejsb', 'TS0601')]
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
    .applies_to('_TZE284_kobbcyum', 'TS0601')
    .applies_to('_TZE284_hecsejsb', 'TS0601')
    .tuya_sensor(dp_id=1, attribute_name='energy', type=t.uint32_t, divisor=100, state_class=SensorStateClass.TOTAL_INCREASING, device_class=SensorDeviceClass.ENERGY, unit=UnitOfEnergy.KILO_WATT_HOUR, entity_type=EntityType.STANDARD, fallback_name='Energy')
    .tuya_attribute(dp_id=6, attribute_name='voltage', type=t.uint32_t, access=foundation.ZCLAttributeAccess.Read | foundation.ZCLAttributeAccess.Report)
    .tuya_attribute(dp_id=255, attribute_name='current', type=t.uint32_t, access=foundation.ZCLAttributeAccess.Read | foundation.ZCLAttributeAccess.Report)
    .tuya_attribute(dp_id=254, attribute_name='power', type=t.uint32_t, access=foundation.ZCLAttributeAccess.Read | foundation.ZCLAttributeAccess.Report)
    .tuya_dp_multi(dp_id=6, attribute_mapping=[DPToAttributeMapping(ep_attribute=TuyaMCUCluster.ep_attribute, attribute_name='voltage', converter=lambda x: _be(x, 0, 2)), DPToAttributeMapping(ep_attribute=TuyaMCUCluster.ep_attribute, attribute_name='current', converter=lambda x: _be(x, 3, 2)), DPToAttributeMapping(ep_attribute=TuyaMCUCluster.ep_attribute, attribute_name='power', converter=lambda x: _be(x, 6, 2))])
    .sensor(attribute_name='voltage', cluster_id=TUYA_CLUSTER_ID, divisor=10, state_class=SensorStateClass.MEASUREMENT, device_class=SensorDeviceClass.VOLTAGE, unit=UnitOfElectricPotential.VOLT, entity_type=EntityType.STANDARD, fallback_name='Voltage')
    .sensor(attribute_name='current', cluster_id=TUYA_CLUSTER_ID, divisor=1000, state_class=SensorStateClass.MEASUREMENT, device_class=SensorDeviceClass.CURRENT, unit=UnitOfElectricCurrent.AMPERE, entity_type=EntityType.STANDARD, fallback_name='Current')
    .sensor(attribute_name='power', cluster_id=TUYA_CLUSTER_ID, state_class=SensorStateClass.MEASUREMENT, device_class=SensorDeviceClass.POWER, unit=UnitOfPower.WATT, entity_type=EntityType.STANDARD, fallback_name='Power')
    .tuya_onoff(dp_id=16)
    .tuya_dp_attribute(dp_id=110, attribute_name='event', type=Event, access=foundation.ZCLAttributeAccess.Read | foundation.ZCLAttributeAccess.Report, converter=lambda x: Event(int(x)))
    .enum(attribute_name='event', enum_class=Event, cluster_id=TUYA_CLUSTER_ID, entity_platform=EntityPlatform.SENSOR, entity_type=EntityType.STANDARD, translation_key='event', fallback_name='Event')
    .tuya_enum(dp_id=102, attribute_name='over_voltage_setting', enum_class=OverVoltageSetting, entity_type=EntityType.CONFIG, translation_key='over_voltage_setting', fallback_name='Over voltage setting')
    .tuya_enum(dp_id=103, attribute_name='under_voltage_setting', enum_class=UnderVoltageSetting, entity_type=EntityType.CONFIG, translation_key='under_voltage_setting', fallback_name='Under voltage setting')
    .tuya_enum(dp_id=105, attribute_name='over_power_setting', enum_class=OverPowerSetting, entity_type=EntityType.CONFIG, translation_key='over_power_setting', fallback_name='Over power setting')
    .tuya_enum(dp_id=107, attribute_name='temperature_setting', enum_class=TemperatureSetting, entity_type=EntityType.CONFIG, translation_key='temperature_setting', fallback_name='Temperature setting')
    .tuya_switch(dp_id=112, attribute_name='auto_reclosing', entity_type=EntityType.CONFIG, translation_key='auto_reclosing', fallback_name='Auto reclosing')
    .tuya_switch(dp_id=113, attribute_name='restore_default', entity_type=EntityType.CONFIG, translation_key='restore_default', fallback_name='Restore default')
    .tuya_number(dp_id=115, type=t.uint32_t, attribute_name='over_voltage_threshold', min_value=240, max_value=295, unit=UnitOfElectricPotential.VOLT, device_class=NumberDeviceClass.VOLTAGE, entity_type=EntityType.CONFIG, translation_key='over_voltage_threshold', fallback_name='Over voltage threshold')
    .tuya_number(dp_id=116, type=t.uint32_t, attribute_name='under_voltage_threshold', min_value=145, max_value=220, unit=UnitOfElectricPotential.VOLT, device_class=NumberDeviceClass.VOLTAGE, entity_type=EntityType.CONFIG, translation_key='under_voltage_threshold', fallback_name='Under voltage threshold')
    .tuya_number(dp_id=118, type=t.int32s, attribute_name='temperature_threshold', min_value=-25, max_value=100, unit=UnitOfTemperature.CELSIUS, multiplier=0.1, device_class=NumberDeviceClass.TEMPERATURE, entity_type=EntityType.CONFIG, translation_key='temperature_threshold', fallback_name='Temperature threshold')
    .tuya_number(dp_id=119, type=t.uint32_t, attribute_name='over_power_threshold', min_value=5, max_value=25000, step=10, unit=UnitOfPower.WATT, device_class=NumberDeviceClass.POWER, entity_type=EntityType.CONFIG, translation_key='over_power_threshold', fallback_name='Over power threshold')
    .tuya_temperature(dp_id=131, scale=10)
    .tuya_switch(dp_id=143, attribute_name='overcurrent_recloser', entity_type=EntityType.CONFIG, translation_key='overcurrent_recloser', fallback_name='Overcurrent recloser')
    .tuya_switch(dp_id=144, attribute_name='leakage_recloser', entity_type=EntityType.CONFIG, translation_key='leakage_recloser', fallback_name='Leakage recloser')
    .tuya_switch(dp_id=145, attribute_name='overpower_recloser', entity_type=EntityType.CONFIG, translation_key='overpower_recloser', fallback_name='Overpower recloser')
    # DP 15 (leakage_current): z2m exposes no entity for it, not generated
    # DP 104 (over_current_setting): z2m exposes no entity for it, not generated
    # DP 108 (leakage_setting): z2m exposes no entity for it, not generated
    # DP 114 (over_current_threshold): z2m exposes no entity for it, not generated
    # DP 117 (leakage_threshold): z2m exposes no entity for it, not generated
    .skip_configuration()
    .filter(no_builtin_quirk)
    .add_to_registry()
)
