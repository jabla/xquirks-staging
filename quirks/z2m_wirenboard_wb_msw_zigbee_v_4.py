"""Wirenboard WB-MSW-ZIGBEE v.4: Wall-mounted multi sensor.

Generated from the Zigbee2MQTT definition.
Data: zigbee-herdsman-converters, MIT, Copyright (c) 2018 Koen Kanters.
Status: generated, not verified on hardware.
Revision: 8c8f1d51
"""

import functools
import logging
import pathlib

import zhaquirks
from zha.quirks import DEVICE_REGISTRY, DeviceMatch
import zigpy.types as t
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef
from zigpy.zcl.clusters.measurement import OccupancySensing
from zigpy.zcl.clusters.measurement import RelativeHumidity
from zigpy.zcl.clusters.measurement import TemperatureMeasurement

from zhaquirks.builder import (
    CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
    EntityType,
    NumberDeviceClass,
    QuirkBuilder,
    SensorDeviceClass,
    SensorStateClass,
    UnitOfSoundPressure,
    UnitOfTemperature,
    UnitOfTime,
)
from zhaquirks.clusters import CustomCluster


class MsTemperatureMeasurementCluster(CustomCluster, TemperatureMeasurement):
    """TemperatureMeasurement with the attributes z2m adds."""

    class AttributeDefs(TemperatureMeasurement.AttributeDefs):
        """Attribute definitions."""

        sprut_temperature_offset = ZCLAttributeDef(id=0x6600, type=t.int16s, manufacturer_code=0x6666)


class MsRelativeHumidityCluster(CustomCluster, RelativeHumidity):
    """RelativeHumidity with the attributes z2m adds."""

    class AttributeDefs(RelativeHumidity.AttributeDefs):
        """Attribute definitions."""

        sprut_heater = ZCLAttributeDef(id=0x6600, type=t.Bool, manufacturer_code=0x6666)


class MsOccupancySensingCluster(CustomCluster, OccupancySensing):
    """OccupancySensing with the attributes z2m adds."""

    class AttributeDefs(OccupancySensing.AttributeDefs):
        """Attribute definitions."""

        sprut_occupancy_level = ZCLAttributeDef(id=0x6600, type=t.uint16_t, manufacturer_code=0x6666)
        sprut_occupancy_sensitivity = ZCLAttributeDef(id=0x6601, type=t.uint16_t, manufacturer_code=0x6666)


class SprutDeviceCluster(CustomCluster):
    """sprutDevice (z2m custom cluster)."""

    cluster_id = 0x6600

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        is_connected = ZCLAttributeDef(id=0x6604, type=t.Bool, manufacturer_code=0x6666)
        uart_baud_rate = ZCLAttributeDef(id=0x6601, type=t.uint32_t, manufacturer_code=0x6666)


class SprutVocCluster(CustomCluster):
    """sprutVoc (z2m custom cluster)."""

    cluster_id = 0x6601

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        voc = ZCLAttributeDef(id=0x6600, type=t.uint16_t, manufacturer_code=0x6666)


class SprutNoiseCluster(CustomCluster):
    """sprutNoise (z2m custom cluster)."""

    cluster_id = 0x6602

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        noise = ZCLAttributeDef(id=0x6600, type=t.Single, manufacturer_code=0x6666)
        noise_detected = ZCLAttributeDef(id=0x6601, type=t.bitmap8, manufacturer_code=0x6666)
        noise_detect_level = ZCLAttributeDef(id=0x6602, type=t.Single, manufacturer_code=0x6666)
        noise_after_detect_delay = ZCLAttributeDef(id=0x6603, type=t.uint16_t, manufacturer_code=0x6666)



_LOGGER = logging.getLogger(__name__)
_SHIPPED = pathlib.Path(zhaquirks.__file__).resolve().parent
_STEPPED_BACK: set = set()

