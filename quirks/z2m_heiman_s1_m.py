"""Heiman S1-M: Smart smoke alarm.

Generated from the Zigbee2MQTT definition.
Entity names follow zha-device-handlers#5458 (open pull request for this device).
Data: zigbee-herdsman-converters, MIT, Copyright (c) 2018 Koen Kanters.
Status: generated, not verified on hardware.
Revision: 80a50c4c
"""

import functools
import logging
import pathlib

import zhaquirks
from zha.quirks import DEVICE_REGISTRY, DeviceMatch
import zigpy.types as t
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef
from zigpy.zcl.clusters.security import IasZone

from zhaquirks.builder import (
    EntityPlatform,
    EntityType,
    NumberDeviceClass,
    QuirkBuilder,
    UnitOfTime,
)
from zhaquirks.clusters import CustomCluster


class HeimanClusterSpecialCluster(CustomCluster):
    """heimanClusterSpecial (z2m custom cluster)."""

    cluster_id = 0xFC90

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        sensor_preheating_state = ZCLAttributeDef(id=0x0000, type=t.enum8, manufacturer_code=0x120B)
        sensor_self_check_state = ZCLAttributeDef(id=0x0001, type=t.enum8, manufacturer_code=0x120B)
        sensor_fault_state = ZCLAttributeDef(id=0x0002, type=t.uint16_t, manufacturer_code=0x120B)
        sensor_pollution_level = ZCLAttributeDef(id=0x0003, type=t.uint8_t, manufacturer_code=0x120B)
        sensor_sensitivity_level = ZCLAttributeDef(id=0x0004, type=t.uint8_t, manufacturer_code=0x120B)
        sensor_prealarm_threshold = ZCLAttributeDef(id=0x0005, type=t.enum8, manufacturer_code=0x120B)
        sensor_life_state = ZCLAttributeDef(id=0x0006, type=t.enum8, manufacturer_code=0x120B)
        sensor_life_time = ZCLAttributeDef(id=0x0007, type=t.uint16_t, manufacturer_code=0x120B)
        remote_mute = ZCLAttributeDef(id=0x0008, type=t.uint8_t, manufacturer_code=0x120B)
        device_mute_state = ZCLAttributeDef(id=0x0009, type=t.bitmap16, manufacturer_code=0x120B)
        device_cascade_control_enable = ZCLAttributeDef(id=0x000A, type=t.bitmap8, manufacturer_code=0x120B)
        device_sound_tone_type = ZCLAttributeDef(id=0x000B, type=t.enum8, manufacturer_code=0x120B)
        # device_sound_control 0x000C: ARRAY, attribute only
        # device_blink_control 0x000D: ARRAY, attribute only
        smoke_ad_value = ZCLAttributeDef(id=0x000E, type=t.uint16_t, manufacturer_code=0x120B)
        smoke_alarm_type = ZCLAttributeDef(id=0x000F, type=t.enum8, manufacturer_code=0x120B)
        smoke_water_mist_state = ZCLAttributeDef(id=0x0010, type=t.enum8, manufacturer_code=0x120B)
        # smoke_sensor_data 0x0011: ARRAY, attribute only
        device_cascade_state = ZCLAttributeDef(id=0x0012, type=t.enum8, manufacturer_code=0x120B)
        sensor_prealarm_state = ZCLAttributeDef(id=0x0013, type=t.enum8, manufacturer_code=0x120B)
        smoke_level = ZCLAttributeDef(id=0x0016, type=t.uint8_t, access="r", manufacturer_code=0x120B)
        chamber_contamination = ZCLAttributeDef(id=0x0017, type=t.uint8_t, access="r", manufacturer_code=0x120B)
        smoke_concentation_unit = ZCLAttributeDef(id=0x0018, type=t.uint8_t, access="r", manufacturer_code=0x120B)
        emergency_state_control = ZCLAttributeDef(id=0x001C, type=t.uint8_t, manufacturer_code=0x120B)
        sensor_sampling_period = ZCLAttributeDef(id=0x001D, type=t.uint16_t, manufacturer_code=0x120B)
        occupany_sensor_work_mode = ZCLAttributeDef(id=0x001E, type=t.bitmap8, manufacturer_code=0x120B)
        occupied_to_occupied_interval = ZCLAttributeDef(id=0x001F, type=t.uint16_t, manufacturer_code=0x120B)
        occupied_to_occupied_duration = ZCLAttributeDef(id=0x0020, type=t.uint16_t, manufacturer_code=0x120B)
        radar_config_param_of_section1 = ZCLAttributeDef(id=0x0021, type=t.LVBytes, manufacturer_code=0x120B)
        radar_config_param_of_section2 = ZCLAttributeDef(id=0x0022, type=t.LVBytes, manufacturer_code=0x120B)
        radar_config_param_of_section3 = ZCLAttributeDef(id=0x0023, type=t.LVBytes, manufacturer_code=0x120B)
        radar_config_param_of_section4 = ZCLAttributeDef(id=0x0024, type=t.LVBytes, manufacturer_code=0x120B)
        radar_micro_threshold_param = ZCLAttributeDef(id=0x0025, type=t.LVBytes, manufacturer_code=0x120B)
        radar_persence_threshold_param = ZCLAttributeDef(id=0x0026, type=t.LVBytes, manufacturer_code=0x120B)
        radar_learning_control = ZCLAttributeDef(id=0x0027, type=t.uint16_t, manufacturer_code=0x120B)
        radar_learning_state = ZCLAttributeDef(id=0x0028, type=t.enum8, access="r", manufacturer_code=0x120B)
        radar_detection_target_range = ZCLAttributeDef(id=0x0029, type=t.uint16_t, access="r", manufacturer_code=0x120B)
        radar_detection_min_range = ZCLAttributeDef(id=0x002B, type=t.uint16_t, manufacturer_code=0x120B)
        radar_detection_max_range = ZCLAttributeDef(id=0x002C, type=t.uint16_t, manufacturer_code=0x120B)
        shielding_sensor_detection = ZCLAttributeDef(id=0x002D, type=t.uint16_t, manufacturer_code=0x120B)
        dew_point = ZCLAttributeDef(id=0x0033, type=t.int16s, access="r", manufacturer_code=0x120B)
        vpd = ZCLAttributeDef(id=0x0034, type=t.uint16_t, access="r", manufacturer_code=0x120B)
        thi = ZCLAttributeDef(id=0x0035, type=t.uint16_t, access="r", manufacturer_code=0x120B)
        heat_index = ZCLAttributeDef(id=0x0036, type=t.int16s, access="r", manufacturer_code=0x120B)
        sound_volume = ZCLAttributeDef(id=0x0047, type=t.uint8_t, manufacturer_code=0x120B)
        indicator_light_control = ZCLAttributeDef(id=0x1000, type=t.bitmap8, manufacturer_code=0x120B)
        indicator_light_not_disturb_start_time = ZCLAttributeDef(id=0x1001, type=t.uint16_t, manufacturer_code=0x120B)
        indicator_light_not_disturb_end_time = ZCLAttributeDef(id=0x1002, type=t.uint16_t, manufacturer_code=0x120B)
        indicator_light_not_disturb_enable = ZCLAttributeDef(id=0x1003, type=t.uint8_t, manufacturer_code=0x120B)
        heartbeat_indicator = ZCLAttributeDef(id=0x1004, type=t.uint8_t, manufacturer_code=0x120B)
        indicator_light_level_control_of2 = ZCLAttributeDef(id=0x1005, type=t.uint8_t, manufacturer_code=0x120B)
        indicator_light_level_control_of3 = ZCLAttributeDef(id=0x1006, type=t.uint8_t, manufacturer_code=0x120B)
        interconnectable = ZCLAttributeDef(id=0x1007, type=t.uint8_t, access="r", manufacturer_code=0x120B)
        indicator_light_on_off = ZCLAttributeDef(id=0x1008, type=t.uint8_t, manufacturer_code=0x120B)
        remote_self_test = ZCLAttributeDef(id=0x1009, type=t.uint8_t, access="r", manufacturer_code=0x120B)
        fixed_room_name = ZCLAttributeDef(id=0x100B, type=t.enum8, manufacturer_code=0x120B)
        language = ZCLAttributeDef(id=0x100C, type=t.enum8, manufacturer_code=0x120B)
        floors = ZCLAttributeDef(id=0x100E, type=t.enum8, manufacturer_code=0x120B)
        fixed_voices = ZCLAttributeDef(id=0x100F, type=t.enum8, manufacturer_code=0x120B)
        temperature_offset = ZCLAttributeDef(id=0x100D, type=t.int16s, manufacturer_code=0x120B)
        switch_type = ZCLAttributeDef(id=0x1010, type=t.enum8, manufacturer_code=0x120B)
        humidity_offset = ZCLAttributeDef(id=0x1012, type=t.int16s, manufacturer_code=0x120B)
        rebooted_count = ZCLAttributeDef(id=0x0019, type=t.uint16_t, access="r", manufacturer_code=0x120B)
        rejoined_count = ZCLAttributeDef(id=0x001A, type=t.uint16_t, access="r", manufacturer_code=0x120B)
        reported_packages = ZCLAttributeDef(id=0x001B, type=t.uint16_t, access="r", manufacturer_code=0x120B)
        illuminance_threshold = ZCLAttributeDef(id=0x002A, type=t.uint16_t, manufacturer_code=0x120B)
        mcu_software_version = ZCLAttributeDef(id=0x0030, type=t.uint8_t, access="r", manufacturer_code=0x120B)
        wifi_ssid = ZCLAttributeDef(id=0x2000, type=t.CharacterString, manufacturer_code=0x120B)
        wifi_password = ZCLAttributeDef(id=0x2001, type=t.CharacterString, manufacturer_code=0x120B)
        wifi_ssid_candidate = ZCLAttributeDef(id=0x2002, type=t.CharacterString, manufacturer_code=0x120B)
        wifi_password_candidate = ZCLAttributeDef(id=0x2003, type=t.CharacterString, manufacturer_code=0x120B)
        picture_quantity = ZCLAttributeDef(id=0x2004, type=t.uint8_t, manufacturer_code=0x120B)
        picture_quality = ZCLAttributeDef(id=0x2005, type=t.uint8_t, manufacturer_code=0x120B)
        server_address = ZCLAttributeDef(id=0x2006, type=t.CharacterString, access="r", manufacturer_code=0x120B)
        server_address_candidae = ZCLAttributeDef(id=0x2007, type=t.CharacterString, access="r", manufacturer_code=0x120B)
        server_port = ZCLAttributeDef(id=0x2008, type=t.uint8_t, access="r", manufacturer_code=0x120B)
        auth_token = ZCLAttributeDef(id=0x2009, type=t.CharacterString, access="r", manufacturer_code=0x120B)
        zone_capture_mode = ZCLAttributeDef(id=0x200A, type=t.uint8_t, access="r", manufacturer_code=0x120B)
        sensor_armed = ZCLAttributeDef(id=0x200B, type=t.uint8_t, manufacturer_code=0x120B)
        wifi_status = ZCLAttributeDef(id=0x200C, type=t.uint8_t, access="r", manufacturer_code=0x120B)
        wifi_candidate_status = ZCLAttributeDef(id=0x200D, type=t.uint8_t, access="r", manufacturer_code=0x120B)
        wifi_rssi = ZCLAttributeDef(id=0x200E, type=t.int8s, manufacturer_code=0x120B)
        server_status = ZCLAttributeDef(id=0x200F, type=t.int8s, access="r", manufacturer_code=0x120B)
        server_candidate_status = ZCLAttributeDef(id=0x2010, type=t.int8s, access="r", manufacturer_code=0x120B)
        camera_ready = ZCLAttributeDef(id=0x2013, type=t.int8s, access="r", manufacturer_code=0x120B)
        flash_light_brightness = ZCLAttributeDef(id=0x2012, type=t.int8s, access="r", manufacturer_code=0x120B)
        camera_mode = ZCLAttributeDef(id=0x2014, type=t.int8s, access="r", manufacturer_code=0x120B)
        light_effect = ZCLAttributeDef(id=0x2020, type=t.enum8, manufacturer_code=0x120B)
        light_speed = ZCLAttributeDef(id=0x2021, type=t.uint8_t, manufacturer_code=0x120B)
        light_intensity = ZCLAttributeDef(id=0x2022, type=t.uint8_t, manufacturer_code=0x120B)
        light_palette = ZCLAttributeDef(id=0x2023, type=t.enum8, manufacturer_code=0x120B)
        light_custom1 = ZCLAttributeDef(id=0x2024, type=t.uint8_t, manufacturer_code=0x120B)
        light_custom2 = ZCLAttributeDef(id=0x2025, type=t.uint8_t, manufacturer_code=0x120B)
        light_custom3 = ZCLAttributeDef(id=0x2026, type=t.uint8_t, manufacturer_code=0x120B)
        light_options = ZCLAttributeDef(id=0x2027, type=t.bitmap8, manufacturer_code=0x120B)
        light_effect_count = ZCLAttributeDef(id=0x2028, type=t.uint16_t, access="r", manufacturer_code=0x120B)
        light_pixel_count = ZCLAttributeDef(id=0x2029, type=t.uint16_t, manufacturer_code=0x120B)


