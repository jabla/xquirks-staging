"""Aqara WT-A03E: Radiator thermostat W600.

Generated from the Zigbee2MQTT definition.
Data: zigbee-herdsman-converters, MIT, Copyright (c) 2018 Koen Kanters.
Status: generated, not verified on hardware.
Revision: f7592906
"""

import functools
import logging
import pathlib

import zhaquirks
from zha.quirks import DEVICE_REGISTRY, DeviceMatch
import zigpy.types as t
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef
from zigpy.zcl.clusters.hvac import Thermostat

from zhaquirks.builder import (
    EntityPlatform,
    EntityType,
    NumberDeviceClass,
    PERCENTAGE,
    QuirkBuilder,
    SensorStateClass,
    UnitOfTemperature,
)
from zhaquirks.xiaomi import XiaomiAqaraE1Cluster


class ManuSpecificLumiCluster(XiaomiAqaraE1Cluster):
    """manuSpecificLumi (z2m custom cluster) on zhaquirks' Xiaomi base."""

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        mode = ZCLAttributeDef(id=0x0009, type=t.uint8_t, manufacturer_code=0x115F)
        illuminance = ZCLAttributeDef(id=0x0112, type=t.uint32_t, manufacturer_code=0x115F)
        display_unit = ZCLAttributeDef(id=0x0114, type=t.uint8_t, manufacturer_code=0x115F)
        movement = ZCLAttributeDef(id=0x0118, type=t.uint8_t, access="r", manufacturer_code=0x115F)
        air_quality = ZCLAttributeDef(id=0x0129, type=t.uint8_t, manufacturer_code=0x115F)
        curtain_reverse = ZCLAttributeDef(id=0x0400, type=t.Bool, manufacturer_code=0x115F)
        curtain_hand_open = ZCLAttributeDef(id=0x0401, type=t.Bool, manufacturer_code=0x115F)
        curtain_calibrated = ZCLAttributeDef(id=0x0402, type=t.Bool, manufacturer_code=0x115F)
        calibrate = ZCLAttributeDef(id=0x0270, type=t.uint8_t, manufacturer_code=0x115F)
        calibrated = ZCLAttributeDef(id=0x027B, type=t.uint8_t, access="r", manufacturer_code=0x115F)
        temperature_control_abnormal_notification = ZCLAttributeDef(id=0x0274, type=t.uint8_t, manufacturer_code=0x115F)
        display_flip = ZCLAttributeDef(id=0x0330, type=t.uint8_t, manufacturer_code=0x115F)
        window_detection = ZCLAttributeDef(id=0x0273, type=t.uint8_t, manufacturer_code=0x115F)
        child_lock = ZCLAttributeDef(id=0x0277, type=t.uint8_t, manufacturer_code=0x115F)
        anti_freeze_temperature = ZCLAttributeDef(id=0x0279, type=t.uint32_t, manufacturer_code=0x115F)
        position = ZCLAttributeDef(id=0x0360, type=t.Single, access="r", manufacturer_code=0x115F)

    # The struct keys of zhaquirks' Xiaomi base and the endpoint cluster it writes each one to.
    STRUCT_TARGETS = {
        "battery_voltage_mV": "power",
        "battery_percentage": "power",
        "temperature_measurement": "temperature",
        "humidity_measurement": "humidity",
        "pressure_measurement": "pressure",
        "pressure_measurement_precision": "pressure",
        "power": "electrical_measurement",
        "voltage": "electrical_measurement",
        "consumption": "smartenergy_metering",
        "illuminance_measurement": "illuminance",
        "tvoc_measurement": "voc_level",
        "smoke": "ias_zone",
    }

    def _parse_aqara_attributes(self, value):
        """Only the struct values whose cluster the endpoint has: the base class stops at a missing one."""
        attributes = super()._parse_aqara_attributes(value)
        return {key: v for key, v in attributes.items() if key not in self.STRUCT_TARGETS or hasattr(self.endpoint, self.STRUCT_TARGETS[key])}


class Calibrated(t.enum8):
    """calibrated values (z2m)."""

    not_ready = 0x00
    ready = 0x01
    error = 0x02
    in_progress = 0x03



_LOGGER = logging.getLogger(__name__)
_SHIPPED = pathlib.Path(zhaquirks.__file__).resolve().parent
_STEPPED_BACK: set = set()

