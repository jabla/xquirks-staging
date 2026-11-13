"""Third Reality 3RPL01084Z: Multi-function smart presence sensor R3.

Generated from the Zigbee2MQTT definition.
Entity names follow ZHA's own quirk for this device where it shows the same feature.
Data: zigbee-herdsman-converters, MIT, Copyright (c) 2018 Koen Kanters.
Status: generated, not verified on hardware.
Revision: 6daad2f0
"""

import functools
import logging
import pathlib

import zhaquirks
from zha.quirks import DEVICE_REGISTRY, DeviceMatch
import zigpy.types as t
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef

from zhaquirks.builder import (
    CONCENTRATION_PARTS_PER_BILLION,
    EntityType,
    QuirkBuilder,
    SensorStateClass,
)
from zhaquirks.clusters import CustomCluster


class Manufacturer3r60gRadarSpecialClusterCluster(CustomCluster):
    """3r60gRadarSpecialCluster (z2m custom cluster)."""

    cluster_id = 0x042E

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        total_volatile_organic_compounds = ZCLAttributeDef(id=0x0000, type=t.uint32_t, access="r", manufacturer_code=0x1407)
        presence_sensor_detect_distance_level = ZCLAttributeDef(id=0xF002, type=t.uint8_t, manufacturer_code=0x1407)
        tvoc_sensor_calibration = ZCLAttributeDef(id=0xF001, type=t.uint8_t, manufacturer_code=0x1407)
        tvoc_alert_threshold = ZCLAttributeDef(id=0xF003, type=t.uint16_t, manufacturer_code=0x1407)
        motion_detect_sensitivity_level = ZCLAttributeDef(id=0xF004, type=t.uint8_t, manufacturer_code=0x1407)
        presence_detect_sensitivity_level = ZCLAttributeDef(id=0xF005, type=t.uint8_t, manufacturer_code=0x1407)
        presence_hold_time_level = ZCLAttributeDef(id=0xF006, type=t.uint8_t, manufacturer_code=0x1407)
        tvoc_alert_enable = ZCLAttributeDef(id=0xF007, type=t.uint8_t, manufacturer_code=0x1407)



_LOGGER = logging.getLogger(__name__)
_SHIPPED = pathlib.Path(zhaquirks.__file__).resolve().parent
_STEPPED_BACK: set = set()

# The Zigbee fingerprints (manufacturer, model) this quirk is for; None matches any manufacturer.
FINGERPRINTS = [(None, '3RPL01084Z'), ('Third Reality, Inc', '3RPL01084Z')]
# Names that a model-only fingerprint would catch but Zigbee2MQTT gives to other devices.
CLAIMED_ELSEWHERE = set()
# The endpoints this quirk needs, each with the input clusters it puts there where Zigbee2MQTT names none.
ENDPOINTS = {1: (0x042E,)}


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

    Except for the exact names in FINGERPRINTS: ZHA's own quirk for them shows fewer features
    than this file (compared when the file was built), so this quirk stays for them.
    """
    if (device.manufacturer, device.model) in CLAIMED_ELSEWHERE:
        return False
    shipped = None if device.manufacturer is not None and (device.manufacturer, device.model) in FINGERPRINTS else _shipped_quirk(device)
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
    QuirkBuilder(None, '3RPL01084Z')
    .applies_to('Third Reality, Inc', '3RPL01084Z')
    .replaces(Manufacturer3r60gRadarSpecialClusterCluster)
    .sensor(attribute_name=Manufacturer3r60gRadarSpecialClusterCluster.AttributeDefs.total_volatile_organic_compounds.name, cluster_id=Manufacturer3r60gRadarSpecialClusterCluster.cluster_id, state_class=SensorStateClass.MEASUREMENT, unit=CONCENTRATION_PARTS_PER_BILLION, entity_type=EntityType.STANDARD, translation_key='total_volatile_organic_compounds', fallback_name='Total volatile organic compounds', unique_id_suffix='volatile_organic_compounds')
    .write_attr_button(attribute_name=Manufacturer3r60gRadarSpecialClusterCluster.AttributeDefs.tvoc_sensor_calibration.name, cluster_id=Manufacturer3r60gRadarSpecialClusterCluster.cluster_id, attribute_value=1, entity_type=EntityType.STANDARD, translation_key='calibrate_tvoc_sensor', fallback_name='Calibrate TVOC sensor', unique_id_suffix='tvoc_sensor_calibration')
    .number(attribute_name=Manufacturer3r60gRadarSpecialClusterCluster.AttributeDefs.presence_sensor_detect_distance_level.name, cluster_id=Manufacturer3r60gRadarSpecialClusterCluster.cluster_id, min_value=1, max_value=6, entity_type=EntityType.STANDARD, translation_key='presence_sensor_sensitivity', fallback_name='Presence sensor sensitivity', unique_id_suffix='sensor_sensitivity')
    .number(attribute_name=Manufacturer3r60gRadarSpecialClusterCluster.AttributeDefs.tvoc_alert_threshold.name, cluster_id=Manufacturer3r60gRadarSpecialClusterCluster.cluster_id, min_value=3000, max_value=50000, unit=CONCENTRATION_PARTS_PER_BILLION, entity_type=EntityType.STANDARD, translation_key='air_threshold', fallback_name='Air threshold', unique_id_suffix='air_threshold')
    .switch(attribute_name=Manufacturer3r60gRadarSpecialClusterCluster.AttributeDefs.tvoc_alert_enable.name, cluster_id=Manufacturer3r60gRadarSpecialClusterCluster.cluster_id, entity_type=EntityType.STANDARD, translation_key='tvoc_alert_enable', fallback_name='TVOC alert enable')
    .number(attribute_name=Manufacturer3r60gRadarSpecialClusterCluster.AttributeDefs.motion_detect_sensitivity_level.name, cluster_id=Manufacturer3r60gRadarSpecialClusterCluster.cluster_id, min_value=0, max_value=20, unit='level', entity_type=EntityType.STANDARD, translation_key='motion_detect_sensitivity_level', fallback_name='Motion detect sensitivity level')
    .number(attribute_name=Manufacturer3r60gRadarSpecialClusterCluster.AttributeDefs.presence_detect_sensitivity_level.name, cluster_id=Manufacturer3r60gRadarSpecialClusterCluster.cluster_id, min_value=0, max_value=20, unit='level', entity_type=EntityType.STANDARD, translation_key='presence_detect_sensitivity_level', fallback_name='Presence detect sensitivity level')
    .number(attribute_name=Manufacturer3r60gRadarSpecialClusterCluster.AttributeDefs.presence_hold_time_level.name, cluster_id=Manufacturer3r60gRadarSpecialClusterCluster.cluster_id, min_value=1, max_value=4, unit='level', entity_type=EntityType.STANDARD, translation_key='presence_hold_time_level', fallback_name='Presence hold time level')
    # occupancy: standard clusters, ZHA's own entities
    # illuminance: standard clusters, ZHA's own entities
    # light: standard clusters, ZHA's own entities
    # effect: standard clusters, ZHA's own entities
    # power_on_behavior: standard clusters, ZHA's own entities
    .filter(no_builtin_quirk)
    .add_to_registry()
)
