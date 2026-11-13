"""YOKIS MVR500E-UP: Roller shutter module 500W.

Generated from the Zigbee2MQTT definition.
Data: zigbee-herdsman-converters, MIT, Copyright (c) 2018 Koen Kanters.
Status: generated, not verified on hardware.
Revision: d36f3391
"""

import functools
import logging
import pathlib

import zhaquirks
from zha.quirks import DEVICE_REGISTRY, DeviceMatch
import zigpy.types as t
from zigpy.zcl.foundation import BaseAttributeDefs, BaseCommandDefs, Direction, ZCLAttributeDef, ZCLCommandDef

from zhaquirks.builder import (
    EntityType,
    NumberDeviceClass,
    QuirkBuilder,
    UnitOfTime,
)
from zhaquirks.clusters import CustomCluster


class ManuSpecificYokisDeviceCluster(CustomCluster):
    """manuSpecificYokisDevice (z2m custom cluster)."""

    cluster_id = 0xFC01

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        configuration_changed = ZCLAttributeDef(id=0x0005, type=t.uint16_t, access="r", manufacturer_code=0x132D)

    class ServerCommandDefs(BaseCommandDefs):
        """Command definitions (z2m's commands this cluster lacks)."""

        reset_to_factory_settings = ZCLCommandDef(id=0x00, schema={'uc_reset_action': t.int8s}, direction=Direction.Client_to_Server, manufacturer_code=0x132D)
        relaunch_ble_advert = ZCLCommandDef(id=0x11, schema={}, direction=Direction.Client_to_Server, manufacturer_code=0x132D)


class ManuSpecificYokisInputCluster(CustomCluster):
    """manuSpecificYokisInput (z2m custom cluster)."""

    cluster_id = 0xFC02

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        input_mode = ZCLAttributeDef(id=0x0000, type=t.enum8, access="r", manufacturer_code=0x132D)
        contact_mode = ZCLAttributeDef(id=0x0001, type=t.Bool, access="r", manufacturer_code=0x132D)
        last_local_command_state = ZCLAttributeDef(id=0x0002, type=t.Bool, access="r", manufacturer_code=0x132D)
        last_b_p_connect_state = ZCLAttributeDef(id=0x0003, type=t.Bool, access="r", manufacturer_code=0x132D)
        backlight_intensity = ZCLAttributeDef(id=0x0004, type=t.uint8_t, access="r", manufacturer_code=0x132D)

    class ServerCommandDefs(BaseCommandDefs):
        """Command definitions (z2m's commands this cluster lacks)."""

        send_press = ZCLCommandDef(id=0x00, schema={}, direction=Direction.Client_to_Server, manufacturer_code=0x132D)
        send_release = ZCLCommandDef(id=0x01, schema={}, direction=Direction.Client_to_Server, manufacturer_code=0x132D)


class ManuSpecificYokisEntryConfiguratorCluster(CustomCluster):
    """manuSpecificYokisEntryConfigurator (z2m custom cluster)."""

    cluster_id = 0xFC03

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        e_short_press = ZCLAttributeDef(id=0x0001, type=t.Bool, access="r", manufacturer_code=0x132D)
        e_long_press = ZCLAttributeDef(id=0x0002, type=t.Bool, access="r", manufacturer_code=0x132D)
        long_press_duration = ZCLAttributeDef(id=0x0003, type=t.uint16_t, access="r", manufacturer_code=0x132D)
        time_between_press = ZCLAttributeDef(id=0x0004, type=t.uint16_t, access="r", manufacturer_code=0x132D)
        e_r12_m_long_press = ZCLAttributeDef(id=0x0005, type=t.Bool, access="r", manufacturer_code=0x132D)
        e_local_config_lock = ZCLAttributeDef(id=0x0006, type=t.Bool, access="r", manufacturer_code=0x132D)


class ManuSpecificYokisSubSystemCluster(CustomCluster):
    """manuSpecificYokisSubSystem (z2m custom cluster)."""

    cluster_id = 0xFC04

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        power_failure_mode = ZCLAttributeDef(id=0x0001, type=t.enum8, access="r", manufacturer_code=0x132D)


