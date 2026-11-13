"""Wiren Board WB-MSW-ZIGBEE_v.4_official: Wall-mounted multi sensor with official Wiren Board firmware.

Generated from the Zigbee2MQTT definition.
Data: zigbee-herdsman-converters, MIT, Copyright (c) 2018 Koen Kanters.
Status: generated, not verified on hardware.
Revision: 7cc7d45d
"""

import functools
import logging
import pathlib

import zhaquirks
from zha.quirks import DEVICE_REGISTRY, DeviceMatch
import zigpy.types as t
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef
from zigpy.zcl.clusters.general import AnalogInput
from zigpy.zcl.clusters.general import MultistateInput
from zigpy.zcl.clusters.general import MultistateOutput
from zigpy.zcl.clusters.measurement import OccupancySensing
from zigpy.zcl.clusters.measurement import TemperatureMeasurement

from zhaquirks.builder import (
    EntityPlatform,
    EntityType,
    NumberDeviceClass,
    QuirkBuilder,
    UnitOfSoundPressure,
    UnitOfTemperature,
    UnitOfTime,
)
from zhaquirks.clusters import CustomCluster


class GenAnalogInputCluster(CustomCluster, AnalogInput):
    """AnalogInput with the attributes z2m adds."""

    class AttributeDefs(AnalogInput.AttributeDefs):
        """Attribute definitions."""

        noise_detected = ZCLAttributeDef(id=0x1000, type=t.Bool, access="r", manufacturer_code=None)
        noise_threshold = ZCLAttributeDef(id=0x1001, type=t.uint16_t, manufacturer_code=None)
        noise_timeout = ZCLAttributeDef(id=0x1002, type=t.uint16_t, manufacturer_code=None)


class GenMultistateInputCluster(CustomCluster, MultistateInput):
    """MultistateInput with the attributes z2m adds."""

    class AttributeDefs(MultistateInput.AttributeDefs):
        """Attribute definitions."""

        msw_slave_id = ZCLAttributeDef(id=0x1000, type=t.uint8_t, access="r", manufacturer_code=None)
        msw_serial_number = ZCLAttributeDef(id=0x1001, type=t.uint32_t, access="r", manufacturer_code=None)
        msw_fw_version = ZCLAttributeDef(id=0x1002, type=t.CharacterString, access="r", manufacturer_code=None)
        msw_fw_signature = ZCLAttributeDef(id=0x1003, type=t.CharacterString, access="r", manufacturer_code=None)
        msw_boot_version = ZCLAttributeDef(id=0x1004, type=t.CharacterString, access="r", manufacturer_code=None)
        msw_component_version = ZCLAttributeDef(id=0x1005, type=t.CharacterString, access="r", manufacturer_code=None)
        msw_component_signature = ZCLAttributeDef(id=0x1006, type=t.CharacterString, access="r", manufacturer_code=None)


class GenMultistateOutputCluster(CustomCluster, MultistateOutput):
    """MultistateOutput with the attributes z2m adds."""

    class AttributeDefs(MultistateOutput.AttributeDefs):
        """Attribute definitions."""

        ir_rom_id = ZCLAttributeDef(id=0x1000, type=t.uint16_t, manufacturer_code=None)


class MsTemperatureMeasurementCluster(CustomCluster, TemperatureMeasurement):
    """TemperatureMeasurement with the attributes z2m adds."""

    class AttributeDefs(TemperatureMeasurement.AttributeDefs):
        """Attribute definitions."""

        temperature_offset = ZCLAttributeDef(id=0x1000, type=t.int16s, manufacturer_code=None)


class MsOccupancySensingCluster(CustomCluster, OccupancySensing):
    """OccupancySensing with the attributes z2m adds."""

    class AttributeDefs(OccupancySensing.AttributeDefs):
        """Attribute definitions."""

        occupancy_level = ZCLAttributeDef(id=0x1000, type=t.uint16_t, access="r", manufacturer_code=None)
        occupancy_sensitivity = ZCLAttributeDef(id=0x1001, type=t.uint16_t, manufacturer_code=None)
        occupancy_timeout = ZCLAttributeDef(id=0x1002, type=t.uint16_t, manufacturer_code=None)


class WbVocCluster(CustomCluster):
    """wbVoc (z2m custom cluster)."""

    cluster_id = 0x042E

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        measured_value = ZCLAttributeDef(id=0x0000, type=t.Single, access="r", manufacturer_code=None)


class Connectivity(t.enum8):
    """connectivity values (z2m)."""

    offline = 0x01
    online = 0x02
    firmware_update = 0x03
    component_update = 0x04


class IrAction(t.enum8):
    """ir_action values (z2m)."""

    stop = 0x00
    learn_ram = 0x01
    learn_rom = 0x02
    play_ram = 0x03
    play_rom = 0x04
    clear_all_rom = 0x05



_LOGGER = logging.getLogger(__name__)
_SHIPPED = pathlib.Path(zhaquirks.__file__).resolve().parent
_STEPPED_BACK: set = set()

