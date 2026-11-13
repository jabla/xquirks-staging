"""HOBEIAN ZG-204ZL: Luminance motion sensor.

Generated from the Zigbee2MQTT definition.
Zigbee2MQTT lists these names with _TZE200_1ibpyhdc / TS0601, _TZE200_3towulqd / TS0601,
_TZE200_bh3n6gk8 / TS0601, _TZE200_gjldowol / TS0601, _TZE200_ttcovulf / TS0601, but the quirk
ZHA ships for those does not fit them (different dp maps). These names get their own quirk
instead of an alias; once a quirk shipped with ZHA matches them, this file steps back.
Data: zigbee-herdsman-converters, MIT, Copyright (c) 2018 Koen Kanters.
Status: generated, not verified on hardware.
Revision: 0b1a796c
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
    UnitOfTime,
)
from zhaquirks.tuya.builder import TuyaQuirkBuilder
from zhaquirks.tuya.tuya_motion import TuyaOccupancySensing


class Sensitivity(t.enum8):
    """sensitivity values (z2m)."""

    low = 0x00
    medium = 0x01
    high = 0x02


class KeepTime(t.enum8):
    """keep_time values (z2m)."""

    Time_10 = 0x00
    Time_30 = 0x01
    Time_60 = 0x02
    Time_120 = 0x03



_LOGGER = logging.getLogger(__name__)
_SHIPPED = pathlib.Path(zhaquirks.__file__).resolve().parent
_STEPPED_BACK: set = set()

# The Zigbee fingerprints (manufacturer, model) this quirk is for; None matches any manufacturer.
FINGERPRINTS = [('_TZE200_s6hzw8g2', 'TS0601'), ('_TZE200_jxyhl4eq', 'TS0601'), ('_TZE200_qxyh4r7g', 'TS0601'), ('_TZE200_na5qlzow', 'TS0601')]
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
    TuyaQuirkBuilder()
    .applies_to('_TZE200_s6hzw8g2', 'TS0601')
    .applies_to('_TZE200_jxyhl4eq', 'TS0601')
    .applies_to('_TZE200_qxyh4r7g', 'TS0601')
    .applies_to('_TZE200_na5qlzow', 'TS0601')
    .tuya_dp(dp_id=1, ep_attribute=TuyaOccupancySensing.ep_attribute, attribute_name=OccupancySensing.AttributeDefs.occupancy.name, converter=lambda x: x == 0)
    .adds(TuyaOccupancySensing)
    .tuya_battery(dp_id=4, scale=2)
    .tuya_enum(dp_id=9, attribute_name='sensitivity', enum_class=Sensitivity, entity_type=EntityType.CONFIG, translation_key='sensitivity', fallback_name='Sensitivity')
    .tuya_enum(dp_id=10, attribute_name='keep_time', enum_class=KeepTime, entity_type=EntityType.CONFIG, translation_key='keep_time', fallback_name='Keep time')
    .tuya_illuminance(dp_id=12)
    .tuya_number(dp_id=102, type=t.uint32_t, attribute_name='illuminance_interval', min_value=1, max_value=720, step=1, unit=UnitOfTime.MINUTES, device_class=NumberDeviceClass.DURATION, entity_type=EntityType.CONFIG, translation_key='illuminance_interval', fallback_name='Illuminance interval')
    # DP 101 (illuminance): z2m maps DP 12 to the same key too, not generated
    .skip_configuration()
    .filter(no_builtin_quirk)
    .add_to_registry()
)