class PowerFailureMode(t.enum8):
    """power_failure_mode values (z2m)."""

    last_state = 0x00
    off = 0x01
    on = 0x02
    blink = 0x03


class InputMode(t.enum8):
    """input_mode values (z2m)."""

    unknown = 0x00
    push_button = 0x01
    switch = 0x02
    relay = 0x03
    fp_in = 0x04


class ContactMode(t.enum8):
    """contact_mode values (z2m)."""

    nc = 0x00
    no = 0x01



_LOGGER = logging.getLogger(__name__)
_SHIPPED = pathlib.Path(zhaquirks.__file__).resolve().parent
_STEPPED_BACK: set = set()

# The Zigbee fingerprints (manufacturer, model) this quirk is for; None matches any manufacturer.
FINGERPRINTS = [(None, 'MVR500E-UP')]
# Names that a model-only fingerprint would catch but Zigbee2MQTT gives to other devices.
CLAIMED_ELSEWHERE = set()
# The endpoints this quirk needs, each with the input clusters it puts there where Zigbee2MQTT names none.
ENDPOINTS = {1: (0xFC01, 0xFC02, 0xFC03, 0xFC04)}


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
    QuirkBuilder(None, 'MVR500E-UP')
    .replaces(ManuSpecificYokisSubSystemCluster)
    .replaces(ManuSpecificYokisEntryConfiguratorCluster)
    .replaces(ManuSpecificYokisInputCluster)
    .replaces(ManuSpecificYokisDeviceCluster)
    .enum(attribute_name=ManuSpecificYokisSubSystemCluster.AttributeDefs.power_failure_mode.name, cluster_id=ManuSpecificYokisSubSystemCluster.cluster_id, enum_class=PowerFailureMode, entity_type=EntityType.CONFIG, translation_key='power_failure_mode', fallback_name='Power failure mode')
    .enum(attribute_name=ManuSpecificYokisInputCluster.AttributeDefs.input_mode.name, cluster_id=ManuSpecificYokisInputCluster.cluster_id, enum_class=InputMode, entity_type=EntityType.CONFIG, translation_key='input_mode', fallback_name='Input mode')
    .enum(attribute_name=ManuSpecificYokisInputCluster.AttributeDefs.contact_mode.name, cluster_id=ManuSpecificYokisInputCluster.cluster_id, enum_class=ContactMode, entity_type=EntityType.CONFIG, translation_key='contact_mode', fallback_name='Contact mode')
    .binary_sensor(attribute_name=ManuSpecificYokisInputCluster.AttributeDefs.last_local_command_state.name, cluster_id=ManuSpecificYokisInputCluster.cluster_id, entity_type=EntityType.DIAGNOSTIC, translation_key='last_local_command_state', fallback_name='Last local command state')
    .binary_sensor(attribute_name=ManuSpecificYokisInputCluster.AttributeDefs.last_b_p_connect_state.name, cluster_id=ManuSpecificYokisInputCluster.cluster_id, entity_type=EntityType.DIAGNOSTIC, translation_key='last_bp_connect_state', fallback_name='Last bp connect state')
    .switch(attribute_name=ManuSpecificYokisEntryConfiguratorCluster.AttributeDefs.e_short_press.name, cluster_id=ManuSpecificYokisEntryConfiguratorCluster.cluster_id, entity_type=EntityType.CONFIG, translation_key='enable_short_press', fallback_name='Enable short press')
    .switch(attribute_name=ManuSpecificYokisEntryConfiguratorCluster.AttributeDefs.e_long_press.name, cluster_id=ManuSpecificYokisEntryConfiguratorCluster.cluster_id, entity_type=EntityType.CONFIG, translation_key='enable_long_press', fallback_name='Enable long press')
    .number(attribute_name=ManuSpecificYokisEntryConfiguratorCluster.AttributeDefs.long_press_duration.name, cluster_id=ManuSpecificYokisEntryConfiguratorCluster.cluster_id, min_value=0, max_value=5000, step=1, unit=UnitOfTime.MILLISECONDS, device_class=NumberDeviceClass.DURATION, entity_type=EntityType.CONFIG, translation_key='long_press_duration', fallback_name='Long press duration')
    .number(attribute_name=ManuSpecificYokisEntryConfiguratorCluster.AttributeDefs.time_between_press.name, cluster_id=ManuSpecificYokisEntryConfiguratorCluster.cluster_id, min_value=100, max_value=600, step=1, unit=UnitOfTime.MILLISECONDS, device_class=NumberDeviceClass.DURATION, entity_type=EntityType.CONFIG, translation_key='time_between_press', fallback_name='Time between press')
    .switch(attribute_name=ManuSpecificYokisEntryConfiguratorCluster.AttributeDefs.e_r12_m_long_press.name, cluster_id=ManuSpecificYokisEntryConfiguratorCluster.cluster_id, entity_type=EntityType.CONFIG, translation_key='enable_R12M_long_press', fallback_name='Enable R12M long press')
    .switch(attribute_name=ManuSpecificYokisEntryConfiguratorCluster.AttributeDefs.e_local_config_lock.name, cluster_id=ManuSpecificYokisEntryConfiguratorCluster.cluster_id, entity_type=EntityType.CONFIG, translation_key='enable_local_config_lock', fallback_name='Enable local config lock')
    .command_button(command_name=ManuSpecificYokisDeviceCluster.ServerCommandDefs.reset_to_factory_settings.name, cluster_id=ManuSpecificYokisDeviceCluster.cluster_id, command_args=(0,), entity_type=EntityType.CONFIG, initially_disabled=True, translation_key='reset_to_factory_settings_factory_reset', fallback_name='Reset to factory settings (factory reset)', unique_id_suffix='reset_to_factory_settings_factory_reset')
    .command_button(command_name=ManuSpecificYokisDeviceCluster.ServerCommandDefs.reset_to_factory_settings.name, cluster_id=ManuSpecificYokisDeviceCluster.cluster_id, command_args=(1,), entity_type=EntityType.CONFIG, initially_disabled=True, translation_key='reset_to_factory_settings_configuration_reset', fallback_name='Reset to factory settings (configuration reset)', unique_id_suffix='reset_to_factory_settings_configuration_reset')
    .command_button(command_name=ManuSpecificYokisDeviceCluster.ServerCommandDefs.reset_to_factory_settings.name, cluster_id=ManuSpecificYokisDeviceCluster.cluster_id, command_args=(2,), entity_type=EntityType.CONFIG, initially_disabled=True, translation_key='reset_to_factory_settings_network_reset', fallback_name='Reset to factory settings (network reset)', unique_id_suffix='reset_to_factory_settings_network_reset')
    .command_button(command_name=ManuSpecificYokisDeviceCluster.ServerCommandDefs.relaunch_ble_advert.name, cluster_id=ManuSpecificYokisDeviceCluster.cluster_id, entity_type=EntityType.CONFIG, translation_key='relaunch_ble_advert', fallback_name='Relaunch ble advert', unique_id_suffix='relaunch_ble_advert')
    .command_button(command_name=ManuSpecificYokisInputCluster.ServerCommandDefs.send_press.name, cluster_id=ManuSpecificYokisInputCluster.cluster_id, entity_type=EntityType.CONFIG, translation_key='send_press', fallback_name='Send press', unique_id_suffix='send_press')
    .command_button(command_name=ManuSpecificYokisInputCluster.ServerCommandDefs.send_release.name, cluster_id=ManuSpecificYokisInputCluster.cluster_id, entity_type=EntityType.CONFIG, translation_key='send_release', fallback_name='Send release', unique_id_suffix='send_release')
    # identify: standard clusters, ZHA's own entities
    # cover: standard clusters, ZHA's own entities
    # action: standard clusters, ZHA's own entities
    # select_input_mode: z2m's own code, not generated
    .filter(no_builtin_quirk)
    .add_to_registry()
)