# The Zigbee fingerprints (manufacturer, model) this quirk is for; None matches any manufacturer.
FINGERPRINTS = [(None, 'WB-MSW-ZIGBEE v.4')]
# Names that a model-only fingerprint would catch but Zigbee2MQTT gives to other devices.
CLAIMED_ELSEWHERE = set()
# The endpoints this quirk needs, each with the input clusters it puts there where Zigbee2MQTT names none.
ENDPOINTS = {1: (0x000C, 0x0012, 0x0402, 0x0406, 0x042E), 6: ()}


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
    QuirkBuilder(None, 'WB-MSW-ZIGBEE v.4')
    .replaces(WbVocCluster)
    .replaces(MsOccupancySensingCluster)
    .replaces(MsTemperatureMeasurementCluster)
    .replaces(GenMultistateOutputCluster, endpoint_id=6)
    .replaces(GenMultistateInputCluster)
    .replaces(GenAnalogInputCluster)
    .binary_sensor(attribute_name=GenAnalogInputCluster.AttributeDefs.noise_detected.name, cluster_id=GenAnalogInputCluster.cluster_id, entity_type=EntityType.STANDARD, translation_key='noise', fallback_name='Noise')
    .number(attribute_name=GenAnalogInputCluster.AttributeDefs.noise_threshold.name, cluster_id=GenAnalogInputCluster.cluster_id, min_value=0, max_value=150, unit=UnitOfSoundPressure.WEIGHTED_DECIBEL_A, device_class=NumberDeviceClass.SOUND_PRESSURE, entity_type=EntityType.CONFIG, translation_key='noise_threshold', fallback_name='Noise threshold')
    .number(attribute_name=GenAnalogInputCluster.AttributeDefs.noise_timeout.name, cluster_id=GenAnalogInputCluster.cluster_id, min_value=0, max_value=2000, unit=UnitOfTime.SECONDS, device_class=NumberDeviceClass.DURATION, entity_type=EntityType.CONFIG, translation_key='noise_timeout', fallback_name='Noise timeout')
    .enum(attribute_name=GenMultistateInputCluster.AttributeDefs.present_value.name, cluster_id=GenMultistateInputCluster.cluster_id, enum_class=Connectivity, entity_platform=EntityPlatform.SENSOR, entity_type=EntityType.DIAGNOSTIC, translation_key='connectivity', fallback_name='Connectivity')
    .sensor(attribute_name=GenMultistateInputCluster.AttributeDefs.msw_slave_id.name, cluster_id=GenMultistateInputCluster.cluster_id, entity_type=EntityType.DIAGNOSTIC, translation_key='modbus_slave_id', fallback_name='Modbus slave ID')
    .sensor(attribute_name=GenMultistateInputCluster.AttributeDefs.msw_serial_number.name, cluster_id=GenMultistateInputCluster.cluster_id, entity_type=EntityType.DIAGNOSTIC, translation_key='serial_number', fallback_name='Serial number')
    .number(attribute_name=MsTemperatureMeasurementCluster.AttributeDefs.temperature_offset.name, cluster_id=MsTemperatureMeasurementCluster.cluster_id, min_value=-10, max_value=10, step=0.1, unit=UnitOfTemperature.CELSIUS, multiplier=0.01, device_class=NumberDeviceClass.TEMPERATURE_DELTA, entity_type=EntityType.CONFIG, translation_key='temperature_offset', fallback_name='Temperature offset')
    .sensor(attribute_name=MsOccupancySensingCluster.AttributeDefs.occupancy_level.name, cluster_id=MsOccupancySensingCluster.cluster_id, entity_type=EntityType.DIAGNOSTIC, translation_key='occupancy_level', fallback_name='Occupancy level')
    .number(attribute_name=MsOccupancySensingCluster.AttributeDefs.occupancy_sensitivity.name, cluster_id=MsOccupancySensingCluster.cluster_id, min_value=0, max_value=2000, entity_type=EntityType.CONFIG, translation_key='occupancy_sensitivity', fallback_name='Occupancy sensitivity')
    .number(attribute_name=MsOccupancySensingCluster.AttributeDefs.occupancy_timeout.name, cluster_id=MsOccupancySensingCluster.cluster_id, min_value=0, max_value=2000, unit=UnitOfTime.SECONDS, device_class=NumberDeviceClass.DURATION, entity_type=EntityType.CONFIG, translation_key='occupancy_timeout', fallback_name='Occupancy timeout')
    .number(attribute_name=GenMultistateOutputCluster.AttributeDefs.ir_rom_id.name, cluster_id=GenMultistateOutputCluster.cluster_id, endpoint_id=6, min_value=0, max_value=79, entity_type=EntityType.STANDARD, translation_key='ir_rom_id', fallback_name='IR rom ID')
    .enum(attribute_name=GenMultistateOutputCluster.AttributeDefs.present_value.name, cluster_id=GenMultistateOutputCluster.cluster_id, endpoint_id=6, enum_class=IrAction, entity_type=EntityType.STANDARD, translation_key='ir_action', fallback_name='IR action')
    # temperature: standard clusters, ZHA's own entities
    # noise_level: standard clusters, ZHA's own entities
    # status_led: standard clusters, ZHA's own entities
    # voc: standard clusters, ZHA's own entities
    # switch: standard clusters, ZHA's own entities
    # switch: standard clusters, ZHA's own entities
    # switch: standard clusters, ZHA's own entities
    # switch: standard clusters, ZHA's own entities
    # illuminance: standard clusters, ZHA's own entities
    # humidity: standard clusters, ZHA's own entities
    # occupancy: standard clusters, ZHA's own entities
    # co2: standard clusters, ZHA's own entities
    # fw_version: z2m's own code, not generated
    # fw_signature: z2m's own code, not generated
    # boot_version: z2m's own code, not generated
    # component_version: z2m's own code, not generated
    # component_signature: z2m's own code, not generated
    .filter(no_builtin_quirk)
    .add_to_registry()
)
