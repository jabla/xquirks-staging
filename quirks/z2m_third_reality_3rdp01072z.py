"""Third Reality 3RDP01072Z: Smart Dual Plug ZP1.

Generated from the Zigbee2MQTT definition.
Entity names follow ZHA's own quirk for this device where it shows the same feature.
Data: zigbee-herdsman-converters, MIT, Copyright (c) 2018 Koen Kanters.
Status: generated, not verified on hardware.
Revision: ad4dacae
"""

import functools
import logging
import pathlib

import zhaquirks
from zha.quirks import DEVICE_REGISTRY, DeviceMatch
import zigpy.types as t
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef
from zigpy.zcl.clusters.general import Basic

from zhaquirks.builder import (
    EntityType,
    NumberDeviceClass,
    PERCENTAGE,
    QuirkBuilder,
    UnitOfTime,
)
from zhaquirks.clusters import CustomCluster


class GenBasicCluster(CustomCluster, Basic):
    """Basic with the attributes z2m adds."""

    class AttributeDefs(Basic.AttributeDefs):
        """Attribute definitions."""

        red_led_brightness = ZCLAttributeDef(id=0xFF01, type=t.uint8_t, manufacturer_code=None)


class Manufacturer3rDualPlugSpecialclusterCluster(CustomCluster):
    """3rDualPlugSpecialcluster (z2m custom cluster)."""

    cluster_id = 0xFF03

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        reset_total_energy = ZCLAttributeDef(id=0x0000, type=t.uint8_t, manufacturer_code=0x1407)
        countdown_to_turn_off = ZCLAttributeDef(id=0x0001, type=t.uint16_t, manufacturer_code=0x1407)
        countdown_to_turn_on = ZCLAttributeDef(id=0x0002, type=t.uint16_t, manufacturer_code=0x1407)
        metering_only_mode = ZCLAttributeDef(id=0x0050, type=t.uint8_t, manufacturer_code=0x1407)



_LOGGER = logging.getLogger(__name__)
_SHIPPED = pathlib.Path(zhaquirks.__file__).resolve().parent
_STEPPED_BACK: set = set()

# The Zigbee fingerprints (manufacturer, model) this quirk is for; None matches any manufacturer.
FINGERPRINTS = [(None, '3RDP01072Z'), (None, '3RWP01073Z'), ('Third Reality, Inc', '3RDP01072Z'), ('Third Reality, Inc', '3RWP01073Z')]
# Names that a model-only fingerprint would catch but Zigbee2MQTT gives to other devices.
CLAIMED_ELSEWHERE = set()
# The endpoints this quirk needs, each with the input clusters it puts there where Zigbee2MQTT names none.
ENDPOINTS = {1: (0x0000,), 2: ()}


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


