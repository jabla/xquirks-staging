"""NEO NAS-WV03B: Smart sprinkler timer with measurements.

Generated from the Zigbee2MQTT definition.
Zigbee2MQTT lists these names with _TZE204_rzrrjkz2 / TS0601, _TZE204_uab532m0 / TS0601, but the
quirk ZHA ships for those does not fit them (it shows DP 15 at 264.172 x z2m's value). These
names get their own quirk instead of an alias; once a quirk shipped with ZHA matches them, this
file steps back.
Data: zigbee-herdsman-converters, MIT, Copyright (c) 2018 Koen Kanters.
Status: generated, not verified on hardware.
Revision: 923408f4
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
    NumberDeviceClass,
    SensorDeviceClass,
    SensorStateClass,
    UnitOfTime,
)
from zhaquirks.tuya import TUYA_CLUSTER_ID
from zhaquirks.tuya.builder import TuyaQuirkBuilder


class Status(t.enum8):
    """status values (z2m)."""

    off = 0x00
    on_auto = 0x01
    button_locked = 0x02
    on_manual_app = 0x03
    on_manual_button = 0x04


class WaterTotalReset(t.enum8):
    """water_total_reset values (z2m)."""

    idle = 0x00
    reset = 0x01


class Refresh(t.enum8):
    """refresh values (z2m)."""

    idle = 0x00



_LOGGER = logging.getLogger(__name__)
_SHIPPED = pathlib.Path(zhaquirks.__file__).resolve().parent
_STEPPED_BACK: set = set()

# The Zigbee fingerprints (manufacturer, model) this quirk is for; None matches any manufacturer.
FINGERPRINTS = [('_TZE284_rzrrjkz2', 'TS0601'), ('_TZE284_uab532m0', 'TS0601'), ('_TZE204_nnhwcvbk', 'TS0601'), ('_TZE284_nnhwcvbk', 'TS0601')]
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
    .applies_to('_TZE284_rzrrjkz2', 'TS0601')
    .applies_to('_TZE284_uab532m0', 'TS0601')
    .applies_to('_TZE204_nnhwcvbk', 'TS0601')
    .applies_to('_TZE284_nnhwcvbk', 'TS0601')
    .tuya_onoff(dp_id=1)
    .tuya_dp_attribute(dp_id=3, attribute_name='status', type=Status, access=foundation.ZCLAttributeAccess.Read | foundation.ZCLAttributeAccess.Report, converter=lambda x: Status(int(x)))
    .enum(attribute_name='status', enum_class=Status, cluster_id=TUYA_CLUSTER_ID, entity_platform=EntityPlatform.SENSOR, entity_type=EntityType.STANDARD, translation_key='status', fallback_name='Status')
    .tuya_number(dp_id=5, type=t.uint32_t, attribute_name='countdown', min_value=1, max_value=240, step=1, unit=UnitOfTime.MINUTES, device_class=NumberDeviceClass.DURATION, entity_type=EntityType.CONFIG, translation_key='countdown', fallback_name='Countdown')
    .tuya_sensor(dp_id=6, attribute_name='countdown_left', type=t.uint32_t, state_class=SensorStateClass.MEASUREMENT, device_class=SensorDeviceClass.DURATION, unit=UnitOfTime.MINUTES, entity_type=EntityType.STANDARD, translation_key='countdown_left', fallback_name='Countdown left')
    .tuya_sensor(dp_id=9, attribute_name='water_current', type=t.uint32_t, divisor=1000, state_class=SensorStateClass.MEASUREMENT, unit='gal/min', entity_type=EntityType.STANDARD, translation_key='water_current', fallback_name='Water current')
    .tuya_battery(dp_id=11, scale=2)
    .tuya_sensor(dp_id=15, attribute_name='water_total', type=t.uint32_t, divisor=1000, state_class=SensorStateClass.MEASUREMENT, unit='gal', entity_type=EntityType.STANDARD, translation_key='water_total', fallback_name='Water total')
    .tuya_binary_sensor(dp_id=19, attribute_name='fault', entity_type=EntityType.DIAGNOSTIC, translation_key='fault', fallback_name='Fault')
    .tuya_dp_attribute(dp_id=101, attribute_name='water_total_reset', type=WaterTotalReset, access=foundation.ZCLAttributeAccess.Read | foundation.ZCLAttributeAccess.Write, converter=lambda x: WaterTotalReset(int(x)), dp_converter=lambda x: t.Bool(int(x)))
    .enum(attribute_name='water_total_reset', enum_class=WaterTotalReset, cluster_id=TUYA_CLUSTER_ID, entity_platform=EntityPlatform.SELECT, entity_type=EntityType.CONFIG, translation_key='water_total_reset', fallback_name='Water total reset')
    .tuya_number(dp_id=102, type=t.uint32_t, attribute_name='quantitative_watering', min_value=1, max_value=10000, step=1, unit='gal', entity_type=EntityType.CONFIG, translation_key='quantitative_watering', fallback_name='Quantitative watering')
    .tuya_switch(dp_id=103, attribute_name='flow_switch', entity_type=EntityType.STANDARD, translation_key='flow_switch', fallback_name='Flow switch')
    .tuya_switch(dp_id=104, attribute_name='child_lock', entity_type=EntityType.CONFIG, translation_key='child_lock', fallback_name='Child lock')
    .tuya_sensor(dp_id=105, attribute_name='surplus_flow', type=t.uint32_t, state_class=SensorStateClass.MEASUREMENT, unit='gal', entity_type=EntityType.STANDARD, translation_key='surplus_flow', fallback_name='Surplus flow')
    .tuya_sensor(dp_id=106, attribute_name='single_watering_duration', type=t.uint32_t, state_class=SensorStateClass.MEASUREMENT, device_class=SensorDeviceClass.DURATION, unit=UnitOfTime.SECONDS, entity_type=EntityType.STANDARD, translation_key='single_watering_duration', fallback_name='Single watering duration')
    .tuya_dp_attribute(dp_id=107, attribute_name='refresh', type=Refresh, access=foundation.ZCLAttributeAccess.Read | foundation.ZCLAttributeAccess.Write, converter=lambda x: Refresh(int(x)), dp_converter=lambda x: t.Bool(int(x)))
    .enum(attribute_name='refresh', enum_class=Refresh, cluster_id=TUYA_CLUSTER_ID, entity_platform=EntityPlatform.SELECT, entity_type=EntityType.CONFIG, translation_key='refresh', fallback_name='Refresh')
    .tuya_sensor(dp_id=108, attribute_name='single_watering_amount', type=t.uint32_t, state_class=SensorStateClass.MEASUREMENT, unit='gal', entity_type=EntityType.STANDARD, translation_key='single_watering_amount', fallback_name='Single watering amount')
    .tuya_number(dp_id=109, type=t.uint32_t, attribute_name='on_with_countdown', min_value=1, max_value=240, step=1, unit=UnitOfTime.MINUTES, device_class=NumberDeviceClass.DURATION, entity_type=EntityType.STANDARD, translation_key='on_with_countdown', fallback_name='On with countdown')
    # DP 37 (weather_delay): z2m exposes no entity for it, not generated
    # DP 38 (normal_timer): z2m exposes no entity for it, not generated
    # DP 42 (weather_switch): z2m exposes no entity for it, not generated
    # DP 47 (smart_irrigation): z2m exposes no entity for it, not generated
    # DP 110 (quantitative_water_linkage): z2m exposes no entity for it, not generated
    .skip_configuration()
    .filter(no_builtin_quirk)
    .add_to_registry()
)
