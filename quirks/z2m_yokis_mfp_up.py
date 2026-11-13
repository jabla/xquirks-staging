"""YOKIS MFP-UP: Remote module for pilot wire heating system.

Generated from the Zigbee2MQTT definition.
Data: zigbee-herdsman-converters, MIT, Copyright (c) 2018 Koen Kanters.
Status: generated, not verified on hardware.
Revision: fd8fe532
"""

import functools
import logging
import pathlib

import zhaquirks
from zha.quirks import DEVICE_REGISTRY, DeviceMatch
import zigpy.types as t
from zigpy.zcl.foundation import BaseAttributeDefs, BaseCommandDefs, Direction, ZCLAttributeDef, ZCLCommandDef

from zhaquirks.builder import (
    EntityPlatform,
    EntityType,
    QuirkBuilder,
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


class ManuSpecificYokisSubSystemCluster(CustomCluster):
    """manuSpecificYokisSubSystem (z2m custom cluster)."""

    cluster_id = 0xFC04

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        power_failure_mode = ZCLAttributeDef(id=0x0001, type=t.enum8, access="r", manufacturer_code=0x132D)


class ManuSpecificYokisPilotWireCluster(CustomCluster):
    """manuSpecificYokisPilotWire (z2m custom cluster)."""

    cluster_id = 0xFC0A

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        actual_order = ZCLAttributeDef(id=0x0000, type=t.uint8_t, access="r", manufacturer_code=0x132D)
        order_timer = ZCLAttributeDef(id=0x0001, type=t.uint32_t, access="r", manufacturer_code=0x132D)
        pre_order_timer = ZCLAttributeDef(id=0x0002, type=t.uint32_t, access="r", manufacturer_code=0x132D)
        timer_unit = ZCLAttributeDef(id=0x0003, type=t.uint8_t, access="r", manufacturer_code=0x132D)
        led_mode = ZCLAttributeDef(id=0x0004, type=t.uint8_t, access="r", manufacturer_code=0x132D)
        pilot_wire_relay_mode = ZCLAttributeDef(id=0x0005, type=t.uint8_t, access="r", manufacturer_code=0x132D)
        order_scrolling_mode = ZCLAttributeDef(id=0x0006, type=t.uint8_t, access="r", manufacturer_code=0x132D)
        order_number_supported = ZCLAttributeDef(id=0x0007, type=t.uint8_t, access="r", manufacturer_code=0x132D)
        fallback_order = ZCLAttributeDef(id=0x0008, type=t.uint8_t, access="r", manufacturer_code=0x132D)

    class ServerCommandDefs(BaseCommandDefs):
        """Command definitions (z2m's commands this cluster lacks)."""

        set_order = ZCLCommandDef(id=0x00, schema={'order': t.uint8_t}, direction=Direction.Client_to_Server, manufacturer_code=0x132D)
        toggle_order = ZCLCommandDef(id=0x01, schema={}, direction=Direction.Client_to_Server, manufacturer_code=0x132D)


class PowerFailureMode(t.enum8):
    """power_failure_mode values (z2m)."""

    last_state = 0x00
    off = 0x01
    on = 0x02
    blink = 0x03


class ActualOrder(t.enum8):
    """actual_order values (z2m)."""

    stop = 0x00
    frost_off = 0x01
    eco = 0x02
    confort_2 = 0x03
    confort_1 = 0x04
    confort = 0x05
    shortcut_error = 0x06
    temperature_error = 0x07


class TimerUnit(t.enum8):
    """timer_unit values (z2m)."""

    second = 0x00
    minutes = 0x01


class LedMode(t.enum8):
    """led_mode values (z2m)."""

    led_on = 0x00
    led_off = 0x01


class PilotWireRelayMode(t.enum8):
    """pilot_wire_relay_mode values (z2m)."""

    relay_on = 0x00
    relay_off = 0x01


class OrderScrollingMode(t.enum8):
    """order_scrolling_mode values (z2m)."""

    forward = 0x00
    backward = 0x01


class OrderNumberSupported(t.enum8):
    """order_number_supported values (z2m)."""

    four_orders = 0x00
    six_orders = 0x01


class FallbackOrder(t.enum8):
    """fallback_order values (z2m)."""

    stop = 0x00
    frost_off = 0x01
    eco = 0x02
    confort_2 = 0x03
    confort_1 = 0x04
    confort = 0x05



_LOGGER = logging.getLogger(__name__)
_SHIPPED = pathlib.Path(zhaquirks.__file__).resolve().parent
_STEPPED_BACK: set = set()

# The Zigbee fingerprints (manufacturer, model) this quirk is for; None matches any manufacturer.
FINGERPRINTS = [(None, 'MFP-UP')]
# Names that a model-only fingerprint would catch but Zigbee2MQTT gives to other devices.
CLAIMED_ELSEWHERE = set()
# The endpoints this quirk needs, each with the input clusters it puts there where Zigbee2MQTT names none.
ENDPOINTS = {1: (0xFC01, 0xFC04, 0xFC0A)}


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
    QuirkBuilder(None, 'MFP-UP')
    .replaces(ManuSpecificYokisPilotWireCluster)
    .replaces(ManuSpecificYokisSubSystemCluster)
    .replaces(ManuSpecificYokisDeviceCluster)
    .enum(attribute_name=ManuSpecificYokisSubSystemCluster.AttributeDefs.power_failure_mode.name, cluster_id=ManuSpecificYokisSubSystemCluster.cluster_id, enum_class=PowerFailureMode, entity_type=EntityType.CONFIG, translation_key='power_failure_mode', fallback_name='Power failure mode')
    .enum(attribute_name=ManuSpecificYokisPilotWireCluster.AttributeDefs.actual_order.name, cluster_id=ManuSpecificYokisPilotWireCluster.cluster_id, enum_class=ActualOrder, entity_platform=EntityPlatform.SENSOR, entity_type=EntityType.DIAGNOSTIC, translation_key='actual_order', fallback_name='Actual order')
    .number(attribute_name=ManuSpecificYokisPilotWireCluster.AttributeDefs.order_timer.name, cluster_id=ManuSpecificYokisPilotWireCluster.cluster_id, min_value=0, max_value=4294967295, step=1, entity_type=EntityType.CONFIG, translation_key='order_timer', fallback_name='Order timer')
    .number(attribute_name=ManuSpecificYokisPilotWireCluster.AttributeDefs.pre_order_timer.name, cluster_id=ManuSpecificYokisPilotWireCluster.cluster_id, min_value=0, max_value=4294967295, step=1, entity_type=EntityType.CONFIG, translation_key='pre_order_timer', fallback_name='Pre order timer')
    .enum(attribute_name=ManuSpecificYokisPilotWireCluster.AttributeDefs.timer_unit.name, cluster_id=ManuSpecificYokisPilotWireCluster.cluster_id, enum_class=TimerUnit, entity_type=EntityType.CONFIG, translation_key='timer_unit', fallback_name='Timer unit')
    .enum(attribute_name=ManuSpecificYokisPilotWireCluster.AttributeDefs.led_mode.name, cluster_id=ManuSpecificYokisPilotWireCluster.cluster_id, enum_class=LedMode, entity_type=EntityType.CONFIG, translation_key='led_mode', fallback_name='LED mode')
    .enum(attribute_name=ManuSpecificYokisPilotWireCluster.AttributeDefs.pilot_wire_relay_mode.name, cluster_id=ManuSpecificYokisPilotWireCluster.cluster_id, enum_class=PilotWireRelayMode, entity_type=EntityType.CONFIG, translation_key='pilot_wire_relay_mode', fallback_name='Pilot wire relay mode')
    .enum(attribute_name=ManuSpecificYokisPilotWireCluster.AttributeDefs.order_scrolling_mode.name, cluster_id=ManuSpecificYokisPilotWireCluster.cluster_id, enum_class=OrderScrollingMode, entity_type=EntityType.CONFIG, translation_key='order_scrolling_mode', fallback_name='Order scrolling mode')
    .enum(attribute_name=ManuSpecificYokisPilotWireCluster.AttributeDefs.order_number_supported.name, cluster_id=ManuSpecificYokisPilotWireCluster.cluster_id, enum_class=OrderNumberSupported, entity_type=EntityType.CONFIG, translation_key='order_number_supported', fallback_name='Order number supported')
    .enum(attribute_name=ManuSpecificYokisPilotWireCluster.AttributeDefs.fallback_order.name, cluster_id=ManuSpecificYokisPilotWireCluster.cluster_id, enum_class=FallbackOrder, entity_type=EntityType.CONFIG, translation_key='fallback_order', fallback_name='Fallback order')
    .command_button(command_name=ManuSpecificYokisPilotWireCluster.ServerCommandDefs.set_order.name, cluster_id=ManuSpecificYokisPilotWireCluster.cluster_id, command_args=(0,), entity_type=EntityType.CONFIG, translation_key='pilotwire_set_order_stop', fallback_name='Pilotwire set order (stop)', unique_id_suffix='pilotwire_set_order_stop')
    .command_button(command_name=ManuSpecificYokisPilotWireCluster.ServerCommandDefs.set_order.name, cluster_id=ManuSpecificYokisPilotWireCluster.cluster_id, command_args=(1,), entity_type=EntityType.CONFIG, translation_key='pilotwire_set_order_frost_off', fallback_name='Pilotwire set order (frost off)', unique_id_suffix='pilotwire_set_order_frost_off')
    .command_button(command_name=ManuSpecificYokisPilotWireCluster.ServerCommandDefs.set_order.name, cluster_id=ManuSpecificYokisPilotWireCluster.cluster_id, command_args=(2,), entity_type=EntityType.CONFIG, translation_key='pilotwire_set_order_eco', fallback_name='Pilotwire set order (eco)', unique_id_suffix='pilotwire_set_order_eco')
    .command_button(command_name=ManuSpecificYokisPilotWireCluster.ServerCommandDefs.set_order.name, cluster_id=ManuSpecificYokisPilotWireCluster.cluster_id, command_args=(3,), entity_type=EntityType.CONFIG, translation_key='pilotwire_set_order_confort_2', fallback_name='Pilotwire set order (confort 2)', unique_id_suffix='pilotwire_set_order_confort_2')
    .command_button(command_name=ManuSpecificYokisPilotWireCluster.ServerCommandDefs.set_order.name, cluster_id=ManuSpecificYokisPilotWireCluster.cluster_id, command_args=(4,), entity_type=EntityType.CONFIG, translation_key='pilotwire_set_order_confort_1', fallback_name='Pilotwire set order (confort 1)', unique_id_suffix='pilotwire_set_order_confort_1')
    .command_button(command_name=ManuSpecificYokisPilotWireCluster.ServerCommandDefs.set_order.name, cluster_id=ManuSpecificYokisPilotWireCluster.cluster_id, command_args=(5,), entity_type=EntityType.CONFIG, translation_key='pilotwire_set_order_confort', fallback_name='Pilotwire set order (confort)', unique_id_suffix='pilotwire_set_order_confort')
    .command_button(command_name=ManuSpecificYokisPilotWireCluster.ServerCommandDefs.toggle_order.name, cluster_id=ManuSpecificYokisPilotWireCluster.cluster_id, entity_type=EntityType.CONFIG, translation_key='pilotwire_toggle_order', fallback_name='Pilotwire toggle order', unique_id_suffix='pilotwire_toggle_order')
    .command_button(command_name=ManuSpecificYokisDeviceCluster.ServerCommandDefs.reset_to_factory_settings.name, cluster_id=ManuSpecificYokisDeviceCluster.cluster_id, command_args=(0,), entity_type=EntityType.CONFIG, initially_disabled=True, translation_key='reset_to_factory_settings_factory_reset', fallback_name='Reset to factory settings (factory reset)', unique_id_suffix='reset_to_factory_settings_factory_reset')
    .command_button(command_name=ManuSpecificYokisDeviceCluster.ServerCommandDefs.reset_to_factory_settings.name, cluster_id=ManuSpecificYokisDeviceCluster.cluster_id, command_args=(1,), entity_type=EntityType.CONFIG, initially_disabled=True, translation_key='reset_to_factory_settings_configuration_reset', fallback_name='Reset to factory settings (configuration reset)', unique_id_suffix='reset_to_factory_settings_configuration_reset')
    .command_button(command_name=ManuSpecificYokisDeviceCluster.ServerCommandDefs.reset_to_factory_settings.name, cluster_id=ManuSpecificYokisDeviceCluster.cluster_id, command_args=(2,), entity_type=EntityType.CONFIG, initially_disabled=True, translation_key='reset_to_factory_settings_network_reset', fallback_name='Reset to factory settings (network reset)', unique_id_suffix='reset_to_factory_settings_network_reset')
    .command_button(command_name=ManuSpecificYokisDeviceCluster.ServerCommandDefs.relaunch_ble_advert.name, cluster_id=ManuSpecificYokisDeviceCluster.cluster_id, entity_type=EntityType.CONFIG, translation_key='relaunch_ble_advert', fallback_name='Relaunch ble advert', unique_id_suffix='relaunch_ble_advert')
    # identify: standard clusters, ZHA's own entities
    # power: standard clusters, ZHA's own entities
    # current: standard clusters, ZHA's own entities
    # energy: standard clusters, ZHA's own entities
    .filter(no_builtin_quirk)
    .add_to_registry()
)
