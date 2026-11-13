"""Sprut.device Neptun.Smart: Neptun Smart leak protect module..

Generated from the Zigbee2MQTT definition.
Data: zigbee-herdsman-converters, MIT, Copyright (c) 2018 Koen Kanters.
Status: generated, not verified on hardware.
Revision: b88623af
"""

import functools
import logging
import pathlib

import zhaquirks
from zha.quirks import DEVICE_REGISTRY, DeviceMatch
import zigpy.types as t
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef
from zigpy.zcl.clusters.measurement import OzoneConcentration
from zigpy.zcl.clusters.measurement import SulfurDioxideConcentration
from zigpy.zcl.clusters.smartenergy import Metering

from zhaquirks.builder import (
    EntityPlatform,
    EntityType,
    NumberDeviceClass,
    QuirkBuilder,
    UnitOfTime,
)
from zhaquirks.clusters import CustomCluster


class LeakControllerCluster(CustomCluster, OzoneConcentration):
    """OzoneConcentration with the attributes z2m adds."""

    class AttributeDefs(OzoneConcentration.AttributeDefs):
        """Attribute definitions."""

        add_mode = ZCLAttributeDef(id=0x6600, type=t.Bool, manufacturer_code=0x6666)
        zone_count = ZCLAttributeDef(id=0x6601, type=t.uint8_t, manufacturer_code=0x6666)
        close_if_lost = ZCLAttributeDef(id=0x6602, type=t.Bool, manufacturer_code=0x6666)
        block_key = ZCLAttributeDef(id=0x6603, type=t.Bool, manufacturer_code=0x6666)
        assign_zone = ZCLAttributeDef(id=0x6604, type=t.uint8_t, manufacturer_code=0x6666)
        relay_group = ZCLAttributeDef(id=0x6605, type=t.uint8_t, manufacturer_code=0x6666)
        rf_sensor_count = ZCLAttributeDef(id=0x6606, type=t.uint8_t, access="r", manufacturer_code=0x6666)
        feedback_enable = ZCLAttributeDef(id=0x6607, type=t.Bool, manufacturer_code=0x6666)
        feedback_config = ZCLAttributeDef(id=0x6608, type=t.Bool, manufacturer_code=0x6666)
        alarm_time = ZCLAttributeDef(id=0x6609, type=t.uint16_t, manufacturer_code=0x6666)
        error = ZCLAttributeDef(id=0x660A, type=t.uint32_t, access="r", manufacturer_code=0x6666)
        close_power = ZCLAttributeDef(id=0x660B, type=t.Bool, manufacturer_code=0x6666)
        valve1status = ZCLAttributeDef(id=0x6610, type=t.uint8_t, access="r", manufacturer_code=0x6666)
        valve2status = ZCLAttributeDef(id=0x6611, type=t.uint8_t, access="r", manufacturer_code=0x6666)
        valve3status = ZCLAttributeDef(id=0x6612, type=t.uint8_t, access="r", manufacturer_code=0x6666)
        valve4status = ZCLAttributeDef(id=0x6613, type=t.uint8_t, access="r", manufacturer_code=0x6666)


class LeakLineCluster(CustomCluster, SulfurDioxideConcentration):
    """SulfurDioxideConcentration with the attributes z2m adds."""

    class AttributeDefs(SulfurDioxideConcentration.AttributeDefs):
        """Attribute definitions."""

        line_type = ZCLAttributeDef(id=0x6600, type=t.uint8_t, manufacturer_code=0x6666)
        line_assign = ZCLAttributeDef(id=0x6601, type=t.uint8_t, manufacturer_code=0x6666)
        line_status = ZCLAttributeDef(id=0x6602, type=t.uint8_t, access="r", manufacturer_code=0x6666)
        line_sensor_count = ZCLAttributeDef(id=0x6603, type=t.uint8_t, access="r", manufacturer_code=0x6666)


class SprutDeviceCluster(CustomCluster):
    """SprutDevice (z2m custom cluster)."""

    cluster_id = 0x6600

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        address = ZCLAttributeDef(id=0x6605, type=t.uint32_t, manufacturer_code=0x6666)
        uart_baud_rate = ZCLAttributeDef(id=0x6601, type=t.int32s, manufacturer_code=0x6666)


