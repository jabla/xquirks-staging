"""Mowe MW836P: Smart presence sensor with relay (24 GHz mmWave radar + infrared).

Generated from the Zigbee2MQTT definition.
Data: zigbee-herdsman-converters, MIT, Copyright (c) 2018 Koen Kanters.
Status: generated, not verified on hardware.
Revision: 80963943
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
)
from zhaquirks.tuya.builder import TuyaQuirkBuilder
from zhaquirks.tuya.tuya_motion import TuyaOccupancySensing


class RelayDelay(t.enum8):
    """relay_delay values (z2m)."""

    Delay_0 = 0x00
    Delay_1 = 0x01
    Delay_5 = 0x02
    Delay_10 = 0x03
    Delay_20 = 0x04
    Delay_30 = 0x05


class DetectionRange(t.enum8):
    """detection_range values (z2m)."""

    Range_2m = 0x00
    Range_3m = 0x01


class NobodyTime(t.enum8):
    """nobody_time values (z2m)."""

    Time_10s = 0x00
    Time_20s = 0x01
    Time_30s = 0x02
    Time_60s = 0x03
    Time_180s = 0x04



_LOGGER = logging.getLogger(__name__)
_SHIPPED = pathlib.Path(zhaquirks.__file__).resolve().parent
_STEPPED_BACK: set = set()

# The Zigbee fingerprints (manufacturer, model) this quirk is for; None matches any manufacturer.
FINGERPRINTS = [('_TZE284_mexuq6lm', 'TS0601')]
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
    .applies_to('_TZE284_mexuq6lm', 'TS0601')
    .tuya_dp(dp_id=1, ep_attribute=TuyaOccupancySensing.ep_attribute, attribute_name=OccupancySensing.AttributeDefs.occupancy.name, converter=lambda x: x == 1)
    .adds(TuyaOccupancySensing)
    .tuya_switch(dp_id=101, attribute_name='auto_monitoring', entity_type=EntityType.CONFIG, translation_key='auto_monitoring', fallback_name='Auto monitoring')
    .tuya_illuminance(dp_id=103)
    .tuya_switch(dp_id=104, attribute_name='infrared', entity_type=EntityType.CONFIG, translation_key='infrared', fallback_name='Infrared')
    .tuya_switch(dp_id=105, attribute_name='induction_switch', entity_type=EntityType.CONFIG, translation_key='induction_switch', fallback_name='Induction switch')
    .tuya_sensor(dp_id=107, attribute_name='hardware_version', type=t.CharacterString, converter=lambda x: str(x), entity_type=EntityType.DIAGNOSTIC, translation_key='hardware_version', fallback_name='Hardware version')
    .tuya_sensor(dp_id=108, attribute_name='soft_version', type=t.CharacterString, converter=lambda x: str(x), entity_type=EntityType.DIAGNOSTIC, translation_key='soft_version', fallback_name='Soft version')
    .tuya_sensor(dp_id=109, attribute_name='radar_id', type=t.CharacterString, converter=lambda x: str(x), entity_type=EntityType.DIAGNOSTIC, translation_key='radar_id', fallback_name='Radar ID')
    .tuya_switch(dp_id=111, attribute_name='relay', entity_type=EntityType.CONFIG, translation_key='relay', fallback_name='Relay')
    .tuya_enum(dp_id=112, attribute_name='relay_delay', enum_class=RelayDelay, entity_type=EntityType.CONFIG, translation_key='relay_delay', fallback_name='Relay delay')
    .tuya_binary_sensor(dp_id=113, attribute_name='relay_off_trigger', entity_type=EntityType.DIAGNOSTIC, translation_key='relay_off_trigger', fallback_name='Relay off trigger')
    .tuya_switch(dp_id=114, attribute_name='micro_motion_detection', entity_type=EntityType.CONFIG, translation_key='micro_motion_detection', fallback_name='Micro motion detection')
    .tuya_binary_sensor(dp_id=115, attribute_name='self_test', entity_type=EntityType.DIAGNOSTIC, translation_key='z2m_self_test', fallback_name='Self test')
    .tuya_enum(dp_id=120, attribute_name='detection_range', enum_class=DetectionRange, entity_type=EntityType.CONFIG, translation_key='z2m_detection_range', fallback_name='Detection range')
    .tuya_number(dp_id=122, type=t.uint32_t, attribute_name='motion_sensitivity', min_value=1, max_value=3, step=1, entity_type=EntityType.CONFIG, translation_key='motion_sensitivity', fallback_name='Motion sensitivity')
    .tuya_number(dp_id=123, type=t.uint32_t, attribute_name='static_sensitivity', min_value=1, max_value=3, step=1, entity_type=EntityType.CONFIG, translation_key='static_sensitivity', fallback_name='Static sensitivity')
    .tuya_enum(dp_id=133, attribute_name='nobody_time', enum_class=NobodyTime, entity_type=EntityType.CONFIG, translation_key='nobody_time', fallback_name='Nobody time')
    .skip_configuration()
    .filter(no_builtin_quirk)
    .add_to_registry()
)
