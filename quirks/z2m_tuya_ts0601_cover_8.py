"""Tuya TS0601_cover_8: Cover motor.

Generated from the Zigbee2MQTT definition.
Zigbee2MQTT lists these names with _TZE200_9vpe3fl1 / TS0601, but the quirk ZHA ships for those
does not fit them (legacy). These names get their own quirk instead of an alias; once a quirk
shipped with ZHA matches them, this file steps back.
Data: zigbee-herdsman-converters, MIT, Copyright (c) 2018 Koen Kanters.
Status: generated, not verified on hardware.
Revision: 0ba18726
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
)
from zhaquirks.tuya import TUYA_CLUSTER_ID
from zhaquirks.tuya.builder import TuyaQuirkBuilder


class ReverseDirection(t.enum8):
    """reverse_direction values (z2m)."""

    forward = 0x00
    back = 0x01


class UpperStrokeLimit(t.enum8):
    """upper_stroke_limit values (z2m)."""

    RESET = 0x00
    SET = 0x01


class MiddleStrokeLimit(t.enum8):
    """middle_stroke_limit values (z2m)."""

    RESET = 0x00
    SET = 0x01


class LowerStrokeLimit(t.enum8):
    """lower_stroke_limit values (z2m)."""

    RESET = 0x00
    SET = 0x01


class MotorWorkingMode(t.enum8):
    """motor_working_mode values (z2m)."""

    continuous = 0x00
    intermittently = 0x01



_LOGGER = logging.getLogger(__name__)
_SHIPPED = pathlib.Path(zhaquirks.__file__).resolve().parent
_STEPPED_BACK: set = set()

# The Zigbee fingerprints (manufacturer, model) this quirk is for; None matches any manufacturer.
FINGERPRINTS = [('_TZE204_r0jdjrvi', 'TS0601'), ('_TZE200_g5xqosu7', 'TS0601'), ('_TZE204_g5xqosu7', 'TS0601'), ('_TZE284_fzo2pocs', 'TS0601')]
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
    .applies_to('_TZE204_r0jdjrvi', 'TS0601')
    .applies_to('_TZE200_g5xqosu7', 'TS0601')
    .applies_to('_TZE204_g5xqosu7', 'TS0601')
    .applies_to('_TZE284_fzo2pocs', 'TS0601')
    .tuya_cover(control_dp=1, position_state_dp=3, position_control_dp=2, invert=False)
    .tuya_enum(dp_id=5, attribute_name='reverse_direction', enum_class=ReverseDirection, entity_type=EntityType.CONFIG, translation_key='reverse_direction', fallback_name='Reverse direction')
    .tuya_dp_attribute(dp_id=12, attribute_name='motor_fault', type=t.Bool, access=foundation.ZCLAttributeAccess.Read | foundation.ZCLAttributeAccess.Report, converter=lambda x: x == 1)
    .binary_sensor(attribute_name='motor_fault', cluster_id=TUYA_CLUSTER_ID, entity_type=EntityType.STANDARD, translation_key='motor_fault', fallback_name='Motor fault')
    .tuya_dp_attribute(dp_id=103, attribute_name='upper_stroke_limit', type=UpperStrokeLimit, access=foundation.ZCLAttributeAccess.Read | foundation.ZCLAttributeAccess.Write, converter=lambda x: UpperStrokeLimit(int(x)), dp_converter=lambda x: t.Bool(int(x)))
    .enum(attribute_name='upper_stroke_limit', enum_class=UpperStrokeLimit, cluster_id=TUYA_CLUSTER_ID, entity_platform=EntityPlatform.SELECT, entity_type=EntityType.CONFIG, translation_key='upper_stroke_limit', fallback_name='Upper stroke limit')
    .tuya_dp_attribute(dp_id=104, attribute_name='middle_stroke_limit', type=MiddleStrokeLimit, access=foundation.ZCLAttributeAccess.Read | foundation.ZCLAttributeAccess.Write, converter=lambda x: MiddleStrokeLimit(int(x)), dp_converter=lambda x: t.Bool(int(x)))
    .enum(attribute_name='middle_stroke_limit', enum_class=MiddleStrokeLimit, cluster_id=TUYA_CLUSTER_ID, entity_platform=EntityPlatform.SELECT, entity_type=EntityType.CONFIG, translation_key='middle_stroke_limit', fallback_name='Middle stroke limit')
    .tuya_dp_attribute(dp_id=105, attribute_name='lower_stroke_limit', type=LowerStrokeLimit, access=foundation.ZCLAttributeAccess.Read | foundation.ZCLAttributeAccess.Write, converter=lambda x: LowerStrokeLimit(int(x)), dp_converter=lambda x: t.Bool(int(x)))
    .enum(attribute_name='lower_stroke_limit', enum_class=LowerStrokeLimit, cluster_id=TUYA_CLUSTER_ID, entity_platform=EntityPlatform.SELECT, entity_type=EntityType.CONFIG, translation_key='lower_stroke_limit', fallback_name='Lower stroke limit')
    .tuya_enum(dp_id=106, attribute_name='motor_working_mode', enum_class=MotorWorkingMode, entity_type=EntityType.CONFIG, translation_key='motor_working_mode', fallback_name='Motor working mode')
    .skip_configuration()
    .filter(no_builtin_quirk)
    .add_to_registry()
)
