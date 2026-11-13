"""SONOFF SNZB-02M: Temperature and humidity sensor.

Generated from the Zigbee2MQTT definition.
Entity names follow zha-device-handlers#4263 (open pull request for this device).
Data: zigbee-herdsman-converters, MIT, Copyright (c) 2018 Koen Kanters.
Status: generated, not verified on hardware.
Revision: 332797fc
"""

import functools
import logging
import pathlib

import zhaquirks
from zha.quirks import DEVICE_REGISTRY, DeviceMatch
import zigpy.types as t
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef
from zigpy.zcl.clusters.measurement import PressureMeasurement

from zhaquirks.builder import (
    EntityType,
    NumberDeviceClass,
    PERCENTAGE,
    QuirkBuilder,
    SensorDeviceClass,
    SensorStateClass,
    UnitOfPressure,
    UnitOfTemperature,
)
from zhaquirks.clusters import CustomCluster


class MsPressureMeasurementCluster(CustomCluster, PressureMeasurement):
    """PressureMeasurement with the attributes z2m adds."""

    class AttributeDefs(PressureMeasurement.AttributeDefs):
        """Attribute definitions."""

        pressure = ZCLAttributeDef(id=0x0004, type=t.int32s, access="r", manufacturer_code=None)


class CustomClusterEwelinkCluster(CustomCluster):
    """customClusterEwelink (z2m custom cluster)."""

    cluster_id = 0xFC11

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        temperature_compensation = ZCLAttributeDef(id=0x2003, type=t.int16s, manufacturer_code=None)
        relative_humidity_compensation = ZCLAttributeDef(id=0x2004, type=t.int16s, manufacturer_code=None)
        pressure_compensation = ZCLAttributeDef(id=0x2007, type=t.int16s, manufacturer_code=None)



_LOGGER = logging.getLogger(__name__)
_SHIPPED = pathlib.Path(zhaquirks.__file__).resolve().parent
_STEPPED_BACK: set = set()

# The Zigbee fingerprints (manufacturer, model) this quirk is for; None matches any manufacturer.
FINGERPRINTS = [(None, 'SNZB-02M')]
# Names that a model-only fingerprint would catch but Zigbee2MQTT gives to other devices.
CLAIMED_ELSEWHERE = set()
# The endpoints this quirk needs, each with the input clusters it puts there where Zigbee2MQTT names none.
ENDPOINTS = {1: (0x0403, 0xFC11)}


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
    QuirkBuilder(None, 'SNZB-02M')
    .replaces(CustomClusterEwelinkCluster)
    .replaces(MsPressureMeasurementCluster)
    .sensor(attribute_name=MsPressureMeasurementCluster.AttributeDefs.pressure.name, cluster_id=MsPressureMeasurementCluster.cluster_id, divisor=100, state_class=SensorStateClass.MEASUREMENT, device_class=SensorDeviceClass.PRESSURE, unit=UnitOfPressure.HPA, entity_type=EntityType.STANDARD, fallback_name='Pressure')
    .number(attribute_name=CustomClusterEwelinkCluster.AttributeDefs.temperature_compensation.name, cluster_id=CustomClusterEwelinkCluster.cluster_id, min_value=-50, max_value=50, step=0.1, unit=UnitOfTemperature.CELSIUS, multiplier=0.01, device_class=NumberDeviceClass.TEMPERATURE_DELTA, entity_type=EntityType.CONFIG, translation_key='temperature_compensation', fallback_name='Temperature compensation')
    .number(attribute_name=CustomClusterEwelinkCluster.AttributeDefs.relative_humidity_compensation.name, cluster_id=CustomClusterEwelinkCluster.cluster_id, min_value=-50, max_value=50, step=0.1, unit=PERCENTAGE, multiplier=0.01, entity_type=EntityType.CONFIG, translation_key='relative_humidity_compensation', fallback_name='Relative humidity compensation')
    .number(attribute_name=CustomClusterEwelinkCluster.AttributeDefs.pressure_compensation.name, cluster_id=CustomClusterEwelinkCluster.cluster_id, min_value=-200, max_value=200, step=0.1, unit=UnitOfPressure.HPA, multiplier=0.01, device_class=NumberDeviceClass.PRESSURE, entity_type=EntityType.CONFIG, translation_key='pressure_compensation', fallback_name='Pressure compensation')
    # battery: standard clusters, ZHA's own entities
    # temperature: standard clusters, ZHA's own entities
    # humidity: standard clusters, ZHA's own entities
    # dew_point: standard clusters, ZHA's own entities
    # vpd: standard clusters, ZHA's own entities
    .filter(no_builtin_quirk)
    .add_to_registry()
)
