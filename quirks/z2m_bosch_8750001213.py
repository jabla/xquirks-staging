"""Bosch 8750001213: Twinguard.

Generated from the Zigbee2MQTT definition.
Data: zigbee-herdsman-converters, MIT, Copyright (c) 2018 Koen Kanters.
Status: generated, not verified on hardware.
Revision: 7ae1d931
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
    LIGHT_LUX,
    PERCENTAGE,
    QuirkBuilder,
    SensorDeviceClass,
    SensorStateClass,
    UnitOfTemperature,
)
from zhaquirks.clusters import CustomCluster


class TwinguardMeasurementsCluster(CustomCluster):
    """twinguardMeasurements (z2m custom cluster)."""

    cluster_id = 0xE002

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        humidity = ZCLAttributeDef(id=0x4000, type=t.uint16_t, manufacturer_code=0x1209)
        unknown1 = ZCLAttributeDef(id=0x4001, type=t.uint16_t, manufacturer_code=0x1209)
        unknown2 = ZCLAttributeDef(id=0x4002, type=t.uint16_t, manufacturer_code=0x1209)
        airpurity = ZCLAttributeDef(id=0x4003, type=t.uint16_t, manufacturer_code=0x1209)
        temperature = ZCLAttributeDef(id=0x4004, type=t.int16s, manufacturer_code=0x1209)
        illuminance = ZCLAttributeDef(id=0x4005, type=t.uint16_t, manufacturer_code=0x1209)
        battery = ZCLAttributeDef(id=0x4006, type=t.uint16_t, manufacturer_code=0x1209)
        unknown3 = ZCLAttributeDef(id=0x4007, type=t.uint16_t, manufacturer_code=0x1209)
        unknown4 = ZCLAttributeDef(id=0x4008, type=t.uint16_t, manufacturer_code=0x1209)
        pressure = ZCLAttributeDef(id=0x4009, type=t.uint16_t, manufacturer_code=0x1209)
        unknown6 = ZCLAttributeDef(id=0x400A, type=t.uint16_t, manufacturer_code=0x1209)
        unknown7 = ZCLAttributeDef(id=0x400B, type=t.uint16_t, manufacturer_code=0x1209)
        unknown8 = ZCLAttributeDef(id=0x400C, type=t.uint16_t, manufacturer_code=0x1209)



_LOGGER = logging.getLogger(__name__)
_SHIPPED = pathlib.Path(zhaquirks.__file__).resolve().parent
_STEPPED_BACK: set = set()

# The Zigbee fingerprints (manufacturer, model) this quirk is for; None matches any manufacturer.
FINGERPRINTS = [(None, 'Champion')]
# Names that a model-only fingerprint would catch but Zigbee2MQTT gives to other devices.
CLAIMED_ELSEWHERE = set()
# The endpoints this quirk needs, each with the input clusters it puts there where Zigbee2MQTT names none.
ENDPOINTS = {3: (0xE002,)}


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
    QuirkBuilder(None, 'Champion')
    .replaces(TwinguardMeasurementsCluster, endpoint_id=3)
    .sensor(attribute_name=TwinguardMeasurementsCluster.AttributeDefs.temperature.name, cluster_id=TwinguardMeasurementsCluster.cluster_id, endpoint_id=3, divisor=100, state_class=SensorStateClass.MEASUREMENT, device_class=SensorDeviceClass.TEMPERATURE, unit=UnitOfTemperature.CELSIUS, entity_type=EntityType.STANDARD, fallback_name='Temperature')
    .sensor(attribute_name=TwinguardMeasurementsCluster.AttributeDefs.illuminance.name, cluster_id=TwinguardMeasurementsCluster.cluster_id, endpoint_id=3, divisor=2, state_class=SensorStateClass.MEASUREMENT, device_class=SensorDeviceClass.ILLUMINANCE, unit=LIGHT_LUX, entity_type=EntityType.STANDARD, fallback_name='Illuminance')
    .sensor(attribute_name=TwinguardMeasurementsCluster.AttributeDefs.battery.name, cluster_id=TwinguardMeasurementsCluster.cluster_id, endpoint_id=3, divisor=2, state_class=SensorStateClass.MEASUREMENT, unit=PERCENTAGE, entity_type=EntityType.DIAGNOSTIC, translation_key='battery', fallback_name='Battery')
    # smoke: z2m's own code, not generated
    # humidity: z2m's own code, not generated
    # eco2: z2m's own code, not generated
    # aqi: z2m's own code, not generated
    # siren_state: z2m's own code, not generated
    # alarm: standard clusters or z2m's own code, not generated
    # self_test: z2m's own code, not generated
    # sensitivity: z2m's own code, not generated
    # pre_alarm: z2m's own code, not generated
    # heartbeat: z2m's own code, not generated
    .filter(no_builtin_quirk)
    .add_to_registry()
)
