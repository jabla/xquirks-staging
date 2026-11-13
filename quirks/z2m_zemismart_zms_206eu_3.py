"""Zemismart ZMS-206EU-3: Smart screen switch 3 gang.

Generated from the Zigbee2MQTT definition.
Data: zigbee-herdsman-converters, MIT, Copyright (c) 2018 Koen Kanters.
Status: generated, not verified on hardware.
Revision: 436a1a96
"""

import functools
import logging
import pathlib

import zhaquirks
from zha.quirks import DEVICE_REGISTRY, DeviceMatch
import zigpy.types as t

from zhaquirks.builder import (
    EntityType,
    NumberDeviceClass,
    PERCENTAGE,
    UnitOfTime,
)
from zhaquirks.tuya.builder import TuyaQuirkBuilder


class IndicatorStatus(t.enum8):
    """indicator_status values (z2m)."""

    off = 0x00
    on_off_status = 0x01
    switch_position = 0x02


class DelayOffSchedule(t.enum8):
    """delay_off_schedule values (z2m)."""

    red = 0x00
    blue = 0x01
    green = 0x02
    white = 0x03
    yellow = 0x04
    magenta = 0x05
    cyan = 0x06
    warmwhite = 0x07
    warmyellow = 0x08


class RelayStatusL1(t.enum8):
    """relay_status_l1 values (z2m)."""

    power_off = 0x00
    power_on = 0x01
    restart_memory = 0x02


class RelayStatusL2(t.enum8):
    """relay_status_l2 values (z2m)."""

    power_off = 0x00
    power_on = 0x01
    restart_memory = 0x02


class RelayStatusL3(t.enum8):
    """relay_status_l3 values (z2m)."""

    power_off = 0x00
    power_on = 0x01
    restart_memory = 0x02


class SwitchColorOn(t.enum8):
    """switch_color_on values (z2m)."""

    red = 0x00
    blue = 0x01
    green = 0x02
    white = 0x03
    yellow = 0x04
    magenta = 0x05
    cyan = 0x06
    warmwhite = 0x07
    warmyellow = 0x08


class SwitchColorOff(t.enum8):
    """switch_color_off values (z2m)."""

    red = 0x00
    blue = 0x01
    green = 0x02
    white = 0x03
    yellow = 0x04
    magenta = 0x05
    cyan = 0x06
    warmwhite = 0x07
    warmyellow = 0x08


class RadarConfig(t.enum8):
    """radar_config values (z2m)."""

    none = 0x00
    Config_10s = 0x01
    Config_20s = 0x02
    Config_30s = 0x03
    Config_45s = 0x04
    Config_60s = 0x05



_LOGGER = logging.getLogger(__name__)
_SHIPPED = pathlib.Path(zhaquirks.__file__).resolve().parent
_STEPPED_BACK: set = set()

