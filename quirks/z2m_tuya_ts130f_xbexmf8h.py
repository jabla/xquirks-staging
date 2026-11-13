"""Tuya TS130F_xbexmf8h: Blind/curtain motor controller.

Generated from the Zigbee2MQTT definition.
Data: zigbee-herdsman-converters, MIT, Copyright (c) 2018 Koen Kanters.
Status: generated, not verified on hardware.
Revision: c106935d
"""

import functools
import logging
import pathlib

import zhaquirks
from zha.quirks import DEVICE_REGISTRY, DeviceMatch
import zigpy.types as t
from zigpy.profiles.zha import DeviceType
from zigpy.zcl import foundation
from zigpy.zcl.clusters.closures import WindowCovering

from zhaquirks.builder import (
    EntityType,
    SensorDeviceClass,
    SensorStateClass,
    UnitOfTime,
)
from zhaquirks.tuya import TUYA_CLUSTER_ID
from zhaquirks.tuya.builder import TuyaQuirkBuilder
from zhaquirks.tuya.mcu import TuyaWindowCovering


class CalibrationValue(t.enum8):
    """calibration wire values (z2m)."""

    on = 0x00
    off = 0x01


class MotorDirection(t.enum8):
    """motor_direction values (z2m)."""

    normal = 0x00
    reversed = 0x01


class SwitchType(t.enum8):
    """switch_type values (z2m)."""

    momentary = 0x00
    toggle = 0x01


class BacklightModeValue(t.enum8):
    """backlight_mode wire values (z2m)."""

    on = 0x00
    off = 0x01



_LOGGER = logging.getLogger(__name__)
_SHIPPED = pathlib.Path(zhaquirks.__file__).resolve().parent
_STEPPED_BACK: set = set()

# The Zigbee fingerprints (manufacturer, model) this quirk is for; None matches any manufacturer.
FINGERPRINTS = [('_TZE20C_xbexmf8h', 'TS130F')]
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
    .applies_to('_TZE20C_xbexmf8h', 'TS130F')
    .tuya_dp(dp_id=1, ep_attribute=TuyaWindowCovering.ep_attribute, attribute_name=TuyaWindowCovering.AttributeDefs.tuya_cover_command.name)
    .tuya_dp(dp_id=2, ep_attribute=TuyaWindowCovering.ep_attribute, attribute_name=WindowCovering.AttributeDefs.current_position_lift_percentage.name, converter=lambda x: 100 - x, dp_converter=lambda x: 100 - x)
    .adds(TuyaWindowCovering)
    .replaces_endpoint(1, device_type=DeviceType.WINDOW_COVERING_DEVICE)
    .tuya_dp_attribute(dp_id=3, attribute_name='calibration', type=t.Bool, access=foundation.ZCLAttributeAccess.Read | foundation.ZCLAttributeAccess.Write, converter=lambda x: x == 0, dp_converter=lambda x: CalibrationValue.on if x else CalibrationValue.off)
    .switch(attribute_name='calibration', cluster_id=TUYA_CLUSTER_ID, entity_type=EntityType.CONFIG, translation_key='calibration', fallback_name='Calibration')
    .tuya_enum(dp_id=8, attribute_name='motor_direction', enum_class=MotorDirection, entity_type=EntityType.CONFIG, translation_key='motor_direction', fallback_name='Motor direction')
    .tuya_sensor(dp_id=10, attribute_name='calibration_time', type=t.uint32_t, divisor=10, state_class=SensorStateClass.MEASUREMENT, device_class=SensorDeviceClass.DURATION, unit=UnitOfTime.SECONDS, entity_type=EntityType.DIAGNOSTIC, translation_key='calibration_time', fallback_name='Calibration time')
    .tuya_enum(dp_id=12, attribute_name='switch_type', enum_class=SwitchType, entity_type=EntityType.CONFIG, translation_key='switch_type', fallback_name='Switch type')
    .tuya_dp_attribute(dp_id=14, attribute_name='backlight_mode', type=t.Bool, access=foundation.ZCLAttributeAccess.Read | foundation.ZCLAttributeAccess.Write, converter=lambda x: x == 0, dp_converter=lambda x: BacklightModeValue.on if x else BacklightModeValue.off)
    .switch(attribute_name='backlight_mode', cluster_id=TUYA_CLUSTER_ID, entity_type=EntityType.CONFIG, translation_key='backlight_mode', fallback_name='Backlight mode')
    .filter(no_builtin_quirk)
    .add_to_registry()
)