# The Zigbee fingerprints (manufacturer, model) this quirk is for; None matches any manufacturer.
FINGERPRINTS = [(None, 'lumi.airrtc.aeu005')]
# Names that a model-only fingerprint would catch but Zigbee2MQTT gives to other devices.
CLAIMED_ELSEWHERE = set()
# The endpoints this quirk needs, each with the input clusters it puts there where Zigbee2MQTT names none.
ENDPOINTS = {1: (0x0201, 0xFCC0)}


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
    QuirkBuilder(None, 'lumi.airrtc.aeu005')
    .replaces(ManuSpecificLumiCluster)
    .binary_sensor(attribute_name=Thermostat.AttributeDefs.temp_setpoint_hold.name, cluster_id=Thermostat.cluster_id, entity_type=EntityType.STANDARD, translation_key='override_active', fallback_name='Manual override')
    .write_attr_button(attribute_name=ManuSpecificLumiCluster.AttributeDefs.calibrate.name, cluster_id=ManuSpecificLumiCluster.cluster_id, attribute_value=1, entity_type=EntityType.CONFIG, translation_key='calibrate', fallback_name='Calibrate')
    .enum(attribute_name=ManuSpecificLumiCluster.AttributeDefs.calibrated.name, cluster_id=ManuSpecificLumiCluster.cluster_id, enum_class=Calibrated, entity_platform=EntityPlatform.SENSOR, entity_type=EntityType.STANDARD, translation_key='calibration_status', fallback_name='Calibration status')
    .switch(attribute_name=ManuSpecificLumiCluster.AttributeDefs.temperature_control_abnormal_notification.name, cluster_id=ManuSpecificLumiCluster.cluster_id, entity_type=EntityType.CONFIG, translation_key='temperature_control_abnormal_notification', fallback_name='Temperature control abnormal notification')
    .switch(attribute_name=ManuSpecificLumiCluster.AttributeDefs.display_flip.name, cluster_id=ManuSpecificLumiCluster.cluster_id, entity_type=EntityType.CONFIG, translation_key='display_flip', fallback_name='Display flip')
    .switch(attribute_name=ManuSpecificLumiCluster.AttributeDefs.window_detection.name, cluster_id=ManuSpecificLumiCluster.cluster_id, entity_type=EntityType.CONFIG, translation_key='open_window_detection', fallback_name='Open window detection')
    .switch(attribute_name=ManuSpecificLumiCluster.AttributeDefs.child_lock.name, cluster_id=ManuSpecificLumiCluster.cluster_id, entity_type=EntityType.CONFIG, translation_key='child_lock', fallback_name='Child lock')
    .number(attribute_name=ManuSpecificLumiCluster.AttributeDefs.anti_freeze_temperature.name, cluster_id=ManuSpecificLumiCluster.cluster_id, min_value=5, max_value=15, step=0.5, unit=UnitOfTemperature.CELSIUS, multiplier=0.01, device_class=NumberDeviceClass.TEMPERATURE, entity_type=EntityType.CONFIG, translation_key='anti_freeze_temperature', fallback_name='Anti freeze temperature')
    .sensor(attribute_name=ManuSpecificLumiCluster.AttributeDefs.position.name, cluster_id=ManuSpecificLumiCluster.cluster_id, state_class=SensorStateClass.MEASUREMENT, unit=PERCENTAGE, entity_type=EntityType.STANDARD, translation_key='z2m_valve_position', fallback_name='Valve position')
    # battery: z2m's own code, not generated
    # voltage: z2m's own code, not generated
    # valve_alarm: z2m's own code, not generated
    # window_open: z2m's own code, not generated
    # climate: standard clusters, ZHA's own entities
    # temperature_setpoint_hold_duration: standard cluster, no ZHA entity, not generated
    # local_temperature_internal: z2m's own code, not generated
    # sensor: z2m's own code, not generated
    # external_temperature_input: z2m's own code, not generated
    # external_temperature_problem: z2m's own code, not generated
    # preset_home_temperature: z2m's own code, not generated
    # preset_away_temperature: z2m's own code, not generated
    # preset_sleep_temperature: z2m's own code, not generated
    # preset_vacation_temperature: z2m's own code, not generated
    # preset_wind_down_temperature: z2m's own code, not generated
    # weekly_schedule_sunday: z2m's own code, not generated
    # weekly_schedule_monday: z2m's own code, not generated
    # weekly_schedule_tuesday: z2m's own code, not generated
    # weekly_schedule_wednesday: z2m's own code, not generated
    # weekly_schedule_thursday: z2m's own code, not generated
    # weekly_schedule_friday: z2m's own code, not generated
    # weekly_schedule_saturday: z2m's own code, not generated
    # schedule_upload_status: z2m's own code, not generated
    # save_schedule: z2m's own code, not generated
    # clear_schedule: z2m's own code, not generated
    # identify: standard clusters, ZHA's own entities
    .filter(no_builtin_quirk)
    .add_to_registry()
)
