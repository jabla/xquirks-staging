"""Sber SBDV-00202: Smart Wall Socket.

Generated from the Zigbee2MQTT definition.
Data: zigbee-herdsman-converters, MIT, Copyright (c) 2018 Koen Kanters.
Status: generated, not verified on hardware.
Revision: 1b845d6a
"""

import functools
import logging
import pathlib

import zhaquirks
from zha.quirks import DEVICE_REGISTRY, DeviceMatch
import zigpy.types as t
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef
from zigpy.zcl.clusters.homeautomation import Diagnostic

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


class EmergencyShutoffRecovery(t.enum8):
    """emergency_shutoff_recovery values (z2m)."""

    disabled = 0x00
    voltage_is_good = 0x01



_LOGGER = logging.getLogger(__name__)
_SHIPPED = pathlib.Path(zhaquirks.__file__).resolve().parent
_STEPPED_BACK: set = set()

# The Zigbee fingerprints (manufacturer, model) this quirk is for; None matches any manufacturer.
FINGERPRINTS = [('SDevices', 'SBDV-00202')]
# Names that a model-only fingerprint would catch but Zigbee2MQTT gives to other devices.
CLAIMED_ELSEWHERE = set()
# The endpoints this quirk needs, each with the input clusters it puts there where Zigbee2MQTT names none.
ENDPOINTS = {1: (0x0B05, 0xFCCF)}


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
    QuirkBuilder('SDevices', 'SBDV-00202')
    .replaces(ManuSpecificSDevicesCluster)
    .switch(attribute_name=ManuSpecificSDevicesCluster.AttributeDefs.child_lock.name, cluster_id=ManuSpecificSDevicesCluster.cluster_id, entity_type=EntityType.STANDARD, translation_key='child_lock', fallback_name='Child lock')
    .sensor(attribute_name=ManuSpecificSDevicesCluster.AttributeDefs.rms_voltage_mv.name, cluster_id=ManuSpecificSDevicesCluster.cluster_id, divisor=1000, state_class=SensorStateClass.MEASUREMENT, device_class=SensorDeviceClass.VOLTAGE, unit=UnitOfElectricPotential.VOLT, entity_type=EntityType.STANDARD, fallback_name='Voltage')
    .sensor(attribute_name=ManuSpecificSDevicesCluster.AttributeDefs.rms_current_ma.name, cluster_id=ManuSpecificSDevicesCluster.cluster_id, divisor=1000, state_class=SensorStateClass.MEASUREMENT, device_class=SensorDeviceClass.CURRENT, unit=UnitOfElectricCurrent.AMPERE, entity_type=EntityType.STANDARD, fallback_name='Current')
    .sensor(attribute_name=ManuSpecificSDevicesCluster.AttributeDefs.active_power_mw.name, cluster_id=ManuSpecificSDevicesCluster.cluster_id, divisor=1000, state_class=SensorStateClass.MEASUREMENT, device_class=SensorDeviceClass.POWER, unit=UnitOfPower.WATT, entity_type=EntityType.STANDARD, fallback_name='Power')
    .switch(attribute_name=ManuSpecificSDevicesCluster.AttributeDefs.led_indicator_on_enable.name, cluster_id=ManuSpecificSDevicesCluster.cluster_id, entity_type=EntityType.STANDARD, translation_key='led_indicator_on_enable', fallback_name='LED indication')
    .number(attribute_name=ManuSpecificSDevicesCluster.AttributeDefs.led_indicator_on_h.name, cluster_id=ManuSpecificSDevicesCluster.cluster_id, min_value=0, max_value=359, unit='°', entity_type=EntityType.STANDARD, translation_key='led_indicator_on_h', fallback_name='Hue')
    .number(attribute_name=ManuSpecificSDevicesCluster.AttributeDefs.led_indicator_on_s.name, cluster_id=ManuSpecificSDevicesCluster.cluster_id, min_value=0, max_value=254, entity_type=EntityType.STANDARD, translation_key='led_indicator_on_s', fallback_name='Saturation')
    .number(attribute_name=ManuSpecificSDevicesCluster.AttributeDefs.led_indicator_on_b.name, cluster_id=ManuSpecificSDevicesCluster.cluster_id, min_value=1, max_value=254, entity_type=EntityType.STANDARD, translation_key='led_indicator_on_b', fallback_name='Brightness')
    .switch(attribute_name=ManuSpecificSDevicesCluster.AttributeDefs.led_indicator_off_enable.name, cluster_id=ManuSpecificSDevicesCluster.cluster_id, entity_type=EntityType.STANDARD, translation_key='led_indicator_off_enable', fallback_name='LED indication')
    .number(attribute_name=ManuSpecificSDevicesCluster.AttributeDefs.led_indicator_off_h.name, cluster_id=ManuSpecificSDevicesCluster.cluster_id, min_value=0, max_value=359, unit='°', entity_type=EntityType.STANDARD, translation_key='led_indicator_off_h', fallback_name='Hue')
    .number(attribute_name=ManuSpecificSDevicesCluster.AttributeDefs.led_indicator_off_s.name, cluster_id=ManuSpecificSDevicesCluster.cluster_id, min_value=0, max_value=254, entity_type=EntityType.STANDARD, translation_key='led_indicator_off_s', fallback_name='Saturation')
    .number(attribute_name=ManuSpecificSDevicesCluster.AttributeDefs.led_indicator_off_b.name, cluster_id=ManuSpecificSDevicesCluster.cluster_id, min_value=1, max_value=254, entity_type=EntityType.STANDARD, translation_key='led_indicator_off_b', fallback_name='Brightness')
    .enum(attribute_name=ManuSpecificSDevicesCluster.AttributeDefs.emergency_shutoff_recovery.name, cluster_id=ManuSpecificSDevicesCluster.cluster_id, enum_class=EmergencyShutoffRecovery, entity_type=EntityType.STANDARD, translation_key='emergency_shutoff_recovery', fallback_name='Emergency shutoff recovery')
    .number(attribute_name=ManuSpecificSDevicesCluster.AttributeDefs.upper_voltage_threshold.name, cluster_id=ManuSpecificSDevicesCluster.cluster_id, min_value=230000, max_value=260000, step=1000, unit=UnitOfElectricPotential.MILLIVOLT, device_class=NumberDeviceClass.VOLTAGE, entity_type=EntityType.STANDARD, translation_key='upper_voltage_threshold', fallback_name='Upper voltage threshold')
    .number(attribute_name=ManuSpecificSDevicesCluster.AttributeDefs.lower_voltage_threshold.name, cluster_id=ManuSpecificSDevicesCluster.cluster_id, min_value=100000, max_value=230000, step=1000, unit=UnitOfElectricPotential.MILLIVOLT, device_class=NumberDeviceClass.VOLTAGE, entity_type=EntityType.STANDARD, translation_key='lower_voltage_threshold', fallback_name='Lower voltage threshold')
    .number(attribute_name=ManuSpecificSDevicesCluster.AttributeDefs.upper_current_threshold.name, cluster_id=ManuSpecificSDevicesCluster.cluster_id, min_value=100, max_value=16000, step=100, unit=UnitOfElectricCurrent.MILLIAMPERE, device_class=NumberDeviceClass.CURRENT, entity_type=EntityType.STANDARD, translation_key='upper_current_threshold', fallback_name='Upper current threshold')
    .number(attribute_name=ManuSpecificSDevicesCluster.AttributeDefs.upper_temp_threshold.name, cluster_id=ManuSpecificSDevicesCluster.cluster_id, min_value=-200, max_value=200, step=1, unit=UnitOfTemperature.CELSIUS, device_class=NumberDeviceClass.TEMPERATURE, entity_type=EntityType.STANDARD, translation_key='temperature_threshold', fallback_name='Temperature threshold')
    .sensor(attribute_name=Diagnostic.AttributeDefs.number_of_resets.name, cluster_id=Diagnostic.cluster_id, entity_type=EntityType.DIAGNOSTIC, translation_key='resets_count', fallback_name='Resets count')
    # device_temperature: standard clusters, ZHA's own entities
    # identify: standard clusters, ZHA's own entities
    # switch: standard clusters, ZHA's own entities
    # power_on_behavior: standard clusters, ZHA's own entities
    # serial_number: standard clusters, ZHA's own entities
    # emergency_overvoltage: z2m's own code, not generated
    # emergency_undervoltage: z2m's own code, not generated
    # emergency_overcurrent: z2m's own code, not generated
    # emergency_overheat: z2m's own code, not generated
    .filter(no_builtin_quirk)
    .add_to_registry()
)
