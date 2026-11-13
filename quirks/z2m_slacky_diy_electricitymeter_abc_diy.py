"""Slacky-DIY ElectricityMeter-ABC-DIY: Three phase Electricity Meter via optical port.

Generated from the Zigbee2MQTT definition.
Data: zigbee-herdsman-converters, MIT, Copyright (c) 2018 Koen Kanters.
Status: generated, not verified on hardware.
Revision: a5f6876e
"""

import functools
import logging
import pathlib

import zhaquirks
from zha.quirks import DEVICE_REGISTRY, DeviceMatch
import zigpy.types as t
from zigpy.zcl.foundation import ZCLAttributeDef
from zigpy.zcl.clusters.smartenergy import Metering

from zhaquirks.builder import (
    EntityType,
    PERCENTAGE,
    QuirkBuilder,
    SensorStateClass,
)
from zhaquirks.clusters import CustomCluster


class SeMeteringCluster(CustomCluster, Metering):
    """Metering with the attributes z2m adds."""

    class AttributeDefs(Metering.AttributeDefs):
        """Attribute definitions."""

        device_model = ZCLAttributeDef(id=0xF000, type=t.enum8, manufacturer_code=None)
        device_address = ZCLAttributeDef(id=0xF001, type=t.uint32_t, manufacturer_code=None)
        read_period = ZCLAttributeDef(id=0xF002, type=t.uint8_t, manufacturer_code=None)
        date_release = ZCLAttributeDef(id=0xF003, type=t.LVBytes, access="r", manufacturer_code=None)
        device_name = ZCLAttributeDef(id=0xF004, type=t.LVBytes, access="r", manufacturer_code=None)
        device_password = ZCLAttributeDef(id=0xF005, type=t.LVBytes, manufacturer_code=None)


class DeviceModelPreset(t.enum8):
    """device_model_preset values (z2m)."""

    no_device = 0x00
    NARTIS_I300 = 0x01



_LOGGER = logging.getLogger(__name__)
_SHIPPED = pathlib.Path(zhaquirks.__file__).resolve().parent
_STEPPED_BACK: set = set()

# The Zigbee fingerprints (manufacturer, model) this quirk is for; None matches any manufacturer.
FINGERPRINTS = [(None, 'ElectricityMeterABC_DIY')]
# Names that a model-only fingerprint would catch but Zigbee2MQTT gives to other devices.
CLAIMED_ELSEWHERE = set()
# The endpoints this quirk needs, each with the input clusters it puts there where Zigbee2MQTT names none.
ENDPOINTS = {1: (0x0702,)}


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
    QuirkBuilder(None, 'ElectricityMeterABC_DIY')
    .replaces(SeMeteringCluster)
    .sensor(attribute_name=SeMeteringCluster.AttributeDefs.remaining_battery_life.name, cluster_id=SeMeteringCluster.cluster_id, state_class=SensorStateClass.MEASUREMENT, unit=PERCENTAGE, entity_type=EntityType.STANDARD, translation_key='battery_life', fallback_name='Battery life')
    .number(attribute_name=SeMeteringCluster.AttributeDefs.read_period.name, cluster_id=SeMeteringCluster.cluster_id, min_value=1, max_value=255, entity_type=EntityType.STANDARD, translation_key='device_measurement_preset', fallback_name='Device measurement preset')
    .enum(attribute_name=SeMeteringCluster.AttributeDefs.device_model.name, cluster_id=SeMeteringCluster.cluster_id, enum_class=DeviceModelPreset, entity_type=EntityType.STANDARD, translation_key='device_model_preset', fallback_name='Device model preset')
    # device_temperature: standard clusters, ZHA's own entities
    # power: standard clusters, ZHA's own entities
    # voltage: standard clusters, ZHA's own entities
    # current: standard clusters, ZHA's own entities
    # energy: standard clusters, ZHA's own entities
    # power_phase_b: standard clusters, ZHA's own entities
    # power_phase_c: standard clusters, ZHA's own entities
    # voltage_phase_b: standard clusters, ZHA's own entities
    # voltage_phase_c: standard clusters, ZHA's own entities
    # current_phase_b: standard clusters, ZHA's own entities
    # current_phase_c: standard clusters, ZHA's own entities
    # energy_tier_1: standard clusters or z2m's own code, not generated
    # energy_tier_2: standard clusters or z2m's own code, not generated
    # energy_tier_3: standard clusters or z2m's own code, not generated
    # energy_tier_4: standard clusters or z2m's own code, not generated
    # model_name: z2m's own code, not generated
    # serial_number: standard cluster, no ZHA entity, not generated
    # date_release: z2m's own code, not generated
    # tamper: standard cluster, no ZHA entity, not generated
    # battery_low: standard cluster, no ZHA entity, not generated
    # device_address_preset: standard clusters or z2m's own code, not generated
    # device_password_preset: standard clusters or z2m's own code, not generated
    .filter(no_builtin_quirk)
    .add_to_registry()
)
