"""Lytko L101Ze-SLM: Single channel thermostat without display.

Generated from the Zigbee2MQTT definition.
Data: zigbee-herdsman-converters, MIT, Copyright (c) 2018 Koen Kanters.
Status: generated, not verified on hardware.
Revision: 4ca4c645
"""

import functools
import logging
import pathlib

import zhaquirks
from zha.quirks import DEVICE_REGISTRY, DeviceMatch
import zigpy.types as t
from zigpy.zcl.foundation import ZCLAttributeDef
from zigpy.zcl.clusters.hvac import Thermostat

from zhaquirks.builder import (
    EntityType,
    QuirkBuilder,
)
from zhaquirks.clusters import CustomCluster


class HvacThermostatCluster(CustomCluster, Thermostat):
    """Thermostat with the attributes z2m adds."""

    class AttributeDefs(Thermostat.AttributeDefs):
        """Attribute definitions."""

        lytko_sensor = ZCLAttributeDef(id=0xFF00, type=t.enum8, manufacturer_code=0x7777)
        lytko_target_first = ZCLAttributeDef(id=0xFF01, type=t.Bool, manufacturer_code=0x7777)
        sensor_type = ZCLAttributeDef(id=0x7700, type=t.enum8, manufacturer_code=0x7777)
        target_temp_first = ZCLAttributeDef(id=0x7701, type=t.Bool, manufacturer_code=0x7777)


class RemoteSensing(t.enum8):
    """remote_sensing values (z2m)."""

    internally = 0x00
    remotely = 0x01


class SensorType(t.enum8):
    """sensor_type values (z2m)."""

    Type_3_3K = 0x00
    Type_5_0K = 0x01
    Type_6_8K = 0x02
    Type_10_0K = 0x03
    Type_12_0K = 0x04
    Type_14_8K = 0x05
    Type_15_0K = 0x06
    Type_20_0K = 0x07
    Type_33_0K = 0x08
    Type_47_0K = 0x09



_LOGGER = logging.getLogger(__name__)
_SHIPPED = pathlib.Path(zhaquirks.__file__).resolve().parent
_STEPPED_BACK: set = set()

# The Zigbee fingerprints (manufacturer, model) this quirk is for; None matches any manufacturer.
FINGERPRINTS = [(None, 'L101Ze-SLM')]
# Names that a model-only fingerprint would catch but Zigbee2MQTT gives to other devices.
CLAIMED_ELSEWHERE = set()
# The endpoints this quirk needs, each with the input clusters it puts there where Zigbee2MQTT names none.
ENDPOINTS = {3: ()}


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
    QuirkBuilder(None, 'L101Ze-SLM')
    .replaces(HvacThermostatCluster, endpoint_id=3)
    .enum(attribute_name=HvacThermostatCluster.AttributeDefs.remote_sensing.name, cluster_id=HvacThermostatCluster.cluster_id, endpoint_id=3, enum_class=RemoteSensing, entity_type=EntityType.CONFIG, translation_key='remote_sensing', fallback_name='Remote sensing')
    .enum(attribute_name=HvacThermostatCluster.AttributeDefs.lytko_sensor.name, cluster_id=HvacThermostatCluster.cluster_id, endpoint_id=3, enum_class=SensorType, entity_type=EntityType.CONFIG, translation_key='z2m_sensor', fallback_name='Sensor')
    # occupied_setback: attribute occupiedSetback has no known type, not generated
    # power_apparent: standard clusters, ZHA's own entities
    # climate: standard clusters, ZHA's own entities
    # identify: standard clusters, ZHA's own entities
    # current_3: standard clusters, ZHA's own entities
    # energy_3: standard clusters, ZHA's own entities
    .filter(no_builtin_quirk)
    .add_to_registry()
)
