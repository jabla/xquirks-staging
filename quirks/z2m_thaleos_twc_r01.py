"""THALEOS TWC-R01: Smart thermostat for electric heater with pilot wire.

Generated from the Zigbee2MQTT definition.
Data: zigbee-herdsman-converters, MIT, Copyright (c) 2018 Koen Kanters.
Status: generated, not verified on hardware.
Revision: ba547454
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
    SensorDeviceClass,
    SensorStateClass,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfTemperature,
)
from zhaquirks.tuya.builder import TuyaQuirkBuilder


class PilotWireMode(t.enum8):
    """pilot_wire_mode values (z2m)."""

    comfort = 0x00
    eco = 0x01
    antifrost = 0x02
    off = 0x03
    comfort_1 = 0x04
    comfort_2 = 0x05



_LOGGER = logging.getLogger(__name__)
_SHIPPED = pathlib.Path(zhaquirks.__file__).resolve().parent
_STEPPED_BACK: set = set()

# The Zigbee fingerprints (manufacturer, model) this quirk is for; None matches any manufacturer.
FINGERPRINTS = [('_TZE204_ilzkxrav', 'TS0601')]
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
    .applies_to('_TZE204_ilzkxrav', 'TS0601')
    .tuya_enum(dp_id=2, attribute_name='pilot_wire_mode', enum_class=PilotWireMode, entity_type=EntityType.CONFIG, translation_key='pilot_wire_mode', fallback_name='Pilot wire mode')
    .tuya_sensor(dp_id=11, attribute_name='power', type=t.uint32_t, divisor=10, state_class=SensorStateClass.MEASUREMENT, device_class=SensorDeviceClass.POWER, unit=UnitOfPower.WATT, entity_type=EntityType.STANDARD, fallback_name='Power')
    .tuya_sensor(dp_id=16, attribute_name='local_temperature', type=t.uint32_t, divisor=10, state_class=SensorStateClass.MEASUREMENT, device_class=SensorDeviceClass.TEMPERATURE, unit=UnitOfTemperature.CELSIUS, entity_type=EntityType.STANDARD, translation_key='local_temperature', fallback_name='Local temperature')
    .tuya_number(dp_id=19, type=t.int32s, attribute_name='local_temperature_calibration', min_value=-8, max_value=8, step=0.5, unit=UnitOfTemperature.CELSIUS, device_class=NumberDeviceClass.TEMPERATURE_DELTA, entity_type=EntityType.CONFIG, translation_key='z2m_local_temperature_calibration', fallback_name='Local temperature calibration')
    .tuya_switch(dp_id=40, attribute_name='eco_mode', entity_type=EntityType.STANDARD, translation_key='eco_mode', fallback_name='Eco mode')
    .tuya_switch(dp_id=110, attribute_name='open_window', entity_type=EntityType.CONFIG, translation_key='open_window', fallback_name='Open window')
    .tuya_number(dp_id=111, type=t.uint32_t, attribute_name='open_window_temperature', min_value=0, max_value=35, unit=UnitOfTemperature.CELSIUS, device_class=NumberDeviceClass.TEMPERATURE, entity_type=EntityType.CONFIG, translation_key='open_window_temperature', fallback_name='Open window temperature')
    .tuya_switch(dp_id=114, attribute_name='device_mode_type', entity_type=EntityType.CONFIG, translation_key='device_mode_type', fallback_name='Device mode type')
    .tuya_sensor(dp_id=115, attribute_name='voltage', type=t.uint32_t, divisor=10, state_class=SensorStateClass.MEASUREMENT, device_class=SensorDeviceClass.VOLTAGE, unit=UnitOfElectricPotential.VOLT, entity_type=EntityType.STANDARD, fallback_name='Voltage')
    .tuya_sensor(dp_id=116, attribute_name='current', type=t.uint32_t, divisor=10, state_class=SensorStateClass.MEASUREMENT, device_class=SensorDeviceClass.CURRENT, unit=UnitOfElectricCurrent.AMPERE, entity_type=EntityType.STANDARD, fallback_name='Current')
    .tuya_sensor(dp_id=117, attribute_name='energy', type=t.uint32_t, divisor=10, state_class=SensorStateClass.TOTAL_INCREASING, device_class=SensorDeviceClass.ENERGY, unit=UnitOfEnergy.KILO_WATT_HOUR, entity_type=EntityType.STANDARD, fallback_name='Energy')
    .tuya_sensor(dp_id=119, attribute_name='energy_today', type=t.uint32_t, divisor=10, state_class=SensorStateClass.TOTAL_INCREASING, device_class=SensorDeviceClass.ENERGY, unit=UnitOfEnergy.KILO_WATT_HOUR, entity_type=EntityType.STANDARD, translation_key='energy_today', fallback_name='Energy today')
    .tuya_sensor(dp_id=120, attribute_name='energy_yesterday', type=t.uint32_t, divisor=10, state_class=SensorStateClass.TOTAL_INCREASING, device_class=SensorDeviceClass.ENERGY, unit=UnitOfEnergy.KILO_WATT_HOUR, entity_type=EntityType.STANDARD, translation_key='energy_yesterday', fallback_name='Energy yesterday')
    # DP 20 (fault): z2m exposes no entity for it, not generated
    # DP 101 (week_program): z2m exposes no entity for it, not generated
    # DP 102 (work_state): z2m exposes no entity for it, not generated
    # DP 103 (week_program_1): z2m exposes no entity for it, not generated
    # DP 104 (week_program_2): z2m exposes no entity for it, not generated
    # DP 105 (week_program_3): z2m exposes no entity for it, not generated
    # DP 106 (week_program_4): z2m exposes no entity for it, not generated
    # DP 107 (week_program_5): z2m exposes no entity for it, not generated
    # DP 108 (week_program_6): z2m exposes no entity for it, not generated
    # DP 109 (week_program_7): z2m exposes no entity for it, not generated
    # DP 112 (window_time): z2m exposes no entity for it, not generated
    # DP 113 (window_timeout): z2m exposes no entity for it, not generated
    .skip_configuration()
    .filter(no_builtin_quirk)
    .add_to_registry()
)
