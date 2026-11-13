"""Bosch BSIR-EZ: Outdoor siren.

Generated from the Zigbee2MQTT definition.
Data: zigbee-herdsman-converters, MIT, Copyright (c) 2018 Koen Kanters.
Status: generated, not verified on hardware.
Revision: ee98e472
"""

import functools
import logging
import pathlib

import zhaquirks
from zha.quirks import DEVICE_REGISTRY, DeviceMatch
import zigpy.types as t
from zigpy.zcl.foundation import Direction, ZCLAttributeDef, ZCLCommandDef
from zigpy.zcl.clusters.general import PowerConfiguration
from zigpy.zcl.clusters.security import IasWd
from zigpy.zcl.clusters.security import IasZone

from zhaquirks.builder import (
    EntityPlatform,
    EntityType,
    NumberDeviceClass,
    QuirkBuilder,
    SensorStateClass,
    UnitOfTime,
)
from zhaquirks.clusters import CustomCluster


class GenPowerCfgCluster(CustomCluster, PowerConfiguration):
    """PowerConfiguration with the attributes z2m adds."""

    class AttributeDefs(PowerConfiguration.AttributeDefs):
        """Attribute definitions."""

        solar_panel_voltage = ZCLAttributeDef(id=0xA000, type=t.uint16_t, manufacturer_code=0x1209)
        unknown_attribute = ZCLAttributeDef(id=0xA001, type=t.uint8_t, manufacturer_code=0x1209)
        primary_power_source = ZCLAttributeDef(id=0xA002, type=t.uint8_t, manufacturer_code=0x1209)


class SsIasZoneCluster(CustomCluster, IasZone):
    """IasZone with the attributes z2m adds."""

    class AttributeDefs(IasZone.AttributeDefs):
        """Attribute definitions."""

        current_power_source = ZCLAttributeDef(id=0xA001, type=t.uint8_t, manufacturer_code=0x1209)


class SsIasWdCluster(CustomCluster, IasWd):
    """IasWd with the attributes z2m adds."""

    class AttributeDefs(IasWd.AttributeDefs):
        """Attribute definitions."""

        siren_duration = ZCLAttributeDef(id=0xA000, type=t.uint8_t, manufacturer_code=0x1209)
        alarm_mode = ZCLAttributeDef(id=0xA001, type=t.uint8_t, manufacturer_code=0x1209)
        siren_volume = ZCLAttributeDef(id=0xA002, type=t.uint8_t, manufacturer_code=0x1209)
        siren_delay = ZCLAttributeDef(id=0xA003, type=t.uint16_t, manufacturer_code=0x1209)
        light_delay = ZCLAttributeDef(id=0xA004, type=t.uint16_t, manufacturer_code=0x1209)
        light_duration = ZCLAttributeDef(id=0xA005, type=t.uint8_t, manufacturer_code=0x1209)
        device_state = ZCLAttributeDef(id=0xA006, type=t.uint8_t, manufacturer_code=0x1209)

    class ServerCommandDefs(IasWd.ServerCommandDefs):
        """Command definitions (z2m's commands this cluster lacks)."""

        alarm_control = ZCLCommandDef(id=0xF0, schema={'data': t.uint8_t}, direction=Direction.Client_to_Server, manufacturer_code=0x1209)


class DeviceState(t.enum8):
    """device_state values (z2m)."""

    idle = 0x00
    siren_active_from_external_trigger = 0x05
    light_active_from_external_trigger = 0x06
    siren_and_light_active_from_external_trigger = 0x07
    siren_active = 0x09
    light_active = 0x0A
    siren_and_light_active = 0x0B


class AlarmMode(t.enum8):
    """alarm_mode values (z2m)."""

    only_light = 0x00
    only_siren = 0x01
    siren_and_light = 0x02


class SirenVolume(t.enum8):
    """siren_volume values (z2m)."""

    reduced = 0x01
    medium = 0x02
    loud = 0x03


class PrimaryPowerSource(t.enum8):
    """primary_power_source values (z2m)."""

    solar_panel = 0x00
    ac_power_supply = 0x01
    dc_power_supply = 0x02


class CurrentPowerSource(t.enum8):
    """current_power_source values (z2m)."""

    battery = 0x00
    solar_panel = 0x01
    ac_power = 0x02
    dc_power = 0x03



_LOGGER = logging.getLogger(__name__)
_SHIPPED = pathlib.Path(zhaquirks.__file__).resolve().parent
_STEPPED_BACK: set = set()

