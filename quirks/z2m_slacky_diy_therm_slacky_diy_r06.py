"""Slacky-DIY THERM_SLACKY_DIY_R06: Tuya Thermostat for Floor Heating with custom Firmware.

Generated from the Zigbee2MQTT definition.
Data: zigbee-herdsman-converters, MIT, Copyright (c) 2018 Koen Kanters.
Status: generated, not verified on hardware.
Revision: 203b7726
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

        sound = ZCLAttributeDef(id=0xF008, type=t.Bool, manufacturer_code=None)
        relay_type = ZCLAttributeDef(id=0xF00A, type=t.Bool, manufacturer_code=None)
        brightness_level = ZCLAttributeDef(id=0xF009, type=t.enum8, manufacturer_code=None)
        sensor = ZCLAttributeDef(id=0xF000, type=t.enum8, manufacturer_code=None)
        frost_protect_on_off = ZCLAttributeDef(id=0xF005, type=t.Bool, manufacturer_code=None)
        heat_protect = ZCLAttributeDef(id=0xF002, type=t.int16s, manufacturer_code=None)
        schedule_mode = ZCLAttributeDef(id=0xF007, type=t.enum8, manufacturer_code=None)


class BrightnessLevel(t.enum8):
    """brightness_level values (z2m)."""

    Off = 0x00
    Low = 0x01
    Medium = 0x02
    High = 0x03


class Sensor(t.enum8):
    """sensor values (z2m)."""

    Inner_IN = 0x00
    All_AL = 0x01
    Outer_OU = 0x02


class ScheduleMode(t.enum8):
    """schedule_mode values (z2m)."""

    Off = 0x00
    Mode_5_plus_2 = 0x01
    Mode_6_plus_1 = 0x02
    Mode_7 = 0x03



_LOGGER = logging.getLogger(__name__)
_SHIPPED = pathlib.Path(zhaquirks.__file__).resolve().parent
_STEPPED_BACK: set = set()

# The Zigbee fingerprints (manufacturer, model) this quirk is for; None matches any manufacturer.
FINGERPRINTS = [(None, 'Tuya_Thermostat_r06')]
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
    QuirkBuilder(None, 'Tuya_Thermostat_r06')
    .replaces(HvacThermostatCluster)
    .switch(attribute_name=HvacThermostatCluster.AttributeDefs.sound.name, cluster_id=HvacThermostatCluster.cluster_id, entity_type=EntityType.STANDARD, translation_key='sound', fallback_name='Sound')
    .switch(attribute_name=HvacThermostatCluster.AttributeDefs.relay_type.name, cluster_id=HvacThermostatCluster.cluster_id, on_value=0, off_value=1, entity_type=EntityType.STANDARD, translation_key='relay_type', fallback_name='Relay type')
    .enum(attribute_name=HvacThermostatCluster.AttributeDefs.brightness_level.name, cluster_id=HvacThermostatCluster.cluster_id, enum_class=BrightnessLevel, entity_type=EntityType.STANDARD, translation_key='brightness_level', fallback_name='Brightness level')
    .enum(attribute_name=HvacThermostatCluster.AttributeDefs.sensor.name, cluster_id=HvacThermostatCluster.cluster_id, enum_class=Sensor, entity_type=EntityType.STANDARD, translation_key='sensor', fallback_name='Sensor')
    .switch(attribute_name=HvacThermostatCluster.AttributeDefs.frost_protect_on_off.name, cluster_id=HvacThermostatCluster.cluster_id, entity_type=EntityType.STANDARD, translation_key='frost_protect_on_off', fallback_name='Frost protect on off')
    .number(attribute_name=HvacThermostatCluster.AttributeDefs.heat_protect.name, cluster_id=HvacThermostatCluster.cluster_id, min_value=35, max_value=60, step=1, unit=UnitOfTemperature.CELSIUS, multiplier=0.01, device_class=NumberDeviceClass.TEMPERATURE, entity_type=EntityType.STANDARD, translation_key='heat_protect', fallback_name='Heat protect')
    .enum(attribute_name=HvacThermostatCluster.AttributeDefs.schedule_mode.name, cluster_id=HvacThermostatCluster.cluster_id, enum_class=ScheduleMode, entity_type=EntityType.STANDARD, translation_key='schedule_mode', fallback_name='Schedule mode')
    # hysteresis_temperature: attribute minSetpointDeadBand has no known type, not generated
    # child_lock: standard clusters, ZHA's own entities
    # programming_operation_mode: standard cluster, no ZHA entity, not generated
    # max_heat_setpoint_limit: standard clusters, ZHA's own entities
    # climate: standard clusters, ZHA's own entities
    # schedule_monday: standard clusters or z2m's own code, not generated
    # schedule_sunday: standard clusters or z2m's own code, not generated
    # settings_reset: standard clusters or z2m's own code, not generated
    .filter(no_builtin_quirk)
    .add_to_registry()
)
