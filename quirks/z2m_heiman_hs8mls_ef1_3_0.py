"""Heiman HS8MLS-EF1-3.0: PIR sensor with night light.

Generated from the Zigbee2MQTT definition.
Data: zigbee-herdsman-converters, MIT, Copyright (c) 2018 Koen Kanters.
Status: generated, not verified on hardware.
Revision: 2adf5e87
"""

import functools
import logging
import pathlib

import zhaquirks
from zha.quirks import DEVICE_REGISTRY, DeviceMatch
import zigpy.types as t
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef
from zigpy.zcl.clusters.measurement import OccupancySensing

from zhaquirks.builder import (
    EntityType,
    QuirkBuilder,
)
from zhaquirks.clusters import CustomCluster


class HeimanClusterRadarCluster(CustomCluster):
    """heimanClusterRadar (z2m custom cluster)."""

    cluster_id = 0xFC8B

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        enable_indicator = ZCLAttributeDef(id=0xF001, type=t.uint8_t, manufacturer_code=0x120B)
        sensitivity = ZCLAttributeDef(id=0xF002, type=t.uint8_t, manufacturer_code=0x120B)
        enable_sub_region_isolation = ZCLAttributeDef(id=0xF006, type=t.uint8_t, manufacturer_code=0x120B)
        installation_method = ZCLAttributeDef(id=0xF007, type=t.uint8_t, manufacturer_code=0x120B)
        cell_mounted_table = ZCLAttributeDef(id=0xF008, type=t.LVBytes, manufacturer_code=0x120B)
        wall_mounted_table = ZCLAttributeDef(id=0xF009, type=t.LVBytes, manufacturer_code=0x120B)
        sub_region_isolation_table = ZCLAttributeDef(id=0xF00A, type=t.LVBytes, manufacturer_code=0x120B)


class Sensitivity(t.enum8):
    """sensitivity values (z2m)."""

    high = 0x00
    medium = 0x01
    low = 0x02



_LOGGER = logging.getLogger(__name__)
_SHIPPED = pathlib.Path(zhaquirks.__file__).resolve().parent
_STEPPED_BACK: set = set()

# The Zigbee fingerprints (manufacturer, model) this quirk is for; None matches any manufacturer.
FINGERPRINTS = [(None, 'HS8MIS-86-EF1-3.0')]
# Names that a model-only fingerprint would catch but Zigbee2MQTT gives to other devices.
CLAIMED_ELSEWHERE = set()
# The endpoints this quirk needs, each with the input clusters it puts there where Zigbee2MQTT names none.
ENDPOINTS = {1: (0x0406, 0xFC8B)}


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
    QuirkBuilder(None, 'HS8MIS-86-EF1-3.0')
    .replaces(HeimanClusterRadarCluster)
    .switch(attribute_name=HeimanClusterRadarCluster.AttributeDefs.enable_indicator.name, cluster_id=HeimanClusterRadarCluster.cluster_id, entity_type=EntityType.STANDARD, translation_key='enable_indicator', fallback_name='Enable indicator')
    .number(attribute_name=OccupancySensing.AttributeDefs.ultrasonic_o_to_u_delay.name, cluster_id=OccupancySensing.cluster_id, min_value=60, max_value=3600, entity_type=EntityType.STANDARD, translation_key='radar_delay_time', fallback_name='Radar delay time')
    .enum(attribute_name=HeimanClusterRadarCluster.AttributeDefs.sensitivity.name, cluster_id=HeimanClusterRadarCluster.cluster_id, enum_class=Sensitivity, entity_type=EntityType.STANDARD, translation_key='sensitivity', fallback_name='Sensitivity')
    # occupancy: standard clusters, ZHA's own entities
    # switch: standard clusters, ZHA's own entities
    # power_on_behavior: standard clusters, ZHA's own entities
    # ambient_light: standard clusters, ZHA's own entities
    .filter(no_builtin_quirk)
    .add_to_registry()
)