# The Zigbee fingerprints (manufacturer, model) this quirk is for; None matches any manufacturer.
FINGERPRINTS = [(None, 'RBSH-OS-ZB-EU')]
# Names that a model-only fingerprint would catch but Zigbee2MQTT gives to other devices.
CLAIMED_ELSEWHERE = set()
# The endpoints this quirk needs, each with the input clusters it puts there where Zigbee2MQTT names none.
ENDPOINTS = {1: (0x0001, 0x0500, 0x0502)}


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
    QuirkBuilder(None, 'RBSH-OS-ZB-EU')
    .replaces(SsIasWdCluster)
    .replaces(SsIasZoneCluster)
    .replaces(GenPowerCfgCluster)
    .enum(attribute_name=SsIasWdCluster.AttributeDefs.device_state.name, cluster_id=SsIasWdCluster.cluster_id, enum_class=DeviceState, entity_platform=EntityPlatform.SENSOR, entity_type=EntityType.STANDARD, translation_key='device_state', fallback_name='Device state')
    .enum(attribute_name=SsIasWdCluster.AttributeDefs.alarm_mode.name, cluster_id=SsIasWdCluster.cluster_id, enum_class=AlarmMode, entity_type=EntityType.CONFIG, translation_key='alarm_mode', fallback_name='Alarm mode')
    .enum(attribute_name=SsIasWdCluster.AttributeDefs.siren_volume.name, cluster_id=SsIasWdCluster.cluster_id, enum_class=SirenVolume, entity_type=EntityType.CONFIG, translation_key='siren_volume', fallback_name='Siren volume')
    .number(attribute_name=SsIasWdCluster.AttributeDefs.siren_duration.name, cluster_id=SsIasWdCluster.cluster_id, min_value=1, max_value=15, step=1, unit=UnitOfTime.MINUTES, device_class=NumberDeviceClass.DURATION, entity_type=EntityType.CONFIG, translation_key='siren_duration', fallback_name='Siren duration')
    .number(attribute_name=SsIasWdCluster.AttributeDefs.light_duration.name, cluster_id=SsIasWdCluster.cluster_id, min_value=1, max_value=15, step=1, unit=UnitOfTime.MINUTES, device_class=NumberDeviceClass.DURATION, entity_type=EntityType.CONFIG, translation_key='light_duration', fallback_name='Light duration')
    .number(attribute_name=SsIasWdCluster.AttributeDefs.siren_delay.name, cluster_id=SsIasWdCluster.cluster_id, min_value=0, max_value=180, step=1, unit=UnitOfTime.SECONDS, device_class=NumberDeviceClass.DURATION, entity_type=EntityType.CONFIG, translation_key='siren_delay', fallback_name='Siren delay')
    .number(attribute_name=SsIasWdCluster.AttributeDefs.light_delay.name, cluster_id=SsIasWdCluster.cluster_id, min_value=0, max_value=180, step=1, unit=UnitOfTime.SECONDS, device_class=NumberDeviceClass.DURATION, entity_type=EntityType.CONFIG, translation_key='light_delay', fallback_name='Light delay')
    .enum(attribute_name=GenPowerCfgCluster.AttributeDefs.primary_power_source.name, cluster_id=GenPowerCfgCluster.cluster_id, enum_class=PrimaryPowerSource, entity_type=EntityType.CONFIG, translation_key='primary_power_source', fallback_name='Primary power source')
    .enum(attribute_name=SsIasZoneCluster.AttributeDefs.current_power_source.name, cluster_id=SsIasZoneCluster.cluster_id, enum_class=CurrentPowerSource, entity_platform=EntityPlatform.SENSOR, entity_type=EntityType.DIAGNOSTIC, translation_key='current_power_source', fallback_name='Current power source')
    .sensor(attribute_name=GenPowerCfgCluster.AttributeDefs.solar_panel_voltage.name, cluster_id=GenPowerCfgCluster.cluster_id, divisor=10, state_class=SensorStateClass.MEASUREMENT, unit='volt', entity_type=EntityType.DIAGNOSTIC, translation_key='solar_panel_voltage', fallback_name='Solar panel voltage')
    .command_button(command_name=SsIasWdCluster.ServerCommandDefs.alarm_control.name, cluster_id=SsIasWdCluster.cluster_id, command_args=(7,), entity_type=EntityType.CONFIG, translation_key='trigger_alarm', fallback_name='Trigger alarm', unique_id_suffix='trigger_alarm')
    .command_button(command_name=SsIasWdCluster.ServerCommandDefs.alarm_control.name, cluster_id=SsIasWdCluster.cluster_id, command_args=(0,), entity_type=EntityType.CONFIG, translation_key='stop_alarm', fallback_name='Stop alarm', unique_id_suffix='stop_alarm')
    # battery: standard clusters, ZHA's own entities
    # external_trigger: standard clusters or z2m's own code, not generated
    # tamper: standard clusters or z2m's own code, not generated
    # power_outage: standard clusters or z2m's own code, not generated
    # battery_low: standard clusters, ZHA's own entities
    .filter(no_builtin_quirk)
    .add_to_registry()
)
