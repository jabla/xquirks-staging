"""SONOFF SNZB-02UL: E-ink screen temperature and humidity sensor.

Generated from the Zigbee2MQTT definition.
Entity names follow zha-device-handlers#5340 (open pull request for this device).
Data: zigbee-herdsman-converters, MIT, Copyright (c) 2018 Koen Kanters.
Status: generated, not verified on hardware.
Revision: 191e5179
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
    NumberDeviceClass,
    PERCENTAGE,
    QuirkBuilder,
    UnitOfTemperature,
)
from zhaquirks.clusters import CustomCluster


class CustomClusterEwelinkCluster(CustomCluster):
    """customClusterEwelink (z2m custom cluster)."""

    cluster_id = 0xFC11

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        comfort_temperature_max = ZCLAttributeDef(id=0x0003, type=t.int16s, manufacturer_code=None)
        comfort_temperature_min = ZCLAttributeDef(id=0x0004, type=t.int16s, manufacturer_code=None)
        comfort_humidity_min = ZCLAttributeDef(id=0x0005, type=t.uint16_t, manufacturer_code=None)
        comfort_humidity_max = ZCLAttributeDef(id=0x0006, type=t.uint16_t, manufacturer_code=None)
        temperature_unit = ZCLAttributeDef(id=0x0007, type=t.uint16_t, manufacturer_code=None)
        temperature_offset = ZCLAttributeDef(id=0x2003, type=t.int16s, manufacturer_code=None)
        humidity_offset = ZCLAttributeDef(id=0x2004, type=t.int16s, manufacturer_code=None)
        # remote_sensor_data 0x601E: ARRAY, attribute only
        longitude = ZCLAttributeDef(id=0x5016, type=t.int32s, manufacturer_code=None)
        latitude = ZCLAttributeDef(id=0x5017, type=t.int32s, manufacturer_code=None)


class TemperatureUnits(t.enum8):
    """temperature_units values (z2m)."""

    Celsius = 0x00
    Fahrenheit = 0x01



_LOGGER = logging.getLogger(__name__)
_SHIPPED = pathlib.Path(zhaquirks.__file__).resolve().parent
_STEPPED_BACK: set = set()

# The Zigbee fingerprints (manufacturer, model) this quirk is for; None matches any manufacturer.
FINGERPRINTS = [(None, 'SNZB-02UL')]
# Names that a model-only fingerprint would catch but Zigbee2MQTT gives to other devices.
CLAIMED_ELSEWHERE = set()
# The endpoints this quirk needs, each with the input clusters it puts there where Zigbee2MQTT names none.
ENDPOINTS = {1: (0xFC11,)}


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
    QuirkBuilder(None, 'SNZB-02UL')
    .replaces(CustomClusterEwelinkCluster)
    .number(attribute_name=CustomClusterEwelinkCluster.AttributeDefs.comfort_temperature_min.name, cluster_id=CustomClusterEwelinkCluster.cluster_id, min_value=0, max_value=50, step=0.1, unit=UnitOfTemperature.CELSIUS, multiplier=0.01, device_class=NumberDeviceClass.TEMPERATURE, entity_type=EntityType.CONFIG, translation_key='comfort_temperature_min', fallback_name='Comfort temperature min')
    .number(attribute_name=CustomClusterEwelinkCluster.AttributeDefs.comfort_temperature_max.name, cluster_id=CustomClusterEwelinkCluster.cluster_id, min_value=0, max_value=50, step=0.1, unit=UnitOfTemperature.CELSIUS, multiplier=0.01, device_class=NumberDeviceClass.TEMPERATURE, entity_type=EntityType.CONFIG, translation_key='comfort_temperature_max', fallback_name='Comfort temperature max')
    .enum(attribute_name=CustomClusterEwelinkCluster.AttributeDefs.temperature_unit.name, cluster_id=CustomClusterEwelinkCluster.cluster_id, enum_class=TemperatureUnits, entity_type=EntityType.CONFIG, translation_key='display_unit', fallback_name='Display unit')
    .number(attribute_name=CustomClusterEwelinkCluster.AttributeDefs.comfort_humidity_min.name, cluster_id=CustomClusterEwelinkCluster.cluster_id, min_value=5, max_value=95, step=0.1, unit=PERCENTAGE, multiplier=0.01, entity_type=EntityType.CONFIG, translation_key='comfort_humidity_min', fallback_name='Comfort humidity min')
    .number(attribute_name=CustomClusterEwelinkCluster.AttributeDefs.comfort_humidity_max.name, cluster_id=CustomClusterEwelinkCluster.cluster_id, min_value=5, max_value=95, step=0.1, unit=PERCENTAGE, multiplier=0.01, entity_type=EntityType.CONFIG, translation_key='comfort_humidity_max', fallback_name='Comfort humidity max')
    .number(attribute_name=CustomClusterEwelinkCluster.AttributeDefs.temperature_offset.name, cluster_id=CustomClusterEwelinkCluster.cluster_id, min_value=-50, max_value=50, step=0.1, unit=UnitOfTemperature.CELSIUS, multiplier=0.01, device_class=NumberDeviceClass.TEMPERATURE_DELTA, entity_type=EntityType.CONFIG, translation_key='temperature_offset', fallback_name='Temperature offset')
    .number(attribute_name=CustomClusterEwelinkCluster.AttributeDefs.humidity_offset.name, cluster_id=CustomClusterEwelinkCluster.cluster_id, min_value=-50, max_value=50, step=0.1, unit=PERCENTAGE, multiplier=0.01, entity_type=EntityType.CONFIG, translation_key='humidity_offset', fallback_name='Humidity offset')
    # battery: standard clusters, ZHA's own entities
    # temperature: standard clusters, ZHA's own entities
    # humidity: standard clusters, ZHA's own entities
    # dew_point: standard clusters, ZHA's own entities
    # vpd: standard clusters, ZHA's own entities
    # remote_sensors_state: z2m's own code, not generated
    # remote_temperature: z2m's own code, not generated
    # remote_humidity: z2m's own code, not generated
    # remote_pressure: z2m's own code, not generated
    # weather: z2m's own code, not generated
    .filter(no_builtin_quirk)
    .add_to_registry()
)
