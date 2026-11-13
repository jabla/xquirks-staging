"""Lincukoo E04CF-Z10T: Smart gas and CO sensor.

Generated from the Zigbee2MQTT definition.
Data: zigbee-herdsman-converters, MIT, Copyright (c) 2018 Koen Kanters.
Status: generated, not verified on hardware.
Revision: b5d3e77d
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
    SensorStateClass,
)
from zhaquirks.tuya import TUYA_CLUSTER_ID
from zhaquirks.tuya.builder import TuyaQuirkBuilder


class GasSensorState(t.enum8):
    """gas_sensor_state values (z2m)."""

    normal = 0x00
    alarm = 0x01


class CheckingResult(t.enum8):
    """checking_result values (z2m)."""

    checking = 0x00
    check_success = 0x01
    check_failure = 0x02
    others = 0x03


class CoState(t.enum8):
    """co_state values (z2m)."""

    normal = 0x00
    alarm = 0x01



_LOGGER = logging.getLogger(__name__)
_SHIPPED = pathlib.Path(zhaquirks.__file__).resolve().parent
_STEPPED_BACK: set = set()

# The Zigbee fingerprints (manufacturer, model) this quirk is for; None matches any manufacturer.
FINGERPRINTS = [('_TZE204_ra9zfiwr', 'TS0601'), ('_TZE28C1000000_ra9zfiwr', 'TS0601')]
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
    .applies_to('_TZE204_ra9zfiwr', 'TS0601')
    .applies_to('_TZE28C1000000_ra9zfiwr', 'TS0601')
    .tuya_dp_attribute(dp_id=1, attribute_name='gas_sensor_state', type=GasSensorState, access=foundation.ZCLAttributeAccess.Read | foundation.ZCLAttributeAccess.Report, converter=lambda x: GasSensorState(int(x)))
    .enum(attribute_name='gas_sensor_state', enum_class=GasSensorState, cluster_id=TUYA_CLUSTER_ID, entity_platform=EntityPlatform.SENSOR, entity_type=EntityType.STANDARD, translation_key='gas_sensor_state', fallback_name='Gas sensor state')
    .tuya_sensor(dp_id=2, attribute_name='gas', type=t.uint32_t, divisor=1000, state_class=SensorStateClass.MEASUREMENT, unit='%LEL', entity_type=EntityType.STANDARD, translation_key='gas', fallback_name='Gas')
    .tuya_switch(dp_id=8, attribute_name='self_checking', entity_type=EntityType.CONFIG, translation_key='self_checking', fallback_name='Self checking')
    .tuya_dp_attribute(dp_id=9, attribute_name='checking_result', type=CheckingResult, access=foundation.ZCLAttributeAccess.Read | foundation.ZCLAttributeAccess.Report, converter=lambda x: CheckingResult(int(x)))
    .enum(attribute_name='checking_result', enum_class=CheckingResult, cluster_id=TUYA_CLUSTER_ID, entity_platform=EntityPlatform.SENSOR, entity_type=EntityType.STANDARD, translation_key='checking_result', fallback_name='Checking result')
    .tuya_dp_attribute(dp_id=18, attribute_name='co_state', type=CoState, access=foundation.ZCLAttributeAccess.Read | foundation.ZCLAttributeAccess.Report, converter=lambda x: CoState(int(x)))
    .enum(attribute_name='co_state', enum_class=CoState, cluster_id=TUYA_CLUSTER_ID, entity_platform=EntityPlatform.SENSOR, entity_type=EntityType.STANDARD, translation_key='co_state', fallback_name='Co state')
    .tuya_sensor(dp_id=19, attribute_name='co', type=t.uint32_t, state_class=SensorStateClass.MEASUREMENT, unit=CONCENTRATION_PARTS_PER_MILLION, entity_type=EntityType.STANDARD, translation_key='co', fallback_name='CO')
    .tuya_number(dp_id=101, type=t.uint32_t, attribute_name='set_max_gas_alarm', min_value=0.1, max_value=20, step=0.1, unit='%LEL', multiplier=0.001, entity_type=EntityType.CONFIG, translation_key='set_max_gas_alarm', fallback_name='Set max gas alarm')
    .tuya_number(dp_id=102, type=t.uint32_t, attribute_name='set_max_co_alarm', min_value=10, max_value=1000, step=10, unit=CONCENTRATION_PARTS_PER_MILLION, entity_type=EntityType.CONFIG, translation_key='set_max_co_alarm', fallback_name='Set max co alarm')
    .skip_configuration()
    .filter(no_builtin_quirk)
    .add_to_registry()
)
