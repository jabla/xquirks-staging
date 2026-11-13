"""YOKIS MTR1300E-UP: Remote power switch with timer 1300W.

Generated from the Zigbee2MQTT definition.
Data: zigbee-herdsman-converters, MIT, Copyright (c) 2018 Koen Kanters.
Status: generated, not verified on hardware.
Revision: 3510a7a3
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


class ManuSpecificYokisLightControlCluster(CustomCluster):
    """manuSpecificYokisLightControl (z2m custom cluster)."""

    cluster_id = 0xFC06

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        on_off = ZCLAttributeDef(id=0x0000, type=t.Bool, access="r", manufacturer_code=0x132D)
        prev_state = ZCLAttributeDef(id=0x0001, type=t.Bool, access="r", manufacturer_code=0x132D)
        on_timer = ZCLAttributeDef(id=0x0002, type=t.uint32_t, access="r", manufacturer_code=0x132D)
        e_on_timer = ZCLAttributeDef(id=0x0003, type=t.Bool, access="r", manufacturer_code=0x132D)
        pre_on_delay = ZCLAttributeDef(id=0x0004, type=t.uint32_t, access="r", manufacturer_code=0x132D)
        e_pre_on_delay = ZCLAttributeDef(id=0x0005, type=t.Bool, access="r", manufacturer_code=0x132D)
        pre_off_delay = ZCLAttributeDef(id=0x0008, type=t.uint32_t, access="r", manufacturer_code=0x132D)
        e_pre_off_delay = ZCLAttributeDef(id=0x0009, type=t.Bool, access="r", manufacturer_code=0x132D)
        pulse_duration = ZCLAttributeDef(id=0x000A, type=t.uint16_t, access="r", manufacturer_code=0x132D)
        time_type = ZCLAttributeDef(id=0x000B, type=t.enum8, access="r", manufacturer_code=0x132D)
        long_on_duration = ZCLAttributeDef(id=0x000C, type=t.uint32_t, access="r", manufacturer_code=0x132D)
        operating_mode = ZCLAttributeDef(id=0x000D, type=t.enum8, access="r", manufacturer_code=0x132D)
        stop_announce_time = ZCLAttributeDef(id=0x0013, type=t.uint32_t, access="r", manufacturer_code=0x132D)
        e_stop_announce = ZCLAttributeDef(id=0x0014, type=t.Bool, access="r", manufacturer_code=0x132D)
        e_deaf = ZCLAttributeDef(id=0x0015, type=t.Bool, access="r", manufacturer_code=0x132D)
        e_blink = ZCLAttributeDef(id=0x0016, type=t.Bool, access="r", manufacturer_code=0x132D)
        blink_amount = ZCLAttributeDef(id=0x0017, type=t.uint8_t, access="r", manufacturer_code=0x132D)
        blink_on_time = ZCLAttributeDef(id=0x0018, type=t.uint32_t, access="r", manufacturer_code=0x132D)
        blink_off_time = ZCLAttributeDef(id=0x0019, type=t.uint32_t, access="r", manufacturer_code=0x132D)
        deaf_blink_amount = ZCLAttributeDef(id=0x001A, type=t.uint8_t, access="r", manufacturer_code=0x132D)
        deaf_blink_time = ZCLAttributeDef(id=0x001B, type=t.uint16_t, access="r", manufacturer_code=0x132D)
        state_after_blink = ZCLAttributeDef(id=0x001C, type=t.enum8, access="r", manufacturer_code=0x132D)
        e_nc_command = ZCLAttributeDef(id=0x001D, type=t.Bool, access="r", manufacturer_code=0x132D)

    class ServerCommandDefs(BaseCommandDefs):
        """Command definitions (z2m's commands this cluster lacks)."""

        long_on = ZCLCommandDef(id=0x07, schema={}, direction=Direction.Client_to_Server, manufacturer_code=0x132D)


class PowerFailureMode(t.enum8):
    """power_failure_mode values (z2m)."""

    last_state = 0x00
    off = 0x01
    on = 0x02
    blink = 0x03


class TimeType(t.enum8):
    """time_type values (z2m)."""

    seconds = 0x00
    minutes = 0x01


class OperatingMode(t.enum8):
    """operating_mode values (z2m)."""

    timer = 0x00
    staircase = 0x01
    pulse = 0x02


class StateAfterBlink(t.enum8):
    """state_after_blink values (z2m)."""

    previous = 0x00
    off = 0x01
    on = 0x02
    infinite = 0x03


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
FINGERPRINTS = [(None, 'MTR1300E-UP'), (None, 'MTR1300EB-UP')]
# Names that a model-only fingerprint would catch but Zigbee2MQTT gives to other devices.
CLAIMED_ELSEWHERE = set()
# The endpoints this quirk needs, each with the input clusters it puts there where Zigbee2MQTT names none.
ENDPOINTS = {1: (0xFC01, 0xFC02, 0xFC03, 0xFC04, 0xFC06)}


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
    QuirkBuilder(None, 'MTR1300E-UP')
    .applies_to(None, 'MTR1300EB-UP')
    .replaces(ManuSpecificYokisLightControlCluster)
    .replaces(ManuSpecificYokisSubSystemCluster)
    .replaces(ManuSpecificYokisEntryConfiguratorCluster)
    .replaces(ManuSpecificYokisInputCluster)
    .replaces(ManuSpecificYokisDeviceCluster)
    .enum(attribute_name=ManuSpecificYokisSubSystemCluster.AttributeDefs.power_failure_mode.name, cluster_id=ManuSpecificYokisSubSystemCluster.cluster_id, enum_class=PowerFailureMode, entity_type=EntityType.CONFIG, translation_key='power_failure_mode', fallback_name='Power failure mode')
    .binary_sensor(attribute_name=ManuSpecificYokisLightControlCluster.AttributeDefs.prev_state.name, cluster_id=ManuSpecificYokisLightControlCluster.cluster_id, entity_type=EntityType.DIAGNOSTIC, translation_key='prev_state', fallback_name='Prev state')
    .number(attribute_name=ManuSpecificYokisLightControlCluster.AttributeDefs.on_timer.name, cluster_id=ManuSpecificYokisLightControlCluster.cluster_id, min_value=0, max_value=3600, step=1, unit=UnitOfTime.SECONDS, device_class=NumberDeviceClass.DURATION, entity_type=EntityType.CONFIG, translation_key='on_timer', fallback_name='On timer')
    .switch(attribute_name=ManuSpecificYokisLightControlCluster.AttributeDefs.e_pre_on_delay.name, cluster_id=ManuSpecificYokisLightControlCluster.cluster_id, entity_type=EntityType.CONFIG, translation_key='enable_pre_on_delay', fallback_name='Enable pre on delay')
    .number(attribute_name=ManuSpecificYokisLightControlCluster.AttributeDefs.pre_on_delay.name, cluster_id=ManuSpecificYokisLightControlCluster.cluster_id, min_value=0, max_value=3600, step=1, unit=UnitOfTime.SECONDS, device_class=NumberDeviceClass.DURATION, entity_type=EntityType.CONFIG, translation_key='pre_on_delay', fallback_name='Pre on delay')
    .switch(attribute_name=ManuSpecificYokisLightControlCluster.AttributeDefs.e_pre_off_delay.name, cluster_id=ManuSpecificYokisLightControlCluster.cluster_id, entity_type=EntityType.CONFIG, translation_key='enable_pre_off_delay', fallback_name='Enable pre off delay')
    .number(attribute_name=ManuSpecificYokisLightControlCluster.AttributeDefs.pre_off_delay.name, cluster_id=ManuSpecificYokisLightControlCluster.cluster_id, min_value=0, max_value=3600, step=1, unit=UnitOfTime.SECONDS, device_class=NumberDeviceClass.DURATION, entity_type=EntityType.CONFIG, translation_key='pre_off_delay', fallback_name='Pre off delay')
    .number(attribute_name=ManuSpecificYokisLightControlCluster.AttributeDefs.pulse_duration.name, cluster_id=ManuSpecificYokisLightControlCluster.cluster_id, min_value=20, max_value=65534, step=1, unit=UnitOfTime.MILLISECONDS, device_class=NumberDeviceClass.DURATION, entity_type=EntityType.CONFIG, translation_key='pulse_duration', fallback_name='Pulse duration')
    .enum(attribute_name=ManuSpecificYokisLightControlCluster.AttributeDefs.time_type.name, cluster_id=ManuSpecificYokisLightControlCluster.cluster_id, enum_class=TimeType, entity_type=EntityType.CONFIG, translation_key='time_type', fallback_name='Time type')
    .number(attribute_name=ManuSpecificYokisLightControlCluster.AttributeDefs.long_on_duration.name, cluster_id=ManuSpecificYokisLightControlCluster.cluster_id, min_value=0, max_value=4233600, step=1, unit=UnitOfTime.SECONDS, device_class=NumberDeviceClass.DURATION, entity_type=EntityType.CONFIG, translation_key='long_on_duration', fallback_name='Long on duration')
    .enum(attribute_name=ManuSpecificYokisLightControlCluster.AttributeDefs.operating_mode.name, cluster_id=ManuSpecificYokisLightControlCluster.cluster_id, enum_class=OperatingMode, entity_type=EntityType.CONFIG, translation_key='operating_mode', fallback_name='Operating mode')
    .switch(attribute_name=ManuSpecificYokisLightControlCluster.AttributeDefs.e_stop_announce.name, cluster_id=ManuSpecificYokisLightControlCluster.cluster_id, entity_type=EntityType.CONFIG, translation_key='enable_stop_announce', fallback_name='Enable stop announce')
    .number(attribute_name=ManuSpecificYokisLightControlCluster.AttributeDefs.stop_announce_time.name, cluster_id=ManuSpecificYokisLightControlCluster.cluster_id, min_value=0, max_value=4233600, step=1, unit=UnitOfTime.SECONDS, device_class=NumberDeviceClass.DURATION, entity_type=EntityType.CONFIG, translation_key='stop_announce_time', fallback_name='Stop announce time')
    .switch(attribute_name=ManuSpecificYokisLightControlCluster.AttributeDefs.e_deaf.name, cluster_id=ManuSpecificYokisLightControlCluster.cluster_id, entity_type=EntityType.CONFIG, translation_key='enable_deaf', fallback_name='Enable deaf')
    .number(attribute_name=ManuSpecificYokisLightControlCluster.AttributeDefs.deaf_blink_amount.name, cluster_id=ManuSpecificYokisLightControlCluster.cluster_id, min_value=0, max_value=20, step=1, entity_type=EntityType.CONFIG, translation_key='deaf_blink_amount', fallback_name='Deaf blink amount')
    .number(attribute_name=ManuSpecificYokisLightControlCluster.AttributeDefs.deaf_blink_time.name, cluster_id=ManuSpecificYokisLightControlCluster.cluster_id, min_value=100, max_value=20000, step=1, entity_type=EntityType.CONFIG, translation_key='deaf_blink_time', fallback_name='Deaf blink time')
    .switch(attribute_name=ManuSpecificYokisLightControlCluster.AttributeDefs.e_blink.name, cluster_id=ManuSpecificYokisLightControlCluster.cluster_id, entity_type=EntityType.CONFIG, translation_key='enable_blink', fallback_name='Enable blink')
    .number(attribute_name=ManuSpecificYokisLightControlCluster.AttributeDefs.blink_amount.name, cluster_id=ManuSpecificYokisLightControlCluster.cluster_id, min_value=0, max_value=20, step=1, entity_type=EntityType.CONFIG, translation_key='blink_amount', fallback_name='Blink amount')
    .number(attribute_name=ManuSpecificYokisLightControlCluster.AttributeDefs.blink_on_time.name, cluster_id=ManuSpecificYokisLightControlCluster.cluster_id, min_value=0, max_value=4233600, step=1, entity_type=EntityType.CONFIG, translation_key='blink_on_time', fallback_name='Blink on time')
    .number(attribute_name=ManuSpecificYokisLightControlCluster.AttributeDefs.blink_off_time.name, cluster_id=ManuSpecificYokisLightControlCluster.cluster_id, min_value=0, max_value=4233600, step=1, entity_type=EntityType.CONFIG, translation_key='blink_off_time', fallback_name='Blink off time')
    .enum(attribute_name=ManuSpecificYokisLightControlCluster.AttributeDefs.state_after_blink.name, cluster_id=ManuSpecificYokisLightControlCluster.cluster_id, enum_class=StateAfterBlink, entity_type=EntityType.CONFIG, translation_key='state_after_blink', fallback_name='State after blink')
    .switch(attribute_name=ManuSpecificYokisLightControlCluster.AttributeDefs.e_nc_command.name, cluster_id=ManuSpecificYokisLightControlCluster.cluster_id, entity_type=EntityType.CONFIG, translation_key='enable_nc_command', fallback_name='Enable nc command')
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
    .command_button(command_name=ManuSpecificYokisLightControlCluster.ServerCommandDefs.long_on.name, cluster_id=ManuSpecificYokisLightControlCluster.cluster_id, entity_type=EntityType.CONFIG, translation_key='long_on_command', fallback_name='Long on command', unique_id_suffix='long_on_command')
    .command_button(command_name=ManuSpecificYokisDeviceCluster.ServerCommandDefs.reset_to_factory_settings.name, cluster_id=ManuSpecificYokisDeviceCluster.cluster_id, command_args=(0,), entity_type=EntityType.CONFIG, initially_disabled=True, translation_key='reset_to_factory_settings_factory_reset', fallback_name='Reset to factory settings (factory reset)', unique_id_suffix='reset_to_factory_settings_factory_reset')
    .command_button(command_name=ManuSpecificYokisDeviceCluster.ServerCommandDefs.reset_to_factory_settings.name, cluster_id=ManuSpecificYokisDeviceCluster.cluster_id, command_args=(1,), entity_type=EntityType.CONFIG, initially_disabled=True, translation_key='reset_to_factory_settings_configuration_reset', fallback_name='Reset to factory settings (configuration reset)', unique_id_suffix='reset_to_factory_settings_configuration_reset')
    .command_button(command_name=ManuSpecificYokisDeviceCluster.ServerCommandDefs.reset_to_factory_settings.name, cluster_id=ManuSpecificYokisDeviceCluster.cluster_id, command_args=(2,), entity_type=EntityType.CONFIG, initially_disabled=True, translation_key='reset_to_factory_settings_network_reset', fallback_name='Reset to factory settings (network reset)', unique_id_suffix='reset_to_factory_settings_network_reset')
    .command_button(command_name=ManuSpecificYokisDeviceCluster.ServerCommandDefs.relaunch_ble_advert.name, cluster_id=ManuSpecificYokisDeviceCluster.cluster_id, entity_type=EntityType.CONFIG, translation_key='relaunch_ble_advert', fallback_name='Relaunch ble advert', unique_id_suffix='relaunch_ble_advert')
    .command_button(command_name=ManuSpecificYokisInputCluster.ServerCommandDefs.send_press.name, cluster_id=ManuSpecificYokisInputCluster.cluster_id, entity_type=EntityType.CONFIG, translation_key='send_press', fallback_name='Send press', unique_id_suffix='send_press')
    .command_button(command_name=ManuSpecificYokisInputCluster.ServerCommandDefs.send_release.name, cluster_id=ManuSpecificYokisInputCluster.cluster_id, entity_type=EntityType.CONFIG, translation_key='send_release', fallback_name='Send release', unique_id_suffix='send_release')
    # switch: standard clusters, ZHA's own entities
    # identify: standard clusters, ZHA's own entities
    # move_to_position_prop: z2m's own code, not generated
    # pulse_prop: z2m's own code, not generated
    # blink_prop: z2m's own code, not generated
    # deaf_blink_prop: z2m's own code, not generated
    # select_input_mode: z2m's own code, not generated
    .filter(no_builtin_quirk)
    .add_to_registry()
)