# The Zigbee fingerprints (manufacturer, model) this quirk is for; None matches any manufacturer.
FINGERPRINTS = [(None, 'WBMSW4')]
# Names that a model-only fingerprint would catch but Zigbee2MQTT gives to other devices.
CLAIMED_ELSEWHERE = set()
# The endpoints this quirk needs, each with the input clusters it puts there where Zigbee2MQTT names none.
ENDPOINTS = {1: (0x0402, 0x0405, 0x0406, 0x6600, 0x6601, 0x6602)}


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
    QuirkBuilder(None, 'WBMSW4')
    .replaces(SprutNoiseCluster)
    .replaces(SprutVocCluster)
    .replaces(SprutDeviceCluster)
    .replaces(MsOccupancySensingCluster)
    .replaces(MsRelativeHumidityCluster)
    .replaces(MsTemperatureMeasurementCluster)
    .binary_sensor(attribute_name=SprutDeviceCluster.AttributeDefs.is_connected.name, cluster_id=SprutDeviceCluster.cluster_id, entity_type=EntityType.DIAGNOSTIC, translation_key='uart_connection', fallback_name='Uart connection')
    .number(attribute_name=MsTemperatureMeasurementCluster.AttributeDefs.sprut_temperature_offset.name, cluster_id=MsTemperatureMeasurementCluster.cluster_id, min_value=-10, max_value=10, unit=UnitOfTemperature.CELSIUS, multiplier=0.01, device_class=NumberDeviceClass.TEMPERATURE_DELTA, entity_type=EntityType.CONFIG, translation_key='temperature_offset', fallback_name='Temperature offset')
    .switch(attribute_name=MsRelativeHumidityCluster.AttributeDefs.sprut_heater.name, cluster_id=MsRelativeHumidityCluster.cluster_id, entity_type=EntityType.CONFIG, translation_key='th_heater', fallback_name='Th heater')
    .number(attribute_name=MsOccupancySensingCluster.AttributeDefs.sprut_occupancy_sensitivity.name, cluster_id=MsOccupancySensingCluster.cluster_id, min_value=0, max_value=2000, entity_type=EntityType.CONFIG, translation_key='occupancy_sensitivity', fallback_name='Occupancy sensitivity')
    .sensor(attribute_name=MsOccupancySensingCluster.AttributeDefs.sprut_occupancy_level.name, cluster_id=MsOccupancySensingCluster.cluster_id, entity_type=EntityType.DIAGNOSTIC, translation_key='occupancy_level', fallback_name='Occupancy level')
    .sensor(attribute_name=SprutNoiseCluster.AttributeDefs.noise.name, cluster_id=SprutNoiseCluster.cluster_id, state_class=SensorStateClass.MEASUREMENT, device_class=SensorDeviceClass.SOUND_PRESSURE, unit=UnitOfSoundPressure.WEIGHTED_DECIBEL_A, entity_type=EntityType.DIAGNOSTIC, translation_key='noise', fallback_name='Noise')
    .number(attribute_name=SprutNoiseCluster.AttributeDefs.noise_detect_level.name, cluster_id=SprutNoiseCluster.cluster_id, min_value=0, max_value=150, unit=UnitOfSoundPressure.WEIGHTED_DECIBEL_A, device_class=NumberDeviceClass.SOUND_PRESSURE, entity_type=EntityType.CONFIG, translation_key='noise_detect_level', fallback_name='Noise detect level')
    .binary_sensor(attribute_name=SprutNoiseCluster.AttributeDefs.noise_detected.name, cluster_id=SprutNoiseCluster.cluster_id, entity_type=EntityType.STANDARD, translation_key='noise_detected', fallback_name='Noise detected')
    .number(attribute_name=SprutNoiseCluster.AttributeDefs.noise_after_detect_delay.name, cluster_id=SprutNoiseCluster.cluster_id, min_value=0, max_value=2000, unit=UnitOfTime.SECONDS, device_class=NumberDeviceClass.DURATION, entity_type=EntityType.CONFIG, translation_key='noise_timeout', fallback_name='Noise timeout')
    .sensor(attribute_name=SprutVocCluster.AttributeDefs.voc.name, cluster_id=SprutVocCluster.cluster_id, state_class=SensorStateClass.MEASUREMENT, unit=CONCENTRATION_MICROGRAMS_PER_CUBIC_METER, entity_type=EntityType.STANDARD, translation_key='z2m_voc', fallback_name='VOC')
    # activity_led: standard clusters, ZHA's own entities
    # temperature: standard clusters, ZHA's own entities
    # humidity: standard clusters, ZHA's own entities
    # co2: standard clusters, ZHA's own entities
    # occupancy_timeout: standard clusters, ZHA's own entities
    # uart_baud_rate: enum values outside 0..65535, not generated
    # switch: standard clusters, ZHA's own entities
    # switch: standard clusters, ZHA's own entities
    # switch: standard clusters, ZHA's own entities
    # illuminance: standard clusters, ZHA's own entities
    # occupancy: standard clusters, ZHA's own entities
    .filter(no_builtin_quirk)
    .add_to_registry()
)
