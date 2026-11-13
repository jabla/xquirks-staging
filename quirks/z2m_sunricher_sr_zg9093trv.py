"""Sunricher SR-ZG9093TRV: Zigbee thermostatic radiator valve.

Generated from the Zigbee2MQTT definition.
Data: zigbee-herdsman-converters, MIT, Copyright (c) 2018 Koen Kanters.
Status: generated, not verified on hardware.
Revision: 1e5a5dd4
"""

import functools
import logging
import pathlib

import zhaquirks
from zha.quirks import DEVICE_REGISTRY, DeviceMatch
import zigpy.types as t
from zigpy.zcl.foundation import ZCLAttributeDef
from zigpy.zcl.clusters.hvac import Thermostat
from zigpy.zcl.clusters.hvac import UserInterface

from zhaquirks.builder import (
    EntityPlatform,
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

        screen_timeout = ZCLAttributeDef(id=0x100D, type=t.uint8_t, manufacturer_code=0x1224)
        anti_freezing_temp = ZCLAttributeDef(id=0x1005, type=t.uint8_t, manufacturer_code=0x1224)
        temperature_display_mode = ZCLAttributeDef(id=0x1008, type=t.enum8, manufacturer_code=0x1224)
        window_open_check = ZCLAttributeDef(id=0x1009, type=t.uint8_t, manufacturer_code=0x1224)
        hysteresis = ZCLAttributeDef(id=0x100A, type=t.uint8_t, manufacturer_code=0x1224)
        window_open_flag = ZCLAttributeDef(id=0x100B, type=t.enum8, manufacturer_code=0x1224)
        forced_heating_time = ZCLAttributeDef(id=0x100E, type=t.uint8_t, manufacturer_code=0x1224)
        error_code = ZCLAttributeDef(id=0x2003, type=t.bitmap8, manufacturer_code=0x1224)
        away_or_boost_mode = ZCLAttributeDef(id=0x2002, type=t.enum8, manufacturer_code=0x1224)


class TemperatureDisplayMode(t.enum8):
    """temperature_display_mode values (z2m)."""

    set_temp = 0x01
    room_temp = 0x02


class ErrorCode(t.enum8):
    """error_code values (z2m)."""

    no_error = 0x00
    motor_error = 0x04
    motor_timeout = 0x05


class TemperatureDisplayUnit(t.enum8):
    """temperature_display_unit values (z2m)."""

    celsius = 0x00
    fahrenheit = 0x01



_LOGGER = logging.getLogger(__name__)
_SHIPPED = pathlib.Path(zhaquirks.__file__).resolve().parent
_STEPPED_BACK: set = set()

# The Zigbee fingerprints (manufacturer, model) this quirk is for; None matches any manufacturer.
FINGERPRINTS = [(None, 'ZG9340')]
# Names that a model-only fingerprint would catch but Zigbee2MQTT gives to other devices.
CLAIMED_ELSEWHERE = set()
# The endpoints this quirk needs, each with the input clusters it puts there where Zigbee2MQTT names none.
ENDPOINTS = {1: (0x0201, 0x0204)}


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
    QuirkBuilder(None, 'ZG9340')
    .replaces(HvacThermostatCluster)
    .number(attribute_name=HvacThermostatCluster.AttributeDefs.screen_timeout.name, cluster_id=HvacThermostatCluster.cluster_id, min_value=10, max_value=30, unit=UnitOfTime.SECONDS, device_class=NumberDeviceClass.DURATION, entity_type=EntityType.CONFIG, translation_key='screen_timeout', fallback_name='Screen timeout')
    .number(attribute_name=HvacThermostatCluster.AttributeDefs.anti_freezing_temp.name, cluster_id=HvacThermostatCluster.cluster_id, min_value=0, max_value=10, unit=UnitOfTemperature.CELSIUS, device_class=NumberDeviceClass.TEMPERATURE, entity_type=EntityType.CONFIG, translation_key='anti_freezing_temp', fallback_name='Anti freezing temp')
    .enum(attribute_name=HvacThermostatCluster.AttributeDefs.temperature_display_mode.name, cluster_id=HvacThermostatCluster.cluster_id, enum_class=TemperatureDisplayMode, entity_type=EntityType.STANDARD, translation_key='temperature_display_mode', fallback_name='Temperature display mode')
    .number(attribute_name=HvacThermostatCluster.AttributeDefs.window_open_check.name, cluster_id=HvacThermostatCluster.cluster_id, min_value=0, max_value=10, unit=UnitOfTemperature.CELSIUS, device_class=NumberDeviceClass.TEMPERATURE, entity_type=EntityType.CONFIG, translation_key='window_open_check', fallback_name='Window open check')
    .number(attribute_name=HvacThermostatCluster.AttributeDefs.hysteresis.name, cluster_id=HvacThermostatCluster.cluster_id, min_value=5, max_value=20, step=0.1, unit=UnitOfTemperature.CELSIUS, device_class=NumberDeviceClass.TEMPERATURE_DELTA, entity_type=EntityType.CONFIG, translation_key='hysteresis', fallback_name='Hysteresis')
    .binary_sensor(attribute_name=HvacThermostatCluster.AttributeDefs.window_open_flag.name, cluster_id=HvacThermostatCluster.cluster_id, entity_type=EntityType.STANDARD, translation_key='window_open_flag', fallback_name='Window open flag')
    .number(attribute_name=HvacThermostatCluster.AttributeDefs.forced_heating_time.name, cluster_id=HvacThermostatCluster.cluster_id, min_value=10, max_value=90, unit='10s', entity_type=EntityType.CONFIG, translation_key='forced_heating_time', fallback_name='Forced heating time')
    .enum(attribute_name=HvacThermostatCluster.AttributeDefs.error_code.name, cluster_id=HvacThermostatCluster.cluster_id, enum_class=ErrorCode, entity_platform=EntityPlatform.SENSOR, entity_type=EntityType.STANDARD, translation_key='error_code', fallback_name='Error code')
    .enum(attribute_name=UserInterface.AttributeDefs.temperature_display_mode.name, cluster_id=UserInterface.cluster_id, enum_class=TemperatureDisplayUnit, entity_type=EntityType.CONFIG, translation_key='temperature_display_unit', fallback_name='Temperature display unit', unique_id_suffix='thermostat_ui_temperature_display_mode')
    # battery: standard clusters, ZHA's own entities
    # identify: standard clusters, ZHA's own entities
    # schedule_sunday: standard clusters or z2m's own code, not generated
    # schedule_monday: standard clusters or z2m's own code, not generated
    # schedule_tuesday: standard clusters or z2m's own code, not generated
    # schedule_wednesday: standard clusters or z2m's own code, not generated
    # schedule_thursday: standard clusters or z2m's own code, not generated
    # schedule_friday: standard clusters or z2m's own code, not generated
    # schedule_saturday: standard clusters or z2m's own code, not generated
    # child_lock: standard clusters, ZHA's own entities
    # climate: standard clusters, ZHA's own entities
    .filter(no_builtin_quirk)
    .add_to_registry()
)
