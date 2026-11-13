"""Senoro Senoro.Win v2: Window sensor with 3-state opening (DP101), optional alarm, battery.

Generated from the Zigbee2MQTT definition.
Data: zigbee-herdsman-converters, MIT, Copyright (c) 2018 Koen Kanters.
Status: generated, not verified on hardware.
Revision: fdfea030
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


class OpeningState(t.enum8):
    """opening_state values (z2m)."""

    open = 0x00
    closed = 0x01
    tilted = 0x02



_LOGGER = logging.getLogger(__name__)
_SHIPPED = pathlib.Path(zhaquirks.__file__).resolve().parent
_STEPPED_BACK: set = set()

# The Zigbee fingerprints (manufacturer, model) this quirk is for; None matches any manufacturer.
FINGERPRINTS = [('_TZE284_6teua268', 'TS0601')]
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
    .applies_to('_TZE284_6teua268', 'TS0601')
    .tuya_dp_attribute(dp_id=101, attribute_name='opening_state', type=OpeningState, access=foundation.ZCLAttributeAccess.Read | foundation.ZCLAttributeAccess.Report, converter=lambda x: OpeningState(int(x)))
    .enum(attribute_name='opening_state', enum_class=OpeningState, cluster_id=TUYA_CLUSTER_ID, entity_platform=EntityPlatform.SENSOR, entity_type=EntityType.STANDARD, translation_key='opening_state', fallback_name='Opening state')
    .tuya_switch(dp_id=16, attribute_name='alarm_state', entity_type=EntityType.STANDARD, translation_key='alarm_state', fallback_name='Alarm state')
    .tuya_switch(dp_id=107, attribute_name='setup_mode', entity_type=EntityType.CONFIG, translation_key='setup_mode', fallback_name='Setup mode')
    .tuya_switch(dp_id=103, attribute_name='alarm_siren', entity_type=EntityType.STANDARD, translation_key='alarm_siren', fallback_name='Alarm siren')
    .tuya_number(dp_id=109, type=t.uint32_t, attribute_name='alarm_siren_duration', min_value=5, max_value=180, step=1, entity_type=EntityType.CONFIG, translation_key='alarm_siren_duration', fallback_name='Alarm siren duration')
    .tuya_sensor(dp_id=102, attribute_name='vibration', type=t.uint32_t, entity_type=EntityType.STANDARD, translation_key='vibration', fallback_name='Vibration')
    .tuya_number(dp_id=106, type=t.uint32_t, attribute_name='vibration_limit', min_value=0, max_value=100, step=1, entity_type=EntityType.CONFIG, translation_key='vibration_limit', fallback_name='Vibration limit')
    .tuya_number(dp_id=110, type=t.uint32_t, attribute_name='vibration_siren_duration', min_value=5, max_value=180, step=1, entity_type=EntityType.CONFIG, translation_key='vibration_siren_duration', fallback_name='Vibration siren duration')
    .tuya_switch(dp_id=108, attribute_name='vibration_siren', entity_type=EntityType.CONFIG, translation_key='vibration_siren', fallback_name='Vibration siren')
    .tuya_switch(dp_id=104, attribute_name='close_signal', entity_type=EntityType.STANDARD, translation_key='close_signal', fallback_name='Close signal')
    .tuya_number(dp_id=105, type=t.uint32_t, attribute_name='transmission_power', min_value=11, max_value=19, step=1, entity_type=EntityType.CONFIG, translation_key='transmission_power', fallback_name='Transmission power')
    .tuya_binary_sensor(dp_id=111, attribute_name='magnetic_status', entity_type=EntityType.STANDARD, translation_key='magnetic_status', fallback_name='Magnetic status')
    .tuya_battery(dp_id=2, scale=2)
    .skip_configuration()
    .filter(no_builtin_quirk)
    .add_to_registry()
)
