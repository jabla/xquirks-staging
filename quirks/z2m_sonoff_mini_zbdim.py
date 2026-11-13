"""SONOFF MINI-ZBDIM: Zigbee smart mini dimmer switch.

Generated from the Zigbee2MQTT definition.
Entity names follow zha-device-handlers#5165 (open pull request for this device).
Data: zigbee-herdsman-converters, MIT, Copyright (c) 2018 Koen Kanters.
Status: generated, not verified on hardware.
Revision: 46cf2992
"""

import functools
import logging
import pathlib

import zhaquirks
from zha.quirks import DEVICE_REGISTRY, DeviceMatch
import zigpy.types as t
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef

from zhaquirks.builder import (
    EntityPlatform,
    EntityType,
    NumberDeviceClass,
    PERCENTAGE,
    QuirkBuilder,
    SensorDeviceClass,
    SensorStateClass,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfPower,
    UnitOfTime,
)
from zhaquirks.clusters import CustomCluster


class CustomClusterEwelinkCluster(CustomCluster):
    """customClusterEwelink (z2m custom cluster)."""

    cluster_id = 0xFC11

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        network_led = ZCLAttributeDef(id=0x0001, type=t.Bool, manufacturer_code=None)
        back_light = ZCLAttributeDef(id=0x0002, type=t.Bool, manufacturer_code=None)
        fault_code = ZCLAttributeDef(id=0x0010, type=t.int32s, manufacturer_code=None)
        radio_power = ZCLAttributeDef(id=0x0012, type=t.int16s, manufacturer_code=None)
        radio_power_with_manu_code = ZCLAttributeDef(id=0x0012, type=t.int16s, manufacturer_code=0x1286)
        delayed_power_on_state = ZCLAttributeDef(id=0x0014, type=t.Bool, manufacturer_code=None)
        delayed_power_on_time = ZCLAttributeDef(id=0x0015, type=t.uint16_t, manufacturer_code=None)
        external_trigger_mode = ZCLAttributeDef(id=0x0016, type=t.uint8_t, manufacturer_code=None)
        detach_relay_mode = ZCLAttributeDef(id=0x0017, type=t.Bool, manufacturer_code=None)
        device_work_mode = ZCLAttributeDef(id=0x0018, type=t.uint8_t, manufacturer_code=None)
        detach_relay_mode2 = ZCLAttributeDef(id=0x0019, type=t.bitmap8, manufacturer_code=None)
        motor_travel_calibration_action = ZCLAttributeDef(id=0x5001, type=t.uint8_t, manufacturer_code=None)
        lack_water_close_valve_timeout = ZCLAttributeDef(id=0x5011, type=t.uint16_t, manufacturer_code=None)
        motor_travel_calibration_status = ZCLAttributeDef(id=0x5012, type=t.uint8_t, manufacturer_code=None)
        motor_run_status = ZCLAttributeDef(id=0x5013, type=t.uint8_t, manufacturer_code=None)
        accurrent_current_value = ZCLAttributeDef(id=0x7004, type=t.uint32_t, manufacturer_code=None)
        accurrent_voltage_value = ZCLAttributeDef(id=0x7005, type=t.uint32_t, manufacturer_code=None)
        accurrent_power_value = ZCLAttributeDef(id=0x7006, type=t.uint32_t, manufacturer_code=None)
        outlet_control_protect = ZCLAttributeDef(id=0x7007, type=t.uint8_t, manufacturer_code=None)
        energy_today = ZCLAttributeDef(id=0x7009, type=t.uint32_t, manufacturer_code=None)
        energy_month = ZCLAttributeDef(id=0x700A, type=t.uint32_t, manufacturer_code=None)
        energy_yesterday = ZCLAttributeDef(id=0x700B, type=t.uint32_t, manufacturer_code=None)
        set_calibration_action = ZCLAttributeDef(id=0x001D, type=t.CharacterString, manufacturer_code=None)
        calibration_status = ZCLAttributeDef(id=0x001E, type=t.uint8_t, manufacturer_code=None)
        calibration_progress = ZCLAttributeDef(id=0x0020, type=t.uint8_t, manufacturer_code=None)
        min_brightness_threshold = ZCLAttributeDef(id=0x4001, type=t.uint8_t, manufacturer_code=None)
        max_brightness_threshold = ZCLAttributeDef(id=0x4002, type=t.uint8_t, manufacturer_code=None)
        dimming_light_rate = ZCLAttributeDef(id=0x4003, type=t.uint8_t, manufacturer_code=None)
        transition_time = ZCLAttributeDef(id=0x001F, type=t.uint32_t, manufacturer_code=None)
        level_for_calibration = ZCLAttributeDef(id=0x4006, type=t.uint8_t, access="r", manufacturer_code=None)
        # programmable_stepper_sequence 0x0022: ARRAY, attribute only
        detach_relay_action_event = ZCLAttributeDef(id=0x0028, type=t.uint8_t, access="r", manufacturer_code=None)


