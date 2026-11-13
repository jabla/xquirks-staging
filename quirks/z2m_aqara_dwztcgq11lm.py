"""Aqara DWZTCGQ11LM: Multi-state sensor P100.

Generated from the Zigbee2MQTT definition.
Data: zigbee-herdsman-converters, MIT, Copyright (c) 2018 Koen Kanters.
Status: generated, not verified on hardware.
Revision: 4edc7850
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
    QuirkBuilder,
    UnitOfTime,
)
from zhaquirks.xiaomi import XiaomiAqaraE1Cluster


class ManuSpecificLumiCluster(XiaomiAqaraE1Cluster):
    """manuSpecificLumi (z2m custom cluster) on zhaquirks' Xiaomi base."""

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        mode = ZCLAttributeDef(id=0x0009, type=t.uint8_t, manufacturer_code=0x115F)
        illuminance = ZCLAttributeDef(id=0x0112, type=t.uint32_t, manufacturer_code=0x115F)
        display_unit = ZCLAttributeDef(id=0x0114, type=t.uint8_t, manufacturer_code=0x115F)
        movement = ZCLAttributeDef(id=0x0118, type=t.uint8_t, access="r", manufacturer_code=0x115F)
        air_quality = ZCLAttributeDef(id=0x0129, type=t.uint8_t, manufacturer_code=0x115F)
        curtain_reverse = ZCLAttributeDef(id=0x0400, type=t.Bool, manufacturer_code=0x115F)
        curtain_hand_open = ZCLAttributeDef(id=0x0401, type=t.Bool, manufacturer_code=0x115F)
        curtain_calibrated = ZCLAttributeDef(id=0x0402, type=t.Bool, manufacturer_code=0x115F)
        device_mode = ZCLAttributeDef(id=0x0116, type=t.uint8_t, manufacturer_code=0x115F)
        door_window_type = ZCLAttributeDef(id=0x01EB, type=t.uint8_t, manufacturer_code=0x115F)
        sensitivity = ZCLAttributeDef(id=0x010C, type=t.uint8_t, manufacturer_code=0x115F)
        report_interval = ZCLAttributeDef(id=0x01EC, type=t.uint32_t, manufacturer_code=0x115F)
        orientation_detection = ZCLAttributeDef(id=0x01F0, type=t.Bool, manufacturer_code=0x115F)
        movement_detection = ZCLAttributeDef(id=0x01ED, type=t.Bool, manufacturer_code=0x115F)
        fall_detection = ZCLAttributeDef(id=0x01D8, type=t.Bool, manufacturer_code=0x115F)
        vibration_detection = ZCLAttributeDef(id=0x0107, type=t.Bool, manufacturer_code=0x115F)
        triple_tap_detection = ZCLAttributeDef(id=0x01EF, type=t.Bool, manufacturer_code=0x115F)
        orientation = ZCLAttributeDef(id=0x01F1, type=t.uint8_t, access="r", manufacturer_code=0x115F)
        device_posture = ZCLAttributeDef(id=0x01EE, type=t.uint8_t, access="r", manufacturer_code=0x115F)

    # The struct keys of zhaquirks' Xiaomi base and the endpoint cluster it writes each one to.
    STRUCT_TARGETS = {
        "battery_voltage_mV": "power",
        "battery_percentage": "power",
        "temperature_measurement": "temperature",
        "humidity_measurement": "humidity",
        "pressure_measurement": "pressure",
        "pressure_measurement_precision": "pressure",
        "power": "electrical_measurement",
        "voltage": "electrical_measurement",
        "consumption": "smartenergy_metering",
        "illuminance_measurement": "illuminance",
        "tvoc_measurement": "voc_level",
        "smoke": "ias_zone",
    }

    def _parse_aqara_attributes(self, value):
        """Only the struct values whose cluster the endpoint has: the base class stops at a missing one."""
        attributes = super()._parse_aqara_attributes(value)
        return {key: v for key, v in attributes.items() if key not in self.STRUCT_TARGETS or hasattr(self.endpoint, self.STRUCT_TARGETS[key])}


class DeviceMode(t.enum8):
    """device_mode values (z2m)."""

    door_window = 0x03
    object = 0x05


class DoorWindowType(t.enum8):
    """door_window_type values (z2m)."""

    casement_window = 0x01
    hopper_window = 0x02
    composite_window = 0x03
    hinged_door = 0x04


class Orientation(t.enum8):
    """orientation values (z2m)."""

    face_up = 0x01
    face_down = 0x02
    vertical = 0x03
    tilt = 0x04


