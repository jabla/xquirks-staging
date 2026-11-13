"""Schneider Electric 41ECSFWMZ-VW: Wiser 40/300-Series Module AC Fan Controller.

Generated from the Zigbee2MQTT definition.
Data: zigbee-herdsman-converters, MIT, Copyright (c) 2018 Koen Kanters.
Status: generated, not verified on hardware.
Revision: 02896892
"""

import functools
import logging
import pathlib

import zhaquirks
from zha.quirks import DEVICE_REGISTRY, DeviceMatch
import zigpy.types as t
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef

from zhaquirks.builder import (
    EntityType,
    QuirkBuilder,
)
from zhaquirks.clusters import CustomCluster


class ManuSpecificSchneiderFanSwitchConfigurationCluster(CustomCluster):
    """manuSpecificSchneiderFanSwitchConfiguration (z2m custom cluster)."""

    cluster_id = 0xFC04

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        led_indication = ZCLAttributeDef(id=0x0002, type=t.uint8_t, manufacturer_code=0x105E)
        led_orientation = ZCLAttributeDef(id=0x0060, type=t.uint8_t, manufacturer_code=0x105E)


class IndicatorMode(t.enum8):
    """indicator_mode values (z2m)."""

    always_on = 0x03
    on_with_timeout_but_as_locator = 0x04
    on_with_timeout = 0x05


class IndicatorOrientation(t.enum8):
    """indicator_orientation values (z2m)."""

    horizontal_right = 0x00
    vertical_bottom = 0x01
    horizontal_left = 0x02
    vertical_top = 0x03



_LOGGER = logging.getLogger(__name__)
_SHIPPED = pathlib.Path(zhaquirks.__file__).resolve().parent
_STEPPED_BACK: set = set()

# The Zigbee fingerprints (manufacturer, model) this quirk is for; None matches any manufacturer.
FINGERPRINTS = [(None, 'CHFAN/SWITCH/1')]
# Names that a model-only fingerprint would catch but Zigbee2MQTT gives to other devices.
CLAIMED_ELSEWHERE = set()
# The endpoints this quirk needs, each with the input clusters it puts there where Zigbee2MQTT names none.
ENDPOINTS = {7: (0xFC04,)}


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
    QuirkBuilder(None, 'CHFAN/SWITCH/1')
    .replaces(ManuSpecificSchneiderFanSwitchConfigurationCluster, endpoint_id=7)
    .enum(attribute_name=ManuSpecificSchneiderFanSwitchConfigurationCluster.AttributeDefs.led_indication.name, cluster_id=ManuSpecificSchneiderFanSwitchConfigurationCluster.cluster_id, endpoint_id=7, enum_class=IndicatorMode, entity_type=EntityType.STANDARD, translation_key='indicator_mode', fallback_name='Indicator mode')
    .enum(attribute_name=ManuSpecificSchneiderFanSwitchConfigurationCluster.AttributeDefs.led_orientation.name, cluster_id=ManuSpecificSchneiderFanSwitchConfigurationCluster.cluster_id, endpoint_id=7, enum_class=IndicatorOrientation, entity_type=EntityType.STANDARD, translation_key='indicator_orientation', fallback_name='Indicator orientation')
    # fan: standard clusters, ZHA's own entities
    .filter(no_builtin_quirk)
    .add_to_registry()
)
