"""KnockautX PIMS3028: Cover plug-in receiver multi STAK 3/STAS 3.

Generated from the Zigbee2MQTT definition.
Data: zigbee-herdsman-converters, MIT, Copyright (c) 2018 Koen Kanters.
Status: generated, not verified on hardware.
Revision: 9163a985
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
    EntityPlatform,
    EntityType,
    NumberDeviceClass,
    PERCENTAGE,
    SensorDeviceClass,
    SensorStateClass,
    UnitOfTime,
)
from zhaquirks.tuya import TUYA_CLUSTER_ID
from zhaquirks.tuya.builder import TuyaQuirkBuilder
from zhaquirks.tuya.mcu import TuyaWindowCovering


class Mode(t.enum8):
    """mode values (z2m)."""

    up = 0x00
    up_delete = 0x01
    remove_up_down = 0x02


class ControlBack(t.enum8):
    """control_back values (z2m)."""

    forward = 0x00
    back = 0x01


class WorkState(t.enum8):
    """work_state values (z2m)."""

    opening = 0x00
    closing = 0x01
    State_123 = 0x02


class SituationSet(t.enum8):
    """situation_set values (z2m)."""

    fully_open = 0x00
    fully_close = 0x01


class CoverLimit(t.enum8):
    """cover_limit values (z2m)."""

    set_up = 0x00
    set_down = 0x01
    delete_up = 0x02
    delete_down = 0x03
    delete_both = 0x04


class Calibration(t.enum8):
    """calibration values (z2m)."""

    start = 0x00
    end = 0x01


class Reset(t.enum8):
    """reset values (z2m)."""

    reset = 0x00



_LOGGER = logging.getLogger(__name__)
_SHIPPED = pathlib.Path(zhaquirks.__file__).resolve().parent
_STEPPED_BACK: set = set()

# The Zigbee fingerprints (manufacturer, model) this quirk is for; None matches any manufacturer.
FINGERPRINTS = [('_TZE200_eqpaxqdv', 'TS0601')]
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
    .applies_to('_TZE200_eqpaxqdv', 'TS0601')
    .tuya_dp(dp_id=1, ep_attribute=TuyaWindowCovering.ep_attribute, attribute_name=TuyaWindowCovering.AttributeDefs.tuya_cover_command.name)
    .tuya_dp(dp_id=2, ep_attribute=TuyaWindowCovering.ep_attribute, attribute_name=WindowCovering.AttributeDefs.current_position_lift_percentage.name, converter=lambda x: 100 - x, dp_converter=lambda x: 100 - x)
    .tuya_dp(dp_id=3, ep_attribute=TuyaWindowCovering.ep_attribute, attribute_name=WindowCovering.AttributeDefs.current_position_lift_percentage.name)
    .adds(TuyaWindowCovering)
    .replaces_endpoint(1, device_type=DeviceType.WINDOW_COVERING_DEVICE)
    .tuya_enum(dp_id=4, attribute_name='mode', enum_class=Mode, entity_type=EntityType.CONFIG, translation_key='mode', fallback_name='Mode')
    .tuya_enum(dp_id=5, attribute_name='control_back', enum_class=ControlBack, entity_type=EntityType.CONFIG, translation_key='control_back', fallback_name='Control back')
    .tuya_switch(dp_id=6, attribute_name='auto_power', entity_type=EntityType.STANDARD, translation_key='auto_power', fallback_name='Auto power')
    .tuya_dp_attribute(dp_id=7, attribute_name='work_state', type=WorkState, access=foundation.ZCLAttributeAccess.Read | foundation.ZCLAttributeAccess.Report, converter=lambda x: WorkState(int(x)))
    .enum(attribute_name='work_state', enum_class=WorkState, cluster_id=TUYA_CLUSTER_ID, entity_platform=EntityPlatform.SENSOR, entity_type=EntityType.STANDARD, translation_key='work_state', fallback_name='Work state')
    .tuya_sensor(dp_id=10, attribute_name='time_total', type=t.uint32_t, state_class=SensorStateClass.MEASUREMENT, device_class=SensorDeviceClass.DURATION, unit=UnitOfTime.SECONDS, entity_type=EntityType.STANDARD, translation_key='time_total', fallback_name='Time total')
    .tuya_dp_attribute(dp_id=11, attribute_name='situation_set', type=SituationSet, access=foundation.ZCLAttributeAccess.Read | foundation.ZCLAttributeAccess.Report, converter=lambda x: SituationSet(int(x)))
    .enum(attribute_name='situation_set', enum_class=SituationSet, cluster_id=TUYA_CLUSTER_ID, entity_platform=EntityPlatform.SENSOR, entity_type=EntityType.STANDARD, translation_key='situation_set', fallback_name='Situation set')
    .tuya_binary_sensor(dp_id=12, attribute_name='fault', entity_type=EntityType.STANDARD, translation_key='fault', fallback_name='Fault')
    .tuya_enum(dp_id=16, attribute_name='cover_limit', enum_class=CoverLimit, entity_type=EntityType.CONFIG, translation_key='cover_limit', fallback_name='Cover limit')
    .tuya_number(dp_id=19, type=t.uint32_t, attribute_name='favorite_position', min_value=0, max_value=100, step=1, unit=PERCENTAGE, entity_type=EntityType.CONFIG, translation_key='favorite_position', fallback_name='Favorite position')
    .tuya_number(dp_id=21, type=t.uint32_t, attribute_name='angle_horizontal', min_value=0, max_value=100, step=25, unit='°', entity_type=EntityType.CONFIG, translation_key='angle_horizontal', fallback_name='Angle horizontal')
    .tuya_enum(dp_id=101, attribute_name='calibration', enum_class=Calibration, entity_type=EntityType.CONFIG, translation_key='calibration', fallback_name='Calibration')
    .tuya_number(dp_id=102, type=t.uint32_t, attribute_name='quick_calibration', min_value=0, max_value=900, unit=UnitOfTime.SECONDS, device_class=NumberDeviceClass.DURATION, entity_type=EntityType.CONFIG, translation_key='quick_calibration', fallback_name='Quick calibration')
    .tuya_switch(dp_id=103, attribute_name='switch', entity_type=EntityType.STANDARD, translation_key='z2m_switch', fallback_name='Switch')
    .tuya_enum(dp_id=104, attribute_name='reset', enum_class=Reset, entity_type=EntityType.CONFIG, translation_key='reset', fallback_name='Reset')
    # DP 1 (state): lock, unlock: TuyaWindowCovering sends only open, stop and close, not generated
    .skip_configuration()
    .filter(no_builtin_quirk)
    .add_to_registry()
)