class LeakSensorCluster(CustomCluster):
    """LeakSensor (z2m custom cluster)."""

    cluster_id = 0x6604

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        leak_detected = ZCLAttributeDef(id=0x6602, type=t.Bool, access="r", manufacturer_code=0x6666)


class ZoneCount(t.enum8):
    """zone_count values (z2m)."""

    Single_zone = 0x01
    Dual_zone = 0x02


class SwitchRelayOnAlarm(t.enum8):
    """switch_relay_on_alarm values (z2m)."""

    Dont_switch = 0x00
    On_first_zone_alarm = 0x01
    On_second_zone_alarm = 0x02
    On_any_zone_alarm = 0x03


class SwitchRelayOnValveClosing(t.enum8):
    """switch_relay_on_valve_closing values (z2m)."""

    Dont_switch = 0x00
    On_first_zone = 0x01
    On_second_zone = 0x02
    On_any_zone = 0x03


class Valve1Status(t.enum8):
    """valve_1_status values (z2m)."""

    Unknown = 0x00
    Ok = 0x01
    Open_circuit = 0x02
    Valve_stuck = 0x03


class Valve2Status(t.enum8):
    """valve_2_status values (z2m)."""

    Unknown = 0x00
    Ok = 0x01
    Open_circuit = 0x02
    Valve_stuck = 0x03


class Valve3Status(t.enum8):
    """valve_3_status values (z2m)."""

    Unknown = 0x00
    Ok = 0x01
    Open_circuit = 0x02
    Valve_stuck = 0x03


class Valve4Status(t.enum8):
    """valve_4_status values (z2m)."""

    Unknown = 0x00
    Ok = 0x01
    Open_circuit = 0x02
    Valve_stuck = 0x03


class Type(t.enum8):
    """type values (z2m)."""

    Water_leak_sensor = 0x00
    Button_falling_edge_trigger = 0x01
    Switch_switch_valve_on_signal_level = 0x02


class ZoneAssignment(t.enum8):
    """zone_assignment values (z2m)."""

    Close_valves_in_zone_1 = 0x01
    Close_valves_in_zone_2 = 0x02
    Close_valves_in_both_zones = 0x03


class Status(t.enum8):
    """status values (z2m)."""

    Ok = 0x00
    Sensor_lost = 0x01
    Sensor_detected = 0x02
    Short_circuit = 0x03



_LOGGER = logging.getLogger(__name__)
_SHIPPED = pathlib.Path(zhaquirks.__file__).resolve().parent
_STEPPED_BACK: set = set()