class DevicePosture(t.enum8):
    """device_posture values (z2m)."""

    normal = 0x01
    abnormal = 0x02



_LOGGER = logging.getLogger(__name__)
_SHIPPED = pathlib.Path(zhaquirks.__file__).resolve().parent
_STEPPED_BACK: set = set()

# The Zigbee fingerprints (manufacturer, model) this quirk is for; None matches any manufacturer.
FINGERPRINTS = [(None, 'lumi.vibration.agl002')]
# Names that a model-only fingerprint would catch but Zigbee2MQTT gives to other devices.
CLAIMED_ELSEWHERE = set()
# The endpoints this quirk needs, each with the input clusters it puts there where Zigbee2MQTT names none.
ENDPOINTS = {1: (0xFCC0,)}


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
    QuirkBuilder(None, 'lumi.vibration.agl002')
    .replaces(ManuSpecificLumiCluster)
    .enum(attribute_name=ManuSpecificLumiCluster.AttributeDefs.device_mode.name, cluster_id=ManuSpecificLumiCluster.cluster_id, enum_class=DeviceMode, entity_type=EntityType.CONFIG, translation_key='device_mode', fallback_name='Device mode')
    .enum(attribute_name=ManuSpecificLumiCluster.AttributeDefs.door_window_type.name, cluster_id=ManuSpecificLumiCluster.cluster_id, enum_class=DoorWindowType, entity_type=EntityType.CONFIG, translation_key='door_window_type', fallback_name='Door/window type')
    .number(attribute_name=ManuSpecificLumiCluster.AttributeDefs.sensitivity.name, cluster_id=ManuSpecificLumiCluster.cluster_id, min_value=1, max_value=10, entity_type=EntityType.CONFIG, translation_key='sensitivity', fallback_name='Sensitivity')
    .number(attribute_name=ManuSpecificLumiCluster.AttributeDefs.report_interval.name, cluster_id=ManuSpecificLumiCluster.cluster_id, min_value=5, max_value=300, unit=UnitOfTime.SECONDS, device_class=NumberDeviceClass.DURATION, entity_type=EntityType.CONFIG, translation_key='report_interval', fallback_name='Report interval')
    .switch(attribute_name=ManuSpecificLumiCluster.AttributeDefs.orientation_detection.name, cluster_id=ManuSpecificLumiCluster.cluster_id, entity_type=EntityType.STANDARD, translation_key='orientation_detection', fallback_name='Orientation detection')
    .switch(attribute_name=ManuSpecificLumiCluster.AttributeDefs.movement_detection.name, cluster_id=ManuSpecificLumiCluster.cluster_id, entity_type=EntityType.STANDARD, translation_key='movement_detection', fallback_name='Movement detection')
    .switch(attribute_name=ManuSpecificLumiCluster.AttributeDefs.fall_detection.name, cluster_id=ManuSpecificLumiCluster.cluster_id, entity_type=EntityType.STANDARD, translation_key='fall_detection', fallback_name='Fall detection')
    .switch(attribute_name=ManuSpecificLumiCluster.AttributeDefs.vibration_detection.name, cluster_id=ManuSpecificLumiCluster.cluster_id, entity_type=EntityType.STANDARD, translation_key='vibration_detection', fallback_name='Vibration detection')
    .switch(attribute_name=ManuSpecificLumiCluster.AttributeDefs.triple_tap_detection.name, cluster_id=ManuSpecificLumiCluster.cluster_id, entity_type=EntityType.STANDARD, translation_key='triple_tap_detection', fallback_name='Triple tap detection')
    .enum(attribute_name=ManuSpecificLumiCluster.AttributeDefs.orientation.name, cluster_id=ManuSpecificLumiCluster.cluster_id, enum_class=Orientation, entity_platform=EntityPlatform.SENSOR, entity_type=EntityType.STANDARD, translation_key='orientation', fallback_name='Orientation')
    .enum(attribute_name=ManuSpecificLumiCluster.AttributeDefs.device_posture.name, cluster_id=ManuSpecificLumiCluster.cluster_id, enum_class=DevicePosture, entity_platform=EntityPlatform.SENSOR, entity_type=EntityType.DIAGNOSTIC, translation_key='device_posture', fallback_name='Device posture')
    # contact: standard clusters, ZHA's own entities
    # action: z2m actionEnumLookup (closuresDoorLock.85, not the multistate input present value), not generated
    # battery: z2m's own code, not generated
    # voltage: z2m's own code, not generated
    # identify: standard clusters, ZHA's own entities
    .filter(no_builtin_quirk)
    .add_to_registry()
)
