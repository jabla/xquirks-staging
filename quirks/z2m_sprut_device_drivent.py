"""Sprut.device Drivent: Drivent window drive.

Generated from the Zigbee2MQTT definition.
Data: zigbee-herdsman-converters, MIT, Copyright (c) 2018 Koen Kanters.
Status: generated, not verified on hardware.
Revision: 9bb357c7
"""

import functools
import logging
import pathlib

import zhaquirks
from zha.quirks import DEVICE_REGISTRY, DeviceMatch
import zigpy.types as t
from zigpy.zcl.foundation import BaseAttributeDefs, Direction, ZCLAttributeDef, ZCLCommandDef
from zigpy.zcl.clusters.closures import WindowCovering

from zhaquirks.builder import (
    EntityPlatform,
    EntityType,
    PERCENTAGE,
    QuirkBuilder,
)
from zhaquirks.clusters import CustomCluster


class ClosuresWindowCoveringCluster(CustomCluster, WindowCovering):
    """WindowCovering with the attributes z2m adds."""

    class AttributeDefs(WindowCovering.AttributeDefs):
        """Attribute definitions."""

        drive_state = ZCLAttributeDef(id=0x6609, type=t.uint8_t, access="r", manufacturer_code=0x6666)
        blocked_jam = ZCLAttributeDef(id=0x660A, type=t.Bool, access="r", manufacturer_code=0x6666)
        blocked_many = ZCLAttributeDef(id=0x660B, type=t.Bool, access="r", manufacturer_code=0x6666)
        speed = ZCLAttributeDef(id=0x6606, type=t.uint8_t, manufacturer_code=0x6666)
        calibrate = ZCLAttributeDef(id=0x6605, type=t.Bool, manufacturer_code=0x6666)

    class ServerCommandDefs(WindowCovering.ServerCommandDefs):
        """Command definitions (z2m's commands this cluster lacks)."""

        reset_block = ZCLCommandDef(id=0x03, schema={}, direction=Direction.Client_to_Server, manufacturer_code=0x6666)


class Manufacturer26112Cluster(CustomCluster):
    """26112 (z2m custom cluster)."""

    cluster_id = 0x6600

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        wifi = ZCLAttributeDef(id=0x6600, type=t.Bool, manufacturer_code=0x6666)


class DriveState(t.enum8):
    """drive_state values (z2m)."""

    closing = 0x00
    opening = 0x01
    stopped = 0x02



_LOGGER = logging.getLogger(__name__)
_SHIPPED = pathlib.Path(zhaquirks.__file__).resolve().parent
_STEPPED_BACK: set = set()

# The Zigbee fingerprints (manufacturer, model) this quirk is for; None matches any manufacturer.
FINGERPRINTS = [(None, 'Drivent')]
# Names that a model-only fingerprint would catch but Zigbee2MQTT gives to other devices.
CLAIMED_ELSEWHERE = set()
# The endpoints this quirk needs, each with the input clusters it puts there where Zigbee2MQTT names none.
ENDPOINTS = {1: (0x0102, 0x6600)}


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
    QuirkBuilder(None, 'Drivent')
    .replaces(Manufacturer26112Cluster)
    .replaces(ClosuresWindowCoveringCluster)
    .enum(attribute_name=ClosuresWindowCoveringCluster.AttributeDefs.drive_state.name, cluster_id=ClosuresWindowCoveringCluster.cluster_id, enum_class=DriveState, entity_platform=EntityPlatform.SENSOR, entity_type=EntityType.STANDARD, translation_key='drive_state', fallback_name='Drive state')
    .binary_sensor(attribute_name=ClosuresWindowCoveringCluster.AttributeDefs.blocked_jam.name, cluster_id=ClosuresWindowCoveringCluster.cluster_id, entity_type=EntityType.STANDARD, translation_key='blocked_jam', fallback_name='Blocked jam')
    .binary_sensor(attribute_name=ClosuresWindowCoveringCluster.AttributeDefs.blocked_many.name, cluster_id=ClosuresWindowCoveringCluster.cluster_id, entity_type=EntityType.STANDARD, translation_key='blocked_many', fallback_name='Blocked many')
    .number(attribute_name=ClosuresWindowCoveringCluster.AttributeDefs.speed.name, cluster_id=ClosuresWindowCoveringCluster.cluster_id, min_value=0, max_value=100, step=25, unit=PERCENTAGE, entity_type=EntityType.STANDARD, translation_key='speed', fallback_name='Speed')
    .switch(attribute_name=ClosuresWindowCoveringCluster.AttributeDefs.calibrate.name, cluster_id=ClosuresWindowCoveringCluster.cluster_id, entity_type=EntityType.STANDARD, translation_key='calibrate', fallback_name='Calibrate')
    .switch(attribute_name=Manufacturer26112Cluster.AttributeDefs.wifi.name, cluster_id=Manufacturer26112Cluster.cluster_id, entity_type=EntityType.STANDARD, translation_key='wifi', fallback_name='Wifi')
    .command_button(command_name=ClosuresWindowCoveringCluster.ServerCommandDefs.reset_block.name, cluster_id=ClosuresWindowCoveringCluster.cluster_id, entity_type=EntityType.STANDARD, translation_key='reset_block', fallback_name='Reset block', unique_id_suffix='reset_block')
    # open_limit: zigpy's down_close sends no manufacturer code, z2m sends 0x6666, not generated
    # close_limit: zigpy's stop sends no manufacturer code, z2m sends 0x6666, not generated
    # reset_limit: zigpy's up_open sends no manufacturer code, z2m sends 0x6666, not generated
    # cover: standard clusters, ZHA's own entities
    .filter(no_builtin_quirk)
    .add_to_registry()
)
