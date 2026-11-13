"""ONOKOM OK-AC-H-DK-1-ZB-S-A: Adapter for household Daikin systems.

Generated from the Zigbee2MQTT definition.
Data: zigbee-herdsman-converters, MIT, Copyright (c) 2018 Koen Kanters.
Status: generated, not verified on hardware.
Revision: 6bcd9513
"""

import functools
import logging
import pathlib

import zhaquirks
from zha.quirks import DEVICE_REGISTRY, DeviceMatch
import zigpy.types as t
from zigpy.zcl.foundation import ZCLAttributeDef
from zigpy.zcl.clusters.hvac import Fan
from zigpy.zcl.clusters.hvac import Thermostat

from zhaquirks.builder import (
    EntityPlatform,
    EntityType,
    QuirkBuilder,
    SensorDeviceClass,
    SensorStateClass,
    UnitOfTemperature,
)
from zhaquirks.clusters import CustomCluster


class HvacThermostatCluster(CustomCluster, Thermostat):
    """Thermostat with the attributes z2m adds."""

    class AttributeDefs(Thermostat.AttributeDefs):
        """Attribute definitions."""

        horizontal_vanes = ZCLAttributeDef(id=0x4700, type=t.enum8, manufacturer_code=0x4703)
        vertical_vanes = ZCLAttributeDef(id=0x4701, type=t.enum8, manufacturer_code=0x4703)
        vanes_swing = ZCLAttributeDef(id=0x4702, type=t.enum8, manufacturer_code=0x4703)
        mode = ZCLAttributeDef(id=0x4703, type=t.enum8, manufacturer_code=0x4703)
        status_led = ZCLAttributeDef(id=0x4704, type=t.enum8, manufacturer_code=0x4703)
        ionization = ZCLAttributeDef(id=0x4720, type=t.Bool, manufacturer_code=0x4703)
        self_cleaning = ZCLAttributeDef(id=0x4721, type=t.Bool, manufacturer_code=None)
        mold_protection = ZCLAttributeDef(id=0x4722, type=t.Bool, manufacturer_code=None)
        heating8_deg = ZCLAttributeDef(id=0x4724, type=t.Bool, manufacturer_code=None)
        gentle_wind = ZCLAttributeDef(id=0x4725, type=t.Bool, manufacturer_code=None)
        eco_mode = ZCLAttributeDef(id=0x4727, type=t.Bool, manufacturer_code=0x4703)
        sleep_mode = ZCLAttributeDef(id=0x4728, type=t.Bool, manufacturer_code=None)
        beeper = ZCLAttributeDef(id=0x4730, type=t.Bool, manufacturer_code=None)
        screen_light = ZCLAttributeDef(id=0x4731, type=t.Bool, manufacturer_code=0x4703)
        disable_screen_when_power_off = ZCLAttributeDef(id=0x4732, type=t.Bool, manufacturer_code=None)
        screen_low_bright = ZCLAttributeDef(id=0x4733, type=t.Bool, manufacturer_code=0x4703)
        ac_connected = ZCLAttributeDef(id=0x4734, type=t.enum8, access="r", manufacturer_code=None)
        smart_eye = ZCLAttributeDef(id=0x4735, type=t.enum8, manufacturer_code=None)
        smart_sleep_mode = ZCLAttributeDef(id=0x4736, type=t.enum8, manufacturer_code=None)
        indoor_heat_exchanger_temperature = ZCLAttributeDef(id=0x4740, type=t.uint16_t, access="r", manufacturer_code=None)
        outdoor_heat_exchanger_temperature = ZCLAttributeDef(id=0x4741, type=t.uint16_t, access="r", manufacturer_code=None)


