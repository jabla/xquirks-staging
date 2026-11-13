"""Schneider Electric 545D6102: LK FUGA wiser wireless dimmer.

Generated from the Zigbee2MQTT definition.
Data: zigbee-herdsman-converters, MIT, Copyright (c) 2018 Koen Kanters.
Status: generated, not verified on hardware.
Revision: 87590202
"""

import functools
import logging
import pathlib

import zhaquirks
from zha.quirks import DEVICE_REGISTRY, DeviceMatch
import zigpy.types as t
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef

from zhaquirks.builder import (
    EntityType,
    QuirkBuilder,
)
from zhaquirks.clusters import CustomCluster


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



_LOGGER = logging.getLogger(__name__)
_SHIPPED = pathlib.Path(zhaquirks.__file__).resolve().parent
_STEPPED_BACK: set = set()

# The Zigbee fingerprints (manufacturer, model) this quirk is for; None matches any manufacturer.
FINGERPRINTS = [(None, 'LK Dimmer')]
# Names that a model-only fingerprint would catch but Zigbee2MQTT gives to other devices.
CLAIMED_ELSEWHERE = set()
# The endpoints this quirk needs, each with the input clusters it puts there where Zigbee2MQTT names none.
ENDPOINTS = {21: (), 22: (), 23: (), 24: ()}


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
    QuirkBuilder(None, 'LK Dimmer')
    .replaces(ManuSpecificSchneiderLightSwitchConfigurationCluster, endpoint_id=21)
    .replaces(ManuSpecificSchneiderLightSwitchConfigurationCluster, endpoint_id=22)
    .replaces(ManuSpecificSchneiderLightSwitchConfigurationCluster, endpoint_id=23)
    .replaces(ManuSpecificSchneiderLightSwitchConfigurationCluster, endpoint_id=24)
    .enum(attribute_name=ManuSpecificSchneiderLightSwitchConfigurationCluster.AttributeDefs.led_indication.name, cluster_id=ManuSpecificSchneiderLightSwitchConfigurationCluster.cluster_id, endpoint_id=21, enum_class=IndicatorMode, entity_type=EntityType.STANDARD, translation_key='indicator_mode_s1', fallback_name='Indicator mode s1')
    .enum(attribute_name=ManuSpecificSchneiderLightSwitchConfigurationCluster.AttributeDefs.led_indication.name, cluster_id=ManuSpecificSchneiderLightSwitchConfigurationCluster.cluster_id, endpoint_id=22, enum_class=IndicatorMode, entity_type=EntityType.STANDARD, translation_key='indicator_mode_s2', fallback_name='Indicator mode s2')
    .enum(attribute_name=ManuSpecificSchneiderLightSwitchConfigurationCluster.AttributeDefs.led_indication.name, cluster_id=ManuSpecificSchneiderLightSwitchConfigurationCluster.cluster_id, endpoint_id=23, enum_class=IndicatorMode, entity_type=EntityType.STANDARD, translation_key='indicator_mode_s3', fallback_name='Indicator mode s3')
    .enum(attribute_name=ManuSpecificSchneiderLightSwitchConfigurationCluster.AttributeDefs.led_indication.name, cluster_id=ManuSpecificSchneiderLightSwitchConfigurationCluster.cluster_id, endpoint_id=24, enum_class=IndicatorMode, entity_type=EntityType.STANDARD, translation_key='indicator_mode_s4', fallback_name='Indicator mode s4')
    .enum(attribute_name=ManuSpecificSchneiderLightSwitchConfigurationCluster.AttributeDefs.switch_actions.name, cluster_id=ManuSpecificSchneiderLightSwitchConfigurationCluster.cluster_id, endpoint_id=21, enum_class=SwitchActions, entity_type=EntityType.STANDARD, translation_key='switch_actions_s1', fallback_name='Switch actions s1')
    .enum(attribute_name=ManuSpecificSchneiderLightSwitchConfigurationCluster.AttributeDefs.switch_actions.name, cluster_id=ManuSpecificSchneiderLightSwitchConfigurationCluster.cluster_id, endpoint_id=22, enum_class=SwitchActions, entity_type=EntityType.STANDARD, translation_key='switch_actions_s2', fallback_name='Switch actions s2')
    .enum(attribute_name=ManuSpecificSchneiderLightSwitchConfigurationCluster.AttributeDefs.switch_actions.name, cluster_id=ManuSpecificSchneiderLightSwitchConfigurationCluster.cluster_id, endpoint_id=23, enum_class=SwitchActions, entity_type=EntityType.STANDARD, translation_key='switch_actions_s3', fallback_name='Switch actions s3')
    .enum(attribute_name=ManuSpecificSchneiderLightSwitchConfigurationCluster.AttributeDefs.switch_actions.name, cluster_id=ManuSpecificSchneiderLightSwitchConfigurationCluster.cluster_id, endpoint_id=24, enum_class=SwitchActions, entity_type=EntityType.STANDARD, translation_key='switch_actions_s4', fallback_name='Switch actions s4')
    # light: standard clusters, ZHA's own entities
    # effect_l1: standard clusters, ZHA's own entities
    # power_on_behavior_l1: standard clusters, ZHA's own entities
    # ballast_minimum_level_l1: standard clusters or z2m's own code, not generated
    # ballast_maximum_level_l1: standard clusters or z2m's own code, not generated
    # dimmer_mode_l1: standard clusters or z2m's own code, not generated
    # action: standard clusters or z2m's own code, not generated
    .filter(no_builtin_quirk)
    .add_to_registry()
)
