"""SONOFF MINI-ZB2GS: Zigbee dual-channel smart switch.

Generated from the Zigbee2MQTT definition.
Entity names follow ZHA's own quirk for this device where it shows the same feature.
Entity names follow zha-device-handlers#4075 (open pull request for this device).
Data: zigbee-herdsman-converters, MIT, Copyright (c) 2018 Koen Kanters.
Status: generated, not verified on hardware.
Revision: 78442be4
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
    NumberDeviceClass,
    QuirkBuilder,
    UnitOfTime,
)
from zhaquirks.clusters import CustomCluster


class CustomClusterEwelinkCluster(CustomCluster):
    """customClusterEwelink (z2m custom cluster)."""

    cluster_id = 0xFC11

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        network_led = ZCLAttributeDef(id=0x0001, type=t.Bool, manufacturer_code=None)
        back_light = ZCLAttributeDef(id=0x0002, type=t.Bool, manufacturer_code=None)
        fault_code = ZCLAttributeDef(id=0x0010, type=t.int32s, manufacturer_code=None)
        turbo_mode = ZCLAttributeDef(id=0x0012, type=t.int16s, manufacturer_code=None)
        delayed_power_on_state = ZCLAttributeDef(id=0x0014, type=t.Bool, manufacturer_code=None)
        delayed_power_on_time = ZCLAttributeDef(id=0x0015, type=t.uint16_t, manufacturer_code=None)
        external_trigger_mode = ZCLAttributeDef(id=0x0016, type=t.uint8_t, manufacturer_code=None)
        detach_relay_mode = ZCLAttributeDef(id=0x0017, type=t.Bool, manufacturer_code=None)
        device_work_mode = ZCLAttributeDef(id=0x0018, type=t.uint8_t, manufacturer_code=None)
        detach_relay_mode2 = ZCLAttributeDef(id=0x0019, type=t.bitmap8, manufacturer_code=None)
        motor_travel_calibration_action = ZCLAttributeDef(id=0x5001, type=t.uint8_t, manufacturer_code=None)
        lack_water_close_valve_timeout = ZCLAttributeDef(id=0x5011, type=t.uint16_t, manufacturer_code=None)
        motor_travel_calibration_status = ZCLAttributeDef(id=0x5012, type=t.uint8_t, manufacturer_code=None)
        motor_run_status = ZCLAttributeDef(id=0x5013, type=t.uint8_t, manufacturer_code=None)
        ac_current_current_value = ZCLAttributeDef(id=0x7004, type=t.uint32_t, manufacturer_code=None)
        ac_current_voltage_value = ZCLAttributeDef(id=0x7005, type=t.uint32_t, manufacturer_code=None)
        ac_current_power_value = ZCLAttributeDef(id=0x7006, type=t.uint32_t, manufacturer_code=None)
        outlet_control_protect = ZCLAttributeDef(id=0x7007, type=t.uint8_t, manufacturer_code=None)
        energy_today = ZCLAttributeDef(id=0x7009, type=t.uint32_t, manufacturer_code=None)
        energy_month = ZCLAttributeDef(id=0x700A, type=t.uint32_t, manufacturer_code=None)
        energy_yesterday = ZCLAttributeDef(id=0x700B, type=t.uint32_t, manufacturer_code=None)
        set_calibration_action = ZCLAttributeDef(id=0x001D, type=t.CharacterString, manufacturer_code=None)
        calibration_status = ZCLAttributeDef(id=0x001E, type=t.uint8_t, manufacturer_code=None)
        calibration_progress = ZCLAttributeDef(id=0x0020, type=t.uint8_t, manufacturer_code=None)
        min_brightness_threshold = ZCLAttributeDef(id=0x4001, type=t.uint8_t, manufacturer_code=None)
        max_brightness_threshold = ZCLAttributeDef(id=0x4002, type=t.uint8_t, manufacturer_code=None)
        dimming_light_rate = ZCLAttributeDef(id=0x4003, type=t.uint8_t, manufacturer_code=None)
        transition_time = ZCLAttributeDef(id=0x001F, type=t.uint32_t, manufacturer_code=None)
        level_for_calibration = ZCLAttributeDef(id=0x4006, type=t.uint8_t, access="r", manufacturer_code=None)
        # programmable_stepper_sequence 0x0022: ARRAY, attribute only
        detach_relay_action_event = ZCLAttributeDef(id=0x0028, type=t.uint8_t, access="r", manufacturer_code=None)



_LOGGER = logging.getLogger(__name__)
_SHIPPED = pathlib.Path(zhaquirks.__file__).resolve().parent
_STEPPED_BACK: set = set()

# The Zigbee fingerprints (manufacturer, model) this quirk is for; None matches any manufacturer.
FINGERPRINTS = [(None, 'MINI-ZB2GS'), ('SONOFF', 'MINI-ZB2GS')]
# Names that a model-only fingerprint would catch but Zigbee2MQTT gives to other devices.
CLAIMED_ELSEWHERE = set()
# The endpoints this quirk needs, each with the input clusters it puts there where Zigbee2MQTT names none.
ENDPOINTS = {1: (0xFC11,), 2: ()}


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
    QuirkBuilder(None, 'MINI-ZB2GS')
    .applies_to('SONOFF', 'MINI-ZB2GS')
    .replaces(CustomClusterEwelinkCluster)
    .replaces(CustomClusterEwelinkCluster, endpoint_id=2)
    .switch(attribute_name=CustomClusterEwelinkCluster.AttributeDefs.network_led.name, cluster_id=CustomClusterEwelinkCluster.cluster_id, entity_type=EntityType.CONFIG, translation_key='network_led', fallback_name='Network LED', unique_id_suffix='network_led')
    .switch(attribute_name=CustomClusterEwelinkCluster.AttributeDefs.turbo_mode.name, cluster_id=CustomClusterEwelinkCluster.cluster_id, on_value=20, off_value=9, entity_type=EntityType.CONFIG, translation_key='turbo_mode', fallback_name='Turbo mode', unique_id_suffix='turbo_mode')
    .switch(attribute_name=CustomClusterEwelinkCluster.AttributeDefs.delayed_power_on_state.name, cluster_id=CustomClusterEwelinkCluster.cluster_id, entity_type=EntityType.CONFIG, translation_key='delayed_power_on_state_channel_1', fallback_name='Delayed power on state channel 1')
    .switch(attribute_name=CustomClusterEwelinkCluster.AttributeDefs.delayed_power_on_state.name, cluster_id=CustomClusterEwelinkCluster.cluster_id, endpoint_id=2, entity_type=EntityType.CONFIG, translation_key='delayed_power_on_state_channel_2', fallback_name='Delayed power on state channel 2')
    .number(attribute_name=CustomClusterEwelinkCluster.AttributeDefs.delayed_power_on_time.name, cluster_id=CustomClusterEwelinkCluster.cluster_id, min_value=0.5, max_value=3599.5, step=0.5, unit=UnitOfTime.SECONDS, multiplier=0.5, device_class=NumberDeviceClass.DURATION, entity_type=EntityType.CONFIG, translation_key='delayed_power_on_time_l1', fallback_name='Delayed power on time L1')
    .number(attribute_name=CustomClusterEwelinkCluster.AttributeDefs.delayed_power_on_time.name, cluster_id=CustomClusterEwelinkCluster.cluster_id, endpoint_id=2, min_value=0.5, max_value=3599.5, step=0.5, unit=UnitOfTime.SECONDS, multiplier=0.5, device_class=NumberDeviceClass.DURATION, entity_type=EntityType.CONFIG, translation_key='delayed_power_on_time_l2', fallback_name='Delayed power on time L2')
    # action: standard clusters, ZHA's own entities
    # switch: standard clusters, ZHA's own entities
    # switch: standard clusters, ZHA's own entities
    # power_on_behavior_l1: standard clusters, ZHA's own entities
    # power_on_behavior_l2: standard clusters, ZHA's own entities
    # external_trigger_mode_l1: z2m's own code, not generated
    # external_trigger_mode_l2: z2m's own code, not generated
    # detach_relay_mode: z2m's own code, not generated
    # inching_control_set_l1: z2m's own code, not generated
    # inching_control_set_l2: z2m's own code, not generated
    # programmable_stepper_seq1: z2m's own code, not generated
    # programmable_stepper_seq2: z2m's own code, not generated
    # programmable_stepper_seq3: z2m's own code, not generated
    # programmable_stepper_seq4: z2m's own code, not generated
    .filter(no_builtin_quirk)
    .add_to_registry()
)
