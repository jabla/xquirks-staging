"""Tuya TS0601_cover_12: Curtain motor.

Generated from the Zigbee2MQTT definition.
Data: zigbee-herdsman-converters, MIT, Copyright (c) 2018 Koen Kanters.
Status: generated, not verified on hardware.
Revision: 95a62c99
"""

import functools
import logging
import pathlib

import zhaquirks
from zha.quirks import DEVICE_REGISTRY, DeviceMatch
import zigpy.types as t
from zigpy.zcl import foundation

from zhaquirks.builder import (
    EntityPlatform,
    EntityType,
    PERCENTAGE,
    SensorDeviceClass,
    SensorStateClass,
    UnitOfTime,
)
from zhaquirks.tuya import TUYA_CLUSTER_ID
from zhaquirks.tuya.builder import TuyaQuirkBuilder


class MotorDirection(t.enum8):
    """motor_direction values (z2m)."""

    normal = 0x00
    reversed = 0x01


class MotorState(t.enum8):
    """motor_state values (z2m)."""

    opening = 0x00
    closing = 0x01
    stopped = 0x02


class SituationSet(t.enum8):
    """situation_set values (z2m)."""

    fully_close = 0x00
    fully_open = 0x01



_LOGGER = logging.getLogger(__name__)
_SHIPPED = pathlib.Path(zhaquirks.__file__).resolve().parent
_STEPPED_BACK: set = set()

# The Zigbee fingerprints (manufacturer, model) this quirk is for; None matches any manufacturer.
FINGERPRINTS = [('_TZE284_a0hirjnh', 'TS0601')]
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
    .applies_to('_TZE284_a0hirjnh', 'TS0601')
    .tuya_cover(control_dp=1, position_state_dp=3, position_control_dp=2)
    .tuya_enum(dp_id=5, attribute_name='motor_direction', enum_class=MotorDirection, entity_type=EntityType.CONFIG, translation_key='motor_direction', fallback_name='Motor direction')
    .tuya_dp_attribute(dp_id=7, attribute_name='motor_state', type=MotorState, access=foundation.ZCLAttributeAccess.Read | foundation.ZCLAttributeAccess.Report, converter=lambda x: MotorState(int(x)))
    .enum(attribute_name='motor_state', enum_class=MotorState, cluster_id=TUYA_CLUSTER_ID, entity_platform=EntityPlatform.SENSOR, entity_type=EntityType.DIAGNOSTIC, translation_key='motor_state', fallback_name='Motor state')
    .tuya_sensor(dp_id=10, attribute_name='total_time', type=t.uint32_t, state_class=SensorStateClass.MEASUREMENT, device_class=SensorDeviceClass.DURATION, unit=UnitOfTime.MILLISECONDS, entity_type=EntityType.STANDARD, translation_key='total_time', fallback_name='Total time')
    .tuya_enum(dp_id=11, attribute_name='situation_set', enum_class=SituationSet, entity_type=EntityType.CONFIG, translation_key='situation_set', fallback_name='Situation set')
    .tuya_sensor(dp_id=12, attribute_name='fault', type=t.CharacterString, converter=lambda x: str(x), entity_type=EntityType.STANDARD, translation_key='fault', fallback_name='Fault')
    .tuya_number(dp_id=19, type=t.uint32_t, attribute_name='favorite_position', min_value=0, max_value=100, step=1, unit=PERCENTAGE, entity_type=EntityType.CONFIG, translation_key='favorite_position', fallback_name='Favorite position')
    # DP 6 (auto_power): z2m exposes no entity for it, not generated
    # DP 103 (battery): z2m exposes no entity for it, not generated
    .skip_configuration()
    .filter(no_builtin_quirk)
    .add_to_registry()
)
