"""Namron 4512737/4512738: Touch thermostat.

Generated from the Zigbee2MQTT definition.
Data: zigbee-herdsman-converters, MIT, Copyright (c) 2018 Koen Kanters.
Status: generated, not verified on hardware.
Revision: 6e043097
"""

import functools
import logging
import pathlib

import zhaquirks
from zha.quirks import DEVICE_REGISTRY, DeviceMatch
import zigpy.types as t
from zigpy.zcl.foundation import ZCLAttributeDef
from zigpy.zcl.clusters.hvac import Thermostat

from zhaquirks.builder import (
    EntityType,
    NumberDeviceClass,
    QuirkBuilder,
    UnitOfTemperature,
    UnitOfTime,
)
from zhaquirks.clusters import CustomCluster


class HvacThermostatCluster(CustomCluster, Thermostat):
    """Thermostat with the attributes z2m adds."""

    class AttributeDefs(Thermostat.AttributeDefs):
        """Attribute definitions."""

        lcd_brightness = ZCLAttributeDef(id=0x1000, type=t.enum8, manufacturer_code=0x1224)
        button_vibration_level = ZCLAttributeDef(id=0x1001, type=t.enum8, manufacturer_code=0x1224)
        floor_sensor_type = ZCLAttributeDef(id=0x1002, type=t.enum8, manufacturer_code=0x1224)
        control_type = ZCLAttributeDef(id=0x1003, type=t.enum8, manufacturer_code=0x1224)
        power_up_status = ZCLAttributeDef(id=0x1004, type=t.enum8, manufacturer_code=0x1224)
        floor_sensor_calibration = ZCLAttributeDef(id=0x1005, type=t.int8s, manufacturer_code=0x1224)
        dry_time = ZCLAttributeDef(id=0x1006, type=t.uint8_t, manufacturer_code=0x1224)
        mode_after_dry = ZCLAttributeDef(id=0x1007, type=t.enum8, manufacturer_code=0x1224)
        temperature_display = ZCLAttributeDef(id=0x1008, type=t.enum8, manufacturer_code=0x1224)
        window_open_check2 = ZCLAttributeDef(id=0x1009, type=t.uint8_t, manufacturer_code=0x1224)
        hysterersis = ZCLAttributeDef(id=0x100A, type=t.uint8_t, manufacturer_code=0x1224)
        display_auto_off_enable = ZCLAttributeDef(id=0x100B, type=t.enum8, manufacturer_code=0x1224)
        alarm_air_temp_over_value = ZCLAttributeDef(id=0x2001, type=t.uint8_t, manufacturer_code=0x1224)
        away_mode_set = ZCLAttributeDef(id=0x2002, type=t.enum8, manufacturer_code=0x1224)


class LcdBrightness(t.enum8):
    """lcd_brightness values (z2m)."""

    low = 0x00
    mid = 0x01
    high = 0x02


class ButtonVibrationLevel(t.enum8):
    """button_vibration_level values (z2m)."""

    off = 0x00
    low = 0x01
    high = 0x02


class FloorSensorType(t.enum8):
    """floor_sensor_type values (z2m)."""

    Type_10k = 0x01
    Type_15k = 0x02
    Type_50k = 0x03
    Type_100k = 0x04
    Type_12k = 0x05


class Sensor(t.enum8):
    """sensor values (z2m)."""

    air = 0x00
    floor = 0x01
    both = 0x02


class PowerupStatus(t.enum8):
    """powerup_status values (z2m)."""

    default = 0x00
    last_status = 0x01


class ModeAfterDry(t.enum8):
    """mode_after_dry values (z2m)."""

    off = 0x00
    manual = 0x01
    auto = 0x02
    away = 0x03


class TemperatureDisplay(t.enum8):
    """temperature_display values (z2m)."""

    room = 0x00
    floor = 0x01



_LOGGER = logging.getLogger(__name__)
_SHIPPED = pathlib.Path(zhaquirks.__file__).resolve().parent
_STEPPED_BACK: set = set()