class ExternalTriggerMode(t.enum8):
    """external_trigger_mode values (z2m)."""

    Edge = 0x00
    Pulse = 0x01
    Double_pulse = 0x03
    Triple_pulse = 0x04


class CalibrationStatus(t.enum8):
    """calibration_status values (z2m)."""

    UnCalibrate = 0x00
    Calibrating = 0x01
    CalibrationFailed = 0x02
    Calibrated = 0x03


class DimmingLightRate(t.enum8):
    """dimming_light_rate values (z2m)."""

    X1 = 0x01
    X2 = 0x02
    X3 = 0x03
    X4 = 0x04
    X5 = 0x05



_LOGGER = logging.getLogger(__name__)
_SHIPPED = pathlib.Path(zhaquirks.__file__).resolve().parent
_STEPPED_BACK: set = set()

# The Zigbee fingerprints (manufacturer, model) this quirk is for; None matches any manufacturer.
FINGERPRINTS = [(None, 'MINI-ZBDIM')]
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
    QuirkBuilder(None, 'MINI-ZBDIM')
    .replaces(CustomClusterEwelinkCluster)
    .sensor(attribute_name=CustomClusterEwelinkCluster.AttributeDefs.accurrent_current_value.name, cluster_id=CustomClusterEwelinkCluster.cluster_id, divisor=1000, state_class=SensorStateClass.MEASUREMENT, device_class=SensorDeviceClass.CURRENT, unit=UnitOfElectricCurrent.AMPERE, entity_type=EntityType.STANDARD, translation_key='accurrent_current_value', fallback_name='Current')
    .sensor(attribute_name=CustomClusterEwelinkCluster.AttributeDefs.accurrent_voltage_value.name, cluster_id=CustomClusterEwelinkCluster.cluster_id, divisor=1000, state_class=SensorStateClass.MEASUREMENT, device_class=SensorDeviceClass.VOLTAGE, unit=UnitOfElectricPotential.VOLT, entity_type=EntityType.STANDARD, translation_key='accurrent_voltage_value', fallback_name='Voltage')
    .sensor(attribute_name=CustomClusterEwelinkCluster.AttributeDefs.accurrent_power_value.name, cluster_id=CustomClusterEwelinkCluster.cluster_id, divisor=1000, state_class=SensorStateClass.MEASUREMENT, device_class=SensorDeviceClass.POWER, unit=UnitOfPower.WATT, entity_type=EntityType.STANDARD, translation_key='accurrent_power_value', fallback_name='Power')
    .switch(attribute_name=CustomClusterEwelinkCluster.AttributeDefs.delayed_power_on_state.name, cluster_id=CustomClusterEwelinkCluster.cluster_id, entity_type=EntityType.CONFIG, translation_key='delayed_power_on_state', fallback_name='Delayed power on state')
    .number(attribute_name=CustomClusterEwelinkCluster.AttributeDefs.delayed_power_on_time.name, cluster_id=CustomClusterEwelinkCluster.cluster_id, min_value=0.5, max_value=3599.5, step=0.5, unit=UnitOfTime.SECONDS, multiplier=0.5, device_class=NumberDeviceClass.DURATION, entity_type=EntityType.CONFIG, translation_key='delayed_power_on_time', fallback_name='Delayed power on time')
    .enum(attribute_name=CustomClusterEwelinkCluster.AttributeDefs.external_trigger_mode.name, cluster_id=CustomClusterEwelinkCluster.cluster_id, enum_class=ExternalTriggerMode, entity_type=EntityType.CONFIG, translation_key='external_trigger_mode', fallback_name='External trigger mode')
    .enum(attribute_name=CustomClusterEwelinkCluster.AttributeDefs.calibration_status.name, cluster_id=CustomClusterEwelinkCluster.cluster_id, enum_class=CalibrationStatus, entity_platform=EntityPlatform.SENSOR, entity_type=EntityType.DIAGNOSTIC, translation_key='calibration_status', fallback_name='Calibration status')
    .sensor(attribute_name=CustomClusterEwelinkCluster.AttributeDefs.calibration_progress.name, cluster_id=CustomClusterEwelinkCluster.cluster_id, state_class=SensorStateClass.MEASUREMENT, unit=PERCENTAGE, entity_type=EntityType.DIAGNOSTIC, translation_key='calibration_progress', fallback_name='Calibration progress')
    .number(attribute_name=CustomClusterEwelinkCluster.AttributeDefs.min_brightness_threshold.name, cluster_id=CustomClusterEwelinkCluster.cluster_id, min_value=1, max_value=99, step=1, unit=PERCENTAGE, multiplier=0.3921568627450981, entity_type=EntityType.CONFIG, translation_key='min_brightness_threshold', fallback_name='Min brightness threshold')
    .number(attribute_name=CustomClusterEwelinkCluster.AttributeDefs.max_brightness_threshold.name, cluster_id=CustomClusterEwelinkCluster.cluster_id, min_value=2, max_value=100, step=1, unit=PERCENTAGE, multiplier=0.3921568627450981, entity_type=EntityType.CONFIG, translation_key='max_brightness_threshold', fallback_name='Max brightness threshold')
    .sensor(attribute_name=CustomClusterEwelinkCluster.AttributeDefs.level_for_calibration.name, cluster_id=CustomClusterEwelinkCluster.cluster_id, attribute_converter=lambda x: x / 2.55, state_class=SensorStateClass.MEASUREMENT, unit=PERCENTAGE, entity_type=EntityType.DIAGNOSTIC, translation_key='level_for_calibration', fallback_name='Level for calibration')
    .number(attribute_name=CustomClusterEwelinkCluster.AttributeDefs.transition_time.name, cluster_id=CustomClusterEwelinkCluster.cluster_id, min_value=0, max_value=5, step=0.1, unit=UnitOfTime.SECONDS, multiplier=0.1, device_class=NumberDeviceClass.DURATION, entity_type=EntityType.CONFIG, translation_key='transition_time', fallback_name='Transition time')
    .enum(attribute_name=CustomClusterEwelinkCluster.AttributeDefs.dimming_light_rate.name, cluster_id=CustomClusterEwelinkCluster.cluster_id, enum_class=DimmingLightRate, entity_type=EntityType.CONFIG, translation_key='dimming_light_rate', fallback_name='Dimming light rate')
    # set_calibration_action: z2m enumLookup with own fromZigbee converter, not generated
    # light: standard clusters, ZHA's own entities
    # power_on_behavior: standard clusters, ZHA's own entities
    # inching_control_set: z2m's own code, not generated
    .filter(no_builtin_quirk)
    .add_to_registry()
)
