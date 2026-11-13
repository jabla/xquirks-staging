"""Slacky-DIY THERM_SLACKY_DIY_R0D: Tuya Thermostat for Floor Heating with custom Firmware.

Generated from the Zigbee2MQTT definition.
Data: zigbee-herdsman-converters, MIT, Copyright (c) 2018 Koen Kanters.
Status: generated, not verified on hardware.
Revision: 28a77a54
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
)
from zhaquirks.clusters import CustomCluster


class HvacThermostatCluster(CustomCluster, Thermostat):
    """Thermostat with the attributes z2m adds."""

    class AttributeDefs(Thermostat.AttributeDefs):
        """Attribute definitions."""

        brightness_level = ZCLAttributeDef(id=0xF009, type=t.enum8, manufacturer_code=None)
        screen_sleep_time = ZCLAttributeDef(id=0xF00F, type=t.enum8, manufacturer_code=None)
        led_indicator = ZCLAttributeDef(id=0xF010, type=t.Bool, manufacturer_code=None)
        frost_protect = ZCLAttributeDef(id=0xF001, type=t.int16s, manufacturer_code=None)
        heat_protect = ZCLAttributeDef(id=0xF002, type=t.int16s, manufacturer_code=None)
        eco_mode_cool_temperature = ZCLAttributeDef(id=0xF00B, type=t.int16s, manufacturer_code=None)
        sensor = ZCLAttributeDef(id=0xF000, type=t.enum8, manufacturer_code=None)


class BrightnessLevel(t.enum8):
    """brightness_level values (z2m)."""

    Off = 0x00
    Low = 0x01
    Medium = 0x02
    High = 0x03


class ScreenSleepTime(t.enum8):
    """screen_sleep_time values (z2m)."""

    Time_10s = 0x00
    Time_20s = 0x01
    Time_30s = 0x02
    Time_40s = 0x03
    Time_50s = 0x04
    Time_60s = 0x05


class Sensor(t.enum8):
    """sensor values (z2m)."""

    Inner_IN = 0x00
    All_AL = 0x01
    Outer_OU = 0x02



_LOGGER = logging.getLogger(__name__)
_SHIPPED = pathlib.Path(zhaquirks.__file__).resolve().parent
_STEPPED_BACK: set = set()

# The Zigbee fingerprints (manufacturer, model) this quirk is for; None matches any manufacturer.
FINGERPRINTS = [(None, 'Tuya_Thermostat_r0D')]
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
    QuirkBuilder(None, 'Tuya_Thermostat_r0D')
    .replaces(HvacThermostatCluster)
    .enum(attribute_name=HvacThermostatCluster.AttributeDefs.brightness_level.name, cluster_id=HvacThermostatCluster.cluster_id, enum_class=BrightnessLevel, entity_type=EntityType.STANDARD, translation_key='brightness_level', fallback_name='Brightness level')
    .enum(attribute_name=HvacThermostatCluster.AttributeDefs.screen_sleep_time.name, cluster_id=HvacThermostatCluster.cluster_id, enum_class=ScreenSleepTime, entity_type=EntityType.STANDARD, translation_key='screen_sleep_time', fallback_name='Screen sleep time')
    .switch(attribute_name=HvacThermostatCluster.AttributeDefs.led_indicator.name, cluster_id=HvacThermostatCluster.cluster_id, entity_type=EntityType.STANDARD, translation_key='led_indicator', fallback_name='LED indicator')
    .number(attribute_name=HvacThermostatCluster.AttributeDefs.frost_protect.name, cluster_id=HvacThermostatCluster.cluster_id, min_value=0, max_value=10, step=1, unit=UnitOfTemperature.CELSIUS, multiplier=0.01, device_class=NumberDeviceClass.TEMPERATURE, entity_type=EntityType.STANDARD, translation_key='frost_protect', fallback_name='Frost protect')
    .number(attribute_name=HvacThermostatCluster.AttributeDefs.heat_protect.name, cluster_id=HvacThermostatCluster.cluster_id, min_value=10, max_value=70, step=1, unit=UnitOfTemperature.CELSIUS, multiplier=0.01, device_class=NumberDeviceClass.TEMPERATURE, entity_type=EntityType.STANDARD, translation_key='heat_protect', fallback_name='Heat protect')
    .number(attribute_name=HvacThermostatCluster.AttributeDefs.eco_mode_cool_temperature.name, cluster_id=HvacThermostatCluster.cluster_id, min_value=10, max_value=30, step=1, unit=UnitOfTemperature.CELSIUS, multiplier=0.01, device_class=NumberDeviceClass.TEMPERATURE, entity_type=EntityType.STANDARD, translation_key='eco_mode_cool_temperature', fallback_name='Eco mode cool temperature')
    .enum(attribute_name=HvacThermostatCluster.AttributeDefs.sensor.name, cluster_id=HvacThermostatCluster.cluster_id, enum_class=Sensor, entity_type=EntityType.STANDARD, translation_key='sensor', fallback_name='Sensor')
    # hysteresis_temperature: attribute minSetpointDeadBand has no known type, not generated
    # child_lock: standard clusters, ZHA's own entities
    # programming_operation_mode: standard cluster, no ZHA entity, not generated
    # min_heat_setpoint_limit: standard clusters, ZHA's own entities
    # max_heat_setpoint_limit: standard clusters, ZHA's own entities
    # outdoor_temperature: standard cluster, no ZHA entity, not generated
    # climate: standard clusters, ZHA's own entities
    # schedule_monday: standard clusters or z2m's own code, not generated
    # schedule_tuesday: standard clusters or z2m's own code, not generated
    # schedule_wednesday: standard clusters or z2m's own code, not generated
    # schedule_thursday: standard clusters or z2m's own code, not generated
    # schedule_friday: standard clusters or z2m's own code, not generated
    # schedule_saturday: standard clusters or z2m's own code, not generated
    # schedule_sunday: standard clusters or z2m's own code, not generated
    # settings_reset: standard clusters or z2m's own code, not generated
    .filter(no_builtin_quirk)
    .add_to_registry()
)