# The Zigbee fingerprints (manufacturer, model) this quirk is for; None matches any manufacturer.
FINGERPRINTS = [(None, 'Neptun.Smart')]
# Names that a model-only fingerprint would catch but Zigbee2MQTT gives to other devices.
CLAIMED_ELSEWHERE = set()
# The endpoints this quirk needs, each with the input clusters it puts there where Zigbee2MQTT names none.
ENDPOINTS = {1: (0x0415, 0x6600), 4: (), 5: (), 6: (), 7: (), 8: (), 9: (), 10: (), 11: (), 12: (), 13: (), 14: ()}


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
    QuirkBuilder(None, 'Neptun.Smart')
    .replaces(LeakSensorCluster, endpoint_id=4)
    .replaces(LeakSensorCluster, endpoint_id=5)
    .replaces(LeakSensorCluster, endpoint_id=6)
    .replaces(LeakSensorCluster, endpoint_id=7)
    .replaces(LeakSensorCluster, endpoint_id=8)
    .replaces(LeakSensorCluster, endpoint_id=9)
    .replaces(LeakSensorCluster, endpoint_id=10)
    .replaces(SprutDeviceCluster)
    .replaces(LeakLineCluster, endpoint_id=7)
    .replaces(LeakLineCluster, endpoint_id=8)
    .replaces(LeakLineCluster, endpoint_id=9)
    .replaces(LeakLineCluster, endpoint_id=10)
    .replaces(LeakControllerCluster)
    .number(attribute_name=SprutDeviceCluster.AttributeDefs.address.name, cluster_id=SprutDeviceCluster.cluster_id, min_value=1, max_value=247, step=1, entity_type=EntityType.CONFIG, translation_key='modbus_address', fallback_name='Modbus address')
    .enum(attribute_name=LeakControllerCluster.AttributeDefs.zone_count.name, cluster_id=LeakControllerCluster.cluster_id, enum_class=ZoneCount, entity_type=EntityType.CONFIG, translation_key='zone_count', fallback_name='Zone count')
    .enum(attribute_name=LeakControllerCluster.AttributeDefs.assign_zone.name, cluster_id=LeakControllerCluster.cluster_id, enum_class=SwitchRelayOnAlarm, entity_type=EntityType.CONFIG, translation_key='switch_relay_on_alarm', fallback_name='Switch relay on alarm')
    .enum(attribute_name=LeakControllerCluster.AttributeDefs.relay_group.name, cluster_id=LeakControllerCluster.cluster_id, enum_class=SwitchRelayOnValveClosing, entity_type=EntityType.CONFIG, translation_key='switch_relay_on_valve_closing', fallback_name='Switch relay on valve closing')
    .sensor(attribute_name=LeakControllerCluster.AttributeDefs.rf_sensor_count.name, cluster_id=LeakControllerCluster.cluster_id, entity_type=EntityType.DIAGNOSTIC, translation_key='rf_sensor_count', fallback_name='RF sensor count')
    .number(attribute_name=LeakControllerCluster.AttributeDefs.alarm_time.name, cluster_id=LeakControllerCluster.cluster_id, min_value=0, max_value=255, step=1, unit=UnitOfTime.MINUTES, device_class=NumberDeviceClass.DURATION, entity_type=EntityType.CONFIG, translation_key='alarm_duration', fallback_name='Alarm duration')
    .sensor(attribute_name=LeakControllerCluster.AttributeDefs.error.name, cluster_id=LeakControllerCluster.cluster_id, entity_type=EntityType.DIAGNOSTIC, translation_key='error_code', fallback_name='Error code')
    .enum(attribute_name=LeakControllerCluster.AttributeDefs.valve1status.name, cluster_id=LeakControllerCluster.cluster_id, enum_class=Valve1Status, entity_platform=EntityPlatform.SENSOR, entity_type=EntityType.DIAGNOSTIC, translation_key='valve_1_status', fallback_name='Valve 1 status')
    .enum(attribute_name=LeakControllerCluster.AttributeDefs.valve2status.name, cluster_id=LeakControllerCluster.cluster_id, enum_class=Valve2Status, entity_platform=EntityPlatform.SENSOR, entity_type=EntityType.DIAGNOSTIC, translation_key='valve_2_status', fallback_name='Valve 2 status')
    .enum(attribute_name=LeakControllerCluster.AttributeDefs.valve3status.name, cluster_id=LeakControllerCluster.cluster_id, enum_class=Valve3Status, entity_platform=EntityPlatform.SENSOR, entity_type=EntityType.DIAGNOSTIC, translation_key='valve_3_status', fallback_name='Valve 3 status')
    .enum(attribute_name=LeakControllerCluster.AttributeDefs.valve4status.name, cluster_id=LeakControllerCluster.cluster_id, enum_class=Valve4Status, entity_platform=EntityPlatform.SENSOR, entity_type=EntityType.DIAGNOSTIC, translation_key='valve_4_status', fallback_name='Valve 4 status')
    .enum(attribute_name=LeakLineCluster.AttributeDefs.line_type.name, cluster_id=LeakLineCluster.cluster_id, endpoint_id=7, enum_class=Type, entity_type=EntityType.CONFIG, translation_key='type_wire_1', fallback_name='Type wire_1')
    .enum(attribute_name=LeakLineCluster.AttributeDefs.line_assign.name, cluster_id=LeakLineCluster.cluster_id, endpoint_id=7, enum_class=ZoneAssignment, entity_type=EntityType.CONFIG, translation_key='zone_assignment_wire_1', fallback_name='Zone assignment wire_1')
    .enum(attribute_name=LeakLineCluster.AttributeDefs.line_status.name, cluster_id=LeakLineCluster.cluster_id, endpoint_id=7, enum_class=Status, entity_platform=EntityPlatform.SENSOR, entity_type=EntityType.DIAGNOSTIC, translation_key='status_wire_1', fallback_name='Status wire_1')
    .sensor(attribute_name=LeakLineCluster.AttributeDefs.line_sensor_count.name, cluster_id=LeakLineCluster.cluster_id, endpoint_id=7, entity_type=EntityType.DIAGNOSTIC, translation_key='wired_sensor_count_wire_1', fallback_name='Wired sensor count wire_1')
    .enum(attribute_name=LeakLineCluster.AttributeDefs.line_type.name, cluster_id=LeakLineCluster.cluster_id, endpoint_id=8, enum_class=Type, entity_type=EntityType.CONFIG, translation_key='type_wire_2', fallback_name='Type wire_2')
    .enum(attribute_name=LeakLineCluster.AttributeDefs.line_assign.name, cluster_id=LeakLineCluster.cluster_id, endpoint_id=8, enum_class=ZoneAssignment, entity_type=EntityType.CONFIG, translation_key='zone_assignment_wire_2', fallback_name='Zone assignment wire_2')
    .enum(attribute_name=LeakLineCluster.AttributeDefs.line_status.name, cluster_id=LeakLineCluster.cluster_id, endpoint_id=8, enum_class=Status, entity_platform=EntityPlatform.SENSOR, entity_type=EntityType.DIAGNOSTIC, translation_key='status_wire_2', fallback_name='Status wire_2')
    .sensor(attribute_name=LeakLineCluster.AttributeDefs.line_sensor_count.name, cluster_id=LeakLineCluster.cluster_id, endpoint_id=8, entity_type=EntityType.DIAGNOSTIC, translation_key='wired_sensor_count_wire_2', fallback_name='Wired sensor count wire_2')
    .enum(attribute_name=LeakLineCluster.AttributeDefs.line_type.name, cluster_id=LeakLineCluster.cluster_id, endpoint_id=9, enum_class=Type, entity_type=EntityType.CONFIG, translation_key='type_wire_3', fallback_name='Type wire_3')
    .enum(attribute_name=LeakLineCluster.AttributeDefs.line_assign.name, cluster_id=LeakLineCluster.cluster_id, endpoint_id=9, enum_class=ZoneAssignment, entity_type=EntityType.CONFIG, translation_key='zone_assignment_wire_3', fallback_name='Zone assignment wire_3')
    .enum(attribute_name=LeakLineCluster.AttributeDefs.line_status.name, cluster_id=LeakLineCluster.cluster_id, endpoint_id=9, enum_class=Status, entity_platform=EntityPlatform.SENSOR, entity_type=EntityType.DIAGNOSTIC, translation_key='status_wire_3', fallback_name='Status wire_3')
    .sensor(attribute_name=LeakLineCluster.AttributeDefs.line_sensor_count.name, cluster_id=LeakLineCluster.cluster_id, endpoint_id=9, entity_type=EntityType.DIAGNOSTIC, translation_key='wired_sensor_count_wire_3', fallback_name='Wired sensor count wire_3')
    .enum(attribute_name=LeakLineCluster.AttributeDefs.line_type.name, cluster_id=LeakLineCluster.cluster_id, endpoint_id=10, enum_class=Type, entity_type=EntityType.CONFIG, translation_key='type_wire_4', fallback_name='Type wire_4')
    .enum(attribute_name=LeakLineCluster.AttributeDefs.line_assign.name, cluster_id=LeakLineCluster.cluster_id, endpoint_id=10, enum_class=ZoneAssignment, entity_type=EntityType.CONFIG, translation_key='zone_assignment_wire_4', fallback_name='Zone assignment wire_4')
    .enum(attribute_name=LeakLineCluster.AttributeDefs.line_status.name, cluster_id=LeakLineCluster.cluster_id, endpoint_id=10, enum_class=Status, entity_platform=EntityPlatform.SENSOR, entity_type=EntityType.DIAGNOSTIC, translation_key='status_wire_4', fallback_name='Status wire_4')
    .sensor(attribute_name=LeakLineCluster.AttributeDefs.line_sensor_count.name, cluster_id=LeakLineCluster.cluster_id, endpoint_id=10, entity_type=EntityType.DIAGNOSTIC, translation_key='wired_sensor_count_wire_4', fallback_name='Wired sensor count wire_4')
    .sensor(attribute_name=Metering.AttributeDefs.multiplier.name, cluster_id=Metering.cluster_id, endpoint_id=11, entity_type=EntityType.DIAGNOSTIC, translation_key='multiplier_meter_1', fallback_name='Multiplier meter_1')
    .sensor(attribute_name=Metering.AttributeDefs.multiplier.name, cluster_id=Metering.cluster_id, endpoint_id=12, entity_type=EntityType.DIAGNOSTIC, translation_key='multiplier_meter_2', fallback_name='Multiplier meter_2')
    .sensor(attribute_name=Metering.AttributeDefs.multiplier.name, cluster_id=Metering.cluster_id, endpoint_id=13, entity_type=EntityType.DIAGNOSTIC, translation_key='multiplier_meter_3', fallback_name='Multiplier meter_3')
    .sensor(attribute_name=Metering.AttributeDefs.multiplier.name, cluster_id=Metering.cluster_id, endpoint_id=14, entity_type=EntityType.DIAGNOSTIC, translation_key='multiplier_meter_4', fallback_name='Multiplier meter_4')
    .sensor(attribute_name=Metering.AttributeDefs.divisor.name, cluster_id=Metering.cluster_id, endpoint_id=11, entity_type=EntityType.DIAGNOSTIC, translation_key='divisor_meter_1', fallback_name='Divisor meter_1')
    .sensor(attribute_name=Metering.AttributeDefs.divisor.name, cluster_id=Metering.cluster_id, endpoint_id=12, entity_type=EntityType.DIAGNOSTIC, translation_key='divisor_meter_2', fallback_name='Divisor meter_2')
    .sensor(attribute_name=Metering.AttributeDefs.divisor.name, cluster_id=Metering.cluster_id, endpoint_id=13, entity_type=EntityType.DIAGNOSTIC, translation_key='divisor_meter_3', fallback_name='Divisor meter_3')
    .sensor(attribute_name=Metering.AttributeDefs.divisor.name, cluster_id=Metering.cluster_id, endpoint_id=14, entity_type=EntityType.DIAGNOSTIC, translation_key='divisor_meter_4', fallback_name='Divisor meter_4')
    # uart_baud_rate: enum values outside 0..65535, not generated
    # wireless_sensor_pairing: z2m wire values 'On'/'Off' do not fit BOOLEAN, not generated
    # child_lock: z2m wire values 'On'/'Off' do not fit BOOLEAN, not generated
    # close_valves_if_sensor_lost: z2m wire values 'On'/'Off' do not fit BOOLEAN, not generated
    # wired_sensor_feedback: z2m wire values 'On'/'Off' do not fit BOOLEAN, not generated
    # count_wired_sensors: z2m wire values 'On'/'Off' do not fit BOOLEAN, not generated
    # floor_washing_mode: standard clusters, ZHA's own entities
    # water_leak: z2m wire values 'Alarm'/'No alarm' do not fit BOOLEAN, not generated
    # water_leak: z2m wire values 'Alarm'/'No alarm' do not fit BOOLEAN, not generated
    # water_leak: z2m wire values 'Alarm'/'No alarm' do not fit BOOLEAN, not generated
    # water_leak: z2m wire values 'Alarm'/'No alarm' do not fit BOOLEAN, not generated
    # water_leak: z2m wire values 'Alarm'/'No alarm' do not fit BOOLEAN, not generated
    # water_leak: z2m wire values 'Alarm'/'No alarm' do not fit BOOLEAN, not generated
    # water_leak: z2m wire values 'Alarm'/'No alarm' do not fit BOOLEAN, not generated
    # summation_delivered: standard clusters, ZHA's own entities
    # summation_delivered: standard clusters, ZHA's own entities
    # summation_delivered: standard clusters, ZHA's own entities
    # summation_delivered: standard clusters, ZHA's own entities
    # switch: standard clusters, ZHA's own entities
    # switch: standard clusters, ZHA's own entities
    # water_leak: standard clusters, ZHA's own entities
    .filter(no_builtin_quirk)
    .add_to_registry()
)
