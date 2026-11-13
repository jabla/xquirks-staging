"""Schneider Electric MEG5126-0300/MEG5171-0000: Merten MEG5171 PlusLink Dimmer insert with Merten Wiser System M Push Button (2fold).

Generated from the Zigbee2MQTT definition.
Data: zigbee-herdsman-converters, MIT, Copyright (c) 2018 Koen Kanters.
Status: generated, not verified on hardware.
Revision: 8bd079d1
"""

import functools
import logging
import pathlib

import zhaquirks
from zha.quirks import DEVICE_REGISTRY, DeviceMatch
import zigpy.types as t
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef
from zigpy.zcl.clusters.lighting import Ballast

from zhaquirks.builder import (
    EntityType,
    QuirkBuilder,
)
from zhaquirks.clusters import CustomCluster


class LightingBallastCfgCluster(CustomCluster, Ballast):
    """Ballast with the attributes z2m adds."""

    class AttributeDefs(Ballast.AttributeDefs):
        """Attribute definitions."""

        wiser_control_mode = ZCLAttributeDef(id=0xE000, type=t.enum8, manufacturer_code=0x105E)


class ManuSpecificSchneiderLightSwitchConfigurationCluster(CustomCluster):
    """manuSpecificSchneiderLightSwitchConfiguration (z2m custom cluster)."""

    cluster_id = 0xFF17

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        led_indication = ZCLAttributeDef(id=0x0000, type=t.enum8, manufacturer_code=0x105E)
        up_scene_i_d = ZCLAttributeDef(id=0x0010, type=t.uint8_t, manufacturer_code=0x105E)
        up_group_i_d = ZCLAttributeDef(id=0x0011, type=t.uint16_t, manufacturer_code=0x105E)
        down_scene_i_d = ZCLAttributeDef(id=0x0020, type=t.uint8_t, manufacturer_code=0x105E)
        down_group_i_d = ZCLAttributeDef(id=0x0021, type=t.uint16_t, manufacturer_code=0x105E)
        switch_actions = ZCLAttributeDef(id=0x0001, type=t.enum8, manufacturer_code=0x105E)


class IndicatorMode(t.enum8):
    """indicator_mode values (z2m)."""

    consistent_with_load = 0x00
    always_on = 0x01
    reverse_with_load = 0x02
    always_off = 0x03
    flash_on_click = 0x04


class SwitchActions(t.enum8):
    """switch_actions values (z2m)."""

    light = 0x00
    dimmer = 0x01
    standard_shutter = 0x02
    schneider_shutter = 0x03
    scene = 0x04
    toggle_light = 0x05
    toggle_dimmer = 0x06
    alternate_light = 0x07
    alternate_dimmer = 0x08
    not_used = 0x7F
    schneider_shutter_opposite = 0xFB
    standard_shutter_opposite = 0xFC
    dimmer_opposite = 0xFD
    light_opposite = 0xFE


class DimmerMode(t.enum8):
    """dimmer_mode values (z2m)."""

    auto = 0x00
    rc = 0x01
    rl = 0x02
    rl_led = 0x03



_LOGGER = logging.getLogger(__name__)
_SHIPPED = pathlib.Path(zhaquirks.__file__).resolve().parent
_STEPPED_BACK: set = set()

# The Zigbee fingerprints (manufacturer, model) this quirk is for; None matches any manufacturer.
FINGERPRINTS = [(None, '2GANG/DIMMER/1')]
# Names that a model-only fingerprint would catch but Zigbee2MQTT gives to other devices.
CLAIMED_ELSEWHERE = set()
# The endpoints this quirk needs, each with the input clusters it puts there where Zigbee2MQTT names none.
ENDPOINTS = {3: (0x0301,), 21: (), 22: ()}


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
    QuirkBuilder(None, '2GANG/DIMMER/1')
    .replaces(ManuSpecificSchneiderLightSwitchConfigurationCluster, endpoint_id=21)
    .replaces(ManuSpecificSchneiderLightSwitchConfigurationCluster, endpoint_id=22)
    .replaces(LightingBallastCfgCluster, endpoint_id=3)
    .enum(attribute_name=ManuSpecificSchneiderLightSwitchConfigurationCluster.AttributeDefs.led_indication.name, cluster_id=ManuSpecificSchneiderLightSwitchConfigurationCluster.cluster_id, endpoint_id=21, enum_class=IndicatorMode, entity_type=EntityType.STANDARD, translation_key='indicator_mode_right', fallback_name='Indicator mode right')
    .enum(attribute_name=ManuSpecificSchneiderLightSwitchConfigurationCluster.AttributeDefs.led_indication.name, cluster_id=ManuSpecificSchneiderLightSwitchConfigurationCluster.cluster_id, endpoint_id=22, enum_class=IndicatorMode, entity_type=EntityType.STANDARD, translation_key='indicator_mode_left', fallback_name='Indicator mode left')
    .enum(attribute_name=ManuSpecificSchneiderLightSwitchConfigurationCluster.AttributeDefs.switch_actions.name, cluster_id=ManuSpecificSchneiderLightSwitchConfigurationCluster.cluster_id, endpoint_id=21, enum_class=SwitchActions, entity_type=EntityType.STANDARD, translation_key='switch_actions_right', fallback_name='Switch actions right')
    .enum(attribute_name=ManuSpecificSchneiderLightSwitchConfigurationCluster.AttributeDefs.switch_actions.name, cluster_id=ManuSpecificSchneiderLightSwitchConfigurationCluster.cluster_id, endpoint_id=22, enum_class=SwitchActions, entity_type=EntityType.STANDARD, translation_key='switch_actions_left', fallback_name='Switch actions left')
    .enum(attribute_name=LightingBallastCfgCluster.AttributeDefs.wiser_control_mode.name, cluster_id=LightingBallastCfgCluster.cluster_id, endpoint_id=3, enum_class=DimmerMode, entity_type=EntityType.STANDARD, translation_key='dimmer_mode', fallback_name='Dimmer mode')
    # light: standard clusters, ZHA's own entities
    # ballast_minimum_level: standard clusters, ZHA's own entities
    # ballast_maximum_level: standard clusters, ZHA's own entities
    .filter(no_builtin_quirk)
    .add_to_registry()
)
