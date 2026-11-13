"""HOBEIAN ZG-301Z-MOTO: Curtain Motor Controller.

Generated from the Zigbee2MQTT definition.
Data: zigbee-herdsman-converters, MIT, Copyright (c) 2018 Koen Kanters.
Status: generated, not verified on hardware.
Revision: de315d30
"""

import functools
import logging
import pathlib

import zhaquirks
from zha.quirks import DEVICE_REGISTRY, DeviceMatch
import zigpy.types as t
from zigpy.profiles.zha import DeviceType
from zigpy.zcl.clusters.closures import WindowCovering

from zhaquirks.builder import (
    EntityType,
    NumberDeviceClass,
    UnitOfTime,
)
from zhaquirks.tuya.builder import TuyaQuirkBuilder
from zhaquirks.tuya.mcu import TuyaWindowCovering


class CurCalibration(t.enum8):
    """cur_calibration values (z2m)."""

    start = 0x00
    end = 0x01


class ControlBack(t.enum8):
    """control_back values (z2m)."""

    forward = 0x00
    back = 0x01


class IndicatorMode(t.enum8):
    """indicator_mode values (z2m)."""

    relay = 0x00
    pos = 0x01
    none = 0x02


class SwitchType(t.enum8):
    """switch_type values (z2m)."""

    flip_switch = 0x00
    sync_switch = 0x01
    button_switch = 0x02



_LOGGER = logging.getLogger(__name__)
_SHIPPED = pathlib.Path(zhaquirks.__file__).resolve().parent
_STEPPED_BACK: set = set()

# The Zigbee fingerprints (manufacturer, model) this quirk is for; None matches any manufacturer.
FINGERPRINTS = [(None, 'ZG-301Z-MOTO'), ('HOBEIAN', 'ZG-301Z-MOTO')]
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
    .applies_to(None, 'ZG-301Z-MOTO')
    .applies_to('HOBEIAN', 'ZG-301Z-MOTO')
    .tuya_dp(dp_id=1, ep_attribute=TuyaWindowCovering.ep_attribute, attribute_name=TuyaWindowCovering.AttributeDefs.tuya_cover_command.name)
    .tuya_dp(dp_id=2, ep_attribute=TuyaWindowCovering.ep_attribute, attribute_name=WindowCovering.AttributeDefs.current_position_lift_percentage.name, converter=lambda x: 100 - x, dp_converter=lambda x: 100 - x)
    .adds(TuyaWindowCovering)
    .replaces_endpoint(1, device_type=DeviceType.WINDOW_COVERING_DEVICE)
    .tuya_enum(dp_id=3, attribute_name='cur_calibration', enum_class=CurCalibration, entity_type=EntityType.CONFIG, translation_key='cur_calibration', fallback_name='Cur calibration')
    .tuya_enum(dp_id=8, attribute_name='control_back', enum_class=ControlBack, entity_type=EntityType.CONFIG, translation_key='control_back', fallback_name='Control back')
    .tuya_number(dp_id=10, type=t.uint32_t, attribute_name='tr_timecon', min_value=0, max_value=120, step=1, unit=UnitOfTime.SECONDS, device_class=NumberDeviceClass.DURATION, entity_type=EntityType.CONFIG, translation_key='tr_timecon', fallback_name='Tr timecon')
    .tuya_enum(dp_id=14, attribute_name='indicator_mode', enum_class=IndicatorMode, entity_type=EntityType.CONFIG, translation_key='indicator_mode', fallback_name='Indicator mode')
    .tuya_enum(dp_id=101, attribute_name='switch_type', enum_class=SwitchType, entity_type=EntityType.CONFIG, translation_key='switch_type', fallback_name='Switch type')
    .skip_configuration()
    .filter(no_builtin_quirk)
    .add_to_registry()
)
