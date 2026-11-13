"""SONOFF TP-WGZBA: Zigbee thermostat panel.

Generated from the Zigbee2MQTT definition.
Data: zigbee-herdsman-converters, MIT, Copyright (c) 2018 Koen Kanters.
Status: generated, not verified on hardware.
Revision: a76454ca
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
    QuirkBuilder,
    UnitOfTemperature,
)
from zhaquirks.clusters import CustomCluster


class CustomSonoffTpWgzbaCluster(CustomCluster):
    """customSonoffTpWgzba (z2m custom cluster)."""

    cluster_id = 0xFC11

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        child_lock = ZCLAttributeDef(id=0x0000, type=t.Bool, manufacturer_code=None)
        bt_pairing_broadcast_req = ZCLAttributeDef(id=0x0029, type=t.uint8_t, manufacturer_code=None)
        open_window = ZCLAttributeDef(id=0x6000, type=t.Bool, manufacturer_code=None)
        frost_protection_temperature = ZCLAttributeDef(id=0x6002, type=t.int16s, manufacturer_code=None)
        temporary_mode = ZCLAttributeDef(id=0x6014, type=t.uint8_t, manufacturer_code=None)
        temporary_mode_time = ZCLAttributeDef(id=0x6015, type=t.uint32_t, manufacturer_code=None)
        temporary_mode_temp = ZCLAttributeDef(id=0x6016, type=t.int16s, manufacturer_code=None)
        weekly_schedule_active_num = ZCLAttributeDef(id=0x601D, type=t.uint8_t, manufacturer_code=None)
        # hvac_message_notification 0x6030: ARRAY, attribute only
        # temperature_control_threshold 0x601F: STRUCT, attribute only
        radar_sensitivity_level = ZCLAttributeDef(id=0x6020, type=t.uint8_t, manufacturer_code=None)
        radar_do_not_disturb_enable = ZCLAttributeDef(id=0x6021, type=t.Bool, manufacturer_code=None)
        # radar_do_not_disturb_period 0x6022: STRUCT, attribute only
        screen_working_brightness = ZCLAttributeDef(id=0x6023, type=t.uint8_t, manufacturer_code=None)
        screen_standby_brightness = ZCLAttributeDef(id=0x6024, type=t.uint8_t, manufacturer_code=None)
        screen_night_standby_brightness = ZCLAttributeDef(id=0x6025, type=t.uint8_t, manufacturer_code=None)
        screen_night_mode_enable = ZCLAttributeDef(id=0x6026, type=t.Bool, manufacturer_code=None)
        # screen_night_mode_period 0x6027: STRUCT, attribute only
        relay_output_type = ZCLAttributeDef(id=0x6028, type=t.bitmap8, manufacturer_code=None)
        # remote_attribute_linkage 0x601E: ARRAY, attribute only
        current_ntc_temperature = ZCLAttributeDef(id=0x6031, type=t.int16s, access="r", manufacturer_code=None)
        overheat_protection_temperature = ZCLAttributeDef(id=0x6032, type=t.int16s, manufacturer_code=None)
        overheat_protection_enable = ZCLAttributeDef(id=0x6034, type=t.Bool, manufacturer_code=None)
        radar_enable = ZCLAttributeDef(id=0x6035, type=t.Bool, manufacturer_code=None)


class RadarSensitivity(t.enum8):
    """radar_sensitivity values (z2m)."""

    low = 0x00
    medium = 0x01
    high = 0x02



_LOGGER = logging.getLogger(__name__)
_SHIPPED = pathlib.Path(zhaquirks.__file__).resolve().parent
_STEPPED_BACK: set = set()

# The Zigbee fingerprints (manufacturer, model) this quirk is for; None matches any manufacturer.
FINGERPRINTS = [(None, 'TP-WGZBA')]
# Names that a model-only fingerprint would catch but Zigbee2MQTT gives to other devices.
CLAIMED_ELSEWHERE = set()
# The endpoints this quirk needs, each with the input clusters it puts there where Zigbee2MQTT names none.
ENDPOINTS = {1: (0x0000, 0xFC11)}


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
    QuirkBuilder(None, 'TP-WGZBA')
    .replaces(CustomSonoffTpWgzbaCluster)
    .switch(attribute_name=CustomSonoffTpWgzbaCluster.AttributeDefs.child_lock.name, cluster_id=CustomSonoffTpWgzbaCluster.cluster_id, entity_type=EntityType.CONFIG, translation_key='child_lock', fallback_name='Child lock')
    .switch(attribute_name=CustomSonoffTpWgzbaCluster.AttributeDefs.open_window.name, cluster_id=CustomSonoffTpWgzbaCluster.cluster_id, entity_type=EntityType.CONFIG, translation_key='open_window', fallback_name='Open window')
    .number(attribute_name=CustomSonoffTpWgzbaCluster.AttributeDefs.frost_protection_temperature.name, cluster_id=CustomSonoffTpWgzbaCluster.cluster_id, min_value=5, max_value=15, step=0.5, unit=UnitOfTemperature.CELSIUS, multiplier=0.01, device_class=NumberDeviceClass.TEMPERATURE, entity_type=EntityType.CONFIG, translation_key='frost_protection_temperature', fallback_name='Frost protection temperature')
    .switch(attribute_name=CustomSonoffTpWgzbaCluster.AttributeDefs.overheat_protection_enable.name, cluster_id=CustomSonoffTpWgzbaCluster.cluster_id, entity_type=EntityType.CONFIG, translation_key='ntc_overheat_protection', fallback_name='NTC overheat protection')
    .number(attribute_name=CustomSonoffTpWgzbaCluster.AttributeDefs.overheat_protection_temperature.name, cluster_id=CustomSonoffTpWgzbaCluster.cluster_id, min_value=20, max_value=50, step=0.5, unit=UnitOfTemperature.CELSIUS, multiplier=0.01, device_class=NumberDeviceClass.TEMPERATURE, entity_type=EntityType.CONFIG, translation_key='ntc_overheat_protection_temperature', fallback_name='NTC overheat protection temperature')
    .switch(attribute_name=CustomSonoffTpWgzbaCluster.AttributeDefs.radar_enable.name, cluster_id=CustomSonoffTpWgzbaCluster.cluster_id, entity_type=EntityType.CONFIG, translation_key='radar_detection', fallback_name='Radar detection')
    .enum(attribute_name=CustomSonoffTpWgzbaCluster.AttributeDefs.radar_sensitivity_level.name, cluster_id=CustomSonoffTpWgzbaCluster.cluster_id, enum_class=RadarSensitivity, entity_type=EntityType.CONFIG, translation_key='radar_sensitivity', fallback_name='Radar sensitivity')
    .switch(attribute_name=CustomSonoffTpWgzbaCluster.AttributeDefs.radar_do_not_disturb_enable.name, cluster_id=CustomSonoffTpWgzbaCluster.cluster_id, entity_type=EntityType.CONFIG, translation_key='radar_do_not_disturb', fallback_name='Radar do not disturb')
    .number(attribute_name=CustomSonoffTpWgzbaCluster.AttributeDefs.screen_standby_brightness.name, cluster_id=CustomSonoffTpWgzbaCluster.cluster_id, min_value=0, max_value=8, step=1, entity_type=EntityType.CONFIG, translation_key='standby_brightness', fallback_name='Standby brightness')
    .number(attribute_name=CustomSonoffTpWgzbaCluster.AttributeDefs.screen_working_brightness.name, cluster_id=CustomSonoffTpWgzbaCluster.cluster_id, min_value=0, max_value=8, step=1, entity_type=EntityType.CONFIG, translation_key='active_brightness', fallback_name='Active brightness')
    .switch(attribute_name=CustomSonoffTpWgzbaCluster.AttributeDefs.screen_night_mode_enable.name, cluster_id=CustomSonoffTpWgzbaCluster.cluster_id, entity_type=EntityType.CONFIG, translation_key='night_mode', fallback_name='Night mode')
    .number(attribute_name=CustomSonoffTpWgzbaCluster.AttributeDefs.screen_night_standby_brightness.name, cluster_id=CustomSonoffTpWgzbaCluster.cluster_id, min_value=0, max_value=8, step=1, entity_type=EntityType.CONFIG, translation_key='night_brightness', fallback_name='Night brightness')
    .switch(attribute_name=CustomSonoffTpWgzbaCluster.AttributeDefs.bt_pairing_broadcast_req.name, cluster_id=CustomSonoffTpWgzbaCluster.cluster_id, entity_type=EntityType.CONFIG, translation_key='bluetooth_pairing', fallback_name='Bluetooth pairing')
    .command_button(command_name=Basic.ServerCommandDefs.reset_fact_default.name, cluster_id=Basic.cluster_id, entity_type=EntityType.CONFIG, initially_disabled=True, translation_key='factory_reset', fallback_name='Factory reset', unique_id_suffix='factory_reset')
    # open_window_detected: z2m's own code, not generated
    # schedule_active_group: z2m's own code, not generated
    # schedule_group_to_edit: z2m's own code, not generated
    # weekly_schedule_sunday: z2m's own code, not generated
    # weekly_schedule_monday: z2m's own code, not generated
    # weekly_schedule_tuesday: z2m's own code, not generated
    # weekly_schedule_wednesday: z2m's own code, not generated
    # weekly_schedule_thursday: z2m's own code, not generated
    # weekly_schedule_friday: z2m's own code, not generated
    # weekly_schedule_saturday: z2m's own code, not generated
    # temporary_mode_mode: z2m's own code, not generated
    # temporary_mode_duration: z2m's own code, not generated
    # temporary_mode_target_temperature: z2m's own code, not generated
    # temperature_sensor_select: z2m's own code, not generated
    # external_temperature_input: z2m's own code, not generated
    # hysteresis_low: z2m's own code, not generated
    # hysteresis_high: z2m's own code, not generated
    # hydronic_underfloor_heating_relay_output: z2m's own code, not generated
    # boiler_dry_contact_output: z2m's own code, not generated
    # ntc_temperature: z2m's own code, not generated
    # radar_do_not_disturb_period: z2m's own code, not generated
    # night_mode_period: z2m's own code, not generated
    # read_temperature_control_history: z2m's own code, not generated
    # temperature_control_history: z2m's own code, not generated
    # climate: standard clusters, ZHA's own entities
    .filter(no_builtin_quirk)
    .add_to_registry()
)
