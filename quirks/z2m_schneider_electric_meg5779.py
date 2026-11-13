"""Schneider Electric MEG5779: Merten Connected Room Temperature Controller.

Generated from the Zigbee2MQTT definition.
Data: zigbee-herdsman-converters, MIT, Copyright (c) 2018 Koen Kanters.
Status: generated, not verified on hardware.
Revision: 23ba6480
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
    EntityType,
    NumberDeviceClass,
    PERCENTAGE,
    QuirkBuilder,
    UnitOfTime,
)
from zhaquirks.clusters import CustomCluster


class HvacThermostatCluster(CustomCluster, Thermostat):
    """Thermostat with the attributes z2m adds."""

    class AttributeDefs(Thermostat.AttributeDefs):
        """Attribute definitions."""

        schneider_wiser_specific = ZCLAttributeDef(id=0xE110, type=t.enum8, manufacturer_code=0x105E)
        control_status = ZCLAttributeDef(id=0xE211, type=t.enum8, access="r", manufacturer_code=0x105E)
        local_temperature_source_select = ZCLAttributeDef(id=0xE212, type=t.uint8_t, manufacturer_code=0x105E)
        control_type = ZCLAttributeDef(id=0xE213, type=t.enum8, manufacturer_code=0x105E)
        thermostat_application = ZCLAttributeDef(id=0xE216, type=t.enum8, manufacturer_code=0x105E)
        heating_fuel = ZCLAttributeDef(id=0xE217, type=t.enum8, manufacturer_code=0x105E)
        heat_transfer_medium = ZCLAttributeDef(id=0xE218, type=t.enum8, manufacturer_code=0x105E)
        heating_emitter = ZCLAttributeDef(id=0xE21A, type=t.enum8, manufacturer_code=0x105E)
        wiser_smart_zone_mode = ZCLAttributeDef(id=0xE010, type=t.enum8, manufacturer_code=0x105E)
        wiser_smart_hact_config = ZCLAttributeDef(id=0xE011, type=t.bitmap8, manufacturer_code=0x105E)
        wiser_smart_open_window_detection_status = ZCLAttributeDef(id=0xE012, type=t.uint8_t, access="r", manufacturer_code=0x105E)
        wiser_smart_current_fil_pilote_mode = ZCLAttributeDef(id=0xE020, type=t.enum8, manufacturer_code=0x105E)
        wiser_smart_valve_position = ZCLAttributeDef(id=0xE030, type=t.uint8_t, access="r", manufacturer_code=0x105E)
        wiser_smart_valve_calibration_status = ZCLAttributeDef(id=0xE031, type=t.enum8, access="r", manufacturer_code=0x105E)


class HvacUserInterfaceCfgCluster(CustomCluster, UserInterface):
    """UserInterface with the attributes z2m adds."""

    class AttributeDefs(UserInterface.AttributeDefs):
        """Attribute definitions."""

        display_brightness_active = ZCLAttributeDef(id=0xE000, type=t.uint8_t, manufacturer_code=0x105E)
        display_brightness_inactive = ZCLAttributeDef(id=0xE001, type=t.uint8_t, manufacturer_code=0x105E)
        display_active_timeout = ZCLAttributeDef(id=0xE002, type=t.uint16_t, manufacturer_code=0x105E)


class TemperatureDisplayMode(t.enum8):
    """temperature_display_mode values (z2m)."""

    celsius = 0x00
    fahrenheit = 0x01


class ThermostatApplication(t.enum8):
    """thermostat_application values (z2m)."""

    Occupied_Space = 0x00
    Floor = 0x01
    Not_known = 0xFF


class HeatingFuel(t.enum8):
    """heating_fuel values (z2m)."""

    electricity = 0x00
    gas = 0x01
    oil = 0x02
    solid_fuel = 0x03
    solar = 0x04
    community_heating = 0x05
    heat_pump = 0x06
    not_specified = 0xFF


class HeatTransferMedium(t.enum8):
    """heat_transfer_medium values (z2m)."""

    nothing = 0x00
    hydronic = 0x01
    air = 0x02


class HeatingEmitter(t.enum8):
    """heating_emitter values (z2m)."""

    none = 0x00
    Radiator = 0x01
    Fan_Assisted_Radiator = 0x02
    Radiant_Panel = 0x03
    Floor = 0x04
    Not_specified = 0xFF



_LOGGER = logging.getLogger(__name__)
_SHIPPED = pathlib.Path(zhaquirks.__file__).resolve().parent
_STEPPED_BACK: set = set()

# The Zigbee fingerprints (manufacturer, model) this quirk is for; None matches any manufacturer.
FINGERPRINTS = [(None, 'MEG5779')]
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
    QuirkBuilder(None, 'MEG5779')
    .replaces(HvacUserInterfaceCfgCluster)
    .replaces(HvacThermostatCluster)
    .number(attribute_name=HvacUserInterfaceCfgCluster.AttributeDefs.display_brightness_active.name, cluster_id=HvacUserInterfaceCfgCluster.cluster_id, min_value=0, max_value=100, step=1, unit=PERCENTAGE, entity_type=EntityType.CONFIG, translation_key='display_brightness_active', fallback_name='Display brightness active')
    .number(attribute_name=HvacUserInterfaceCfgCluster.AttributeDefs.display_brightness_inactive.name, cluster_id=HvacUserInterfaceCfgCluster.cluster_id, min_value=0, max_value=100, step=1, unit=PERCENTAGE, entity_type=EntityType.CONFIG, translation_key='display_brightness_inactive', fallback_name='Display brightness inactive')
    .number(attribute_name=HvacUserInterfaceCfgCluster.AttributeDefs.display_active_timeout.name, cluster_id=HvacUserInterfaceCfgCluster.cluster_id, min_value=5, max_value=600, step=5, unit=UnitOfTime.SECONDS, device_class=NumberDeviceClass.DURATION, entity_type=EntityType.CONFIG, translation_key='display_active_timeout', fallback_name='Display active timeout')
    .enum(attribute_name=HvacUserInterfaceCfgCluster.AttributeDefs.temperature_display_mode.name, cluster_id=HvacUserInterfaceCfgCluster.cluster_id, enum_class=TemperatureDisplayMode, entity_type=EntityType.STANDARD, translation_key='temperature_display_mode', fallback_name='Temperature display mode')
    .enum(attribute_name=HvacThermostatCluster.AttributeDefs.thermostat_application.name, cluster_id=HvacThermostatCluster.cluster_id, enum_class=ThermostatApplication, entity_type=EntityType.CONFIG, translation_key='thermostat_application', fallback_name='Thermostat application')
    .enum(attribute_name=HvacThermostatCluster.AttributeDefs.heating_fuel.name, cluster_id=HvacThermostatCluster.cluster_id, enum_class=HeatingFuel, entity_type=EntityType.CONFIG, translation_key='heating_fuel', fallback_name='Heating fuel')
    .enum(attribute_name=HvacThermostatCluster.AttributeDefs.heat_transfer_medium.name, cluster_id=HvacThermostatCluster.cluster_id, enum_class=HeatTransferMedium, entity_type=EntityType.CONFIG, translation_key='heat_transfer_medium', fallback_name='Heat transfer medium')
    .enum(attribute_name=HvacThermostatCluster.AttributeDefs.heating_emitter.name, cluster_id=HvacThermostatCluster.cluster_id, enum_class=HeatingEmitter, entity_type=EntityType.CONFIG, translation_key='heating_emitter', fallback_name='Heating emitter')
    .binary_sensor(attribute_name=HvacThermostatCluster.AttributeDefs.wiser_smart_open_window_detection_status.name, cluster_id=HvacThermostatCluster.cluster_id, entity_type=EntityType.DIAGNOSTIC, translation_key='window_open', fallback_name='Window open')
    # max_heat_setpoint_limit: standard clusters, ZHA's own entities
    # min_heat_setpoint_limit: standard clusters, ZHA's own entities
    # keypadLockout: standard clusters, ZHA's own entities
    # climate: standard clusters, ZHA's own entities
    # max_cool_setpoint_limit: standard cluster, no ZHA entity, not generated
    # min_cool_setpoint_limit: standard cluster, no ZHA entity, not generated
    .filter(no_builtin_quirk)
    .add_to_registry()
)
