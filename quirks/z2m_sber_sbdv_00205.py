"""Sber SBDV-00205: Smart Thermostat.

Generated from the Zigbee2MQTT definition.
Data: zigbee-herdsman-converters, MIT, Copyright (c) 2018 Koen Kanters.
Status: generated, not verified on hardware.
Revision: 776edc2f
"""

import functools
import logging
import pathlib

import zhaquirks
from zha.quirks import DEVICE_REGISTRY, DeviceMatch
import zigpy.types as t
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef
from zigpy.zcl.clusters.homeautomation import Diagnostic
from zigpy.zcl.clusters.hvac import Thermostat
from zigpy.zcl.clusters.hvac import UserInterface

from zhaquirks.builder import (
    EntityType,
    NumberDeviceClass,
    QuirkBuilder,
    SensorDeviceClass,
    SensorStateClass,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfPower,
    UnitOfTemperature,
)
from zhaquirks.clusters import CustomCluster


class HvacThermostatCluster(CustomCluster, Thermostat):
    """Thermostat with the attributes z2m adds."""

    class AttributeDefs(Thermostat.AttributeDefs):
        """Attribute definitions."""

        sdevices_remote_temperature = ZCLAttributeDef(id=0x4001, type=t.int16s, manufacturer_code=0x152F)
        sdevices_remote_temperature_calibration = ZCLAttributeDef(id=0x4002, type=t.int8s, manufacturer_code=0x152F)
        sdevices_sensor_mode = ZCLAttributeDef(id=0x4003, type=t.enum8, manufacturer_code=0x152F)
        sdevices_heating_hysteresis = ZCLAttributeDef(id=0x4019, type=t.int8s, manufacturer_code=0x152F)
        sdevices_min_local_temperature_limit = ZCLAttributeDef(id=0x40F0, type=t.int16s, manufacturer_code=0x152F)
        sdevices_max_local_temperature_limit = ZCLAttributeDef(id=0x40F1, type=t.int16s, manufacturer_code=0x152F)
        sdevices_output_mode = ZCLAttributeDef(id=0x4100, type=t.enum8, manufacturer_code=0x152F)
        sdevices_local_sensor_type = ZCLAttributeDef(id=0x4101, type=t.enum8, manufacturer_code=0x152F)
        sdevices_sensor_error = ZCLAttributeDef(id=0x4102, type=t.bitmap16, access="r", manufacturer_code=0x152F)
        sdevices_event_status = ZCLAttributeDef(id=0x4103, type=t.bitmap16, access="r", manufacturer_code=0x152F)
        sdevices_remote_sensor_timeout = ZCLAttributeDef(id=0x4203, type=t.uint16_t, manufacturer_code=0x152F)


class HvacUserInterfaceCfgCluster(CustomCluster, UserInterface):
    """UserInterface with the attributes z2m adds."""

    class AttributeDefs(UserInterface.AttributeDefs):
        """Attribute definitions."""

        sdevices_brightness_operations_mode = ZCLAttributeDef(id=0x2001, type=t.uint16_t, manufacturer_code=0x152F)
        sdevices_brightness_steady_mode = ZCLAttributeDef(id=0x2002, type=t.uint16_t, manufacturer_code=0x152F)


