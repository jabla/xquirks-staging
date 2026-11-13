"""DIYRuZ DIYRuZ_AirSense: Air quality sensor.

Generated from the Zigbee2MQTT definition.
Data: zigbee-herdsman-converters, MIT, Copyright (c) 2018 Koen Kanters.
Status: generated, not verified on hardware.
Revision: 4ff9377b
"""

import functools
import logging
import pathlib

import zhaquirks
from zha.quirks import DEVICE_REGISTRY, DeviceMatch
import zigpy.types as t
from zigpy.zcl.foundation import ZCLAttributeDef
from zigpy.zcl.clusters.measurement import CarbonDioxideConcentration
from zigpy.zcl.clusters.measurement import PressureMeasurement
from zigpy.zcl.clusters.measurement import RelativeHumidity
from zigpy.zcl.clusters.measurement import TemperatureMeasurement

from zhaquirks.builder import (
    CONCENTRATION_PARTS_PER_MILLION,
    EntityType,
    NumberDeviceClass,
    PERCENTAGE,
    QuirkBuilder,
    UnitOfPressure,
    UnitOfTemperature,
)
from zhaquirks.clusters import CustomCluster


class MsTemperatureMeasurementCluster(CustomCluster, TemperatureMeasurement):
    """TemperatureMeasurement with the attributes z2m adds."""

    class AttributeDefs(TemperatureMeasurement.AttributeDefs):
        """Attribute definitions."""

        temperature_offset = ZCLAttributeDef(id=0x0210, type=t.int16s, manufacturer_code=None)


class MsPressureMeasurementCluster(CustomCluster, PressureMeasurement):
    """PressureMeasurement with the attributes z2m adds."""

    class AttributeDefs(PressureMeasurement.AttributeDefs):
        """Attribute definitions."""

        pressure_offset = ZCLAttributeDef(id=0x0210, type=t.int32s, manufacturer_code=None)


class MsRelativeHumidityCluster(CustomCluster, RelativeHumidity):
    """RelativeHumidity with the attributes z2m adds."""

    class AttributeDefs(RelativeHumidity.AttributeDefs):
        """Attribute definitions."""

        humidity_offset = ZCLAttributeDef(id=0x0210, type=t.int16s, manufacturer_code=None)


class MsCO2Cluster(CustomCluster, CarbonDioxideConcentration):
    """CarbonDioxideConcentration with the attributes z2m adds."""

    class AttributeDefs(CarbonDioxideConcentration.AttributeDefs):
        """Attribute definitions."""

        enable_abc = ZCLAttributeDef(id=0x0202, type=t.Bool, manufacturer_code=None)
        led_feedback = ZCLAttributeDef(id=0x0203, type=t.Bool, manufacturer_code=None)
        threshold1 = ZCLAttributeDef(id=0x0204, type=t.uint16_t, manufacturer_code=None)
        threshold2 = ZCLAttributeDef(id=0x0205, type=t.uint16_t, manufacturer_code=None)



_LOGGER = logging.getLogger(__name__)
_SHIPPED = pathlib.Path(zhaquirks.__file__).resolve().parent
_STEPPED_BACK: set = set()

# The Zigbee fingerprints (manufacturer, model) this quirk is for; None matches any manufacturer.
FINGERPRINTS = [(None, 'DIYRuZ_AirSense')]
# Names that a model-only fingerprint would catch but Zigbee2MQTT gives to other devices.
CLAIMED_ELSEWHERE = set()
# The endpoints this quirk needs, each with the input clusters it puts there where Zigbee2MQTT names none.
ENDPOINTS = {1: (0x0402, 0x0403, 0x0405, 0x040D)}


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
    QuirkBuilder(None, 'DIYRuZ_AirSense')
    .replaces(MsCO2Cluster)
    .replaces(MsRelativeHumidityCluster)
    .replaces(MsPressureMeasurementCluster)
    .replaces(MsTemperatureMeasurementCluster)
    .switch(attribute_name=MsCO2Cluster.AttributeDefs.led_feedback.name, cluster_id=MsCO2Cluster.cluster_id, entity_type=EntityType.STANDARD, translation_key='led_feedback', fallback_name='LED feedback')
    .switch(attribute_name=MsCO2Cluster.AttributeDefs.enable_abc.name, cluster_id=MsCO2Cluster.cluster_id, entity_type=EntityType.STANDARD, translation_key='enable_abc', fallback_name='Enable abc')
    .number(attribute_name=MsCO2Cluster.AttributeDefs.threshold1.name, cluster_id=MsCO2Cluster.cluster_id, min_value=0, max_value=50000, unit=CONCENTRATION_PARTS_PER_MILLION, entity_type=EntityType.STANDARD, translation_key='threshold1', fallback_name='Threshold1')
    .number(attribute_name=MsCO2Cluster.AttributeDefs.threshold2.name, cluster_id=MsCO2Cluster.cluster_id, min_value=0, max_value=50000, unit=CONCENTRATION_PARTS_PER_MILLION, entity_type=EntityType.STANDARD, translation_key='threshold2', fallback_name='Threshold2')
    .number(attribute_name=MsTemperatureMeasurementCluster.AttributeDefs.temperature_offset.name, cluster_id=MsTemperatureMeasurementCluster.cluster_id, min_value=-20, max_value=20, unit=UnitOfTemperature.CELSIUS, device_class=NumberDeviceClass.TEMPERATURE_DELTA, entity_type=EntityType.STANDARD, translation_key='temperature_offset', fallback_name='Temperature offset')
    .number(attribute_name=MsRelativeHumidityCluster.AttributeDefs.humidity_offset.name, cluster_id=MsRelativeHumidityCluster.cluster_id, min_value=-50, max_value=50, unit=PERCENTAGE, entity_type=EntityType.STANDARD, translation_key='humidity_offset', fallback_name='Humidity offset')
    .number(attribute_name=MsPressureMeasurementCluster.AttributeDefs.pressure_offset.name, cluster_id=MsPressureMeasurementCluster.cluster_id, min_value=-1000, max_value=1000, unit=UnitOfPressure.HPA, device_class=NumberDeviceClass.PRESSURE, entity_type=EntityType.STANDARD, translation_key='pressure_offset', fallback_name='Pressure offset')
    # co2: standard clusters, ZHA's own entities
    # temperature: standard clusters, ZHA's own entities
    # humidity: standard clusters, ZHA's own entities
    # pressure: standard clusters or z2m's own code, not generated
    .filter(no_builtin_quirk)
    .add_to_registry()
)