class HvacFanCtrlCluster(CustomCluster, Fan):
    """Fan with the attributes z2m adds."""

    class AttributeDefs(Fan.AttributeDefs):
        """Attribute definitions."""

        fan_speed = ZCLAttributeDef(id=0x4700, type=t.enum8, manufacturer_code=0x4703)
        smart_fan_speed = ZCLAttributeDef(id=0x4701, type=t.enum8, manufacturer_code=0x4703)
        quiet_mode = ZCLAttributeDef(id=0x4710, type=t.Bool, manufacturer_code=0x4703)
        turbo_mode = ZCLAttributeDef(id=0x4711, type=t.Bool, manufacturer_code=0x4703)
        compressor_power_limit = ZCLAttributeDef(id=0x4720, type=t.uint8_t, manufacturer_code=None)
        current_compressor_power = ZCLAttributeDef(id=0x4721, type=t.uint8_t, access="r", manufacturer_code=None)
        target_compressor_power = ZCLAttributeDef(id=0x4722, type=t.uint8_t, access="r", manufacturer_code=None)
        target_fan_rpm = ZCLAttributeDef(id=0x4723, type=t.uint8_t, manufacturer_code=0x4703)
        current_fan_rpm = ZCLAttributeDef(id=0x4724, type=t.uint8_t, access="r", manufacturer_code=0x4703)


class AcConnected(t.enum8):
    """ac_connected values (z2m)."""

    disconnected = 0x00
    invalid_data_recieved = 0x01
    connected_with_issues = 0x02
    connected = 0x03


class Mode(t.enum8):
    """mode values (z2m)."""

    heat = 0x01
    cool = 0x02
    auto = 0x03
    dry = 0x04
    fan_only = 0x05


class StatusLed(t.enum8):
    """status_led values (z2m)."""

    normal_mode = 0x00
    disabled_if_no_errors = 0x01
    disabled_untill_reboot = 0x02
    always_disabled = 0x03
    green_untill_reboot = 0x08
    red_untill_reboot = 0x09



_LOGGER = logging.getLogger(__name__)
_SHIPPED = pathlib.Path(zhaquirks.__file__).resolve().parent
_STEPPED_BACK: set = set()