class AlarmState(t.enum8):
    """alarm_state values (z2m)."""

    normal = 0x00
    prealarm = 0x01
    alarmed = 0x02
    critical_alarm = 0x03


class SmokeUnit(t.enum8):
    """smoke_unit values (z2m)."""

    dB_m = 0x00
    percent_ft_OBS = 0x01


class ChamberContamination(t.enum8):
    """chamber_contamination values (z2m)."""

    Normal = 0x00
    Light_contamination = 0x01
    Medium_contamination = 0x02
    Critical_contamination = 0x03


class SirenForAutomationOnly(t.enum8):
    """siren_for_automation_only values (z2m)."""

    stop = 0x00
    smoke_siren = 0x01
    co_siren = 0x02



_LOGGER = logging.getLogger(__name__)
_SHIPPED = pathlib.Path(zhaquirks.__file__).resolve().parent
_STEPPED_BACK: set = set()

# The Zigbee fingerprints (manufacturer, model) this quirk is for; None matches any manufacturer.
FINGERPRINTS = [(None, 'S1-M')]
# Names that a model-only fingerprint would catch but Zigbee2MQTT gives to other devices.
CLAIMED_ELSEWHERE = set()
# The endpoints this quirk needs, each with the input clusters it puts there where Zigbee2MQTT names none.
ENDPOINTS = {1: (0x0500, 0xFC90)}


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
    QuirkBuilder(None, 'S1-M')
    .replaces(HeimanClusterSpecialCluster)
    .enum(attribute_name=HeimanClusterSpecialCluster.AttributeDefs.sensor_prealarm_state.name, cluster_id=HeimanClusterSpecialCluster.cluster_id, enum_class=AlarmState, entity_platform=EntityPlatform.SENSOR, entity_type=EntityType.STANDARD, translation_key='alarm_state', fallback_name='Alarm state')
    .switch(attribute_name=HeimanClusterSpecialCluster.AttributeDefs.remote_mute.name, cluster_id=HeimanClusterSpecialCluster.cluster_id, entity_type=EntityType.STANDARD, translation_key='buzzer_manual_mute', fallback_name='Buzzer manual mute')
    .switch(attribute_name=HeimanClusterSpecialCluster.AttributeDefs.heartbeat_indicator.name, cluster_id=HeimanClusterSpecialCluster.cluster_id, entity_type=EntityType.STANDARD, translation_key='heartbeat_indicator', fallback_name='Heartbeat indicator')
    .binary_sensor(attribute_name=HeimanClusterSpecialCluster.AttributeDefs.interconnectable.name, cluster_id=HeimanClusterSpecialCluster.cluster_id, entity_type=EntityType.STANDARD, translation_key='interconnectable', fallback_name='Interconnectable')
    .sensor(attribute_name=HeimanClusterSpecialCluster.AttributeDefs.smoke_level.name, cluster_id=HeimanClusterSpecialCluster.cluster_id, divisor=100, entity_type=EntityType.STANDARD, translation_key='smoke_level', fallback_name='Smoke level')
    .enum(attribute_name=HeimanClusterSpecialCluster.AttributeDefs.smoke_concentation_unit.name, cluster_id=HeimanClusterSpecialCluster.cluster_id, enum_class=SmokeUnit, entity_platform=EntityPlatform.SENSOR, entity_type=EntityType.STANDARD, translation_key='smoke_unit', fallback_name='Smoke unit')
    .enum(attribute_name=HeimanClusterSpecialCluster.AttributeDefs.chamber_contamination.name, cluster_id=HeimanClusterSpecialCluster.cluster_id, enum_class=ChamberContamination, entity_platform=EntityPlatform.SENSOR, entity_type=EntityType.STANDARD, translation_key='chamber_contamination', fallback_name='Chamber contamination')
    .enum(attribute_name=HeimanClusterSpecialCluster.AttributeDefs.device_cascade_state.name, cluster_id=HeimanClusterSpecialCluster.cluster_id, enum_class=SirenForAutomationOnly, entity_type=EntityType.STANDARD, translation_key='siren_for_automation_only', fallback_name='Siren for automation only')
    .number(attribute_name=HeimanClusterSpecialCluster.AttributeDefs.shielding_sensor_detection.name, cluster_id=HeimanClusterSpecialCluster.cluster_id, min_value=0, max_value=20, unit=UnitOfTime.MINUTES, device_class=NumberDeviceClass.DURATION, entity_type=EntityType.STANDARD, translation_key='shielding_sensor_detection', fallback_name='Shielding sensor detection')
    .number(attribute_name=HeimanClusterSpecialCluster.AttributeDefs.temperature_offset.name, cluster_id=HeimanClusterSpecialCluster.cluster_id, min_value=-15, max_value=15, step=0.1, multiplier=0.01, entity_type=EntityType.STANDARD, translation_key='temperature_offset', fallback_name='Temperature offset')
    .number(attribute_name=HeimanClusterSpecialCluster.AttributeDefs.humidity_offset.name, cluster_id=HeimanClusterSpecialCluster.cluster_id, min_value=-15, max_value=15, step=0.1, multiplier=0.01, entity_type=EntityType.STANDARD, translation_key='humidity_offset', fallback_name='Humidity offset')
    .sensor(attribute_name=HeimanClusterSpecialCluster.AttributeDefs.reported_packages.name, cluster_id=HeimanClusterSpecialCluster.cluster_id, entity_type=EntityType.STANDARD, translation_key='reported_packages', fallback_name='Reported packages')
    .sensor(attribute_name=HeimanClusterSpecialCluster.AttributeDefs.rejoined_count.name, cluster_id=HeimanClusterSpecialCluster.cluster_id, entity_type=EntityType.STANDARD, translation_key='rejoined_count', fallback_name='Rejoined count')
    .sensor(attribute_name=HeimanClusterSpecialCluster.AttributeDefs.rebooted_count.name, cluster_id=HeimanClusterSpecialCluster.cluster_id, entity_type=EntityType.STANDARD, translation_key='rebooted_count', fallback_name='Rebooted count')
    .command_button(command_name=IasZone.ServerCommandDefs.init_test_mode.name, cluster_id=IasZone.cluster_id, command_args=(1, 1), entity_type=EntityType.STANDARD, translation_key='trigger_selftest', fallback_name='Trigger selftest', unique_id_suffix='trigger_selftest')
    # link_available: the same attribute on the same endpoint as another entity
    # battery: standard clusters, ZHA's own entities
    # identify: standard clusters, ZHA's own entities
    # temperature: standard clusters, ZHA's own entities
    # humidity: standard clusters, ZHA's own entities
    # smoke: standard clusters, ZHA's own entities
    # battery_low: standard clusters, ZHA's own entities
    # test: standard clusters, ZHA's own entities
    # fault_state: z2m's own code, not generated
    # muted: z2m's own code, not generated
    .filter(no_builtin_quirk)
    .add_to_registry()
)