# The Zigbee fingerprints (manufacturer, model) this quirk is for; None matches any manufacturer.
FINGERPRINTS = [('_TZE204_k7v0eqke', 'TS0601'), ('_TZE204_iyki9kjp', 'TS0601'), ('_TZE284_k7v0eqke', 'TS0601'), ('_TZE284_e4pf6l87', 'TS0601'), ('_TZE28C1000000_e4pf6l87', 'TS0601')]
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
    .applies_to('_TZE204_k7v0eqke', 'TS0601')
    .applies_to('_TZE204_iyki9kjp', 'TS0601')
    .applies_to('_TZE284_k7v0eqke', 'TS0601')
    .applies_to('_TZE284_e4pf6l87', 'TS0601')
    .applies_to('_TZE28C1000000_e4pf6l87', 'TS0601')
    .tuya_switch(dp_id=1, attribute_name='state_l1', entity_type=EntityType.STANDARD, translation_key='z2m_state', fallback_name='State')
    .tuya_switch(dp_id=2, attribute_name='state_l2', entity_type=EntityType.STANDARD, translation_key='z2m_state', fallback_name='State')
    .tuya_switch(dp_id=3, attribute_name='state_l3', entity_type=EntityType.STANDARD, translation_key='state_l3', fallback_name='State')
    .tuya_number(dp_id=7, type=t.uint32_t, attribute_name='countdown_l1', min_value=0, max_value=43200, step=1, unit=UnitOfTime.SECONDS, device_class=NumberDeviceClass.DURATION, entity_type=EntityType.CONFIG, translation_key='z2m_countdown', fallback_name='Countdown')
    .tuya_number(dp_id=8, type=t.uint32_t, attribute_name='countdown_l2', min_value=0, max_value=43200, step=1, unit=UnitOfTime.SECONDS, device_class=NumberDeviceClass.DURATION, entity_type=EntityType.CONFIG, translation_key='z2m_countdown', fallback_name='Countdown')
    .tuya_number(dp_id=9, type=t.uint32_t, attribute_name='countdown_l3', min_value=0, max_value=43200, step=1, unit=UnitOfTime.SECONDS, device_class=NumberDeviceClass.DURATION, entity_type=EntityType.CONFIG, translation_key='z2m_countdown', fallback_name='Countdown')
    .tuya_onoff(dp_id=13)
    .tuya_enum(dp_id=15, attribute_name='indicator_status', enum_class=IndicatorStatus, entity_type=EntityType.CONFIG, translation_key='indicator_status', fallback_name='Indicator status')
    .tuya_switch(dp_id=16, attribute_name='backlight_mode', entity_type=EntityType.CONFIG, translation_key='backlight_mode', fallback_name='Backlight mode')
    .tuya_enum(dp_id=19, attribute_name='delay_off_schedule', enum_class=DelayOffSchedule, entity_type=EntityType.CONFIG, translation_key='delay_off_schedule', fallback_name='Delay off schedule')
    .tuya_enum(dp_id=29, attribute_name='relay_status_l1', enum_class=RelayStatusL1, entity_type=EntityType.CONFIG, translation_key='relay_status_l1', fallback_name='Relay status')
    .tuya_enum(dp_id=30, attribute_name='relay_status_l2', enum_class=RelayStatusL2, entity_type=EntityType.CONFIG, translation_key='relay_status_l2', fallback_name='Relay status')
    .tuya_enum(dp_id=31, attribute_name='relay_status_l3', enum_class=RelayStatusL3, entity_type=EntityType.CONFIG, translation_key='relay_status_l3', fallback_name='Relay status')
    .tuya_switch(dp_id=101, attribute_name='child_lock', entity_type=EntityType.CONFIG, translation_key='child_lock', fallback_name='Child lock')
    .tuya_number(dp_id=102, type=t.uint32_t, attribute_name='backlight_brightness', min_value=0, max_value=100, step=1, unit=PERCENTAGE, entity_type=EntityType.CONFIG, translation_key='backlight_brightness', fallback_name='Backlight brightness')
    .tuya_enum(dp_id=103, attribute_name='switch_color_on', enum_class=SwitchColorOn, entity_type=EntityType.CONFIG, translation_key='switch_color_on', fallback_name='Switch color on')
    .tuya_enum(dp_id=104, attribute_name='switch_color_off', enum_class=SwitchColorOff, entity_type=EntityType.CONFIG, translation_key='switch_color_off', fallback_name='Switch color off')
    .tuya_enum(dp_id=111, attribute_name='radar_config', enum_class=RadarConfig, entity_type=EntityType.CONFIG, translation_key='radar_config', fallback_name='Radar config')
    # DP 14 (relay_status): z2m exposes no entity for it, not generated
    # DP 24 (test_bit): z2m exposes no entity for it, not generated
    # DP 105 (name_l1): z2m class custom (string output), not generated
    # DP 106 (name_l2): z2m class custom (string output), not generated
    # DP 107 (name_l3): z2m class custom (string output), not generated
    # DP 209 (cycle_schedule): z2m class custom (string output), not generated
    .skip_configuration()
    .filter(no_builtin_quirk)
    .add_to_registry()
)
