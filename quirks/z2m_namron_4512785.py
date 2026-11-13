"""Namron 4512785: Zigbee 30A relay with NTC temperature sensors and water leak detection.

Generated from the Zigbee2MQTT definition.
Data: zigbee-herdsman-converters, MIT, Copyright (c) 2018 Koen Kanters.
Status: generated, not verified on hardware.
Revision: ea825701
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
    QuirkBuilder,
    UnitOfTemperature,
)
from zhaquirks.clusters import CustomCluster


class NamronPrivate04E0Cluster(CustomCluster):
    """namronPrivate04E0 (z2m custom cluster)."""

    cluster_id = 0x04E0

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        ntc2_temperature = ZCLAttributeDef(id=0x0000, type=t.int16s, access="r", manufacturer_code=None)
        ntc_sensor_type1 = ZCLAttributeDef(id=0x0001, type=t.enum8, manufacturer_code=None)
        ntc_sensor_type2 = ZCLAttributeDef(id=0x0002, type=t.enum8, manufacturer_code=None)
        water_sensor_value = ZCLAttributeDef(id=0x0003, type=t.Bool, access="r", manufacturer_code=None)
        ntc_calibration1 = ZCLAttributeDef(id=0x0004, type=t.int8s, manufacturer_code=None)
        ntc_calibration2 = ZCLAttributeDef(id=0x0005, type=t.int8s, manufacturer_code=None)
        water_alarm_relay_action = ZCLAttributeDef(id=0x0006, type=t.enum8, manufacturer_code=None)
        ntc1_operation_select = ZCLAttributeDef(id=0x0007, type=t.enum8, manufacturer_code=None)
        ntc2_operation_select = ZCLAttributeDef(id=0x0008, type=t.enum8, manufacturer_code=None)
        ntc1_relay_auto_temp = ZCLAttributeDef(id=0x0009, type=t.int16s, manufacturer_code=None)
        ntc2_relay_auto_temp = ZCLAttributeDef(id=0x000A, type=t.int16s, manufacturer_code=None)
        override_option = ZCLAttributeDef(id=0x000B, type=t.enum8, manufacturer_code=None)
        ntc1_temp_hysteresis = ZCLAttributeDef(id=0x000C, type=t.int8s, manufacturer_code=None)
        ntc2_temp_hysteresis = ZCLAttributeDef(id=0x000D, type=t.int8s, manufacturer_code=None)
        water_condition_alarm = ZCLAttributeDef(id=0x000E, type=t.Bool, access="r", manufacturer_code=None)
        ntc_condition_alarm = ZCLAttributeDef(id=0x000F, type=t.Bool, access="r", manufacturer_code=None)
        is_execute_condition = ZCLAttributeDef(id=0x0010, type=t.Bool, access="r", manufacturer_code=None)


class Ntc1SensorType(t.enum8):
    """ntc1_sensor_type values (z2m)."""

    none = 0x00
    NTC_10K = 0x01
    NTC_12K = 0x02
    NTC_15K = 0x03
    NTC_22K = 0x04
    NTC_33K = 0x05
    NTC_47K = 0x06


class Ntc2SensorType(t.enum8):
    """ntc2_sensor_type values (z2m)."""

    none = 0x00
    NTC_10K = 0x01
    NTC_12K = 0x02
    NTC_15K = 0x03
    NTC_22K = 0x04
    NTC_33K = 0x05
    NTC_47K = 0x06


class WaterAlarmRelayAction(t.enum8):
    """water_alarm_relay_action values (z2m)."""

    no_action = 0x00
    turn_off_restore = 0x01
    turn_on_restore = 0x02
    turn_off_stay = 0x03
    turn_on_stay = 0x04
    no_water_turn_off = 0x05
    no_water_turn_on = 0x06


class Ntc1OperationMode(t.enum8):
    """ntc1_operation_mode values (z2m)."""

    no_action = 0x00
    off_when_hot_on_when_cold = 0x01
    on_when_hot_off_when_cold = 0x02
    off_when_hot_stay = 0x03
    on_when_hot_stay = 0x04


class Ntc2OperationMode(t.enum8):
    """ntc2_operation_mode values (z2m)."""

    no_action = 0x00
    off_when_hot_on_when_cold = 0x01
    on_when_hot_off_when_cold = 0x02
    off_when_hot_stay = 0x03
    on_when_hot_stay = 0x04


class OverrideOption(t.enum8):
    """override_option values (z2m)."""

    no_priority = 0x00
    water_alarm_priority = 0x01
    ntc_priority = 0x02



_LOGGER = logging.getLogger(__name__)
_SHIPPED = pathlib.Path(zhaquirks.__file__).resolve().parent
_STEPPED_BACK: set = set()

# The Zigbee fingerprints (manufacturer, model) this quirk is for; None matches any manufacturer.
FINGERPRINTS = [(None, '4512785')]
# Names that a model-only fingerprint would catch but Zigbee2MQTT gives to other devices.
CLAIMED_ELSEWHERE = set()
# The endpoints this quirk needs, each with the input clusters it puts there where Zigbee2MQTT names none.
ENDPOINTS = {1: (0x04E0,)}


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
    QuirkBuilder(None, '4512785')
    .replaces(NamronPrivate04E0Cluster)
    .binary_sensor(attribute_name=NamronPrivate04E0Cluster.AttributeDefs.water_sensor_value.name, cluster_id=NamronPrivate04E0Cluster.cluster_id, entity_type=EntityType.STANDARD, translation_key='water_sensor', fallback_name='Water sensor')
    .enum(attribute_name=NamronPrivate04E0Cluster.AttributeDefs.ntc_sensor_type1.name, cluster_id=NamronPrivate04E0Cluster.cluster_id, enum_class=Ntc1SensorType, entity_type=EntityType.CONFIG, translation_key='ntc1_sensor_type', fallback_name='Ntc1 sensor type')
    .enum(attribute_name=NamronPrivate04E0Cluster.AttributeDefs.ntc_sensor_type2.name, cluster_id=NamronPrivate04E0Cluster.cluster_id, enum_class=Ntc2SensorType, entity_type=EntityType.CONFIG, translation_key='ntc2_sensor_type', fallback_name='Ntc2 sensor type')
    .enum(attribute_name=NamronPrivate04E0Cluster.AttributeDefs.water_alarm_relay_action.name, cluster_id=NamronPrivate04E0Cluster.cluster_id, enum_class=WaterAlarmRelayAction, entity_type=EntityType.CONFIG, translation_key='water_alarm_relay_action', fallback_name='Water alarm relay action')
    .enum(attribute_name=NamronPrivate04E0Cluster.AttributeDefs.ntc1_operation_select.name, cluster_id=NamronPrivate04E0Cluster.cluster_id, enum_class=Ntc1OperationMode, entity_type=EntityType.CONFIG, translation_key='ntc1_operation_mode', fallback_name='Ntc1 operation mode')
    .enum(attribute_name=NamronPrivate04E0Cluster.AttributeDefs.ntc2_operation_select.name, cluster_id=NamronPrivate04E0Cluster.cluster_id, enum_class=Ntc2OperationMode, entity_type=EntityType.CONFIG, translation_key='ntc2_operation_mode', fallback_name='Ntc2 operation mode')
    .number(attribute_name=NamronPrivate04E0Cluster.AttributeDefs.ntc1_relay_auto_temp.name, cluster_id=NamronPrivate04E0Cluster.cluster_id, min_value=0, max_value=100, step=0.1, unit=UnitOfTemperature.CELSIUS, multiplier=0.1, device_class=NumberDeviceClass.TEMPERATURE, entity_type=EntityType.CONFIG, translation_key='ntc1_relay_auto_temp', fallback_name='Ntc1 relay auto temp')
    .number(attribute_name=NamronPrivate04E0Cluster.AttributeDefs.ntc2_relay_auto_temp.name, cluster_id=NamronPrivate04E0Cluster.cluster_id, min_value=0, max_value=100, step=0.1, unit=UnitOfTemperature.CELSIUS, multiplier=0.1, device_class=NumberDeviceClass.TEMPERATURE, entity_type=EntityType.CONFIG, translation_key='ntc2_relay_auto_temp', fallback_name='Ntc2 relay auto temp')
    .enum(attribute_name=NamronPrivate04E0Cluster.AttributeDefs.override_option.name, cluster_id=NamronPrivate04E0Cluster.cluster_id, enum_class=OverrideOption, entity_type=EntityType.CONFIG, translation_key='override_option', fallback_name='Override option')
    .number(attribute_name=NamronPrivate04E0Cluster.AttributeDefs.ntc_calibration1.name, cluster_id=NamronPrivate04E0Cluster.cluster_id, min_value=-10, max_value=10, unit=UnitOfTemperature.CELSIUS, device_class=NumberDeviceClass.TEMPERATURE_DELTA, entity_type=EntityType.CONFIG, translation_key='ntc1_calibration', fallback_name='Ntc1 calibration')
    .number(attribute_name=NamronPrivate04E0Cluster.AttributeDefs.ntc_calibration2.name, cluster_id=NamronPrivate04E0Cluster.cluster_id, min_value=-10, max_value=10, unit=UnitOfTemperature.CELSIUS, device_class=NumberDeviceClass.TEMPERATURE_DELTA, entity_type=EntityType.CONFIG, translation_key='ntc2_calibration', fallback_name='Ntc2 calibration')
    .number(attribute_name=NamronPrivate04E0Cluster.AttributeDefs.ntc1_temp_hysteresis.name, cluster_id=NamronPrivate04E0Cluster.cluster_id, min_value=-10, max_value=10, unit=UnitOfTemperature.CELSIUS, device_class=NumberDeviceClass.TEMPERATURE_DELTA, entity_type=EntityType.CONFIG, translation_key='ntc1_temp_hysteresis', fallback_name='Ntc1 temp hysteresis')
    .number(attribute_name=NamronPrivate04E0Cluster.AttributeDefs.ntc2_temp_hysteresis.name, cluster_id=NamronPrivate04E0Cluster.cluster_id, min_value=-10, max_value=10, unit=UnitOfTemperature.CELSIUS, device_class=NumberDeviceClass.TEMPERATURE_DELTA, entity_type=EntityType.CONFIG, translation_key='ntc2_temp_hysteresis', fallback_name='Ntc2 temp hysteresis')
    .binary_sensor(attribute_name=NamronPrivate04E0Cluster.AttributeDefs.water_condition_alarm.name, cluster_id=NamronPrivate04E0Cluster.cluster_id, entity_type=EntityType.STANDARD, translation_key='water_condition_alarm', fallback_name='Water condition alarm')
    .binary_sensor(attribute_name=NamronPrivate04E0Cluster.AttributeDefs.ntc_condition_alarm.name, cluster_id=NamronPrivate04E0Cluster.cluster_id, entity_type=EntityType.STANDARD, translation_key='ntc_condition_alarm', fallback_name='NTC condition alarm')
    .binary_sensor(attribute_name=NamronPrivate04E0Cluster.AttributeDefs.is_execute_condition.name, cluster_id=NamronPrivate04E0Cluster.cluster_id, entity_type=EntityType.STANDARD, translation_key='is_execute_condition', fallback_name='Is execute condition')
    # device_temperature: z2m numeric with own fromZigbee converter, not generated
    # ntc1_temperature: z2m numeric with own fromZigbee converter, not generated
    # ntc2_temperature: z2m numeric with own fromZigbee converter, not generated
    # switch: standard clusters, ZHA's own entities
    # power_on_behavior: standard clusters, ZHA's own entities
    # power: standard clusters, ZHA's own entities
    # voltage: standard clusters, ZHA's own entities
    # current: standard clusters, ZHA's own entities
    # energy: standard clusters, ZHA's own entities
    .filter(no_builtin_quirk)
    .add_to_registry()
)