class ManuSpecificSDevicesCluster(CustomCluster):
    """manuSpecificSDevices (z2m custom cluster)."""

    cluster_id = 0xFCCF

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        button_enable_multi_click = ZCLAttributeDef(id=0x1002, type=t.Bool, manufacturer_code=0x152F)
        child_lock = ZCLAttributeDef(id=0x1003, type=t.Bool, manufacturer_code=0x152F)
        led_indicator_on_enable = ZCLAttributeDef(id=0x2001, type=t.Bool, manufacturer_code=0x152F)
        led_indicator_on_h = ZCLAttributeDef(id=0x2002, type=t.uint16_t, manufacturer_code=0x152F)
        led_indicator_on_s = ZCLAttributeDef(id=0x2003, type=t.uint8_t, manufacturer_code=0x152F)
        led_indicator_on_b = ZCLAttributeDef(id=0x2004, type=t.uint8_t, manufacturer_code=0x152F)
        led_indicator_off_enable = ZCLAttributeDef(id=0x2005, type=t.Bool, manufacturer_code=0x152F)
        led_indicator_off_h = ZCLAttributeDef(id=0x2006, type=t.uint16_t, manufacturer_code=0x152F)
        led_indicator_off_s = ZCLAttributeDef(id=0x2007, type=t.uint8_t, manufacturer_code=0x152F)
        led_indicator_off_b = ZCLAttributeDef(id=0x2008, type=t.uint8_t, manufacturer_code=0x152F)
        led_indication_type = ZCLAttributeDef(id=0x2009, type=t.enum8, manufacturer_code=0x152F)
        emergency_shutoff_state = ZCLAttributeDef(id=0x3001, type=t.bitmap16, access="r", manufacturer_code=0x152F)
        emergency_shutoff_recovery = ZCLAttributeDef(id=0x3002, type=t.bitmap16, manufacturer_code=0x152F)
        upper_voltage_threshold = ZCLAttributeDef(id=0x3011, type=t.uint32_t, manufacturer_code=0x152F)
        lower_voltage_threshold = ZCLAttributeDef(id=0x3012, type=t.uint32_t, manufacturer_code=0x152F)
        upper_current_threshold = ZCLAttributeDef(id=0x3013, type=t.uint32_t, manufacturer_code=0x152F)
        upper_temp_threshold = ZCLAttributeDef(id=0x3014, type=t.int16s, manufacturer_code=0x152F)
        rms_voltage_mv = ZCLAttributeDef(id=0x4001, type=t.uint32_t, access="r", manufacturer_code=0x152F)
        rms_current_ma = ZCLAttributeDef(id=0x4002, type=t.uint32_t, access="r", manufacturer_code=0x152F)
        active_power_mw = ZCLAttributeDef(id=0x4003, type=t.int32s, access="r", manufacturer_code=0x152F)
        power_profile = ZCLAttributeDef(id=0x4100, type=t.enum8, manufacturer_code=0x152F)
        neutral_presence = ZCLAttributeDef(id=0x4101, type=t.enum8, manufacturer_code=0x152F)
        rtc_status = ZCLAttributeDef(id=0x5001, type=t.bitmap16, access="r", manufacturer_code=0x152F)


class SensorType(t.enum8):
    """sensor_type values (z2m)."""

    Type_4p7K = 0x00
    Type_6p8K = 0x01
    Type_10K = 0x02
    Type_12K = 0x03
    Type_15K = 0x04
    Type_33K = 0x05
    Type_47K = 0x06


class SensorMode(t.enum8):
    """sensor_mode values (z2m)."""

    local = 0x00
    remote = 0x01
    both = 0x02


class OutputMode(t.enum8):
    """output_mode values (z2m)."""

    normal = 0x00
    inverted = 0x01



_LOGGER = logging.getLogger(__name__)
_SHIPPED = pathlib.Path(zhaquirks.__file__).resolve().parent
_STEPPED_BACK: set = set()

