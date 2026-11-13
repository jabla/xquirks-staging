"""Slacky-DIY FreePad-08K-SlD: DIY 8 buttons keypad.

Generated from the Zigbee2MQTT definition.
Data: zigbee-herdsman-converters, MIT, Copyright (c) 2018 Koen Kanters.
Status: generated, not verified on hardware.
Revision: 81aec043
"""

import functools
import logging
import pathlib

import zhaquirks
from zha.quirks import DEVICE_REGISTRY, DeviceMatch
import zigpy.types as t
from zigpy.zcl.foundation import ZCLAttributeDef
from zigpy.zcl.clusters.general import LevelControl
from zigpy.zcl.clusters.general import OnOffConfiguration
from zigpy.zcl.clusters.general import Scenes

from zhaquirks.builder import (
    EntityType,
    QuirkBuilder,
)
from zhaquirks.clusters import CustomCluster


class GenScenesCluster(CustomCluster, Scenes):
    """Scenes with the attributes z2m adds."""

    class AttributeDefs(Scenes.AttributeDefs):
        """Attribute definitions."""

        custom_scene_id = ZCLAttributeDef(id=0xF000, type=t.uint8_t, manufacturer_code=None)
        custom_group_id = ZCLAttributeDef(id=0xF001, type=t.uint16_t, manufacturer_code=None)


class GenOnOffSwitchCfgCluster(CustomCluster, OnOffConfiguration):
    """OnOffConfiguration with the attributes z2m adds."""

    class AttributeDefs(OnOffConfiguration.AttributeDefs):
        """Attribute definitions."""

        custom_switch_type = ZCLAttributeDef(id=0xF000, type=t.enum8, manufacturer_code=None)
        custom_device_model_number = ZCLAttributeDef(id=0xF002, type=t.enum8, manufacturer_code=None)


class GenLevelCtrlCluster(CustomCluster, LevelControl):
    """LevelControl with the attributes z2m adds."""

    class AttributeDefs(LevelControl.AttributeDefs):
        """Attribute definitions."""



class SwitchActions(t.enum8):
    """switch_actions values (z2m)."""

    off = 0x00
    on = 0x01
    toggle = 0x02


class SwitchType(t.enum8):
    """switch_type values (z2m)."""

    toggle = 0x00
    momentary = 0x01
    multifunction = 0x02
    brightness_level = 0x03
    brightness_level_up = 0x04
    brightness_level_down = 0x05
    move_to_color_temperature = 0x06
    move_to_color_temperature_up = 0x07
    move_to_color_temperature_down = 0x08
    scene = 0x09



_LOGGER = logging.getLogger(__name__)
_SHIPPED = pathlib.Path(zhaquirks.__file__).resolve().parent
_STEPPED_BACK: set = set()

