"""OWON FDS315: Fall Detection Sensor.

Generated from the Zigbee2MQTT definition.
Data: zigbee-herdsman-converters, MIT, Copyright (c) 2018 Koen Kanters.
Status: generated, not verified on hardware.
Revision: 6d4dc3af
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
    QuirkBuilder,
    SensorDeviceClass,
    SensorStateClass,
    UnitOfLength,
)
from zhaquirks.clusters import CustomCluster


class FallDetectionOwonCluster(CustomCluster):
    """fallDetectionOwon (z2m custom cluster)."""

    cluster_id = 0xFD00

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        status = ZCLAttributeDef(id=0x0000, type=t.enum8, access="r", manufacturer_code=0x113C)
        breathing_rate = ZCLAttributeDef(id=0x0002, type=t.uint8_t, access="r", manufacturer_code=0x113C)
        location_x = ZCLAttributeDef(id=0x0003, type=t.int16s, access="r", manufacturer_code=0x113C)
        location_y = ZCLAttributeDef(id=0x0004, type=t.int16s, access="r", manufacturer_code=0x113C)
        bed_upper_left_x = ZCLAttributeDef(id=0x0100, type=t.int16s, access="r", manufacturer_code=0x113C)
        bed_upper_left_y = ZCLAttributeDef(id=0x0101, type=t.int16s, access="r", manufacturer_code=0x113C)
        bed_lower_right_x = ZCLAttributeDef(id=0x0102, type=t.int16s, access="r", manufacturer_code=0x113C)
        bed_lower_right_y = ZCLAttributeDef(id=0x0103, type=t.int16s, access="r", manufacturer_code=0x113C)
        door_center_x = ZCLAttributeDef(id=0x0108, type=t.int16s, access="r", manufacturer_code=0x113C)
        door_center_y = ZCLAttributeDef(id=0x0109, type=t.int16s, access="r", manufacturer_code=0x113C)
        left_fall_detection_range = ZCLAttributeDef(id=0x010C, type=t.uint16_t, access="r", manufacturer_code=0x113C)
        right_fall_detection_range = ZCLAttributeDef(id=0x010D, type=t.uint16_t, access="r", manufacturer_code=0x113C)
        front_fall_detection_range = ZCLAttributeDef(id=0x010E, type=t.uint16_t, access="r", manufacturer_code=0x113C)


class Status(t.enum8):
    """status values (z2m)."""

    unoccupied = 0x00
    occupied = 0x01
    sitting = 0x02
    on_the_bed = 0x03
    low_posture = 0x04
    falling = 0x05



_LOGGER = logging.getLogger(__name__)
_SHIPPED = pathlib.Path(zhaquirks.__file__).resolve().parent
_STEPPED_BACK: set = set()

# The Zigbee fingerprints (manufacturer, model) this quirk is for; None matches any manufacturer.
FINGERPRINTS = [(None, 'FDS315'), (None, 'FDS315-AH')]
# Names that a model-only fingerprint would catch but Zigbee2MQTT gives to other devices.
CLAIMED_ELSEWHERE = set()
# The endpoints this quirk needs, each with the input clusters it puts there where Zigbee2MQTT names none.
ENDPOINTS = {1: (0xFD00,)}


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
    QuirkBuilder(None, 'FDS315')
    .applies_to(None, 'FDS315-AH')
    .replaces(FallDetectionOwonCluster)
    .enum(attribute_name=FallDetectionOwonCluster.AttributeDefs.status.name, cluster_id=FallDetectionOwonCluster.cluster_id, enum_class=Status, entity_platform=EntityPlatform.SENSOR, entity_type=EntityType.STANDARD, translation_key='status', fallback_name='Status')
    .sensor(attribute_name=FallDetectionOwonCluster.AttributeDefs.breathing_rate.name, cluster_id=FallDetectionOwonCluster.cluster_id, state_class=SensorStateClass.MEASUREMENT, unit='breaths/min', entity_type=EntityType.STANDARD, translation_key='breathing_rate', fallback_name='Breathing rate')
    .sensor(attribute_name=FallDetectionOwonCluster.AttributeDefs.location_x.name, cluster_id=FallDetectionOwonCluster.cluster_id, state_class=SensorStateClass.MEASUREMENT, device_class=SensorDeviceClass.DISTANCE, unit=UnitOfLength.CENTIMETERS, entity_type=EntityType.STANDARD, translation_key='location_x', fallback_name='Location x')
    .sensor(attribute_name=FallDetectionOwonCluster.AttributeDefs.location_y.name, cluster_id=FallDetectionOwonCluster.cluster_id, state_class=SensorStateClass.MEASUREMENT, device_class=SensorDeviceClass.DISTANCE, unit=UnitOfLength.CENTIMETERS, entity_type=EntityType.STANDARD, translation_key='location_y', fallback_name='Location y')
    # fall_detection_settings: standard clusters or z2m's own code, not generated
    .filter(no_builtin_quirk)
    .add_to_registry()
)
