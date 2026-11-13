"""Halo Smart Labs HALO+: Halo+ smart smoke & CO detector with weather radio.

Generated from the Zigbee2MQTT definition.
Data: zigbee-herdsman-converters, MIT, Copyright (c) 2018 Koen Kanters.
Status: generated, not verified on hardware.
Revision: 91b72390
"""

import functools
import logging
import pathlib

import zhaquirks
from zha.quirks import DEVICE_REGISTRY, DeviceMatch
import zigpy.types as t
from zigpy.zcl.foundation import BaseAttributeDefs, BaseCommandDefs, Direction, ZCLAttributeDef, ZCLCommandDef

from zhaquirks.builder import (
    CONCENTRATION_PARTS_PER_MILLION,
    EntityType,
    QuirkBuilder,
    SensorStateClass,
)
from zhaquirks.clusters import CustomCluster


class HaloControlCluster(CustomCluster):
    """haloControl (z2m custom cluster)."""

    cluster_id = 0xFD01

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        test_status = ZCLAttributeDef(id=0x0000, type=t.enum8, access="r", manufacturer_code=0x1201)
        hush_status = ZCLAttributeDef(id=0x0001, type=t.enum8, access="r", manufacturer_code=0x1201)

    class ServerCommandDefs(BaseCommandDefs):
        """Command definitions (z2m's commands this cluster lacks)."""

        halo_test = ZCLCommandDef(id=0x00, schema={'value': t.uint8_t}, direction=Direction.Client_to_Server, manufacturer_code=0x1201)
        halo_hush = ZCLCommandDef(id=0x01, schema={'value': t.uint8_t}, direction=Direction.Client_to_Server, manufacturer_code=0x1201)


class HaloSensorsCluster(CustomCluster):
    """haloSensors (z2m custom cluster)."""

    cluster_id = 0xFD02

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        co_ppm = ZCLAttributeDef(id=0x0002, type=t.int16s, access="r", manufacturer_code=0x1201)


class HaloWeatherCluster(CustomCluster):
    """haloWeather (z2m custom cluster)."""

    cluster_id = 0xFD03

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        weather_alert_status = ZCLAttributeDef(id=0x0000, type=t.enum8, access="r", manufacturer_code=0x1201)
        weather_mute = ZCLAttributeDef(id=0x0001, type=t.Bool, access="r", manufacturer_code=0x1201)
        weather_location = ZCLAttributeDef(id=0x0002, type=t.uint32_t, access="r", manufacturer_code=0x1201)
        # weather_event1 0x0003: BITMAP32, attribute only
        # weather_event2 0x0004: BITMAP32, attribute only
        # weather_event3 0x0005: BITMAP32, attribute only
        weather_station = ZCLAttributeDef(id=0x0006, type=t.uint8_t, access="r", manufacturer_code=0x1201)
        weather_station_rssi1 = ZCLAttributeDef(id=0x0007, type=t.uint8_t, access="r", manufacturer_code=0x1201)
        weather_station_rssi2 = ZCLAttributeDef(id=0x0008, type=t.uint8_t, access="r", manufacturer_code=0x1201)
        weather_station_rssi3 = ZCLAttributeDef(id=0x0009, type=t.uint8_t, access="r", manufacturer_code=0x1201)
        weather_station_rssi4 = ZCLAttributeDef(id=0x000A, type=t.uint8_t, access="r", manufacturer_code=0x1201)
        weather_station_rssi5 = ZCLAttributeDef(id=0x000B, type=t.uint8_t, access="r", manufacturer_code=0x1201)
        weather_station_rssi6 = ZCLAttributeDef(id=0x000C, type=t.uint8_t, access="r", manufacturer_code=0x1201)
        weather_station_rssi7 = ZCLAttributeDef(id=0x000D, type=t.uint8_t, access="r", manufacturer_code=0x1201)

    class ServerCommandDefs(BaseCommandDefs):
        """Command definitions (z2m's commands this cluster lacks)."""

        weather_radio_play = ZCLCommandDef(id=0x03, schema={'value': t.uint8_t}, direction=Direction.Client_to_Server, manufacturer_code=0x1201)



_LOGGER = logging.getLogger(__name__)
_SHIPPED = pathlib.Path(zhaquirks.__file__).resolve().parent
_STEPPED_BACK: set = set()