# The Zigbee fingerprints (manufacturer, model) this quirk is for; None matches any manufacturer.
FINGERPRINTS = [(None, 'FreePad-08K-SlD')]
# Names that a model-only fingerprint would catch but Zigbee2MQTT gives to other devices.
CLAIMED_ELSEWHERE = set()
# The endpoints this quirk needs, each with the input clusters it puts there where Zigbee2MQTT names none.
ENDPOINTS = {1: (), 2: (), 3: (), 4: (), 5: (), 6: (), 7: (), 8: ()}


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
    QuirkBuilder(None, 'FreePad-08K-SlD')
    .replaces(GenLevelCtrlCluster)
    .replaces(GenLevelCtrlCluster, endpoint_id=2)
    .replaces(GenLevelCtrlCluster, endpoint_id=3)
    .replaces(GenLevelCtrlCluster, endpoint_id=4)
    .replaces(GenLevelCtrlCluster, endpoint_id=5)
    .replaces(GenLevelCtrlCluster, endpoint_id=6)
    .replaces(GenLevelCtrlCluster, endpoint_id=7)
    .replaces(GenLevelCtrlCluster, endpoint_id=8)
    .replaces(GenOnOffSwitchCfgCluster)
    .replaces(GenOnOffSwitchCfgCluster, endpoint_id=2)
    .replaces(GenOnOffSwitchCfgCluster, endpoint_id=3)
    .replaces(GenOnOffSwitchCfgCluster, endpoint_id=4)
    .replaces(GenOnOffSwitchCfgCluster, endpoint_id=5)
    .replaces(GenOnOffSwitchCfgCluster, endpoint_id=6)
    .replaces(GenOnOffSwitchCfgCluster, endpoint_id=7)
    .replaces(GenOnOffSwitchCfgCluster, endpoint_id=8)
    .replaces(GenScenesCluster)
    .replaces(GenScenesCluster, endpoint_id=2)
    .replaces(GenScenesCluster, endpoint_id=3)
    .replaces(GenScenesCluster, endpoint_id=4)
    .replaces(GenScenesCluster, endpoint_id=5)
    .replaces(GenScenesCluster, endpoint_id=6)
    .replaces(GenScenesCluster, endpoint_id=7)
    .replaces(GenScenesCluster, endpoint_id=8)
    .enum(attribute_name=GenOnOffSwitchCfgCluster.AttributeDefs.switch_actions.name, cluster_id=GenOnOffSwitchCfgCluster.cluster_id, enum_class=SwitchActions, entity_type=EntityType.STANDARD, translation_key='switch_actions_1', fallback_name='Switch actions 1')
    .enum(attribute_name=GenOnOffSwitchCfgCluster.AttributeDefs.switch_actions.name, cluster_id=GenOnOffSwitchCfgCluster.cluster_id, endpoint_id=2, enum_class=SwitchActions, entity_type=EntityType.STANDARD, translation_key='switch_actions_2', fallback_name='Switch actions 2')
    .enum(attribute_name=GenOnOffSwitchCfgCluster.AttributeDefs.switch_actions.name, cluster_id=GenOnOffSwitchCfgCluster.cluster_id, endpoint_id=3, enum_class=SwitchActions, entity_type=EntityType.STANDARD, translation_key='switch_actions_3', fallback_name='Switch actions 3')
    .enum(attribute_name=GenOnOffSwitchCfgCluster.AttributeDefs.switch_actions.name, cluster_id=GenOnOffSwitchCfgCluster.cluster_id, endpoint_id=4, enum_class=SwitchActions, entity_type=EntityType.STANDARD, translation_key='switch_actions_4', fallback_name='Switch actions 4')
    .enum(attribute_name=GenOnOffSwitchCfgCluster.AttributeDefs.switch_actions.name, cluster_id=GenOnOffSwitchCfgCluster.cluster_id, endpoint_id=5, enum_class=SwitchActions, entity_type=EntityType.STANDARD, translation_key='switch_actions_5', fallback_name='Switch actions 5')
    .enum(attribute_name=GenOnOffSwitchCfgCluster.AttributeDefs.switch_actions.name, cluster_id=GenOnOffSwitchCfgCluster.cluster_id, endpoint_id=6, enum_class=SwitchActions, entity_type=EntityType.STANDARD, translation_key='switch_actions_6', fallback_name='Switch actions 6')
    .enum(attribute_name=GenOnOffSwitchCfgCluster.AttributeDefs.switch_actions.name, cluster_id=GenOnOffSwitchCfgCluster.cluster_id, endpoint_id=7, enum_class=SwitchActions, entity_type=EntityType.STANDARD, translation_key='switch_actions_7', fallback_name='Switch actions 7')
    .enum(attribute_name=GenOnOffSwitchCfgCluster.AttributeDefs.switch_actions.name, cluster_id=GenOnOffSwitchCfgCluster.cluster_id, endpoint_id=8, enum_class=SwitchActions, entity_type=EntityType.STANDARD, translation_key='switch_actions_8', fallback_name='Switch actions 8')
    .enum(attribute_name=GenOnOffSwitchCfgCluster.AttributeDefs.custom_switch_type.name, cluster_id=GenOnOffSwitchCfgCluster.cluster_id, enum_class=SwitchType, entity_type=EntityType.STANDARD, translation_key='switch_type_1', fallback_name='Switch type 1')
    .enum(attribute_name=GenOnOffSwitchCfgCluster.AttributeDefs.custom_switch_type.name, cluster_id=GenOnOffSwitchCfgCluster.cluster_id, endpoint_id=2, enum_class=SwitchType, entity_type=EntityType.STANDARD, translation_key='switch_type_2', fallback_name='Switch type 2')
    .enum(attribute_name=GenOnOffSwitchCfgCluster.AttributeDefs.custom_switch_type.name, cluster_id=GenOnOffSwitchCfgCluster.cluster_id, endpoint_id=3, enum_class=SwitchType, entity_type=EntityType.STANDARD, translation_key='switch_type_3', fallback_name='Switch type 3')
    .enum(attribute_name=GenOnOffSwitchCfgCluster.AttributeDefs.custom_switch_type.name, cluster_id=GenOnOffSwitchCfgCluster.cluster_id, endpoint_id=4, enum_class=SwitchType, entity_type=EntityType.STANDARD, translation_key='switch_type_4', fallback_name='Switch type 4')
    .enum(attribute_name=GenOnOffSwitchCfgCluster.AttributeDefs.custom_switch_type.name, cluster_id=GenOnOffSwitchCfgCluster.cluster_id, endpoint_id=5, enum_class=SwitchType, entity_type=EntityType.STANDARD, translation_key='switch_type_5', fallback_name='Switch type 5')
    .enum(attribute_name=GenOnOffSwitchCfgCluster.AttributeDefs.custom_switch_type.name, cluster_id=GenOnOffSwitchCfgCluster.cluster_id, endpoint_id=6, enum_class=SwitchType, entity_type=EntityType.STANDARD, translation_key='switch_type_6', fallback_name='Switch type 6')
    .enum(attribute_name=GenOnOffSwitchCfgCluster.AttributeDefs.custom_switch_type.name, cluster_id=GenOnOffSwitchCfgCluster.cluster_id, endpoint_id=7, enum_class=SwitchType, entity_type=EntityType.STANDARD, translation_key='switch_type_7', fallback_name='Switch type 7')
    .enum(attribute_name=GenOnOffSwitchCfgCluster.AttributeDefs.custom_switch_type.name, cluster_id=GenOnOffSwitchCfgCluster.cluster_id, endpoint_id=8, enum_class=SwitchType, entity_type=EntityType.STANDARD, translation_key='switch_type_8', fallback_name='Switch type 8')
    .number(attribute_name=GenScenesCluster.AttributeDefs.custom_scene_id.name, cluster_id=GenScenesCluster.cluster_id, min_value=0, max_value=255, entity_type=EntityType.STANDARD, translation_key='scene_id_1', fallback_name='Scene ID 1')
    .number(attribute_name=GenScenesCluster.AttributeDefs.custom_scene_id.name, cluster_id=GenScenesCluster.cluster_id, endpoint_id=2, min_value=0, max_value=255, entity_type=EntityType.STANDARD, translation_key='scene_id_2', fallback_name='Scene ID 2')
    .number(attribute_name=GenScenesCluster.AttributeDefs.custom_scene_id.name, cluster_id=GenScenesCluster.cluster_id, endpoint_id=3, min_value=0, max_value=255, entity_type=EntityType.STANDARD, translation_key='scene_id_3', fallback_name='Scene ID 3')
    .number(attribute_name=GenScenesCluster.AttributeDefs.custom_scene_id.name, cluster_id=GenScenesCluster.cluster_id, endpoint_id=4, min_value=0, max_value=255, entity_type=EntityType.STANDARD, translation_key='scene_id_4', fallback_name='Scene ID 4')
    .number(attribute_name=GenScenesCluster.AttributeDefs.custom_scene_id.name, cluster_id=GenScenesCluster.cluster_id, endpoint_id=5, min_value=0, max_value=255, entity_type=EntityType.STANDARD, translation_key='scene_id_5', fallback_name='Scene ID 5')
    .number(attribute_name=GenScenesCluster.AttributeDefs.custom_scene_id.name, cluster_id=GenScenesCluster.cluster_id, endpoint_id=6, min_value=0, max_value=255, entity_type=EntityType.STANDARD, translation_key='scene_id_6', fallback_name='Scene ID 6')
    .number(attribute_name=GenScenesCluster.AttributeDefs.custom_scene_id.name, cluster_id=GenScenesCluster.cluster_id, endpoint_id=7, min_value=0, max_value=255, entity_type=EntityType.STANDARD, translation_key='scene_id_7', fallback_name='Scene ID 7')
    .number(attribute_name=GenScenesCluster.AttributeDefs.custom_scene_id.name, cluster_id=GenScenesCluster.cluster_id, endpoint_id=8, min_value=0, max_value=255, entity_type=EntityType.STANDARD, translation_key='scene_id_8', fallback_name='Scene ID 8')
    .number(attribute_name=GenScenesCluster.AttributeDefs.custom_group_id.name, cluster_id=GenScenesCluster.cluster_id, min_value=0, max_value=65527, entity_type=EntityType.STANDARD, translation_key='group_id_1', fallback_name='Group ID 1')
    .number(attribute_name=GenScenesCluster.AttributeDefs.custom_group_id.name, cluster_id=GenScenesCluster.cluster_id, endpoint_id=2, min_value=0, max_value=65527, entity_type=EntityType.STANDARD, translation_key='group_id_2', fallback_name='Group ID 2')
    .number(attribute_name=GenScenesCluster.AttributeDefs.custom_group_id.name, cluster_id=GenScenesCluster.cluster_id, endpoint_id=3, min_value=0, max_value=65527, entity_type=EntityType.STANDARD, translation_key='group_id_3', fallback_name='Group ID 3')
    .number(attribute_name=GenScenesCluster.AttributeDefs.custom_group_id.name, cluster_id=GenScenesCluster.cluster_id, endpoint_id=4, min_value=0, max_value=65527, entity_type=EntityType.STANDARD, translation_key='group_id_4', fallback_name='Group ID 4')
    .number(attribute_name=GenScenesCluster.AttributeDefs.custom_group_id.name, cluster_id=GenScenesCluster.cluster_id, endpoint_id=5, min_value=0, max_value=65527, entity_type=EntityType.STANDARD, translation_key='group_id_5', fallback_name='Group ID 5')
    .number(attribute_name=GenScenesCluster.AttributeDefs.custom_group_id.name, cluster_id=GenScenesCluster.cluster_id, endpoint_id=6, min_value=0, max_value=65527, entity_type=EntityType.STANDARD, translation_key='group_id_6', fallback_name='Group ID 6')
    .number(attribute_name=GenScenesCluster.AttributeDefs.custom_group_id.name, cluster_id=GenScenesCluster.cluster_id, endpoint_id=7, min_value=0, max_value=65527, entity_type=EntityType.STANDARD, translation_key='group_id_7', fallback_name='Group ID 7')
    .number(attribute_name=GenScenesCluster.AttributeDefs.custom_group_id.name, cluster_id=GenScenesCluster.cluster_id, endpoint_id=8, min_value=0, max_value=65527, entity_type=EntityType.STANDARD, translation_key='group_id_8', fallback_name='Group ID 8')
    # min_level: attribute minLevel has no known type, not generated
    # min_level: attribute minLevel has no known type, not generated
    # min_level: attribute minLevel has no known type, not generated
    # min_level: attribute minLevel has no known type, not generated
    # min_level: attribute minLevel has no known type, not generated
    # min_level: attribute minLevel has no known type, not generated
    # min_level: attribute minLevel has no known type, not generated
    # min_level: attribute minLevel has no known type, not generated
    # max_level: attribute maxLevel has no known type, not generated
    # max_level: attribute maxLevel has no known type, not generated
    # max_level: attribute maxLevel has no known type, not generated
    # max_level: attribute maxLevel has no known type, not generated
    # max_level: attribute maxLevel has no known type, not generated
    # max_level: attribute maxLevel has no known type, not generated
    # max_level: attribute maxLevel has no known type, not generated
    # max_level: attribute maxLevel has no known type, not generated
    # battery: standard clusters, ZHA's own entities
    # action: standard clusters, ZHA's own entities
    # action: standard clusters, ZHA's own entities
    # action: standard clusters or z2m's own code, not generated
    # action: standard clusters, ZHA's own entities
    # action: standard clusters or z2m's own code, not generated
    .filter(no_builtin_quirk)
    .add_to_registry()
)
