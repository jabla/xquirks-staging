"""Tuya TS0601_4gang_7ytnacie: Four gang smart switch with colored backlight modes.

Generated from the Zigbee2MQTT definition.
Data: zigbee-herdsman-converters, MIT, Copyright (c) 2018 Koen Kanters.
Status: generated, not verified on hardware.
Revision: f5c64c56
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


class PowerOnBehavior(t.enum8):
    """power_on_behavior values (z2m)."""

    off = 0x00
    on = 0x01
    previous = 0x02


class IndicatorMode(t.enum8):
    """indicator_mode values (z2m)."""

    off = 0x00
    on_off_status = 0x01
    switch_position = 0x02


class OnColor(t.enum8):
    """on_color values (z2m)."""

    red = 0x00
    blue = 0x01
    green = 0x02
    white = 0x03
    yellow = 0x04
    magenta = 0x05
    cyan = 0x06
    warm_white = 0x07
    warm_yellow = 0x08


class OffColor(t.enum8):
    """off_color values (z2m)."""

    red = 0x00
    blue = 0x01
    green = 0x02
    white = 0x03
    yellow = 0x04
    magenta = 0x05
    cyan = 0x06
    warm_white = 0x07
    warm_yellow = 0x08



_LOGGER = logging.getLogger(__name__)
_SHIPPED = pathlib.Path(zhaquirks.__file__).resolve().parent
_STEPPED_BACK: set = set()

# The Zigbee fingerprints (manufacturer, model) this quirk is for; None matches any manufacturer.
FINGERPRINTS = [('_TZE204_7ytnacie', 'TS0601'), ('_TZE204_hewlydpz', 'TS0601')]
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
    .applies_to('_TZE204_7ytnacie', 'TS0601')
    .applies_to('_TZE204_hewlydpz', 'TS0601')
    .tuya_onoff(dp_id=13)
    .tuya_switch(dp_id=1, attribute_name='state_l1', entity_type=EntityType.STANDARD, translation_key='z2m_state', fallback_name='State')
    .tuya_switch(dp_id=2, attribute_name='state_l2', entity_type=EntityType.STANDARD, translation_key='z2m_state', fallback_name='State')
    .tuya_switch(dp_id=3, attribute_name='state_l3', entity_type=EntityType.STANDARD, translation_key='state_l3', fallback_name='State')
    .tuya_switch(dp_id=4, attribute_name='state_l4', entity_type=EntityType.STANDARD, translation_key='state_l4', fallback_name='State')
    .tuya_number(dp_id=7, type=t.uint32_t, attribute_name='countdown_l1', min_value=0, max_value=86400, unit=UnitOfTime.SECONDS, device_class=NumberDeviceClass.DURATION, entity_type=EntityType.CONFIG, translation_key='z2m_countdown_l1', fallback_name='Countdown L1')
    .tuya_number(dp_id=8, type=t.uint32_t, attribute_name='countdown_l2', min_value=0, max_value=86400, unit=UnitOfTime.SECONDS, device_class=NumberDeviceClass.DURATION, entity_type=EntityType.CONFIG, translation_key='z2m_countdown_l2', fallback_name='Countdown L2')
    .tuya_number(dp_id=9, type=t.uint32_t, attribute_name='countdown_l3', min_value=0, max_value=86400, unit=UnitOfTime.SECONDS, device_class=NumberDeviceClass.DURATION, entity_type=EntityType.CONFIG, translation_key='z2m_countdown_l3', fallback_name='Countdown L3')
    .tuya_number(dp_id=10, type=t.uint32_t, attribute_name='countdown_l4', min_value=0, max_value=86400, unit=UnitOfTime.SECONDS, device_class=NumberDeviceClass.DURATION, entity_type=EntityType.CONFIG, translation_key='z2m_countdown_l4', fallback_name='Countdown L4')
    .tuya_enum(dp_id=14, attribute_name='power_on_behavior', enum_class=PowerOnBehavior, entity_type=EntityType.CONFIG, translation_key='z2m_power_on_behavior_2', fallback_name='Power-on behavior')
    .tuya_enum(dp_id=15, attribute_name='indicator_mode', enum_class=IndicatorMode, entity_type=EntityType.CONFIG, translation_key='indicator_mode', fallback_name='Indicator mode')
    .tuya_switch(dp_id=16, attribute_name='backlight_switch', entity_type=EntityType.CONFIG, translation_key='backlight_switch', fallback_name='Backlight switch')
    .tuya_switch(dp_id=101, attribute_name='child_lock', entity_type=EntityType.CONFIG, translation_key='child_lock', fallback_name='Child lock')
    .tuya_number(dp_id=102, type=t.uint32_t, attribute_name='backlight', min_value=0, max_value=100, unit=PERCENTAGE, entity_type=EntityType.CONFIG, translation_key='backlight', fallback_name='Backlight')
    .tuya_enum(dp_id=103, attribute_name='on_color', enum_class=OnColor, entity_type=EntityType.CONFIG, translation_key='on_color', fallback_name='On color')
    .tuya_enum(dp_id=104, attribute_name='off_color', enum_class=OffColor, entity_type=EntityType.CONFIG, translation_key='off_color', fallback_name='Off color')
    .skip_configuration()
    .filter(no_builtin_quirk)
    .add_to_registry()
)
