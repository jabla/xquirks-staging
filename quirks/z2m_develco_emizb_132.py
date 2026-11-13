"""Develco EMIZB-132: Wattle AMS HAN power-meter sensor.

Generated from the Zigbee2MQTT definition.
Data: zigbee-herdsman-converters, MIT, Copyright (c) 2018 Koen Kanters.
Status: generated, not verified on hardware.
Revision: c078c9bb
"""

import functools
import logging
import pathlib

import zhaquirks
from zha.quirks import DEVICE_REGISTRY, DeviceMatch
import zigpy.types as t
from zigpy.zcl.foundation import ZCLAttributeDef
from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement
from zigpy.zcl.clusters.smartenergy import Metering

from zhaquirks.builder import (
    EntityType,
    QuirkBuilder,
    SensorStateClass,
)
from zhaquirks.clusters import CustomCluster


class SeMeteringCluster(CustomCluster, Metering):
    """Metering with the attributes z2m adds."""

    class AttributeDefs(Metering.AttributeDefs):
        """Attribute definitions."""

        develco_pulse_configuration = ZCLAttributeDef(id=0x0300, type=t.uint16_t, manufacturer_code=0x1015)
        develco_current_summation = ZCLAttributeDef(id=0x0301, type=t.uint48_t, manufacturer_code=0x1015)
        develco_interface_mode = ZCLAttributeDef(id=0x0302, type=t.enum16, manufacturer_code=0x1015)


class InterfaceMode(t.enum16):
    """interface_mode values (z2m)."""

    norwegian_han = 0x200
    norwegian_han_extra_load = 0x201
    aidon_meter = 0x202
    kaifa_and_kamstrup = 0x203



_LOGGER = logging.getLogger(__name__)
_SHIPPED = pathlib.Path(zhaquirks.__file__).resolve().parent
_STEPPED_BACK: set = set()

# The Zigbee fingerprints (manufacturer, model) this quirk is for; None matches any manufacturer.
FINGERPRINTS = [(None, 'EMIZB-132'), ('frient A/S', 'EMIZB-132')]
# Names that a model-only fingerprint would catch but Zigbee2MQTT gives to other devices.
CLAIMED_ELSEWHERE = set()
# The endpoints this quirk needs, each with the input clusters it puts there where Zigbee2MQTT names none.
ENDPOINTS = {2: (0x0702, 0x0B04)}


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

    Except for the exact names in FINGERPRINTS: ZHA's own quirk for them shows fewer features
    than this file (compared when the file was built), so this quirk stays for them.
    """
    if (device.manufacturer, device.model) in CLAIMED_ELSEWHERE:
        return False
    shipped = None if device.manufacturer is not None and (device.manufacturer, device.model) in FINGERPRINTS else _shipped_quirk(device)
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
    QuirkBuilder(None, 'EMIZB-132')
    .applies_to('frient A/S', 'EMIZB-132')
    .replaces(SeMeteringCluster, endpoint_id=2)
    .sensor(attribute_name=ElectricalMeasurement.AttributeDefs.total_reactive_power.name, cluster_id=ElectricalMeasurement.cluster_id, endpoint_id=2, state_class=SensorStateClass.MEASUREMENT, unit='VAr', entity_type=EntityType.STANDARD, translation_key='power_reactive', fallback_name='Power reactive')
    .enum(attribute_name=SeMeteringCluster.AttributeDefs.develco_interface_mode.name, cluster_id=SeMeteringCluster.cluster_id, endpoint_id=2, enum_class=InterfaceMode, entity_type=EntityType.CONFIG, translation_key='interface_mode', fallback_name='Interface mode')
    # power: standard clusters, ZHA's own entities
    # produced_energy: standard clusters, ZHA's own entities
    # voltage: standard clusters, ZHA's own entities
    # current: standard clusters, ZHA's own entities
    # energy: standard clusters, ZHA's own entities
    # voltage_phase_b: standard clusters, ZHA's own entities
    # voltage_phase_c: standard clusters, ZHA's own entities
    # current_phase_b: standard clusters, ZHA's own entities
    # current_phase_c: standard clusters, ZHA's own entities
    .filter(no_builtin_quirk)
    .add_to_registry()
)
