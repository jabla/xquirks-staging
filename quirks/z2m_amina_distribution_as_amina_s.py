"""Amina Distribution AS amina S: Amina S EV Charger.

Generated from the Zigbee2MQTT definition.
Data: zigbee-herdsman-converters, MIT, Copyright (c) 2018 Koen Kanters.
Status: generated, not verified on hardware.
Revision: 694b264f
"""

import functools
import logging
import pathlib

import zhaquirks
from zha.quirks import DEVICE_REGISTRY, DeviceMatch
import zigpy.types as t
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef
from zigpy.zcl.clusters.general import LevelControl

from zhaquirks.builder import (
    EntityType,
    NumberDeviceClass,
    QuirkBuilder,
    SensorDeviceClass,
    SensorStateClass,
    UnitOfElectricCurrent,
    UnitOfEnergy,
    UnitOfTime,
)
from zhaquirks.clusters import CustomCluster


class AminaControlClusterCluster(CustomCluster):
    """aminaControlCluster (z2m custom cluster)."""

    cluster_id = 0xFEE7

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        alarms = ZCLAttributeDef(id=0x0002, type=t.bitmap16, manufacturer_code=0x143B)
        ev_status = ZCLAttributeDef(id=0x0003, type=t.bitmap16, manufacturer_code=0x143B)
        connect_status = ZCLAttributeDef(id=0x0004, type=t.bitmap16, manufacturer_code=0x143B)
        single_phase = ZCLAttributeDef(id=0x0005, type=t.uint8_t, manufacturer_code=0x143B)
        offline_current = ZCLAttributeDef(id=0x0006, type=t.uint8_t, manufacturer_code=0x143B)
        offline_single_phase = ZCLAttributeDef(id=0x0007, type=t.uint8_t, manufacturer_code=0x143B)
        time_to_offline = ZCLAttributeDef(id=0x0008, type=t.uint16_t, manufacturer_code=0x143B)
        enable_offline = ZCLAttributeDef(id=0x0009, type=t.uint8_t, manufacturer_code=0x143B)
        total_active_energy = ZCLAttributeDef(id=0x0010, type=t.uint32_t, manufacturer_code=0x143B)
        last_session_energy = ZCLAttributeDef(id=0x0011, type=t.uint32_t, manufacturer_code=0x143B)



_LOGGER = logging.getLogger(__name__)
_SHIPPED = pathlib.Path(zhaquirks.__file__).resolve().parent
_STEPPED_BACK: set = set()

# The Zigbee fingerprints (manufacturer, model) this quirk is for; None matches any manufacturer.
FINGERPRINTS = [(None, 'amina S')]
# Names that a model-only fingerprint would catch but Zigbee2MQTT gives to other devices.
CLAIMED_ELSEWHERE = set()
# The endpoints this quirk needs, each with the input clusters it puts there where Zigbee2MQTT names none.
ENDPOINTS = {10: (0x0008, 0xFEE7)}


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
    QuirkBuilder(None, 'amina S')
    .replaces(AminaControlClusterCluster, endpoint_id=10)
    .number(attribute_name=LevelControl.AttributeDefs.current_level.name, cluster_id=LevelControl.cluster_id, endpoint_id=10, min_value=6, max_value=32, step=1, unit=UnitOfElectricCurrent.AMPERE, device_class=NumberDeviceClass.CURRENT, entity_type=EntityType.STANDARD, translation_key='charge_limit', fallback_name='Charge limit')
    .sensor(attribute_name=LevelControl.AttributeDefs.max_level.name, cluster_id=LevelControl.cluster_id, endpoint_id=10, state_class=SensorStateClass.MEASUREMENT, device_class=SensorDeviceClass.CURRENT, unit=UnitOfElectricCurrent.AMPERE, entity_type=EntityType.DIAGNOSTIC, translation_key='hardware_current_limit', fallback_name='Hardware current limit')
    .sensor(attribute_name=AminaControlClusterCluster.AttributeDefs.total_active_energy.name, cluster_id=AminaControlClusterCluster.cluster_id, endpoint_id=10, divisor=1000, state_class=SensorStateClass.TOTAL_INCREASING, device_class=SensorDeviceClass.ENERGY, unit=UnitOfEnergy.KILO_WATT_HOUR, entity_type=EntityType.STANDARD, translation_key='total_active_energy', fallback_name='Total active energy')
    .sensor(attribute_name=AminaControlClusterCluster.AttributeDefs.last_session_energy.name, cluster_id=AminaControlClusterCluster.cluster_id, endpoint_id=10, divisor=1000, state_class=SensorStateClass.TOTAL_INCREASING, device_class=SensorDeviceClass.ENERGY, unit=UnitOfEnergy.KILO_WATT_HOUR, entity_type=EntityType.STANDARD, translation_key='last_session_energy', fallback_name='Last session energy')
    .switch(attribute_name=AminaControlClusterCluster.AttributeDefs.single_phase.name, cluster_id=AminaControlClusterCluster.cluster_id, endpoint_id=10, entity_type=EntityType.CONFIG, translation_key='single_phase', fallback_name='Single phase')
    .switch(attribute_name=AminaControlClusterCluster.AttributeDefs.enable_offline.name, cluster_id=AminaControlClusterCluster.cluster_id, endpoint_id=10, entity_type=EntityType.CONFIG, translation_key='enable_offline', fallback_name='Enable offline')
    .number(attribute_name=AminaControlClusterCluster.AttributeDefs.time_to_offline.name, cluster_id=AminaControlClusterCluster.cluster_id, endpoint_id=10, min_value=0, max_value=60, step=1, unit=UnitOfTime.SECONDS, device_class=NumberDeviceClass.DURATION, entity_type=EntityType.CONFIG, translation_key='time_to_offline', fallback_name='Time to offline')
    .number(attribute_name=AminaControlClusterCluster.AttributeDefs.offline_current.name, cluster_id=AminaControlClusterCluster.cluster_id, endpoint_id=10, min_value=6, max_value=32, step=1, unit=UnitOfElectricCurrent.AMPERE, device_class=NumberDeviceClass.CURRENT, entity_type=EntityType.CONFIG, translation_key='offline_current', fallback_name='Offline current')
    .switch(attribute_name=AminaControlClusterCluster.AttributeDefs.offline_single_phase.name, cluster_id=AminaControlClusterCluster.cluster_id, endpoint_id=10, entity_type=EntityType.CONFIG, translation_key='offline_single_phase', fallback_name='Offline single phase')
    # total_active_power: standard clusters, ZHA's own entities
    # switch: standard clusters, ZHA's own entities
    # power: standard clusters, ZHA's own entities
    # voltage: standard clusters, ZHA's own entities
    # current: standard clusters, ZHA's own entities
    # ac_frequency: standard clusters, ZHA's own entities
    # power_phase_b: standard clusters, ZHA's own entities
    # power_phase_c: standard clusters, ZHA's own entities
    # voltage_phase_b: standard clusters, ZHA's own entities
    # voltage_phase_c: standard clusters, ZHA's own entities
    # current_phase_b: standard clusters, ZHA's own entities
    # current_phase_c: standard clusters, ZHA's own entities
    # ev_status: z2m's own code, not generated
    # alarms: z2m's own code, not generated
    # ev_connected: z2m's own code, not generated
    # charging: z2m's own code, not generated
    # derated: z2m's own code, not generated
    # alarm_active: z2m's own code, not generated
    # charge_limit_with_on_off: standard clusters or z2m's own code, not generated
    .filter(no_builtin_quirk)
    .add_to_registry()
)
