"""Aqara FP310: Presence sensor FP310.

Generated from the Zigbee2MQTT definition.
Data: zigbee-herdsman-converters, MIT, Copyright (c) 2018 Koen Kanters.
Status: generated, not verified on hardware.
Revision: 13a8675e
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
    PERCENTAGE,
    QuirkBuilder,
    SensorDeviceClass,
    SensorStateClass,
    UnitOfLength,
    UnitOfTemperature,
    UnitOfTime,
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
        presence = ZCLAttributeDef(id=0x0142, type=t.uint8_t, access="r", manufacturer_code=0x115F)
        presence_sensitivity = ZCLAttributeDef(id=0x010C, type=t.uint8_t, manufacturer_code=0x115F)
        absence_delay_timer = ZCLAttributeDef(id=0x0197, type=t.uint32_t, manufacturer_code=0x115F)
        ai_interference_source_selfidentification = ZCLAttributeDef(id=0x015E, type=t.uint8_t, manufacturer_code=0x115F)
        ai_sensitivity_adaptive = ZCLAttributeDef(id=0x015D, type=t.uint8_t, manufacturer_code=0x115F)
        temp_and_humidity_sampling = ZCLAttributeDef(id=0x0170, type=t.uint8_t, manufacturer_code=0x115F)
        temp_and_humidity_sampling_period = ZCLAttributeDef(id=0x0162, type=t.uint32_t, manufacturer_code=0x115F)
        temp_reporting_interval = ZCLAttributeDef(id=0x0163, type=t.uint32_t, manufacturer_code=0x115F)
        temp_reporting_threshold = ZCLAttributeDef(id=0x0164, type=t.uint16_t, manufacturer_code=0x115F)
        temp_reporting_mode = ZCLAttributeDef(id=0x0165, type=t.uint8_t, manufacturer_code=0x115F)
        humidity_reporting_interval = ZCLAttributeDef(id=0x016A, type=t.uint32_t, manufacturer_code=0x115F)
        humidity_reporting_threshold = ZCLAttributeDef(id=0x016B, type=t.uint16_t, manufacturer_code=0x115F)
        humidity_report_mode = ZCLAttributeDef(id=0x016C, type=t.uint8_t, manufacturer_code=0x115F)
        light_sampling = ZCLAttributeDef(id=0x0192, type=t.uint8_t, manufacturer_code=0x115F)
        light_sampling_period = ZCLAttributeDef(id=0x0193, type=t.uint32_t, manufacturer_code=0x115F)
        light_reporting_interval = ZCLAttributeDef(id=0x0194, type=t.uint32_t, manufacturer_code=0x115F)
        light_reporting_threshold = ZCLAttributeDef(id=0x0195, type=t.uint16_t, manufacturer_code=0x115F)
        light_report_mode = ZCLAttributeDef(id=0x0196, type=t.uint8_t, manufacturer_code=0x115F)
        target_distance = ZCLAttributeDef(id=0x015F, type=t.uint32_t, access="r", manufacturer_code=0x115F)
        led_disabled_night = ZCLAttributeDef(id=0x0203, type=t.Bool, manufacturer_code=0x115F)

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


class PresenceSensitivity(t.enum8):
    """presence_sensitivity values (z2m)."""

    low = 0x01
    medium = 0x02
    high = 0x03


class TempAndHumiditySampling(t.enum8):
    """temp_and_humidity_sampling values (z2m)."""

    off = 0x00
    low = 0x01
    medium = 0x02
    high = 0x03
    custom = 0x04


class TempReportingMode(t.enum8):
    """temp_reporting_mode values (z2m)."""

    threshold = 0x01
    reporting_interval = 0x02
    threshold_and_interval = 0x03


class HumidityReportMode(t.enum8):
    """humidity_report_mode values (z2m)."""

    threshold = 0x01
    reporting_interval = 0x02
    threshold_and_interval = 0x03


class LightSampling(t.enum8):
    """light_sampling values (z2m)."""

    off = 0x00
    low = 0x01
    medium = 0x02
    high = 0x03
    custom = 0x04


class LightReportMode(t.enum8):
    """light_report_mode values (z2m)."""

    threshold = 0x01
    reporting_interval = 0x02
    threshold_and_interval = 0x03



_LOGGER = logging.getLogger(__name__)
_SHIPPED = pathlib.Path(zhaquirks.__file__).resolve().parent
_STEPPED_BACK: set = set()

# The Zigbee fingerprints (manufacturer, model) this quirk is for; None matches any manufacturer.
FINGERPRINTS = [(None, 'lumi.sensor_occupy.acn1')]
# Names that a model-only fingerprint would catch but Zigbee2MQTT gives to other devices.
CLAIMED_ELSEWHERE = set()
# The endpoints this quirk needs, each with the input clusters it puts there where Zigbee2MQTT names none.
ENDPOINTS = {1: (0xFCC0,)}


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
    QuirkBuilder(None, 'lumi.sensor_occupy.acn1')
    .replaces(ManuSpecificLumiCluster)
    .binary_sensor(attribute_name=ManuSpecificLumiCluster.AttributeDefs.presence.name, cluster_id=ManuSpecificLumiCluster.cluster_id, entity_type=EntityType.STANDARD, translation_key='presence', fallback_name='Presence')
    .enum(attribute_name=ManuSpecificLumiCluster.AttributeDefs.presence_sensitivity.name, cluster_id=ManuSpecificLumiCluster.cluster_id, enum_class=PresenceSensitivity, entity_type=EntityType.STANDARD, translation_key='presence_sensitivity', fallback_name='Presence sensitivity')
    .number(attribute_name=ManuSpecificLumiCluster.AttributeDefs.absence_delay_timer.name, cluster_id=ManuSpecificLumiCluster.cluster_id, min_value=10, max_value=300, step=5, unit=UnitOfTime.SECONDS, device_class=NumberDeviceClass.DURATION, entity_type=EntityType.STANDARD, translation_key='absence_delay_timer', fallback_name='Absence delay timer')
    .switch(attribute_name=ManuSpecificLumiCluster.AttributeDefs.ai_interference_source_selfidentification.name, cluster_id=ManuSpecificLumiCluster.cluster_id, entity_type=EntityType.STANDARD, translation_key='ai_interference_source_selfidentification', fallback_name='Ai interference source selfidentification')
    .switch(attribute_name=ManuSpecificLumiCluster.AttributeDefs.ai_sensitivity_adaptive.name, cluster_id=ManuSpecificLumiCluster.cluster_id, entity_type=EntityType.STANDARD, translation_key='ai_sensitivity_adaptive', fallback_name='Ai sensitivity adaptive')
    .enum(attribute_name=ManuSpecificLumiCluster.AttributeDefs.temp_and_humidity_sampling.name, cluster_id=ManuSpecificLumiCluster.cluster_id, enum_class=TempAndHumiditySampling, entity_type=EntityType.STANDARD, translation_key='temp_and_humidity_sampling', fallback_name='Temp and humidity sampling')
    .number(attribute_name=ManuSpecificLumiCluster.AttributeDefs.temp_and_humidity_sampling_period.name, cluster_id=ManuSpecificLumiCluster.cluster_id, min_value=0.5, max_value=3600, step=0.5, unit=UnitOfTime.SECONDS, multiplier=0.001, device_class=NumberDeviceClass.DURATION, entity_type=EntityType.STANDARD, translation_key='temp_and_humidity_sampling_period', fallback_name='Temp and humidity sampling period')
    .number(attribute_name=ManuSpecificLumiCluster.AttributeDefs.temp_reporting_interval.name, cluster_id=ManuSpecificLumiCluster.cluster_id, min_value=600, max_value=3600, step=600, unit=UnitOfTime.SECONDS, multiplier=0.001, device_class=NumberDeviceClass.DURATION, entity_type=EntityType.STANDARD, translation_key='temp_reporting_interval', fallback_name='Temp reporting interval')
    .number(attribute_name=ManuSpecificLumiCluster.AttributeDefs.temp_reporting_threshold.name, cluster_id=ManuSpecificLumiCluster.cluster_id, min_value=0.2, max_value=3, step=0.1, unit=UnitOfTemperature.CELSIUS, multiplier=0.01, device_class=NumberDeviceClass.TEMPERATURE_DELTA, entity_type=EntityType.STANDARD, translation_key='temp_reporting_threshold', fallback_name='Temp reporting threshold')
    .enum(attribute_name=ManuSpecificLumiCluster.AttributeDefs.temp_reporting_mode.name, cluster_id=ManuSpecificLumiCluster.cluster_id, enum_class=TempReportingMode, entity_type=EntityType.STANDARD, translation_key='temp_reporting_mode', fallback_name='Temp reporting mode')
    .number(attribute_name=ManuSpecificLumiCluster.AttributeDefs.humidity_reporting_interval.name, cluster_id=ManuSpecificLumiCluster.cluster_id, min_value=600, max_value=3600, step=600, unit=UnitOfTime.SECONDS, multiplier=0.001, device_class=NumberDeviceClass.DURATION, entity_type=EntityType.STANDARD, translation_key='humidity_reporting_interval', fallback_name='Humidity reporting interval')
    .number(attribute_name=ManuSpecificLumiCluster.AttributeDefs.humidity_reporting_threshold.name, cluster_id=ManuSpecificLumiCluster.cluster_id, min_value=2, max_value=15, step=0.5, unit=PERCENTAGE, multiplier=0.01, entity_type=EntityType.STANDARD, translation_key='humidity_reporting_threshold', fallback_name='Humidity reporting threshold')
    .enum(attribute_name=ManuSpecificLumiCluster.AttributeDefs.humidity_report_mode.name, cluster_id=ManuSpecificLumiCluster.cluster_id, enum_class=HumidityReportMode, entity_type=EntityType.STANDARD, translation_key='humidity_report_mode', fallback_name='Humidity report mode')
    .enum(attribute_name=ManuSpecificLumiCluster.AttributeDefs.light_sampling.name, cluster_id=ManuSpecificLumiCluster.cluster_id, enum_class=LightSampling, entity_type=EntityType.STANDARD, translation_key='light_sampling', fallback_name='Light sampling')
    .number(attribute_name=ManuSpecificLumiCluster.AttributeDefs.light_sampling_period.name, cluster_id=ManuSpecificLumiCluster.cluster_id, min_value=0.5, max_value=3600, step=0.5, unit=UnitOfTime.SECONDS, multiplier=0.001, device_class=NumberDeviceClass.DURATION, entity_type=EntityType.STANDARD, translation_key='light_sampling_period', fallback_name='Light sampling period')
    .number(attribute_name=ManuSpecificLumiCluster.AttributeDefs.light_reporting_interval.name, cluster_id=ManuSpecificLumiCluster.cluster_id, min_value=20, max_value=3600, step=20, unit=UnitOfTime.SECONDS, multiplier=0.001, device_class=NumberDeviceClass.DURATION, entity_type=EntityType.STANDARD, translation_key='light_reporting_interval', fallback_name='Light reporting interval')
    .number(attribute_name=ManuSpecificLumiCluster.AttributeDefs.light_reporting_threshold.name, cluster_id=ManuSpecificLumiCluster.cluster_id, min_value=3, max_value=20, step=0.5, unit=PERCENTAGE, multiplier=0.01, entity_type=EntityType.STANDARD, translation_key='light_reporting_threshold', fallback_name='Light reporting threshold')
    .enum(attribute_name=ManuSpecificLumiCluster.AttributeDefs.light_report_mode.name, cluster_id=ManuSpecificLumiCluster.cluster_id, enum_class=LightReportMode, entity_type=EntityType.STANDARD, translation_key='light_report_mode', fallback_name='Light report mode')
    .sensor(attribute_name=ManuSpecificLumiCluster.AttributeDefs.target_distance.name, cluster_id=ManuSpecificLumiCluster.cluster_id, divisor=100, state_class=SensorStateClass.MEASUREMENT, device_class=SensorDeviceClass.DISTANCE, unit=UnitOfLength.METERS, entity_type=EntityType.STANDARD, translation_key='target_distance', fallback_name='Target distance')
    .switch(attribute_name=ManuSpecificLumiCluster.AttributeDefs.led_disabled_night.name, cluster_id=ManuSpecificLumiCluster.cluster_id, entity_type=EntityType.CONFIG, translation_key='led_disabled_night', fallback_name='LED disabled night')
    # battery: z2m's own code, not generated
    # voltage: Aqara struct (0x00F7), not generated yet
    # illuminance: standard clusters, ZHA's own entities
    # humidity: standard clusters, ZHA's own entities
    # temperature: standard clusters, ZHA's own entities
    # spatial_learning: z2m's own code, not generated
    # restart_device: z2m's own code, not generated
    # track_target_distance: z2m's own code, not generated
    # detection_range: z2m's own code, not generated
    # schedule_start_time: z2m's own code, not generated
    # schedule_end_time: z2m's own code, not generated
    # identify: standard clusters, ZHA's own entities
    .filter(no_builtin_quirk)
    .add_to_registry()
)
