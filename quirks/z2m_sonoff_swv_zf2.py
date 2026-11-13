"""SONOFF SWV-ZF2: Zigbee dual-channel smart water valve.

Generated from the Zigbee2MQTT definition.
Data: zigbee-herdsman-converters, MIT, Copyright (c) 2018 Koen Kanters.
Status: generated, not verified on hardware.
Revision: 78a4d1f2
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
    SensorDeviceClass,
    SensorStateClass,
    UnitOfTime,
    UnitOfVolume,
)
from zhaquirks.clusters import CustomCluster


class CustomClusterEwelinkCluster(CustomCluster):
    """customClusterEwelink (z2m custom cluster)."""

    cluster_id = 0xFC11

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        child_lock = ZCLAttributeDef(id=0x0000, type=t.Bool, manufacturer_code=None)
        real_time_irrigation_duration = ZCLAttributeDef(id=0x5006, type=t.uint32_t, access="r", manufacturer_code=None)
        real_time_irrigation_volume = ZCLAttributeDef(id=0x5007, type=t.uint32_t, access="r", manufacturer_code=None)
        valve_abnormal_state = ZCLAttributeDef(id=0x500C, type=t.uint8_t, access="r", manufacturer_code=None)
        rain_delay_end_datetime = ZCLAttributeDef(id=0x5014, type=t.uint32_t, access="r", manufacturer_code=None)
        hour_irrigation_volume = ZCLAttributeDef(id=0x501B, type=t.uint32_t, access="r", manufacturer_code=None)
        hour_irrigation_duration = ZCLAttributeDef(id=0x501C, type=t.uint32_t, access="r", manufacturer_code=None)
        # manual_default_settings 0x501D: ARRAY, attribute only
        # seasonal_watering_adjustment 0x501E: ARRAY, attribute only
        # irrigation_schedule_status 0x501F: ARRAY, attribute only
        # valve_alarm_settings 0x5020: ARRAY, attribute only
        unit_of_water_flow = ZCLAttributeDef(id=0x5021, type=t.uint8_t, manufacturer_code=None)



_LOGGER = logging.getLogger(__name__)
_SHIPPED = pathlib.Path(zhaquirks.__file__).resolve().parent
_STEPPED_BACK: set = set()

# The Zigbee fingerprints (manufacturer, model) this quirk is for; None matches any manufacturer.
FINGERPRINTS = [(None, 'SWV-ZF2')]
# Names that a model-only fingerprint would catch but Zigbee2MQTT gives to other devices.
CLAIMED_ELSEWHERE = set()
# The endpoints this quirk needs, each with the input clusters it puts there where Zigbee2MQTT names none.
ENDPOINTS = {1: (0xFC11,), 2: ()}


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
    QuirkBuilder(None, 'SWV-ZF2')
    .replaces(CustomClusterEwelinkCluster)
    .replaces(CustomClusterEwelinkCluster, endpoint_id=2)
    .switch(attribute_name=CustomClusterEwelinkCluster.AttributeDefs.child_lock.name, cluster_id=CustomClusterEwelinkCluster.cluster_id, entity_type=EntityType.CONFIG, translation_key='child_lock', fallback_name='Child lock')
    .sensor(attribute_name=CustomClusterEwelinkCluster.AttributeDefs.real_time_irrigation_duration.name, cluster_id=CustomClusterEwelinkCluster.cluster_id, state_class=SensorStateClass.MEASUREMENT, device_class=SensorDeviceClass.DURATION, unit=UnitOfTime.MINUTES, entity_type=EntityType.STANDARD, translation_key='real_time_irrigation_duration_1', fallback_name='Real time irrigation duration 1')
    .sensor(attribute_name=CustomClusterEwelinkCluster.AttributeDefs.real_time_irrigation_duration.name, cluster_id=CustomClusterEwelinkCluster.cluster_id, endpoint_id=2, state_class=SensorStateClass.MEASUREMENT, device_class=SensorDeviceClass.DURATION, unit=UnitOfTime.MINUTES, entity_type=EntityType.STANDARD, translation_key='real_time_irrigation_duration_2', fallback_name='Real time irrigation duration 2')
    .sensor(attribute_name=CustomClusterEwelinkCluster.AttributeDefs.real_time_irrigation_volume.name, cluster_id=CustomClusterEwelinkCluster.cluster_id, state_class=SensorStateClass.MEASUREMENT, unit=UnitOfVolume.LITERS, entity_type=EntityType.STANDARD, translation_key='real_time_irrigation_volume', fallback_name='Real time irrigation volume')
    .sensor(attribute_name=CustomClusterEwelinkCluster.AttributeDefs.hour_irrigation_duration.name, cluster_id=CustomClusterEwelinkCluster.cluster_id, state_class=SensorStateClass.MEASUREMENT, device_class=SensorDeviceClass.DURATION, unit=UnitOfTime.MINUTES, entity_type=EntityType.STANDARD, translation_key='hour_irrigation_duration_1', fallback_name='Hour irrigation duration 1')
    .sensor(attribute_name=CustomClusterEwelinkCluster.AttributeDefs.hour_irrigation_duration.name, cluster_id=CustomClusterEwelinkCluster.cluster_id, endpoint_id=2, state_class=SensorStateClass.MEASUREMENT, device_class=SensorDeviceClass.DURATION, unit=UnitOfTime.MINUTES, entity_type=EntityType.STANDARD, translation_key='hour_irrigation_duration_2', fallback_name='Hour irrigation duration 2')
    .sensor(attribute_name=CustomClusterEwelinkCluster.AttributeDefs.hour_irrigation_volume.name, cluster_id=CustomClusterEwelinkCluster.cluster_id, state_class=SensorStateClass.MEASUREMENT, unit=UnitOfVolume.LITERS, entity_type=EntityType.STANDARD, translation_key='z2m_hour_irrigation_volume', fallback_name='Hour irrigation volume')
    # flow: z2m numeric with own fromZigbee converter, not generated
    # battery: standard clusters, ZHA's own entities
    # switch: standard clusters, ZHA's own entities
    # switch: standard clusters, ZHA's own entities
    # valve_abnormal_state: z2m's own code, not generated
    # irrigation_plan_remove_1: z2m's own code, not generated
    # irrigation_plan_remove_2: z2m's own code, not generated
    # irrigation_plan_removed_report_1: z2m's own code, not generated
    # irrigation_plan_removed_report_2: z2m's own code, not generated
    # rain_delay: z2m's own code, not generated
    # rain_delay_end_datetime: z2m's own code, not generated
    # seasonal_watering_adjustment: z2m's own code, not generated
    # valve_alarm_settings: z2m's own code, not generated
    # 24_hours_records: z2m's own code, not generated
    # 30_days_records: z2m's own code, not generated
    # 180_days_records: z2m's own code, not generated
    # read_swvzf_records: z2m's own code, not generated
    .filter(no_builtin_quirk)
    .add_to_registry()
)
