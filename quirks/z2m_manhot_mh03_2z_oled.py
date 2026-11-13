"""Manhot MH03-2Z-OLED: OLED Screen Switch 2 Gang.

Generated from the Zigbee2MQTT definition.
Data: zigbee-herdsman-converters, MIT, Copyright (c) 2018 Koen Kanters.
Status: generated, not verified on hardware.
Revision: 1525d924
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
    UnitOfTime,
)
from zhaquirks.tuya.builder import TuyaQuirkBuilder


class RelayStatus(t.enum8):
    """relay_status values (z2m)."""

    off = 0x00
    on = 0x01
    memory = 0x02


class LightMode(t.enum8):
    """light_mode values (z2m)."""

    none = 0x00
    relay = 0x01
    pos = 0x02


class OnColor(t.enum8):
    """on_color values (z2m)."""

    red = 0x00
    orange = 0x01
    green = 0x02
    cyan = 0x03
    blue = 0x04
    purple = 0x05
    magenta = 0x06
    cold_white = 0x07
    warm_yellow = 0x08


class OffColor(t.enum8):
    """off_color values (z2m)."""

    red = 0x00
    orange = 0x01
    green = 0x02
    cyan = 0x03
    blue = 0x04
    purple = 0x05
    magenta = 0x06
    cold_white = 0x07
    warm_yellow = 0x08


class PressOnFun(t.enum8):
    """press_on_fun values (z2m)."""

    disable = 0x00
    press_switch_1 = 0x01
    press_switch_2 = 0x02


class PressOffFun(t.enum8):
    """press_off_fun values (z2m)."""

    disable = 0x00
    press_switch_1 = 0x01
    press_switch_2 = 0x02



_LOGGER = logging.getLogger(__name__)
_SHIPPED = pathlib.Path(zhaquirks.__file__).resolve().parent
_STEPPED_BACK: set = set()

# The Zigbee fingerprints (manufacturer, model) this quirk is for; None matches any manufacturer.
FINGERPRINTS = [('_TZE284_dnhhp8ew', 'TS0601'), ('_TZE28C1000000_dnhhp8ew', 'TS0601')]
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
    .applies_to('_TZE284_dnhhp8ew', 'TS0601')
    .applies_to('_TZE28C1000000_dnhhp8ew', 'TS0601')
    .tuya_switch(dp_id=1, attribute_name='state_l1', entity_type=EntityType.STANDARD, translation_key='z2m_state', fallback_name='State')
    .tuya_switch(dp_id=2, attribute_name='state_l2', entity_type=EntityType.STANDARD, translation_key='z2m_state', fallback_name='State')
    .tuya_number(dp_id=7, type=t.uint32_t, attribute_name='countdown_1', min_value=0, max_value=43200, unit=UnitOfTime.SECONDS, device_class=NumberDeviceClass.DURATION, entity_type=EntityType.CONFIG, translation_key='countdown_1', fallback_name='Countdown 1')
    .tuya_number(dp_id=8, type=t.uint32_t, attribute_name='countdown_2', min_value=0, max_value=43200, unit=UnitOfTime.SECONDS, device_class=NumberDeviceClass.DURATION, entity_type=EntityType.CONFIG, translation_key='countdown_2', fallback_name='Countdown 2')
    .tuya_enum(dp_id=14, attribute_name='relay_status', enum_class=RelayStatus, entity_type=EntityType.CONFIG, translation_key='relay_status', fallback_name='Relay status')
    .tuya_enum(dp_id=15, attribute_name='light_mode', enum_class=LightMode, entity_type=EntityType.CONFIG, translation_key='light_mode', fallback_name='Light mode')
    .tuya_switch(dp_id=16, attribute_name='backlight_switch', entity_type=EntityType.CONFIG, translation_key='backlight_switch', fallback_name='Backlight switch')
    .tuya_number(dp_id=101, type=t.uint32_t, attribute_name='backlight_lightness', min_value=1, max_value=100, entity_type=EntityType.CONFIG, translation_key='backlight_lightness', fallback_name='Backlight lightness')
    .tuya_enum(dp_id=102, attribute_name='on_color', enum_class=OnColor, entity_type=EntityType.CONFIG, translation_key='on_color', fallback_name='On color')
    .tuya_enum(dp_id=103, attribute_name='off_color', enum_class=OffColor, entity_type=EntityType.CONFIG, translation_key='off_color', fallback_name='Off color')
    .tuya_number(dp_id=104, type=t.uint32_t, attribute_name='displayoff_delay', min_value=10, max_value=180, unit=UnitOfTime.SECONDS, device_class=NumberDeviceClass.DURATION, entity_type=EntityType.CONFIG, translation_key='displayoff_delay', fallback_name='Displayoff delay')
    .tuya_switch(dp_id=105, attribute_name='child_lock', entity_type=EntityType.CONFIG, translation_key='child_lock', fallback_name='Child lock')
    .tuya_enum(dp_id=118, attribute_name='press_on_fun', enum_class=PressOnFun, entity_type=EntityType.CONFIG, translation_key='press_on_fun', fallback_name='Press on fun')
    .tuya_enum(dp_id=119, attribute_name='press_off_fun', enum_class=PressOffFun, entity_type=EntityType.CONFIG, translation_key='press_off_fun', fallback_name='Press off fun')
    # DP 106 (sw1_name): z2m class raw with a text expose, not generated
    # DP 107 (sw2_name): z2m class raw with a text expose, not generated
    .skip_configuration()
    .filter(no_builtin_quirk)
    .add_to_registry()
)