# The Zigbee fingerprints (manufacturer, model) this quirk is for; None matches any manufacturer.
FINGERPRINTS = [('SDevices', 'SBDV-00205')]
# Names that a model-only fingerprint would catch but Zigbee2MQTT gives to other devices.
CLAIMED_ELSEWHERE = set()
# The endpoints this quirk needs, each with the input clusters it puts there where Zigbee2MQTT names none.
ENDPOINTS = {1: (0x0201, 0x0204, 0x0B05, 0xFCCF)}


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
    QuirkBuilder('SDevices', 'SBDV-00205')
    .replaces(ManuSpecificSDevicesCluster)
    .replaces(HvacUserInterfaceCfgCluster)
    .replaces(HvacThermostatCluster)
    .number(attribute_name=HvacThermostatCluster.AttributeDefs.sdevices_min_local_temperature_limit.name, cluster_id=HvacThermostatCluster.cluster_id, min_value=1, max_value=35, step=0.01, unit=UnitOfTemperature.CELSIUS, multiplier=0.01, device_class=NumberDeviceClass.TEMPERATURE, entity_type=EntityType.STANDARD, translation_key='min_local_temperature_limit', fallback_name='Min local temperature limit')
    .number(attribute_name=HvacThermostatCluster.AttributeDefs.sdevices_max_local_temperature_limit.name, cluster_id=HvacThermostatCluster.cluster_id, min_value=5, max_value=50, step=0.01, unit=UnitOfTemperature.CELSIUS, multiplier=0.01, device_class=NumberDeviceClass.TEMPERATURE, entity_type=EntityType.STANDARD, translation_key='max_local_temperature_limit', fallback_name='Max local temperature limit')
    .number(attribute_name=HvacThermostatCluster.AttributeDefs.sdevices_heating_hysteresis.name, cluster_id=HvacThermostatCluster.cluster_id, min_value=1, max_value=10, step=0.1, unit=UnitOfTemperature.CELSIUS, multiplier=0.1, device_class=NumberDeviceClass.TEMPERATURE_DELTA, entity_type=EntityType.STANDARD, translation_key='heating_hysteresis', fallback_name='Heating hysteresis')
    .sensor(attribute_name=ManuSpecificSDevicesCluster.AttributeDefs.rms_voltage_mv.name, cluster_id=ManuSpecificSDevicesCluster.cluster_id, divisor=1000, state_class=SensorStateClass.MEASUREMENT, device_class=SensorDeviceClass.VOLTAGE, unit=UnitOfElectricPotential.VOLT, entity_type=EntityType.STANDARD, fallback_name='Voltage')
    .sensor(attribute_name=ManuSpecificSDevicesCluster.AttributeDefs.rms_current_ma.name, cluster_id=ManuSpecificSDevicesCluster.cluster_id, divisor=1000, state_class=SensorStateClass.MEASUREMENT, device_class=SensorDeviceClass.CURRENT, unit=UnitOfElectricCurrent.AMPERE, entity_type=EntityType.STANDARD, fallback_name='Current')
    .sensor(attribute_name=ManuSpecificSDevicesCluster.AttributeDefs.active_power_mw.name, cluster_id=ManuSpecificSDevicesCluster.cluster_id, divisor=1000, state_class=SensorStateClass.MEASUREMENT, device_class=SensorDeviceClass.POWER, unit=UnitOfPower.WATT, entity_type=EntityType.STANDARD, fallback_name='Power')
    .number(attribute_name=ManuSpecificSDevicesCluster.AttributeDefs.upper_current_threshold.name, cluster_id=ManuSpecificSDevicesCluster.cluster_id, min_value=100, max_value=16000, step=100, unit=UnitOfElectricCurrent.MILLIAMPERE, device_class=NumberDeviceClass.CURRENT, entity_type=EntityType.STANDARD, translation_key='upper_current_threshold', fallback_name='Upper current threshold')
    .number(attribute_name=ManuSpecificSDevicesCluster.AttributeDefs.upper_temp_threshold.name, cluster_id=ManuSpecificSDevicesCluster.cluster_id, min_value=-200, max_value=200, step=1, unit=UnitOfTemperature.CELSIUS, device_class=NumberDeviceClass.TEMPERATURE, entity_type=EntityType.STANDARD, translation_key='temperature_threshold', fallback_name='Temperature threshold')
    .enum(attribute_name=HvacThermostatCluster.AttributeDefs.sdevices_local_sensor_type.name, cluster_id=HvacThermostatCluster.cluster_id, enum_class=SensorType, entity_type=EntityType.STANDARD, translation_key='z2m_sensor_type', fallback_name='Sensor type')
    .enum(attribute_name=HvacThermostatCluster.AttributeDefs.sdevices_sensor_mode.name, cluster_id=HvacThermostatCluster.cluster_id, enum_class=SensorMode, entity_type=EntityType.STANDARD, translation_key='sensor_mode', fallback_name='Sensor mode')
    .number(attribute_name=HvacThermostatCluster.AttributeDefs.sdevices_remote_temperature.name, cluster_id=HvacThermostatCluster.cluster_id, min_value=-273.15, max_value=327.67, step=0.01, unit=UnitOfTemperature.CELSIUS, multiplier=0.01, device_class=NumberDeviceClass.TEMPERATURE, entity_type=EntityType.STANDARD, translation_key='remote_temperature', fallback_name='Remote temperature')
    .number(attribute_name=HvacThermostatCluster.AttributeDefs.sdevices_remote_temperature_calibration.name, cluster_id=HvacThermostatCluster.cluster_id, min_value=-12.8, max_value=12.7, step=0.1, unit=UnitOfTemperature.CELSIUS, multiplier=0.1, device_class=NumberDeviceClass.TEMPERATURE_DELTA, entity_type=EntityType.STANDARD, translation_key='remote_temperature_calibration', fallback_name='Remote temperature calibration')
    .number(attribute_name=HvacThermostatCluster.AttributeDefs.sdevices_remote_sensor_timeout.name, cluster_id=HvacThermostatCluster.cluster_id, min_value=1, max_value=65535, entity_type=EntityType.STANDARD, translation_key='remote_sensor_timeout', fallback_name='Remote sensor timeout')
    .enum(attribute_name=HvacThermostatCluster.AttributeDefs.sdevices_output_mode.name, cluster_id=HvacThermostatCluster.cluster_id, enum_class=OutputMode, entity_type=EntityType.STANDARD, translation_key='output_mode', fallback_name='Output mode')
    .number(attribute_name=HvacUserInterfaceCfgCluster.AttributeDefs.sdevices_brightness_operations_mode.name, cluster_id=HvacUserInterfaceCfgCluster.cluster_id, min_value=0, max_value=1000, entity_type=EntityType.STANDARD, translation_key='brightness_operations_mode', fallback_name='Brightness operations mode')
    .number(attribute_name=HvacUserInterfaceCfgCluster.AttributeDefs.sdevices_brightness_steady_mode.name, cluster_id=HvacUserInterfaceCfgCluster.cluster_id, min_value=0, max_value=1000, entity_type=EntityType.STANDARD, translation_key='brightness_steady_mode', fallback_name='Brightness steady mode')
    .sensor(attribute_name=Diagnostic.AttributeDefs.number_of_resets.name, cluster_id=Diagnostic.cluster_id, entity_type=EntityType.DIAGNOSTIC, translation_key='resets_count', fallback_name='Resets count')
    # device_temperature: standard clusters, ZHA's own entities
    # weekly_schedule: standard clusters or z2m's own code, not generated
    # temperature: standard clusters, ZHA's own entities
    # identify: standard clusters, ZHA's own entities
    # rtc_status: z2m's own code, not generated
    # serial_number: standard clusters, ZHA's own entities
    # emergency_overcurrent: z2m's own code, not generated
    # emergency_overheat: z2m's own code, not generated
    # emergency_no_load: z2m's own code, not generated
    # sensor_error_remote_disconnected: z2m's own code, not generated
    # sensor_error_local_disconnected: z2m's own code, not generated
    # sensor_error_short_circuit: z2m's own code, not generated
    # status_heat_inefficient: z2m's own code, not generated
    # status_antifrost: z2m's own code, not generated
    # status_invalid_time: z2m's own code, not generated
    # keypad_lockout: standard clusters, ZHA's own entities
    # climate: standard clusters, ZHA's own entities
    # clear_weekly_schedule: standard clusters or z2m's own code, not generated
    # programming_operation_mode: standard cluster, no ZHA entity, not generated
    # abs_min_heat_setpoint_limit: standard cluster, no ZHA entity, not generated
    # abs_max_heat_setpoint_limit: standard cluster, no ZHA entity, not generated
    # min_heat_setpoint_limit: standard clusters, ZHA's own entities
    # max_heat_setpoint_limit: standard clusters, ZHA's own entities
    .filter(no_builtin_quirk)
    .add_to_registry()
)
