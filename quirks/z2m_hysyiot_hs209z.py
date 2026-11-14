"""HYSYIOT HS209Z: PIR and millimeter-wave radar human presence sensor.

Generated from the Zigbee2MQTT definition.
Data: zigbee-herdsman-converters, MIT, Copyright (c) 2018 Koen Kanters.
Status: generated, not verified on hardware.
Revision: 1e4a89cf
"""

import functools
import logging
import pathlib

import zhaquirks
from zha.quirks import DEVICE_REGISTRY, DeviceMatch
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.measurement import OccupancySensing

from zhaquirks.builder import (
    EntityPlatform,
    EntityType,
    NumberDeviceClass,
    UnitOfLength,
    UnitOfTime,
)
from zhaquirks.tuya import TUYA_CLUSTER_ID
from zhaquirks.tuya.builder import TuyaQuirkBuilder
from zhaquirks.tuya.tuya_motion import TuyaOccupancySensing


class BatteryState(t.enum8):
    """battery_state values (z2m)."""

    low = 0x00
    middle = 0x01
    high = 0x02


class MotionState(t.enum8):
    """motion_state values (z2m)."""

    none = 0x00
    large = 0x01
    small = 0x02
    static = 0x03



_LOGGER = logging.getLogger(__name__)
_SHIPPED = pathlib.Path(zhaquirks.__file__).resolve().parent
_STEPPED_BACK: set = set()

# The Zigbee fingerprints (manufacturer, model) this quirk is for; None matches any manufacturer.
FINGERPRINTS = [('_TZD200_bgjlfsuy', 'TS0601'), ('_TZE200_bgjlfsuy', 'TS0601'), ('_TZD200_bgjlfsuy', 'TS0202'), ('_TZE200_bgjlfsuy', 'TS0202'), (None, 'HS209Z')]
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
    .applies_to('_TZD200_bgjlfsuy', 'TS0601')
    .applies_to('_TZE200_bgjlfsuy', 'TS0601')
    .applies_to('_TZD200_bgjlfsuy', 'TS0202')
    .applies_to('_TZE200_bgjlfsuy', 'TS0202')
    .applies_to(None, 'HS209Z')
    .tuya_dp(dp_id=1, ep_attribute=TuyaOccupancySensing.ep_attribute, attribute_name=OccupancySensing.AttributeDefs.occupancy.name, converter=lambda x: x == 0)
    .adds(TuyaOccupancySensing)
    .prevent_default_entity_creation(endpoint_id=1, cluster_id=OccupancySensing.cluster_id, unique_id_suffix='pir_o_to_u_delay')
    .prevent_default_entity_creation(endpoint_id=1, cluster_id=OccupancySensing.cluster_id, unique_id_suffix='pir_u_to_o_delay')
    .tuya_dp_attribute(dp_id=3, attribute_name='battery_state', type=BatteryState, access=foundation.ZCLAttributeAccess.Read | foundation.ZCLAttributeAccess.Report, converter=lambda x: BatteryState(int(x)))
    .enum(attribute_name='battery_state', enum_class=BatteryState, cluster_id=TUYA_CLUSTER_ID, entity_platform=EntityPlatform.SENSOR, entity_type=EntityType.STANDARD, translation_key='battery_state', fallback_name='Battery state')
    .tuya_battery(dp_id=4, scale=2)
    .tuya_number(dp_id=12, type=t.uint32_t, attribute_name='pir_delay', min_value=30, max_value=120, step=30, unit=UnitOfTime.SECONDS, device_class=NumberDeviceClass.DURATION, entity_type=EntityType.CONFIG, translation_key='pir_delay', fallback_name='PIR delay')
    .tuya_number(dp_id=103, type=t.uint32_t, attribute_name='detection_distance', min_value=1, max_value=500, step=1, unit=UnitOfLength.CENTIMETERS, device_class=NumberDeviceClass.DISTANCE, entity_type=EntityType.CONFIG, translation_key='detection_distance', fallback_name='Detection distance')
    .tuya_number(dp_id=104, type=t.uint32_t, attribute_name='static_sensitivity', min_value=1, max_value=10, step=1, entity_type=EntityType.CONFIG, translation_key='static_sensitivity', fallback_name='Static sensitivity')
    .tuya_dp_attribute(dp_id=105, attribute_name='motion_state', type=MotionState, access=foundation.ZCLAttributeAccess.Read | foundation.ZCLAttributeAccess.Report, converter=lambda x: MotionState(int(x)))
    .enum(attribute_name='motion_state', enum_class=MotionState, cluster_id=TUYA_CLUSTER_ID, entity_platform=EntityPlatform.SENSOR, entity_type=EntityType.STANDARD, translation_key='motion_state', fallback_name='Motion state')
    .tuya_switch(dp_id=107, attribute_name='indicator', entity_type=EntityType.CONFIG, translation_key='indicator', fallback_name='Indicator')
    .tuya_number(dp_id=123, type=t.uint32_t, attribute_name='detection_sensitivity', min_value=1, max_value=10, step=1, entity_type=EntityType.CONFIG, translation_key='detection_sensitivity', fallback_name='Detection sensitivity')
    .filter(no_builtin_quirk)
    .add_to_registry()
)