(
    QuirkBuilder(None, '3RDP01072Z')
    .applies_to(None, '3RWP01073Z')
    .applies_to('Third Reality, Inc', '3RDP01072Z')
    .applies_to('Third Reality, Inc', '3RWP01073Z')
    .replaces(Manufacturer3rDualPlugSpecialclusterCluster)
    .replaces(Manufacturer3rDualPlugSpecialclusterCluster, endpoint_id=2)
    .replaces(GenBasicCluster)
    .write_attr_button(attribute_name=Manufacturer3rDualPlugSpecialclusterCluster.AttributeDefs.reset_total_energy.name, cluster_id=Manufacturer3rDualPlugSpecialclusterCluster.cluster_id, attribute_value=1, entity_type=EntityType.STANDARD, translation_key='reset_total_energy_1', fallback_name='Reset total energy 1', unique_id_suffix='reset_summation_delivered')
    .switch(attribute_name=Manufacturer3rDualPlugSpecialclusterCluster.AttributeDefs.metering_only_mode.name, cluster_id=Manufacturer3rDualPlugSpecialclusterCluster.cluster_id, entity_type=EntityType.STANDARD, translation_key='metering_only_mode_1', fallback_name='Metering only mode 1')
    .number(attribute_name=Manufacturer3rDualPlugSpecialclusterCluster.AttributeDefs.countdown_to_turn_off.name, cluster_id=Manufacturer3rDualPlugSpecialclusterCluster.cluster_id, min_value=0, max_value=60000, unit=UnitOfTime.SECONDS, device_class=NumberDeviceClass.DURATION, entity_type=EntityType.STANDARD, translation_key='countdown_time_on_to_off_1', fallback_name='Countdown time on to off 1', unique_id_suffix='on_to_off_delay')
    .number(attribute_name=Manufacturer3rDualPlugSpecialclusterCluster.AttributeDefs.countdown_to_turn_on.name, cluster_id=Manufacturer3rDualPlugSpecialclusterCluster.cluster_id, min_value=0, max_value=60000, unit=UnitOfTime.SECONDS, device_class=NumberDeviceClass.DURATION, entity_type=EntityType.STANDARD, translation_key='countdown_time_off_to_on_1', fallback_name='Countdown time off to on 1', unique_id_suffix='off_to_on_delay')
    .write_attr_button(attribute_name=Manufacturer3rDualPlugSpecialclusterCluster.AttributeDefs.reset_total_energy.name, cluster_id=Manufacturer3rDualPlugSpecialclusterCluster.cluster_id, endpoint_id=2, attribute_value=1, entity_type=EntityType.STANDARD, translation_key='reset_total_energy_2', fallback_name='Reset total energy 2', unique_id_suffix='reset_summation_delivered')
    .switch(attribute_name=Manufacturer3rDualPlugSpecialclusterCluster.AttributeDefs.metering_only_mode.name, cluster_id=Manufacturer3rDualPlugSpecialclusterCluster.cluster_id, endpoint_id=2, entity_type=EntityType.STANDARD, translation_key='metering_only_mode_2', fallback_name='Metering only mode 2')
    .number(attribute_name=Manufacturer3rDualPlugSpecialclusterCluster.AttributeDefs.countdown_to_turn_off.name, cluster_id=Manufacturer3rDualPlugSpecialclusterCluster.cluster_id, endpoint_id=2, min_value=0, max_value=60000, unit=UnitOfTime.SECONDS, device_class=NumberDeviceClass.DURATION, entity_type=EntityType.STANDARD, translation_key='countdown_time_on_to_off_2', fallback_name='Countdown time on to off 2', unique_id_suffix='on_to_off_delay')
    .number(attribute_name=Manufacturer3rDualPlugSpecialclusterCluster.AttributeDefs.countdown_to_turn_on.name, cluster_id=Manufacturer3rDualPlugSpecialclusterCluster.cluster_id, endpoint_id=2, min_value=0, max_value=60000, unit=UnitOfTime.SECONDS, device_class=NumberDeviceClass.DURATION, entity_type=EntityType.STANDARD, translation_key='countdown_time_off_to_on_2', fallback_name='Countdown time off to on 2', unique_id_suffix='off_to_on_delay')
    .number(attribute_name=GenBasicCluster.AttributeDefs.red_led_brightness.name, cluster_id=GenBasicCluster.cluster_id, min_value=0, max_value=100, unit=PERCENTAGE, entity_type=EntityType.STANDARD, translation_key='red_led_brightness', fallback_name='Red LED brightness')
    # switch: standard clusters, ZHA's own entities
    # power_on_behavior_1: standard clusters, ZHA's own entities
    # power_1: standard clusters, ZHA's own entities
    # voltage_1: standard clusters, ZHA's own entities
    # ac_frequency_1: standard clusters, ZHA's own entities
    # power_factor_1: standard clusters, ZHA's own entities
    # current_1: standard clusters, ZHA's own entities
    # energy_1: standard clusters, ZHA's own entities
    # switch: standard clusters, ZHA's own entities
    # power_on_behavior_2: standard clusters, ZHA's own entities
    # power_2: standard clusters, ZHA's own entities
    # voltage_2: standard clusters, ZHA's own entities
    # ac_frequency_2: standard clusters, ZHA's own entities
    # power_factor_2: standard clusters, ZHA's own entities
    # current_2: standard clusters, ZHA's own entities
    # energy_2: standard clusters, ZHA's own entities
    .filter(no_builtin_quirk)
    .add_to_registry()
)
