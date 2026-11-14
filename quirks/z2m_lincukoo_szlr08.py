"""Lincukoo SZLR08: 24GHz millimeter wave radar.

Generated from the Zigbee2MQTT definition.
Data: zigbee-herdsman-converters, MIT, Copyright (c) 2018 Koen Kanters.
Status: generated, not verified on hardware.
Revision: 5c8cc717
"""

import functools
import logging
import pathlib

import zhaquirks
from zha.quirks import DEVICE_REGISTRY, DeviceMatch
import zigpy.types as t
from zigpy.zcl.clusters.measurement import OccupancySensing

from zhaquirks.builder import (
    EntityType,
    NumberDeviceClass,
    SensorDeviceClass,
    SensorStateClass,
    UnitOfLength,
    UnitOfTime,
)
from zhaquirks.tuya.builder import TuyaQuirkBuilder
from zhaquirks.tuya.tuya_motion import TuyaOccupancySensing


class RelayMode(t.enum8):
    """relay_mode values (z2m)."""

    auto = 0x00
    manual = 0x01


class RadarMode(t.enum8):
    """radar_mode values (z2m)."""

    people_on = 0x00
    people_off = 0x01



_LOGGER = logging.getLogger(__name__)
_SHIPPED = pathlib.Path(zhaquirks.__file__).resolve().parent
_STEPPED_BACK: set = set()

# The Zigbee fingerprints (manufacturer, model) this quirk is for; None matches any manufacturer.
FINGERPRINTS = [('_TZE204_lw5ny7tp', 'TS0601'), ('_TZE28C1000000_lw5ny7tp', 'TS0601')]
# Names that a model-only fingerprint would catch but Zigbee2MQTT gives to other devices.
CLAIMED_ELSEWHERE = set()
# The endpoints this quirk needs, each with the input clusters it puts there where Zigbee2MQTT names none.
ENDPOINTS = {1: (0xEF00,)}


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
    TuyaQuirkBuilder()
    .applies_to('_TZE204_lw5ny7tp', 'TS0601')
    .applies_to('_TZE28C1000000_lw5ny7tp', 'TS0601')
    .tuya_dp(dp_id=1, ep_attribute=TuyaOccupancySensing.ep_attribute, attribute_name=OccupancySensing.AttributeDefs.occupancy.name, converter=lambda x: x == 1)
    .adds(TuyaOccupancySensing)
    .prevent_default_entity_creation(endpoint_id=1, cluster_id=OccupancySensing.cluster_id, unique_id_suffix='pir_o_to_u_delay')
    .prevent_default_entity_creation(endpoint_id=1, cluster_id=OccupancySensing.cluster_id, unique_id_suffix='pir_u_to_o_delay')
    .tuya_illuminance(dp_id=20)
    .tuya_number(dp_id=13, type=t.uint32_t, attribute_name='installation_height', min_value=1.5, max_value=6, step=0.75, unit=UnitOfLength.METERS, multiplier=0.01, device_class=NumberDeviceClass.DISTANCE, entity_type=EntityType.CONFIG, translation_key='z2m_installation_height', fallback_name='Installation height')
    .tuya_number(dp_id=16, type=t.uint32_t, attribute_name='radar_sensitivity', min_value=68, max_value=90, step=1, entity_type=EntityType.CONFIG, translation_key='radar_sensitivity', fallback_name='Radar sensitivity')
    .tuya_sensor(dp_id=19, attribute_name='detection_distance', type=t.uint32_t, state_class=SensorStateClass.MEASUREMENT, device_class=SensorDeviceClass.DISTANCE, unit=UnitOfLength.CENTIMETERS, entity_type=EntityType.STANDARD, translation_key='detection_distance', fallback_name='Detection distance')
    .tuya_number(dp_id=103, type=t.uint32_t, attribute_name='fading_time', min_value=3, max_value=1799, step=1, unit=UnitOfTime.SECONDS, device_class=NumberDeviceClass.DURATION, entity_type=EntityType.CONFIG, translation_key='fading_time', fallback_name='Fading time')
    .tuya_switch(dp_id=101, attribute_name='indicator', entity_type=EntityType.CONFIG, translation_key='indicator', fallback_name='Indicator')
    .tuya_switch(dp_id=104, attribute_name='relay_switch', entity_type=EntityType.STANDARD, translation_key='relay_switch', fallback_name='Relay switch')
    .tuya_switch(dp_id=102, attribute_name='radar_switch', entity_type=EntityType.CONFIG, translation_key='radar_switch', fallback_name='Radar switch')
    .tuya_enum(dp_id=106, attribute_name='relay_mode', enum_class=RelayMode, entity_type=EntityType.CONFIG, translation_key='relay_mode', fallback_name='Relay mode')
    .tuya_enum(dp_id=107, attribute_name='radar_mode', enum_class=RadarMode, entity_type=EntityType.CONFIG, translation_key='radar_mode', fallback_name='Radar mode')
    .skip_configuration()
    .filter(no_builtin_quirk)
    .add_to_registry()
)
