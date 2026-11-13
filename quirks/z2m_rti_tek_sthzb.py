"""Rti-Tek STHZB: Temperature and humidity sensor.

Generated from the Zigbee2MQTT definition.
Data: zigbee-herdsman-converters, MIT, Copyright (c) 2018 Koen Kanters.
Status: generated, not verified on hardware.
Revision: 633a0731
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
)
from zhaquirks.clusters import CustomCluster


class RtiTekFd22Cluster(CustomCluster):
    """rtiTekFd22 (z2m custom cluster)."""

    cluster_id = 0xFD22

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        temperature_unit = ZCLAttributeDef(id=0x0000, type=t.enum8, manufacturer_code=None)
        fault_code = ZCLAttributeDef(id=0x0002, type=t.uint32_t, access="r", manufacturer_code=None)
        product_name = ZCLAttributeDef(id=0x0003, type=t.CharacterString, access="r", manufacturer_code=None)
        internal_temperature_calibration = ZCLAttributeDef(id=0xE005, type=t.int8s, manufacturer_code=None)
        internal_humidity_calibration = ZCLAttributeDef(id=0xE006, type=t.int8s, manufacturer_code=None)
        sample_interval = ZCLAttributeDef(id=0xE009, type=t.uint16_t, manufacturer_code=None)
        temperature_alarm_upper = ZCLAttributeDef(id=0xE00A, type=t.int16s, manufacturer_code=None)
        temperature_alarm_lower = ZCLAttributeDef(id=0xE00B, type=t.int16s, manufacturer_code=None)
        humidity_alarm_upper = ZCLAttributeDef(id=0xE00C, type=t.uint16_t, manufacturer_code=None)
        humidity_alarm_lower = ZCLAttributeDef(id=0xE00D, type=t.uint16_t, manufacturer_code=None)
        temperature_alarm_status = ZCLAttributeDef(id=0xE00E, type=t.enum8, access="r", manufacturer_code=None)
        humidity_alarm_status = ZCLAttributeDef(id=0xE00F, type=t.enum8, access="r", manufacturer_code=None)
        sth2z_humidity_comfort_lower = ZCLAttributeDef(id=0xE014, type=t.uint16_t, manufacturer_code=None)
        sth2z_humidity_comfort_upper = ZCLAttributeDef(id=0xE015, type=t.uint16_t, manufacturer_code=None)
        sth2z_humidity_comfort_temperature_lower = ZCLAttributeDef(id=0xE016, type=t.int16s, manufacturer_code=None)
        sth2z_humidity_comfort_temperature_upper = ZCLAttributeDef(id=0xE017, type=t.int16s, manufacturer_code=None)


class TemperatureAlarmStatus(t.enum8):
    """temperature_alarm_status values (z2m)."""

    normal = 0x00
    low = 0x01
    high = 0x02


class HumidityAlarmStatus(t.enum8):
    """humidity_alarm_status values (z2m)."""

    normal = 0x00
    low = 0x01
    high = 0x02



_LOGGER = logging.getLogger(__name__)
_SHIPPED = pathlib.Path(zhaquirks.__file__).resolve().parent
_STEPPED_BACK: set = set()

# The Zigbee fingerprints (manufacturer, model) this quirk is for; None matches any manufacturer.
FINGERPRINTS = [(None, 'STHZB')]
# Names that a model-only fingerprint would catch but Zigbee2MQTT gives to other devices.
CLAIMED_ELSEWHERE = set()
# The endpoints this quirk needs, each with the input clusters it puts there where Zigbee2MQTT names none.
ENDPOINTS = {1: (0xFD22,)}


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
    QuirkBuilder(None, 'STHZB')
    .replaces(RtiTekFd22Cluster)
    .enum(attribute_name=RtiTekFd22Cluster.AttributeDefs.temperature_alarm_status.name, cluster_id=RtiTekFd22Cluster.cluster_id, enum_class=TemperatureAlarmStatus, entity_platform=EntityPlatform.SENSOR, entity_type=EntityType.DIAGNOSTIC, translation_key='temperature_alarm_status', fallback_name='Temperature alarm status')
    .enum(attribute_name=RtiTekFd22Cluster.AttributeDefs.humidity_alarm_status.name, cluster_id=RtiTekFd22Cluster.cluster_id, enum_class=HumidityAlarmStatus, entity_platform=EntityPlatform.SENSOR, entity_type=EntityType.DIAGNOSTIC, translation_key='humidity_alarm_status', fallback_name='Humidity alarm status')
    # humidity: standard clusters, ZHA's own entities
    # battery: standard clusters, ZHA's own entities
    # product_name: z2m's own code, not generated
    # temperature_unit: z2m's own code, not generated
    # fault_status: z2m's own code, not generated
    .filter(no_builtin_quirk)
    .add_to_registry()
)
