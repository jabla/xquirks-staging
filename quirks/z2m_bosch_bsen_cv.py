"""Bosch BSEN-CV: Door/window contact II plus.

Generated from the Zigbee2MQTT definition.
Data: zigbee-herdsman-converters, MIT, Copyright (c) 2018 Koen Kanters.
Status: generated, not verified on hardware.
Revision: cc439a52
"""

import functools
import logging
import pathlib

import zhaquirks
from zha.quirks import DEVICE_REGISTRY, DeviceMatch
import zigpy.types as t
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef

from zhaquirks.builder import (
    EntityPlatform,
    EntityType,
    NumberDeviceClass,
    QuirkBuilder,
    UnitOfTime,
)
from zhaquirks.clusters import CustomCluster


class BoschDoorWindowContactClusterCluster(CustomCluster):
    """boschDoorWindowContactCluster (z2m custom cluster)."""

    cluster_id = 0xFCAD

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        break_function_enabled = ZCLAttributeDef(id=0x0000, type=t.uint8_t, manufacturer_code=0x1209)
        break_function_state = ZCLAttributeDef(id=0x0001, type=t.uint8_t, manufacturer_code=0x1209)
        break_function_timeout = ZCLAttributeDef(id=0x0002, type=t.uint8_t, manufacturer_code=0x1209)
        vibration_detection_enabled = ZCLAttributeDef(id=0x0004, type=t.uint8_t, manufacturer_code=0x1209)
        vibration_detection_sensitivity = ZCLAttributeDef(id=0x0005, type=t.uint8_t, manufacturer_code=0x1209)
        unknown_one = ZCLAttributeDef(id=0x0007, type=t.uint8_t, manufacturer_code=0x1209)
        unknown_two = ZCLAttributeDef(id=0x0008, type=t.uint16_t, manufacturer_code=0x1209)
        unknown_three = ZCLAttributeDef(id=0x0009, type=t.uint8_t, manufacturer_code=0x1209)
        unknown_four = ZCLAttributeDef(id=0x000A, type=t.uint8_t, manufacturer_code=0x1209)


class VibrationDetectionSensitivity(t.enum8):
    """vibration_detection_sensitivity values (z2m)."""

    low = 0x01
    moderate = 0x02
    medium = 0x03
    high = 0x04
    very_high = 0x05


class BreakFunctionState(t.enum8):
    """break_function_state values (z2m)."""

    idle = 0x00
    break_active = 0x01



_LOGGER = logging.getLogger(__name__)
_SHIPPED = pathlib.Path(zhaquirks.__file__).resolve().parent
_STEPPED_BACK: set = set()

# The Zigbee fingerprints (manufacturer, model) this quirk is for; None matches any manufacturer.
FINGERPRINTS = [(None, 'RBSH-SWDV-ZB')]
# Names that a model-only fingerprint would catch but Zigbee2MQTT gives to other devices.
CLAIMED_ELSEWHERE = set()
# The endpoints this quirk needs, each with the input clusters it puts there where Zigbee2MQTT names none.
ENDPOINTS = {1: (0xFCAD,)}


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
    QuirkBuilder(None, 'RBSH-SWDV-ZB')
    .replaces(BoschDoorWindowContactClusterCluster)
    .switch(attribute_name=BoschDoorWindowContactClusterCluster.AttributeDefs.vibration_detection_enabled.name, cluster_id=BoschDoorWindowContactClusterCluster.cluster_id, entity_type=EntityType.CONFIG, translation_key='vibration_detection_enabled', fallback_name='Vibration detection')
    .enum(attribute_name=BoschDoorWindowContactClusterCluster.AttributeDefs.vibration_detection_sensitivity.name, cluster_id=BoschDoorWindowContactClusterCluster.cluster_id, enum_class=VibrationDetectionSensitivity, entity_type=EntityType.CONFIG, translation_key='vibration_detection_sensitivity', fallback_name='Vibration detection sensitivity')
    .switch(attribute_name=BoschDoorWindowContactClusterCluster.AttributeDefs.break_function_enabled.name, cluster_id=BoschDoorWindowContactClusterCluster.cluster_id, entity_type=EntityType.CONFIG, translation_key='break_function_enabled', fallback_name='Break function')
    .number(attribute_name=BoschDoorWindowContactClusterCluster.AttributeDefs.break_function_timeout.name, cluster_id=BoschDoorWindowContactClusterCluster.cluster_id, min_value=1, max_value=15, unit=UnitOfTime.MINUTES, device_class=NumberDeviceClass.DURATION, entity_type=EntityType.CONFIG, translation_key='break_function_timeout', fallback_name='Automatic time limit for breaks')
    .enum(attribute_name=BoschDoorWindowContactClusterCluster.AttributeDefs.break_function_state.name, cluster_id=BoschDoorWindowContactClusterCluster.cluster_id, enum_class=BreakFunctionState, entity_platform=EntityPlatform.SENSOR, entity_type=EntityType.STANDARD, translation_key='break_function_state', fallback_name='Break function state')
    # contact: standard clusters, ZHA's own entities
    # action: standard clusters, ZHA's own entities
    # vibration: z2m's own code, not generated
    # battery: standard clusters, ZHA's own entities
    # battery_low: standard clusters, ZHA's own entities
    .filter(no_builtin_quirk)
    .add_to_registry()
)