# The Zigbee fingerprints (manufacturer, model) this quirk is for; None matches any manufacturer.
FINGERPRINTS = [(None, '4512737'), (None, '4512738')]
# Names that a model-only fingerprint would catch but Zigbee2MQTT gives to other devices.
CLAIMED_ELSEWHERE = set()
# The endpoints this quirk needs, each with the input clusters it puts there where Zigbee2MQTT names none.
ENDPOINTS = {1: (0x0201,)}


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
    QuirkBuilder(None, '4512737')
    .applies_to(None, '4512738')
    .replaces(HvacThermostatCluster)
    .switch(attribute_name=HvacThermostatCluster.AttributeDefs.away_mode_set.name, cluster_id=HvacThermostatCluster.cluster_id, entity_type=EntityType.STANDARD, translation_key='away_mode', fallback_name='Away mode')
    .enum(attribute_name=HvacThermostatCluster.AttributeDefs.lcd_brightness.name, cluster_id=HvacThermostatCluster.cluster_id, enum_class=LcdBrightness, entity_type=EntityType.STANDARD, translation_key='lcd_brightness', fallback_name='LCD brightness')
    .enum(attribute_name=HvacThermostatCluster.AttributeDefs.button_vibration_level.name, cluster_id=HvacThermostatCluster.cluster_id, enum_class=ButtonVibrationLevel, entity_type=EntityType.STANDARD, translation_key='button_vibration_level', fallback_name='Button vibration level')
    .enum(attribute_name=HvacThermostatCluster.AttributeDefs.floor_sensor_type.name, cluster_id=HvacThermostatCluster.cluster_id, enum_class=FloorSensorType, entity_type=EntityType.STANDARD, translation_key='floor_sensor_type', fallback_name='Floor sensor type')
    .enum(attribute_name=HvacThermostatCluster.AttributeDefs.control_type.name, cluster_id=HvacThermostatCluster.cluster_id, enum_class=Sensor, entity_type=EntityType.STANDARD, translation_key='sensor', fallback_name='Sensor')
    .enum(attribute_name=HvacThermostatCluster.AttributeDefs.power_up_status.name, cluster_id=HvacThermostatCluster.cluster_id, enum_class=PowerupStatus, entity_type=EntityType.STANDARD, translation_key='powerup_status', fallback_name='Powerup status')
    .number(attribute_name=HvacThermostatCluster.AttributeDefs.floor_sensor_calibration.name, cluster_id=HvacThermostatCluster.cluster_id, min_value=-3, max_value=3, step=0.1, unit=UnitOfTemperature.CELSIUS, multiplier=0.1, device_class=NumberDeviceClass.TEMPERATURE_DELTA, entity_type=EntityType.STANDARD, translation_key='floor_sensor_calibration', fallback_name='Floor sensor calibration')
    .number(attribute_name=HvacThermostatCluster.AttributeDefs.dry_time.name, cluster_id=HvacThermostatCluster.cluster_id, min_value=5, max_value=100, unit=UnitOfTime.MINUTES, device_class=NumberDeviceClass.DURATION, entity_type=EntityType.STANDARD, translation_key='dry_time', fallback_name='Dry time')
    .enum(attribute_name=HvacThermostatCluster.AttributeDefs.mode_after_dry.name, cluster_id=HvacThermostatCluster.cluster_id, enum_class=ModeAfterDry, entity_type=EntityType.STANDARD, translation_key='mode_after_dry', fallback_name='Mode after dry')
    .enum(attribute_name=HvacThermostatCluster.AttributeDefs.temperature_display.name, cluster_id=HvacThermostatCluster.cluster_id, enum_class=TemperatureDisplay, entity_type=EntityType.STANDARD, translation_key='temperature_display', fallback_name='Temperature display')
    .number(attribute_name=HvacThermostatCluster.AttributeDefs.window_open_check2.name, cluster_id=HvacThermostatCluster.cluster_id, min_value=0, max_value=4, step=0.5, unit=UnitOfTemperature.CELSIUS, multiplier=0.5, device_class=NumberDeviceClass.TEMPERATURE, entity_type=EntityType.STANDARD, translation_key='window_open_check', fallback_name='Window open check')
    .number(attribute_name=HvacThermostatCluster.AttributeDefs.hysterersis.name, cluster_id=HvacThermostatCluster.cluster_id, min_value=0.5, max_value=5, step=0.1, unit=UnitOfTemperature.CELSIUS, multiplier=0.1, device_class=NumberDeviceClass.TEMPERATURE_DELTA, entity_type=EntityType.STANDARD, translation_key='hysterersis', fallback_name='Hysterersis')
    .number(attribute_name=HvacThermostatCluster.AttributeDefs.alarm_air_temp_over_value.name, cluster_id=HvacThermostatCluster.cluster_id, min_value=0, max_value=35, unit=UnitOfTemperature.CELSIUS, device_class=NumberDeviceClass.TEMPERATURE, entity_type=EntityType.STANDARD, translation_key='alarm_airtemp_overvalue', fallback_name='Alarm airtemp overvalue')
    # local_temperature: standard clusters, ZHA's own entities
    # outdoor_temperature: standard cluster, no ZHA entity, not generated
    # climate: standard clusters, ZHA's own entities
    # child_lock: standard clusters, ZHA's own entities
    # power: standard clusters or z2m's own code, not generated
    # current: standard clusters or z2m's own code, not generated
    # voltage: standard clusters or z2m's own code, not generated
    # energy: standard clusters or z2m's own code, not generated
    # display_auto_off_enabled: z2m's own code, not generated
    .filter(no_builtin_quirk)
    .add_to_registry()
)
