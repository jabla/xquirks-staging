"""Tervix Pro Line X10: Underfloor heating controller - 8 zones.

Generated from the Zigbee2MQTT definition.
Data: zigbee-herdsman-converters, MIT, Copyright (c) 2018 Koen Kanters.
Status: generated, not verified on hardware.
Revision: 16ff8ba1
"""

import functools
import logging
import pathlib

import zhaquirks
from zha.quirks import DEVICE_REGISTRY, DeviceMatch
import zigpy.types as t
from zigpy.zcl import foundation

from zhaquirks.builder import (
    EntityType,
)
from zhaquirks.tuya import TUYA_CLUSTER_ID
from zhaquirks.tuya.builder import TuyaQuirkBuilder


class SystemMode(t.enum8):
    """system_mode values (z2m)."""

    cool = 0x00
    heat = 0x01



_LOGGER = logging.getLogger(__name__)
_SHIPPED = pathlib.Path(zhaquirks.__file__).resolve().parent
_STEPPED_BACK: set = set()

# The Zigbee fingerprints (manufacturer, model) this quirk is for; None matches any manufacturer.
FINGERPRINTS = [('_TZE284_rfpyqax9', 'TS0601'), ('_TZE204_rfpyqax9', 'TS0601')]
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
    .applies_to('_TZE284_rfpyqax9', 'TS0601')
    .applies_to('_TZE204_rfpyqax9', 'TS0601')
    .tuya_switch(dp_id=33, attribute_name='power', entity_type=EntityType.STANDARD, translation_key='power', fallback_name='Power')
    .tuya_switch(dp_id=101, attribute_name='zone_1', entity_type=EntityType.STANDARD, translation_key='zone_1', fallback_name='Zone 1')
    .tuya_switch(dp_id=102, attribute_name='zone_2', entity_type=EntityType.STANDARD, translation_key='zone_2', fallback_name='Zone 2')
    .tuya_switch(dp_id=103, attribute_name='zone_3', entity_type=EntityType.STANDARD, translation_key='zone_3', fallback_name='Zone 3')
    .tuya_switch(dp_id=104, attribute_name='zone_4', entity_type=EntityType.STANDARD, translation_key='zone_4', fallback_name='Zone 4')
    .tuya_switch(dp_id=105, attribute_name='zone_5', entity_type=EntityType.STANDARD, translation_key='zone_5', fallback_name='Zone 5')
    .tuya_switch(dp_id=106, attribute_name='zone_6', entity_type=EntityType.STANDARD, translation_key='zone_6', fallback_name='Zone 6')
    .tuya_switch(dp_id=107, attribute_name='zone_7', entity_type=EntityType.STANDARD, translation_key='zone_7', fallback_name='Zone 7')
    .tuya_switch(dp_id=108, attribute_name='zone_8', entity_type=EntityType.STANDARD, translation_key='zone_8', fallback_name='Zone 8')
    .tuya_dp_attribute(dp_id=109, attribute_name='pump', type=t.Bool, access=foundation.ZCLAttributeAccess.Read | foundation.ZCLAttributeAccess.Report, converter=lambda x: x == 1)
    .binary_sensor(attribute_name='pump', cluster_id=TUYA_CLUSTER_ID, entity_type=EntityType.STANDARD, translation_key='pump', fallback_name='Pump')
    .tuya_dp_attribute(dp_id=110, attribute_name='boiler', type=t.Bool, access=foundation.ZCLAttributeAccess.Read | foundation.ZCLAttributeAccess.Report, converter=lambda x: x == 1)
    .binary_sensor(attribute_name='boiler', cluster_id=TUYA_CLUSTER_ID, entity_type=EntityType.STANDARD, translation_key='boiler', fallback_name='Boiler')
    .tuya_enum(dp_id=111, attribute_name='system_mode', enum_class=SystemMode, entity_type=EntityType.STANDARD, translation_key='system_mode', fallback_name='System mode')
    .skip_configuration()
    .filter(no_builtin_quirk)
    .add_to_registry()
)
