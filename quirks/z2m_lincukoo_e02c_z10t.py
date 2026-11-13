"""Lincukoo E02C-Z10T: Smart air quality monitor (CO2).

Generated from the Zigbee2MQTT definition.
Data: zigbee-herdsman-converters, MIT, Copyright (c) 2018 Koen Kanters.
Status: generated, not verified on hardware.
Revision: 9e7abc32
"""

import functools
import logging
import pathlib

import zhaquirks
from zha.quirks import DEVICE_REGISTRY, DeviceMatch
import zigpy.types as t
from zigpy.zcl import foundation

from zhaquirks.builder import (
    CONCENTRATION_PARTS_PER_MILLION,
    EntityPlatform,
    EntityType,
)
from zhaquirks.tuya import TUYA_CLUSTER_ID
from zhaquirks.tuya.builder import TuyaQuirkBuilder


class TemperatureUnitConvert(t.enum8):
    """temperature_unit_convert values (z2m)."""

    celsius = 0x00
    fahrenheit = 0x01


class ChargeStatus(t.enum8):
    """charge_status values (z2m)."""

    none = 0x00
    charging = 0x01


class ResetCo2(t.enum8):
    """reset_co2 values (z2m)."""

    reset_co2 = 0x00


class ScreenSleep(t.enum8):
    """screen_sleep values (z2m)."""

    after_30s = 0x00
    after_1minute = 0x01
    after_2minutes = 0x02
    after_5minutes = 0x03
    after_10minutes = 0x04
    never_sleep = 0x05



_LOGGER = logging.getLogger(__name__)
_SHIPPED = pathlib.Path(zhaquirks.__file__).resolve().parent
_STEPPED_BACK: set = set()

# The Zigbee fingerprints (manufacturer, model) this quirk is for; None matches any manufacturer.
FINGERPRINTS = [('_TZE204_hyt4iucb', 'TS0601'), ('_TZE28C1000000_hyt4iucb', 'TS0601')]
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
    .applies_to('_TZE204_hyt4iucb', 'TS0601')
    .applies_to('_TZE28C1000000_hyt4iucb', 'TS0601')
    .tuya_temperature(dp_id=2, scale=10)
    .tuya_humidity(dp_id=3, scale=100)
    .tuya_co2(dp_id=4, scale=1e-06)
    .tuya_battery(dp_id=22, scale=2)
    .tuya_enum(dp_id=102, attribute_name='temperature_unit_convert', enum_class=TemperatureUnitConvert, entity_type=EntityType.CONFIG, translation_key='temperature_unit_convert', fallback_name='Temperature unit convert')
    .tuya_switch(dp_id=101, attribute_name='alarm_switch', entity_type=EntityType.STANDARD, translation_key='alarm_switch', fallback_name='Alarm switch')
    .tuya_dp_attribute(dp_id=103, attribute_name='charge_status', type=ChargeStatus, access=foundation.ZCLAttributeAccess.Read | foundation.ZCLAttributeAccess.Report, converter=lambda x: ChargeStatus(int(x)))
    .enum(attribute_name='charge_status', enum_class=ChargeStatus, cluster_id=TUYA_CLUSTER_ID, entity_platform=EntityPlatform.SENSOR, entity_type=EntityType.STANDARD, translation_key='charge_status', fallback_name='Charge status')
    .tuya_enum(dp_id=104, attribute_name='reset_co2', enum_class=ResetCo2, entity_type=EntityType.CONFIG, translation_key='reset_co2', fallback_name='Reset CO2')
    .tuya_enum(dp_id=105, attribute_name='screen_sleep', enum_class=ScreenSleep, entity_type=EntityType.CONFIG, translation_key='screen_sleep', fallback_name='Screen sleep')
    .tuya_number(dp_id=106, type=t.uint32_t, attribute_name='co2_alarm_value', min_value=1000, max_value=10000, step=100, unit=CONCENTRATION_PARTS_PER_MILLION, entity_type=EntityType.CONFIG, translation_key='co2_alarm_value', fallback_name='CO2 alarm value')
    .tuya_binary_sensor(dp_id=107, attribute_name='co2_alarm', entity_type=EntityType.STANDARD, translation_key='co2_alarm', fallback_name='CO2 alarm')
    .skip_configuration()
    .filter(no_builtin_quirk)
    .add_to_registry()
)