# The Zigbee fingerprints (manufacturer, model) this quirk is for; None matches any manufacturer.
FINGERPRINTS = [(None, 'halo+'), (None, 'haloWX'), (None, 'SABDA1')]
# Names that a model-only fingerprint would catch but Zigbee2MQTT gives to other devices.
CLAIMED_ELSEWHERE = set()
# The endpoints this quirk needs, each with the input clusters it puts there where Zigbee2MQTT names none.
ENDPOINTS = {4: (0xFD01, 0xFD02), 5: (0xFD03,)}


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
    QuirkBuilder(None, 'halo+')
    .applies_to(None, 'haloWX')
    .applies_to(None, 'SABDA1')
    .replaces(HaloWeatherCluster, endpoint_id=5)
    .replaces(HaloSensorsCluster, endpoint_id=4)
    .replaces(HaloControlCluster, endpoint_id=4)
    .sensor(attribute_name=HaloSensorsCluster.AttributeDefs.co_ppm.name, cluster_id=HaloSensorsCluster.cluster_id, endpoint_id=4, state_class=SensorStateClass.MEASUREMENT, unit=CONCENTRATION_PARTS_PER_MILLION, entity_type=EntityType.DIAGNOSTIC, translation_key='co_ppm', fallback_name='Co ppm')
    .command_button(command_name=HaloControlCluster.ServerCommandDefs.halo_hush.name, cluster_id=HaloControlCluster.cluster_id, command_args=(0,), endpoint_id=4, entity_type=EntityType.STANDARD, translation_key='hush_start', fallback_name='Hush (start)', unique_id_suffix='hush_start')
    .command_button(command_name=HaloControlCluster.ServerCommandDefs.halo_hush.name, cluster_id=HaloControlCluster.cluster_id, command_args=(1,), endpoint_id=4, entity_type=EntityType.STANDARD, translation_key='hush_stop', fallback_name='Hush (stop)', unique_id_suffix='hush_stop')
    .command_button(command_name=HaloControlCluster.ServerCommandDefs.halo_test.name, cluster_id=HaloControlCluster.cluster_id, command_args=(1,), endpoint_id=4, entity_type=EntityType.STANDARD, translation_key='test_cycle_start', fallback_name='Test cycle (start)', unique_id_suffix='test_cycle_start')
    .command_button(command_name=HaloControlCluster.ServerCommandDefs.halo_test.name, cluster_id=HaloControlCluster.cluster_id, command_args=(0,), endpoint_id=4, entity_type=EntityType.STANDARD, translation_key='test_cycle_cancel', fallback_name='Test cycle (cancel)', unique_id_suffix='test_cycle_cancel')
    .command_button(command_name=HaloWeatherCluster.ServerCommandDefs.weather_radio_play.name, cluster_id=HaloWeatherCluster.cluster_id, command_args=(1,), endpoint_id=5, entity_type=EntityType.STANDARD, translation_key='weather_playback_play', fallback_name='Weather playback (play)', unique_id_suffix='weather_playback_play')
    .command_button(command_name=HaloWeatherCluster.ServerCommandDefs.weather_radio_play.name, cluster_id=HaloWeatherCluster.cluster_id, command_args=(0,), endpoint_id=5, entity_type=EntityType.STANDARD, translation_key='weather_playback_stop', fallback_name='Weather playback (stop)', unique_id_suffix='weather_playback_stop')
    # smoke: standard clusters, ZHA's own entities
    # carbon_monoxide: standard clusters, ZHA's own entities
    # tamper: standard clusters, ZHA's own entities
    # battery_low: standard clusters, ZHA's own entities
    # test: standard clusters, ZHA's own entities
    # mains_power_connected: standard clusters, ZHA's own entities
    # halo_alert_state: z2m's own code, not generated
    # room: z2m's own code, not generated
    # halo_test_result: z2m's own code, not generated
    # test_in_progress: z2m's own code, not generated
    # halo_hush_state: z2m's own code, not generated
    # hush_active: z2m's own code, not generated
    # light: standard clusters, ZHA's own entities
    # battery: standard clusters, ZHA's own entities
    # voltage: standard clusters, ZHA's own entities
    # temperature: standard clusters, ZHA's own entities
    # humidity: standard clusters, ZHA's own entities
    # pressure: standard clusters, ZHA's own entities
    # weather_alert: z2m's own code, not generated
    # current_weather_alert: z2m's own code, not generated
    # weather_alerts_interest: z2m's own code, not generated
    # weather_location: z2m's own code, not generated
    # weather_station: z2m's own code, not generated
    # weather_frequency: z2m's own code, not generated
    # weather_playing_state: z2m's own code, not generated
    .filter(no_builtin_quirk)
    .add_to_registry()
)
