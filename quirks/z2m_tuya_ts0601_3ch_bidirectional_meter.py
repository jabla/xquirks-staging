"""Tuya TS0601_3ch_bidirectional_meter: 3-channel bidirectional smart energy meter with relay.

Generated from the Zigbee2MQTT definition.
Data: zigbee-herdsman-converters, MIT, Copyright (c) 2018 Koen Kanters.
Status: generated, not verified on hardware.
Revision: d8d61a00
"""

import functools
import logging
import pathlib

import zhaquirks
from zha.quirks import DEVICE_REGISTRY, DeviceMatch
import zigpy.types as t

from zhaquirks.builder import (
    EntityType,
    NumberDeviceClass,
    PERCENTAGE,
    SensorDeviceClass,
    SensorStateClass,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfPower,
)
from zhaquirks.tuya.builder import TuyaQuirkBuilder



_LOGGER = logging.getLogger(__name__)
_SHIPPED = pathlib.Path(zhaquirks.__file__).resolve().parent
_STEPPED_BACK: set = set()

# The Zigbee fingerprints (manufacturer, model) this quirk is for; None matches any manufacturer.
FINGERPRINTS = [('_TZE20C1000000_p3g8xiug', 'TS0601')]
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
    .applies_to('_TZE20C1000000_p3g8xiug', 'TS0601')
    .tuya_onoff(dp_id=16)
    .tuya_sensor(dp_id=1, attribute_name='energy', type=t.uint32_t, divisor=100, state_class=SensorStateClass.TOTAL_INCREASING, device_class=SensorDeviceClass.ENERGY, unit=UnitOfEnergy.KILO_WATT_HOUR, entity_type=EntityType.STANDARD, fallback_name='Energy')
    .tuya_sensor(dp_id=2, attribute_name='produced_energy', type=t.uint32_t, divisor=100, state_class=SensorStateClass.TOTAL_INCREASING, device_class=SensorDeviceClass.ENERGY, unit=UnitOfEnergy.KILO_WATT_HOUR, entity_type=EntityType.STANDARD, translation_key='produced_energy', fallback_name='Produced energy')
    .tuya_sensor(dp_id=9, attribute_name='power', type=t.uint32_t, divisor=10, state_class=SensorStateClass.MEASUREMENT, device_class=SensorDeviceClass.POWER, unit=UnitOfPower.WATT, entity_type=EntityType.STANDARD, fallback_name='Power')
    .tuya_sensor(dp_id=101, attribute_name='voltage', type=t.uint32_t, divisor=10, state_class=SensorStateClass.MEASUREMENT, device_class=SensorDeviceClass.VOLTAGE, unit=UnitOfElectricPotential.VOLT, entity_type=EntityType.STANDARD, fallback_name='Voltage')
    .tuya_temperature(dp_id=131, scale=10)
    .tuya_sensor(dp_id=102, attribute_name='current_a', type=t.uint32_t, divisor=1000, state_class=SensorStateClass.MEASUREMENT, device_class=SensorDeviceClass.CURRENT, unit=UnitOfElectricCurrent.AMPERE, entity_type=EntityType.STANDARD, translation_key='current_a', fallback_name='Current a')
    .tuya_sensor(dp_id=105, attribute_name='power_a', type=t.uint32_t, divisor=10, state_class=SensorStateClass.MEASUREMENT, device_class=SensorDeviceClass.POWER, unit=UnitOfPower.WATT, entity_type=EntityType.STANDARD, translation_key='power_a', fallback_name='Power a')
    .tuya_sensor(dp_id=108, attribute_name='power_factor_a', type=t.uint32_t, divisor=100, state_class=SensorStateClass.MEASUREMENT, unit=PERCENTAGE, entity_type=EntityType.STANDARD, translation_key='power_factor_a', fallback_name='Power factor a')
    .tuya_sensor(dp_id=125, attribute_name='energy_a', type=t.uint32_t, divisor=100, state_class=SensorStateClass.TOTAL_INCREASING, device_class=SensorDeviceClass.ENERGY, unit=UnitOfEnergy.KILO_WATT_HOUR, entity_type=EntityType.STANDARD, translation_key='energy_a', fallback_name='Energy a')
    .tuya_sensor(dp_id=126, attribute_name='reverse_energy_a', type=t.uint32_t, divisor=100, state_class=SensorStateClass.TOTAL_INCREASING, device_class=SensorDeviceClass.ENERGY, unit=UnitOfEnergy.KILO_WATT_HOUR, entity_type=EntityType.STANDARD, translation_key='reverse_energy_a', fallback_name='Reverse energy a')
    .tuya_sensor(dp_id=103, attribute_name='current_b', type=t.uint32_t, divisor=1000, state_class=SensorStateClass.MEASUREMENT, device_class=SensorDeviceClass.CURRENT, unit=UnitOfElectricCurrent.AMPERE, entity_type=EntityType.STANDARD, translation_key='current_b', fallback_name='Current b')
    .tuya_sensor(dp_id=106, attribute_name='power_b', type=t.uint32_t, divisor=10, state_class=SensorStateClass.MEASUREMENT, device_class=SensorDeviceClass.POWER, unit=UnitOfPower.WATT, entity_type=EntityType.STANDARD, translation_key='power_b', fallback_name='Power b')
    .tuya_sensor(dp_id=109, attribute_name='power_factor_b', type=t.uint32_t, divisor=100, state_class=SensorStateClass.MEASUREMENT, unit=PERCENTAGE, entity_type=EntityType.STANDARD, translation_key='power_factor_b', fallback_name='Power factor b')
    .tuya_sensor(dp_id=127, attribute_name='energy_b', type=t.uint32_t, divisor=100, state_class=SensorStateClass.TOTAL_INCREASING, device_class=SensorDeviceClass.ENERGY, unit=UnitOfEnergy.KILO_WATT_HOUR, entity_type=EntityType.STANDARD, translation_key='energy_b', fallback_name='Energy b')
    .tuya_sensor(dp_id=128, attribute_name='reverse_energy_b', type=t.uint32_t, divisor=100, state_class=SensorStateClass.TOTAL_INCREASING, device_class=SensorDeviceClass.ENERGY, unit=UnitOfEnergy.KILO_WATT_HOUR, entity_type=EntityType.STANDARD, translation_key='reverse_energy_b', fallback_name='Reverse energy b')
    .tuya_sensor(dp_id=104, attribute_name='current_c', type=t.uint32_t, divisor=1000, state_class=SensorStateClass.MEASUREMENT, device_class=SensorDeviceClass.CURRENT, unit=UnitOfElectricCurrent.AMPERE, entity_type=EntityType.STANDARD, translation_key='current_c', fallback_name='Current c')
    .tuya_sensor(dp_id=107, attribute_name='power_c', type=t.uint32_t, divisor=10, state_class=SensorStateClass.MEASUREMENT, device_class=SensorDeviceClass.POWER, unit=UnitOfPower.WATT, entity_type=EntityType.STANDARD, translation_key='power_c', fallback_name='Power c')
    .tuya_sensor(dp_id=110, attribute_name='power_factor_c', type=t.uint32_t, divisor=100, state_class=SensorStateClass.MEASUREMENT, unit=PERCENTAGE, entity_type=EntityType.STANDARD, translation_key='power_factor_c', fallback_name='Power factor c')
    .tuya_sensor(dp_id=129, attribute_name='energy_c', type=t.uint32_t, divisor=100, state_class=SensorStateClass.TOTAL_INCREASING, device_class=SensorDeviceClass.ENERGY, unit=UnitOfEnergy.KILO_WATT_HOUR, entity_type=EntityType.STANDARD, translation_key='energy_c', fallback_name='Energy c')
    .tuya_sensor(dp_id=130, attribute_name='reverse_energy_c', type=t.uint32_t, divisor=100, state_class=SensorStateClass.TOTAL_INCREASING, device_class=SensorDeviceClass.ENERGY, unit=UnitOfEnergy.KILO_WATT_HOUR, entity_type=EntityType.STANDARD, translation_key='reverse_energy_c', fallback_name='Reverse energy c')
    .tuya_number(dp_id=111, type=t.uint32_t, attribute_name='power_setting_a', min_value=0, max_value=3680, unit=UnitOfPower.WATT, device_class=NumberDeviceClass.POWER, entity_type=EntityType.CONFIG, translation_key='power_setting_a', fallback_name='Power setting a')
    .tuya_number(dp_id=112, type=t.uint32_t, attribute_name='power_setting_b', min_value=0, max_value=3680, unit=UnitOfPower.WATT, device_class=NumberDeviceClass.POWER, entity_type=EntityType.CONFIG, translation_key='power_setting_b', fallback_name='Power setting b')
    .tuya_number(dp_id=113, type=t.uint32_t, attribute_name='power_setting_c', min_value=0, max_value=3680, unit=UnitOfPower.WATT, device_class=NumberDeviceClass.POWER, entity_type=EntityType.CONFIG, translation_key='power_setting_c', fallback_name='Power setting c')
    .tuya_binary_sensor(dp_id=114, attribute_name='power_alarm_a', entity_type=EntityType.STANDARD, translation_key='power_alarm_a', fallback_name='Power alarm a')
    .tuya_binary_sensor(dp_id=115, attribute_name='power_alarm_b', entity_type=EntityType.STANDARD, translation_key='power_alarm_b', fallback_name='Power alarm b')
    .tuya_binary_sensor(dp_id=116, attribute_name='power_alarm_c', entity_type=EntityType.STANDARD, translation_key='power_alarm_c', fallback_name='Power alarm c')
    .tuya_number(dp_id=132, type=t.uint32_t, attribute_name='voltage_calibration', min_value=0, max_value=260, unit=UnitOfElectricPotential.VOLT, device_class=NumberDeviceClass.VOLTAGE, entity_type=EntityType.CONFIG, translation_key='voltage_calibration', fallback_name='Voltage calibration')
    .tuya_number(dp_id=133, type=t.uint32_t, attribute_name='current_a_calibration', min_value=0, max_value=100000, unit=UnitOfElectricCurrent.MILLIAMPERE, device_class=NumberDeviceClass.CURRENT, entity_type=EntityType.CONFIG, translation_key='current_a_calibration', fallback_name='Current a calibration')
    .tuya_number(dp_id=134, type=t.uint32_t, attribute_name='current_b_calibration', min_value=0, max_value=100000, unit=UnitOfElectricCurrent.MILLIAMPERE, device_class=NumberDeviceClass.CURRENT, entity_type=EntityType.CONFIG, translation_key='current_b_calibration', fallback_name='Current b calibration')
    .tuya_number(dp_id=135, type=t.uint32_t, attribute_name='current_c_calibration', min_value=0, max_value=100000, unit=UnitOfElectricCurrent.MILLIAMPERE, device_class=NumberDeviceClass.CURRENT, entity_type=EntityType.CONFIG, translation_key='current_c_calibration', fallback_name='Current c calibration')
    .tuya_number(dp_id=136, type=t.uint32_t, attribute_name='power_a_calibration', min_value=0, max_value=3680, unit=UnitOfPower.WATT, device_class=NumberDeviceClass.POWER, entity_type=EntityType.CONFIG, translation_key='power_a_calibration', fallback_name='Power a calibration')
    .tuya_number(dp_id=137, type=t.uint32_t, attribute_name='power_b_calibration', min_value=0, max_value=3680, unit=UnitOfPower.WATT, device_class=NumberDeviceClass.POWER, entity_type=EntityType.CONFIG, translation_key='power_b_calibration', fallback_name='Power b calibration')
    .tuya_number(dp_id=138, type=t.uint32_t, attribute_name='power_c_calibration', min_value=0, max_value=3680, unit=UnitOfPower.WATT, device_class=NumberDeviceClass.POWER, entity_type=EntityType.CONFIG, translation_key='power_c_calibration', fallback_name='Power c calibration')
    .skip_configuration()
    .filter(no_builtin_quirk)
    .add_to_registry()
)
