"""Ubisys H1: Heating regulator.

Generated from the Zigbee2MQTT definition.
Entity names follow ZHA's own quirk for this device where it shows the same feature.
Data: zigbee-herdsman-converters, MIT, Copyright (c) 2018 Koen Kanters.
Status: generated, not verified on hardware.
Revision: 913ef3c7
"""

import functools
import logging
import pathlib

import zhaquirks
from zha.quirks import DEVICE_REGISTRY, DeviceMatch
import zigpy.types as t
from zigpy.zcl.foundation import ZCLAttributeDef
from zigpy.zcl.clusters.hvac import Thermostat

from zhaquirks.builder import (
    EntityType,
    NumberDeviceClass,
    QuirkBuilder,
    UnitOfLength,
    UnitOfTemperature,
    UnitOfTime,
)
from zhaquirks.clusters import CustomCluster


class HvacThermostatCluster(CustomCluster, Thermostat):
    """Thermostat with the attributes z2m adds."""

    class AttributeDefs(Thermostat.AttributeDefs):
        """Attribute definitions."""

        ubisys_class_b_temperature_offset = ZCLAttributeDef(id=0x0000, type=t.int8s, manufacturer_code=0x10F2)
        ubisys_return_flow_temperature_weight = ZCLAttributeDef(id=0x0001, type=t.int8s, manufacturer_code=0x10F2)
        # ubisys_raw_outdoor_temperature 0x0002: STRUCT, attribute only
        # ubisys_raw_local_temperature_a 0x0003: STRUCT, attribute only
        # ubisys_raw_local_temperature_b 0x0004: STRUCT, attribute only
        # ubisys_raw_forward_flow_temperature 0x0005: STRUCT, attribute only
        # ubisys_raw_return_flow_temperature 0x0006: STRUCT, attribute only
        # ubisys_installed_extensions 0x0007: BITMAP64, attribute only
        ubisys_temperature_offset = ZCLAttributeDef(id=0x0010, type=t.int8s, manufacturer_code=0x10F2)
        ubisys_default_occupied_heating_setpoint = ZCLAttributeDef(id=0x0011, type=t.int16s, manufacturer_code=0x10F2)
        ubisys_vacation_mode = ZCLAttributeDef(id=0x0012, type=t.Bool, manufacturer_code=0x10F2)
        ubisys_remote_temperature = ZCLAttributeDef(id=0x0013, type=t.int16s, manufacturer_code=0x10F2)
        ubisys_remote_temperature_valid_duration = ZCLAttributeDef(id=0x0014, type=t.uint16_t, manufacturer_code=0x10F2)
        ubisys_detect_open_window = ZCLAttributeDef(id=0x0015, type=t.bitmap8, manufacturer_code=0x10F2)
        ubisys_open_window_state = ZCLAttributeDef(id=0x0016, type=t.bitmap8, manufacturer_code=0x10F2)
        ubisys_open_window_sensitivity = ZCLAttributeDef(id=0x0017, type=t.uint16_t, manufacturer_code=0x10F2)
        ubisys_open_window_detection_period = ZCLAttributeDef(id=0x0018, type=t.uint16_t, manufacturer_code=0x10F2)
        ubisys_open_window_timeout = ZCLAttributeDef(id=0x0019, type=t.uint16_t, manufacturer_code=0x10F2)
        ubisys_proportional_gain = ZCLAttributeDef(id=0x0020, type=t.int16s, manufacturer_code=0x10F2)
        ubisys_proportional_shift = ZCLAttributeDef(id=0x0021, type=t.int8s, manufacturer_code=0x10F2)
        ubisys_integral_factor = ZCLAttributeDef(id=0x0022, type=t.int16s, manufacturer_code=0x10F2)



_LOGGER = logging.getLogger(__name__)
_SHIPPED = pathlib.Path(zhaquirks.__file__).resolve().parent
_STEPPED_BACK: set = set()

# The Zigbee fingerprints (manufacturer, model) this quirk is for; None matches any manufacturer.
FINGERPRINTS = [(None, 'H1'), ('ubisys', 'H1')]
# Names that a model-only fingerprint would catch but Zigbee2MQTT gives to other devices.
CLAIMED_ELSEWHERE = set()
# The endpoints this quirk needs, each with the input clusters it puts there where Zigbee2MQTT names none.
ENDPOINTS = {1: (0x0201,)}


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


(
    QuirkBuilder(None, 'H1')
    .applies_to('ubisys', 'H1')
    .replaces(HvacThermostatCluster)
    .number(attribute_name=HvacThermostatCluster.AttributeDefs.ubisys_remote_temperature_valid_duration.name, cluster_id=HvacThermostatCluster.cluster_id, min_value=0, max_value=65535, unit=UnitOfTime.SECONDS, device_class=NumberDeviceClass.DURATION, entity_type=EntityType.CONFIG, translation_key='remote_temperature_duration', fallback_name='Remote temperature duration')
    .number(attribute_name=HvacThermostatCluster.AttributeDefs.ubisys_open_window_timeout.name, cluster_id=HvacThermostatCluster.cluster_id, min_value=0, max_value=65535, unit=UnitOfTime.SECONDS, device_class=NumberDeviceClass.DURATION, entity_type=EntityType.CONFIG, translation_key='open_window_timeout', fallback_name='Open window timeout')
    .number(attribute_name=HvacThermostatCluster.AttributeDefs.ubisys_open_window_detection_period.name, cluster_id=HvacThermostatCluster.cluster_id, min_value=1, max_value=180, unit=UnitOfLength.METERS, device_class=NumberDeviceClass.DISTANCE, entity_type=EntityType.CONFIG, translation_key='open_window_detection_periode', fallback_name='Open window detection periode')
    .number(attribute_name=HvacThermostatCluster.AttributeDefs.ubisys_open_window_sensitivity.name, cluster_id=HvacThermostatCluster.cluster_id, min_value=1, max_value=30, step=0.5, unit=UnitOfTemperature.CELSIUS, multiplier=0.01, device_class=NumberDeviceClass.TEMPERATURE, entity_type=EntityType.CONFIG, translation_key='open_window_detection_threshold', fallback_name='Open window detection threshold', unique_id_suffix='open_window_sensitivity')
    # open_window_state: standard clusters, ZHA's own entities
    # local_temperature_offset: standard clusters, ZHA's own entities
    # occupied_heating_default_setpoint: standard clusters, ZHA's own entities
    # remote_temperature_duration: z2m range 0..86400 does not fit UINT16, clamped
    # open_window_detect: standard clusters, ZHA's own entities
    # open_window_timeout: z2m range 0..86400 does not fit UINT16, clamped
    # vacation_mode: standard clusters or z2m's own code, not generated
    # battery: standard clusters, ZHA's own entities
    # voltage: standard clusters, ZHA's own entities
    # climate: standard clusters, ZHA's own entities
    .filter(no_builtin_quirk)
    .add_to_registry()
)