# The Zigbee fingerprints (manufacturer, model) this quirk is for; None matches any manufacturer.
FINGERPRINTS = [(None, 'OK-AC-H-DK-1-ZB-S-A')]
# Names that a model-only fingerprint would catch but Zigbee2MQTT gives to other devices.
CLAIMED_ELSEWHERE = set()
# The endpoints this quirk needs, each with the input clusters it puts there where Zigbee2MQTT names none.
ENDPOINTS = {1: (0x0201, 0x0202)}


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
    QuirkBuilder(None, 'OK-AC-H-DK-1-ZB-S-A')
    .replaces(HvacFanCtrlCluster)
    .replaces(HvacThermostatCluster)
    .enum(attribute_name=HvacThermostatCluster.AttributeDefs.ac_connected.name, cluster_id=HvacThermostatCluster.cluster_id, enum_class=AcConnected, entity_platform=EntityPlatform.SENSOR, entity_type=EntityType.STANDARD, translation_key='ac_connected', fallback_name='AC connected')
    .enum(attribute_name=HvacThermostatCluster.AttributeDefs.mode.name, cluster_id=HvacThermostatCluster.cluster_id, enum_class=Mode, entity_type=EntityType.STANDARD, translation_key='mode', fallback_name='Mode')
    .sensor(attribute_name=HvacThermostatCluster.AttributeDefs.outdoor_temperature.name, cluster_id=HvacThermostatCluster.cluster_id, divisor=100, state_class=SensorStateClass.MEASUREMENT, device_class=SensorDeviceClass.TEMPERATURE, unit=UnitOfTemperature.CELSIUS, entity_type=EntityType.STANDARD, translation_key='outdoor_air_temperature', fallback_name='Outdoor air temperature')
    .number(attribute_name=HvacThermostatCluster.AttributeDefs.vertical_vanes.name, cluster_id=HvacThermostatCluster.cluster_id, min_value=0, max_value=1, step=1, entity_type=EntityType.STANDARD, translation_key='vertical_vanes', fallback_name='Vertical vanes')
    .number(attribute_name=HvacThermostatCluster.AttributeDefs.horizontal_vanes.name, cluster_id=HvacThermostatCluster.cluster_id, min_value=0, max_value=1, step=1, entity_type=EntityType.STANDARD, translation_key='horizontal_vanes', fallback_name='Horizontal vanes')
    .number(attribute_name=HvacFanCtrlCluster.AttributeDefs.fan_speed.name, cluster_id=HvacFanCtrlCluster.cluster_id, min_value=0, max_value=5, step=1, entity_type=EntityType.STANDARD, translation_key='fan_speed', fallback_name='Fan speed')
    .number(attribute_name=HvacFanCtrlCluster.AttributeDefs.smart_fan_speed.name, cluster_id=HvacFanCtrlCluster.cluster_id, min_value=0, max_value=7, step=1, entity_type=EntityType.STANDARD, translation_key='smart_fan_speed', fallback_name='Smart fan speed')
    .number(attribute_name=HvacThermostatCluster.AttributeDefs.vanes_swing.name, cluster_id=HvacThermostatCluster.cluster_id, min_value=0, max_value=3, step=1, entity_type=EntityType.STANDARD, translation_key='vanes_swing', fallback_name='Vanes swing')
    .enum(attribute_name=HvacThermostatCluster.AttributeDefs.status_led.name, cluster_id=HvacThermostatCluster.cluster_id, enum_class=StatusLed, entity_type=EntityType.STANDARD, translation_key='status_led', fallback_name='Status LED')
    .switch(attribute_name=HvacFanCtrlCluster.AttributeDefs.quiet_mode.name, cluster_id=HvacFanCtrlCluster.cluster_id, entity_type=EntityType.STANDARD, translation_key='quiet_mode', fallback_name='Quiet mode')
    .switch(attribute_name=HvacThermostatCluster.AttributeDefs.eco_mode.name, cluster_id=HvacThermostatCluster.cluster_id, entity_type=EntityType.STANDARD, translation_key='eco_mode', fallback_name='Eco mode')
    .switch(attribute_name=HvacFanCtrlCluster.AttributeDefs.turbo_mode.name, cluster_id=HvacFanCtrlCluster.cluster_id, entity_type=EntityType.STANDARD, translation_key='turbo_mode', fallback_name='Turbo mode')
    .switch(attribute_name=HvacThermostatCluster.AttributeDefs.ionization.name, cluster_id=HvacThermostatCluster.cluster_id, entity_type=EntityType.STANDARD, translation_key='ionization', fallback_name='Ionization')
    .switch(attribute_name=HvacThermostatCluster.AttributeDefs.screen_light.name, cluster_id=HvacThermostatCluster.cluster_id, entity_type=EntityType.STANDARD, translation_key='screen_light', fallback_name='Screen light')
    .switch(attribute_name=HvacThermostatCluster.AttributeDefs.screen_low_bright.name, cluster_id=HvacThermostatCluster.cluster_id, entity_type=EntityType.STANDARD, translation_key='screen_low_bright', fallback_name='Screen low bright')
    .number(attribute_name=HvacFanCtrlCluster.AttributeDefs.target_fan_rpm.name, cluster_id=HvacFanCtrlCluster.cluster_id, min_value=0, max_value=200, step=1, entity_type=EntityType.STANDARD, translation_key='target_fan_rpm', fallback_name='Target fan rpm')
    .sensor(attribute_name=HvacFanCtrlCluster.AttributeDefs.current_fan_rpm.name, cluster_id=HvacFanCtrlCluster.cluster_id, entity_type=EntityType.STANDARD, translation_key='current_fan_rpm', fallback_name='Current fan rpm')
    # current_temperature: standard clusters, ZHA's own entities
    # target_temperature: standard clusters, ZHA's own entities
    # system_mode: standard clusters, ZHA's own entities
    # zb_fan_speed: standard clusters, ZHA's own entities
    # switch: standard clusters, ZHA's own entities
    .filter(no_builtin_quirk)
    .add_to_registry()
)
