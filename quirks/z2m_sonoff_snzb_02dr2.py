"""SONOFF SNZB-02DR2: Temperature and humidity sensor with display and relay control.

Generated from the Zigbee2MQTT definition.
Entity names follow ZHA's own quirk for this device where it shows the same feature.
Entity names follow zha-device-handlers#5271 (open pull request for this device).
Data: zigbee-herdsman-converters, MIT, Copyright (c) 2018 Koen Kanters.
Status: generated, not verified on hardware.
Revision: 2fc19be5
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


class CustomSonoffSnzb02dr2Cluster(CustomCluster):
    """customSonoffSnzb02dr2 (z2m custom cluster)."""

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
        temperature_sensor_select = ZCLAttributeDef(id=0x600E, type=t.uint8_t, manufacturer_code=None)
        external_temperature = ZCLAttributeDef(id=0x600D, type=t.int16s, manufacturer_code=None)
        external_humidity = ZCLAttributeDef(id=0x6018, type=t.uint16_t, manufacturer_code=None)
        # remote_source_items 0x601E: ARRAY, attribute only


class TemperatureUnits(t.enum8):
    """temperature_units values (ZHA's quirk)."""

    Celsius = 0x00
    Fahrenheit = 0x01



_LOGGER = logging.getLogger(__name__)
_SHIPPED = pathlib.Path(zhaquirks.__file__).resolve().parent
_STEPPED_BACK: set = set()

# The Zigbee fingerprints (manufacturer, model) this quirk is for; None matches any manufacturer.
FINGERPRINTS = [(None, 'SNZB-02DR2'), ('SONOFF', 'SNZB-02DR2')]
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
    QuirkBuilder(None, 'SNZB-02DR2')
    .applies_to('SONOFF', 'SNZB-02DR2')
    .replaces(CustomSonoffSnzb02dr2Cluster)
    .sensor(attribute_name=CustomSonoffSnzb02dr2Cluster.AttributeDefs.external_temperature.name, cluster_id=CustomSonoffSnzb02dr2Cluster.cluster_id, divisor=100, entity_type=EntityType.STANDARD, translation_key='external_temperature', fallback_name='External temperature')
    .sensor(attribute_name=CustomSonoffSnzb02dr2Cluster.AttributeDefs.external_humidity.name, cluster_id=CustomSonoffSnzb02dr2Cluster.cluster_id, divisor=100, entity_type=EntityType.STANDARD, translation_key='external_humidity', fallback_name='External humidity')
    .number(attribute_name=CustomSonoffSnzb02dr2Cluster.AttributeDefs.comfort_temperature_min.name, cluster_id=CustomSonoffSnzb02dr2Cluster.cluster_id, min_value=-10, max_value=60, step=0.1, unit=UnitOfTemperature.CELSIUS, multiplier=0.01, device_class=NumberDeviceClass.TEMPERATURE, entity_type=EntityType.CONFIG, translation_key='comfort_temperature_min', fallback_name='Comfort temperature min', unique_id_suffix='comfort_temperature_min')
    .number(attribute_name=CustomSonoffSnzb02dr2Cluster.AttributeDefs.comfort_temperature_max.name, cluster_id=CustomSonoffSnzb02dr2Cluster.cluster_id, min_value=-10, max_value=60, step=0.1, unit=UnitOfTemperature.CELSIUS, multiplier=0.01, device_class=NumberDeviceClass.TEMPERATURE, entity_type=EntityType.CONFIG, translation_key='comfort_temperature_max', fallback_name='Comfort temperature max', unique_id_suffix='comfort_temperature_max')
    .number(attribute_name=CustomSonoffSnzb02dr2Cluster.AttributeDefs.comfort_humidity_min.name, cluster_id=CustomSonoffSnzb02dr2Cluster.cluster_id, min_value=5, max_value=95, step=0.1, unit=PERCENTAGE, multiplier=0.01, entity_type=EntityType.CONFIG, translation_key='comfort_humidity_min', fallback_name='Comfort humidity min', unique_id_suffix='comfort_humidity_min')
    .number(attribute_name=CustomSonoffSnzb02dr2Cluster.AttributeDefs.comfort_humidity_max.name, cluster_id=CustomSonoffSnzb02dr2Cluster.cluster_id, min_value=5, max_value=95, step=0.1, unit=PERCENTAGE, multiplier=0.01, entity_type=EntityType.CONFIG, translation_key='comfort_humidity_max', fallback_name='Comfort humidity max', unique_id_suffix='comfort_humidity_max')
    .enum(attribute_name=CustomSonoffSnzb02dr2Cluster.AttributeDefs.temperature_unit.name, cluster_id=CustomSonoffSnzb02dr2Cluster.cluster_id, enum_class=TemperatureUnits, entity_type=EntityType.CONFIG, translation_key='display_unit', fallback_name='Display unit', unique_id_suffix='temperature_unit')
    .number(attribute_name=CustomSonoffSnzb02dr2Cluster.AttributeDefs.temperature_offset.name, cluster_id=CustomSonoffSnzb02dr2Cluster.cluster_id, min_value=-50, max_value=50, step=0.1, unit=UnitOfTemperature.CELSIUS, multiplier=0.01, device_class=NumberDeviceClass.TEMPERATURE_DELTA, entity_type=EntityType.CONFIG, translation_key='temperature_offset', fallback_name='Temperature offset', unique_id_suffix='temperature_offset')
    .number(attribute_name=CustomSonoffSnzb02dr2Cluster.AttributeDefs.humidity_offset.name, cluster_id=CustomSonoffSnzb02dr2Cluster.cluster_id, min_value=-50, max_value=50, step=0.1, unit=PERCENTAGE, multiplier=0.01, entity_type=EntityType.CONFIG, translation_key='humidity_offset', fallback_name='Humidity offset', unique_id_suffix='humidity_offset')
    # temperature_sensor_select: z2m enumLookup with own fromZigbee converter, not generated
    # battery: standard clusters, ZHA's own entities
    # voltage: standard clusters, ZHA's own entities
    # temperature: standard clusters, ZHA's own entities
    # humidity: standard clusters, ZHA's own entities
    .filter(no_builtin_quirk)
    .add_to_registry()
)
