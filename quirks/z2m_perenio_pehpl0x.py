"""Perenio PEHPL0X: Power link.

Generated from the Zigbee2MQTT definition.
Data: zigbee-herdsman-converters, MIT, Copyright (c) 2018 Koen Kanters.
Status: generated, not verified on hardware.
Revision: f5170e6f
"""

import functools
import logging
import pathlib

import zhaquirks
from zha.quirks import DEVICE_REGISTRY, DeviceMatch
import zigpy.types as t
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef

from zhaquirks.builder import (
    EntityType,
    QuirkBuilder,
    SIGNAL_STRENGTH_DECIBELS,
    SensorDeviceClass,
    SensorStateClass,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfPower,
)
from zhaquirks.clusters import CustomCluster


class PerenioSpecificCluster(CustomCluster):
    """perenioSpecific (z2m custom cluster)."""

    cluster_id = 0xFC7B

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        default_on_off_state = ZCLAttributeDef(id=0x0000, type=t.uint8_t, manufacturer_code=0x007B)
        alarms = ZCLAttributeDef(id=0x0001, type=t.bitmap8, manufacturer_code=0x007B)
        rms_current = ZCLAttributeDef(id=0x0002, type=t.uint16_t, access="r", manufacturer_code=0x007B)
        rms_voltage = ZCLAttributeDef(id=0x0003, type=t.uint16_t, access="r", manufacturer_code=0x007B)
        voltage_min = ZCLAttributeDef(id=0x0004, type=t.uint16_t, manufacturer_code=0x007B)
        voltage_max = ZCLAttributeDef(id=0x0005, type=t.uint16_t, manufacturer_code=0x007B)
        active_power = ZCLAttributeDef(id=0x000A, type=t.uint16_t, access="r", manufacturer_code=0x007B)
        power_max = ZCLAttributeDef(id=0x000B, type=t.uint16_t, manufacturer_code=0x007B)
        consumed_energy = ZCLAttributeDef(id=0x000E, type=t.uint32_t, access="r", manufacturer_code=0x007B)
        consumed_energy_limit = ZCLAttributeDef(id=0x000F, type=t.uint16_t, manufacturer_code=0x007B)
        rssi = ZCLAttributeDef(id=0x0018, type=t.int8s, access="r", manufacturer_code=0x007B)


class DefaultOnOffState(t.enum8):
    """default_on_off_state values (z2m)."""

    off = 0x00
    on = 0x01
    previous = 0x02



_LOGGER = logging.getLogger(__name__)
_SHIPPED = pathlib.Path(zhaquirks.__file__).resolve().parent
_STEPPED_BACK: set = set()

# The Zigbee fingerprints (manufacturer, model) this quirk is for; None matches any manufacturer.
FINGERPRINTS = [(None, 'PEHPL0X')]
# Names that a model-only fingerprint would catch but Zigbee2MQTT gives to other devices.
CLAIMED_ELSEWHERE = set()
# The endpoints this quirk needs, each with the input clusters it puts there where Zigbee2MQTT names none.
ENDPOINTS = {1: (0xFC7B,)}


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
    QuirkBuilder(None, 'PEHPL0X')
    .replaces(PerenioSpecificCluster)
    .enum(attribute_name=PerenioSpecificCluster.AttributeDefs.default_on_off_state.name, cluster_id=PerenioSpecificCluster.cluster_id, enum_class=DefaultOnOffState, entity_type=EntityType.STANDARD, translation_key='default_on_off_state', fallback_name='Default on off state')
    .sensor(attribute_name=PerenioSpecificCluster.AttributeDefs.rms_voltage.name, cluster_id=PerenioSpecificCluster.cluster_id, state_class=SensorStateClass.MEASUREMENT, device_class=SensorDeviceClass.VOLTAGE, unit=UnitOfElectricPotential.VOLT, entity_type=EntityType.STANDARD, translation_key='rms_voltage', fallback_name='Rms voltage')
    .sensor(attribute_name=PerenioSpecificCluster.AttributeDefs.active_power.name, cluster_id=PerenioSpecificCluster.cluster_id, state_class=SensorStateClass.MEASUREMENT, device_class=SensorDeviceClass.POWER, unit=UnitOfPower.WATT, entity_type=EntityType.STANDARD, translation_key='active_power', fallback_name='Active power')
    .sensor(attribute_name=PerenioSpecificCluster.AttributeDefs.consumed_energy.name, cluster_id=PerenioSpecificCluster.cluster_id, state_class=SensorStateClass.TOTAL_INCREASING, device_class=SensorDeviceClass.ENERGY, unit=UnitOfEnergy.WATT_HOUR, entity_type=EntityType.STANDARD, translation_key='consumed_energy', fallback_name='Consumed energy')
    .number(attribute_name=PerenioSpecificCluster.AttributeDefs.voltage_min.name, cluster_id=PerenioSpecificCluster.cluster_id, min_value=0, max_value=253, entity_type=EntityType.STANDARD, translation_key='voltage_min', fallback_name='Voltage min')
    .number(attribute_name=PerenioSpecificCluster.AttributeDefs.voltage_max.name, cluster_id=PerenioSpecificCluster.cluster_id, min_value=0, max_value=253, entity_type=EntityType.STANDARD, translation_key='voltage_max', fallback_name='Voltage max')
    .number(attribute_name=PerenioSpecificCluster.AttributeDefs.power_max.name, cluster_id=PerenioSpecificCluster.cluster_id, min_value=0, max_value=65534, entity_type=EntityType.STANDARD, translation_key='power_max', fallback_name='Power max')
    .number(attribute_name=PerenioSpecificCluster.AttributeDefs.consumed_energy_limit.name, cluster_id=PerenioSpecificCluster.cluster_id, min_value=0, max_value=65534, entity_type=EntityType.STANDARD, translation_key='consumed_energy_limit', fallback_name='Consumed energy limit')
    .sensor(attribute_name=PerenioSpecificCluster.AttributeDefs.rssi.name, cluster_id=PerenioSpecificCluster.cluster_id, state_class=SensorStateClass.MEASUREMENT, unit=SIGNAL_STRENGTH_DECIBELS, entity_type=EntityType.STANDARD, translation_key='rssi', fallback_name='Rssi')
    # switch: standard clusters, ZHA's own entities
    # alarm_voltage_min: z2m's own code, not generated
    # alarm_voltage_max: z2m's own code, not generated
    # alarm_power_max: z2m's own code, not generated
    # alarm_consumed_energy: z2m's own code, not generated
    .filter(no_builtin_quirk)
    .add_to_registry()
)
