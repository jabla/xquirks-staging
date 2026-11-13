"""Bosch BSP-FD: Smart plug compact [+M].

Generated from the Zigbee2MQTT definition.
Data: zigbee-herdsman-converters, MIT, Copyright (c) 2018 Koen Kanters.
Status: generated, not verified on hardware.
Revision: b2c4eba1
"""

import functools
import logging
import pathlib

import zhaquirks
from zha.quirks import DEVICE_REGISTRY, DeviceMatch
import zigpy.types as t
from zigpy.zcl.foundation import BaseAttributeDefs, Direction, ZCLAttributeDef, ZCLCommandDef
from zigpy.zcl.clusters.smartenergy import Metering

from zhaquirks.builder import (
    EntityType,
    NumberDeviceClass,
    PERCENTAGE,
    QuirkBuilder,
    UnitOfTime,
)
from zhaquirks.clusters import CustomCluster


class SeMeteringCluster(CustomCluster, Metering):
    """Metering with the attributes z2m adds."""

    class AttributeDefs(Metering.AttributeDefs):
        """Attribute definitions."""


    class ServerCommandDefs(Metering.ServerCommandDefs):
        """Command definitions (z2m's commands this cluster lacks)."""

        reset_energy_meters = ZCLCommandDef(id=0x80, schema={}, direction=Direction.Client_to_Server, manufacturer_code=0x1209)


class BoschEnergyDeviceCluster(CustomCluster):
    """boschEnergyDevice (z2m custom cluster)."""

    cluster_id = 0xFCA0

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        auto_off_enabled = ZCLAttributeDef(id=0x0006, type=t.Bool, manufacturer_code=0x1209)
        auto_off_time = ZCLAttributeDef(id=0x0007, type=t.uint16_t, manufacturer_code=0x1209)
        led_brightness = ZCLAttributeDef(id=0x002C, type=t.uint8_t, manufacturer_code=0x1209)
        energy_saving_mode_enabled = ZCLAttributeDef(id=0x002D, type=t.Bool, manufacturer_code=0x1209)
        energy_saving_mode_threshold = ZCLAttributeDef(id=0x002E, type=t.uint16_t, manufacturer_code=0x1209)
        energy_saving_mode_timer = ZCLAttributeDef(id=0x002F, type=t.uint32_t, manufacturer_code=0x1209)



_LOGGER = logging.getLogger(__name__)
_SHIPPED = pathlib.Path(zhaquirks.__file__).resolve().parent
_STEPPED_BACK: set = set()

# The Zigbee fingerprints (manufacturer, model) this quirk is for; None matches any manufacturer.
FINGERPRINTS = [(None, 'RBSH-SP2-ZB-EU')]
# Names that a model-only fingerprint would catch but Zigbee2MQTT gives to other devices.
CLAIMED_ELSEWHERE = set()
# The endpoints this quirk needs, each with the input clusters it puts there where Zigbee2MQTT names none.
ENDPOINTS = {1: (0x0702, 0xFCA0)}


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
    QuirkBuilder(None, 'RBSH-SP2-ZB-EU')
    .replaces(BoschEnergyDeviceCluster)
    .replaces(SeMeteringCluster)
    .number(attribute_name=BoschEnergyDeviceCluster.AttributeDefs.led_brightness.name, cluster_id=BoschEnergyDeviceCluster.cluster_id, min_value=0, max_value=100, step=1, unit=PERCENTAGE, entity_type=EntityType.CONFIG, translation_key='led_brightness', fallback_name='LED brightness')
    .switch(attribute_name=BoschEnergyDeviceCluster.AttributeDefs.energy_saving_mode_enabled.name, cluster_id=BoschEnergyDeviceCluster.cluster_id, entity_type=EntityType.CONFIG, translation_key='energy_saving_mode_enabled', fallback_name='Enable energy-saving mode')
    .number(attribute_name=BoschEnergyDeviceCluster.AttributeDefs.energy_saving_mode_threshold.name, cluster_id=BoschEnergyDeviceCluster.cluster_id, min_value=1, max_value=50, step=1, unit='watt', multiplier=0.1, entity_type=EntityType.CONFIG, translation_key='energy_saving_mode_threshold', fallback_name='Energy-saving threshold')
    .number(attribute_name=BoschEnergyDeviceCluster.AttributeDefs.energy_saving_mode_timer.name, cluster_id=BoschEnergyDeviceCluster.cluster_id, min_value=1, max_value=1800, step=1, unit=UnitOfTime.SECONDS, device_class=NumberDeviceClass.DURATION, entity_type=EntityType.CONFIG, translation_key='energy_saving_mode_timer', fallback_name='Energy-saving timer')
    .command_button(command_name=SeMeteringCluster.ServerCommandDefs.reset_energy_meters.name, cluster_id=SeMeteringCluster.cluster_id, entity_type=EntityType.CONFIG, initially_disabled=True, translation_key='reset_energy_meters', fallback_name='Reset energy meters', unique_id_suffix='reset_energy_meters')
    # switch: standard clusters, ZHA's own entities
    # power_on_behavior: standard clusters, ZHA's own entities
    # power: standard clusters, ZHA's own entities
    # energy: standard clusters, ZHA's own entities
    # produced_energy: standard clusters, ZHA's own entities
    .filter(no_builtin_quirk)
    .add_to_registry()
)
