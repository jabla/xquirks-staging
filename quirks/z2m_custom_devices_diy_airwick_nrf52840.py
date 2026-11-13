"""Custom devices (DiY) AirWick_nRF52840: AirWick smart aerosol dispenser.

Generated from the Zigbee2MQTT definition.
Data: zigbee-herdsman-converters, MIT, Copyright (c) 2018 Koen Kanters.
Status: generated, not verified on hardware.
Revision: de348605
"""

import functools
import logging
import pathlib

import zhaquirks
from zha.quirks import DEVICE_REGISTRY, DeviceMatch
import zigpy.types as t
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef
from zigpy.zcl.clusters.general import OnOff

from zhaquirks.builder import (
    EntityPlatform,
    EntityType,
    NumberDeviceClass,
    QuirkBuilder,
    SensorDeviceClass,
    SensorStateClass,
    UnitOfElectricPotential,
    UnitOfTime,
)
from zhaquirks.clusters import CustomCluster


class AirwickCtrlCluster(CustomCluster):
    """airwickCtrl (z2m custom cluster)."""

    cluster_id = 0xFC00

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        mode = ZCLAttributeDef(id=0x0000, type=t.enum8, manufacturer_code=None)
        auto_interval_min = ZCLAttributeDef(id=0x0001, type=t.uint16_t, manufacturer_code=None)
        schedule_days = ZCLAttributeDef(id=0x0002, type=t.uint8_t, manufacturer_code=None)
        schedule_start_min = ZCLAttributeDef(id=0x0003, type=t.uint16_t, manufacturer_code=None)
        schedule_end_min = ZCLAttributeDef(id=0x0004, type=t.uint16_t, manufacturer_code=None)
        schedule_interval_min = ZCLAttributeDef(id=0x0005, type=t.uint16_t, manufacturer_code=None)
        timezone_min = ZCLAttributeDef(id=0x0006, type=t.int16s, manufacturer_code=None)
        spray_count = ZCLAttributeDef(id=0x0007, type=t.uint32_t, access="r", manufacturer_code=None)
        last_spray_reason = ZCLAttributeDef(id=0x0008, type=t.uint8_t, access="r", manufacturer_code=None)
        # last_spray_time 0x0009: UTC, attribute only
        # next_spray_time 0x000A: UTC, attribute only
        time_valid = ZCLAttributeDef(id=0x000B, type=t.Bool, access="r", manufacturer_code=None)
        physical_mode = ZCLAttributeDef(id=0x000D, type=t.uint8_t, access="r", manufacturer_code=None)
        reset_counter = ZCLAttributeDef(id=0x000E, type=t.Bool, manufacturer_code=None)
        settings_version = ZCLAttributeDef(id=0x000F, type=t.uint8_t, access="r", manufacturer_code=None)
        sync_time = ZCLAttributeDef(id=0x0010, type=t.uint32_t, manufacturer_code=None)
        battery_mv = ZCLAttributeDef(id=0x0011, type=t.uint16_t, access="r", manufacturer_code=None)
        spray_duration_ms = ZCLAttributeDef(id=0x0012, type=t.uint16_t, manufacturer_code=None)
        program1_enabled = ZCLAttributeDef(id=0x0020, type=t.Bool, manufacturer_code=None)
        program1_days = ZCLAttributeDef(id=0x0021, type=t.uint8_t, manufacturer_code=None)
        program1_start_min = ZCLAttributeDef(id=0x0022, type=t.uint16_t, manufacturer_code=None)
        program1_end_min = ZCLAttributeDef(id=0x0023, type=t.uint16_t, manufacturer_code=None)
        program1_interval_min = ZCLAttributeDef(id=0x0024, type=t.uint16_t, manufacturer_code=None)
        program2_enabled = ZCLAttributeDef(id=0x0028, type=t.Bool, manufacturer_code=None)
        program2_days = ZCLAttributeDef(id=0x0029, type=t.uint8_t, manufacturer_code=None)
        program2_start_min = ZCLAttributeDef(id=0x002A, type=t.uint16_t, manufacturer_code=None)
        program2_end_min = ZCLAttributeDef(id=0x002B, type=t.uint16_t, manufacturer_code=None)
        program2_interval_min = ZCLAttributeDef(id=0x002C, type=t.uint16_t, manufacturer_code=None)
        program3_enabled = ZCLAttributeDef(id=0x0030, type=t.Bool, manufacturer_code=None)
        program3_days = ZCLAttributeDef(id=0x0031, type=t.uint8_t, manufacturer_code=None)
        program3_start_min = ZCLAttributeDef(id=0x0032, type=t.uint16_t, manufacturer_code=None)
        program3_end_min = ZCLAttributeDef(id=0x0033, type=t.uint16_t, manufacturer_code=None)
        program3_interval_min = ZCLAttributeDef(id=0x0034, type=t.uint16_t, manufacturer_code=None)
        program4_enabled = ZCLAttributeDef(id=0x0038, type=t.Bool, manufacturer_code=None)
        program4_days = ZCLAttributeDef(id=0x0039, type=t.uint8_t, manufacturer_code=None)
        program4_start_min = ZCLAttributeDef(id=0x003A, type=t.uint16_t, manufacturer_code=None)
        program4_end_min = ZCLAttributeDef(id=0x003B, type=t.uint16_t, manufacturer_code=None)
        program4_interval_min = ZCLAttributeDef(id=0x003C, type=t.uint16_t, manufacturer_code=None)
        program5_enabled = ZCLAttributeDef(id=0x0040, type=t.Bool, manufacturer_code=None)
        program5_days = ZCLAttributeDef(id=0x0041, type=t.uint8_t, manufacturer_code=None)
        program5_start_min = ZCLAttributeDef(id=0x0042, type=t.uint16_t, manufacturer_code=None)
        program5_end_min = ZCLAttributeDef(id=0x0043, type=t.uint16_t, manufacturer_code=None)
        program5_interval_min = ZCLAttributeDef(id=0x0044, type=t.uint16_t, manufacturer_code=None)
        program6_enabled = ZCLAttributeDef(id=0x0048, type=t.Bool, manufacturer_code=None)
        program6_days = ZCLAttributeDef(id=0x0049, type=t.uint8_t, manufacturer_code=None)
        program6_start_min = ZCLAttributeDef(id=0x004A, type=t.uint16_t, manufacturer_code=None)
        program6_end_min = ZCLAttributeDef(id=0x004B, type=t.uint16_t, manufacturer_code=None)
        program6_interval_min = ZCLAttributeDef(id=0x004C, type=t.uint16_t, manufacturer_code=None)
        program7_enabled = ZCLAttributeDef(id=0x0050, type=t.Bool, manufacturer_code=None)
        program7_days = ZCLAttributeDef(id=0x0051, type=t.uint8_t, manufacturer_code=None)
        program7_start_min = ZCLAttributeDef(id=0x0052, type=t.uint16_t, manufacturer_code=None)
        program7_end_min = ZCLAttributeDef(id=0x0053, type=t.uint16_t, manufacturer_code=None)
        program7_interval_min = ZCLAttributeDef(id=0x0054, type=t.uint16_t, manufacturer_code=None)


class Mode(t.enum8):
    """mode values (z2m)."""

    OFF = 0x00
    AUTO = 0x01
    SCHEDULE = 0x02
    PROGRAMMABLE = 0x03


class LastSprayReason(t.enum8):
    """last_spray_reason values (z2m)."""

    none = 0x00
    Zigbee = 0x01
    Button = 0x02
    AUTO = 0x03
    SCHEDULE = 0x04
    PROGRAM = 0x05


class TimeValid(t.enum8):
    """time_valid values (z2m)."""

    OFF = 0x00
    ON = 0x01



_LOGGER = logging.getLogger(__name__)
_SHIPPED = pathlib.Path(zhaquirks.__file__).resolve().parent
_STEPPED_BACK: set = set()

# The Zigbee fingerprints (manufacturer, model) this quirk is for; None matches any manufacturer.
FINGERPRINTS = [(None, 'AirWick_nRF52840')]
# Names that a model-only fingerprint would catch but Zigbee2MQTT gives to other devices.
CLAIMED_ELSEWHERE = set()
# The endpoints this quirk needs, each with the input clusters it puts there where Zigbee2MQTT names none.
ENDPOINTS = {1: (0x0006, 0xFC00)}


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
    QuirkBuilder(None, 'AirWick_nRF52840')
    .replaces(AirwickCtrlCluster)
    .enum(attribute_name=AirwickCtrlCluster.AttributeDefs.mode.name, cluster_id=AirwickCtrlCluster.cluster_id, enum_class=Mode, entity_platform=EntityPlatform.SENSOR, entity_type=EntityType.STANDARD, translation_key='mode', fallback_name='Mode')
    .sensor(attribute_name=AirwickCtrlCluster.AttributeDefs.battery_mv.name, cluster_id=AirwickCtrlCluster.cluster_id, divisor=1000, state_class=SensorStateClass.MEASUREMENT, device_class=SensorDeviceClass.VOLTAGE, unit=UnitOfElectricPotential.VOLT, entity_type=EntityType.STANDARD, translation_key='battery_v', fallback_name='Battery voltage')
    .number(attribute_name=AirwickCtrlCluster.AttributeDefs.spray_duration_ms.name, cluster_id=AirwickCtrlCluster.cluster_id, min_value=300, max_value=1000, step=10, unit=UnitOfTime.MILLISECONDS, device_class=NumberDeviceClass.DURATION, entity_type=EntityType.STANDARD, translation_key='spray_duration_ms', fallback_name='Spray duration')
    .number(attribute_name=AirwickCtrlCluster.AttributeDefs.auto_interval_min.name, cluster_id=AirwickCtrlCluster.cluster_id, min_value=1, max_value=1440, step=1, unit=UnitOfTime.MINUTES, device_class=NumberDeviceClass.DURATION, entity_type=EntityType.CONFIG, translation_key='auto_interval_min', fallback_name='AUTO: interval')
    .switch(attribute_name=AirwickCtrlCluster.AttributeDefs.program1_enabled.name, cluster_id=AirwickCtrlCluster.cluster_id, entity_type=EntityType.CONFIG, translation_key='program_mon_enabled', fallback_name='PROGRAM — monday: enabled')
    .number(attribute_name=AirwickCtrlCluster.AttributeDefs.program1_interval_min.name, cluster_id=AirwickCtrlCluster.cluster_id, min_value=1, max_value=1440, step=1, unit=UnitOfTime.MINUTES, device_class=NumberDeviceClass.DURATION, entity_type=EntityType.CONFIG, translation_key='program_mon_interval_min', fallback_name='PROGRAM — monday: interval')
    .switch(attribute_name=AirwickCtrlCluster.AttributeDefs.program2_enabled.name, cluster_id=AirwickCtrlCluster.cluster_id, entity_type=EntityType.CONFIG, translation_key='program_tue_enabled', fallback_name='PROGRAM — tuesday: enabled')
    .number(attribute_name=AirwickCtrlCluster.AttributeDefs.program2_interval_min.name, cluster_id=AirwickCtrlCluster.cluster_id, min_value=1, max_value=1440, step=1, unit=UnitOfTime.MINUTES, device_class=NumberDeviceClass.DURATION, entity_type=EntityType.CONFIG, translation_key='program_tue_interval_min', fallback_name='PROGRAM — tuesday: interval')
    .switch(attribute_name=AirwickCtrlCluster.AttributeDefs.program3_enabled.name, cluster_id=AirwickCtrlCluster.cluster_id, entity_type=EntityType.CONFIG, translation_key='program_wed_enabled', fallback_name='PROGRAM — wednesday: enabled')
    .number(attribute_name=AirwickCtrlCluster.AttributeDefs.program3_interval_min.name, cluster_id=AirwickCtrlCluster.cluster_id, min_value=1, max_value=1440, step=1, unit=UnitOfTime.MINUTES, device_class=NumberDeviceClass.DURATION, entity_type=EntityType.CONFIG, translation_key='program_wed_interval_min', fallback_name='PROGRAM — wednesday: interval')
    .switch(attribute_name=AirwickCtrlCluster.AttributeDefs.program4_enabled.name, cluster_id=AirwickCtrlCluster.cluster_id, entity_type=EntityType.CONFIG, translation_key='program_thu_enabled', fallback_name='PROGRAM — thursday: enabled')
    .number(attribute_name=AirwickCtrlCluster.AttributeDefs.program4_interval_min.name, cluster_id=AirwickCtrlCluster.cluster_id, min_value=1, max_value=1440, step=1, unit=UnitOfTime.MINUTES, device_class=NumberDeviceClass.DURATION, entity_type=EntityType.CONFIG, translation_key='program_thu_interval_min', fallback_name='PROGRAM — thursday: interval')
    .switch(attribute_name=AirwickCtrlCluster.AttributeDefs.program5_enabled.name, cluster_id=AirwickCtrlCluster.cluster_id, entity_type=EntityType.CONFIG, translation_key='program_fri_enabled', fallback_name='PROGRAM — friday: enabled')
    .number(attribute_name=AirwickCtrlCluster.AttributeDefs.program5_interval_min.name, cluster_id=AirwickCtrlCluster.cluster_id, min_value=1, max_value=1440, step=1, unit=UnitOfTime.MINUTES, device_class=NumberDeviceClass.DURATION, entity_type=EntityType.CONFIG, translation_key='program_fri_interval_min', fallback_name='PROGRAM — friday: interval')
    .switch(attribute_name=AirwickCtrlCluster.AttributeDefs.program6_enabled.name, cluster_id=AirwickCtrlCluster.cluster_id, entity_type=EntityType.CONFIG, translation_key='program_sat_enabled', fallback_name='PROGRAM — saturday: enabled')
    .number(attribute_name=AirwickCtrlCluster.AttributeDefs.program6_interval_min.name, cluster_id=AirwickCtrlCluster.cluster_id, min_value=1, max_value=1440, step=1, unit=UnitOfTime.MINUTES, device_class=NumberDeviceClass.DURATION, entity_type=EntityType.CONFIG, translation_key='program_sat_interval_min', fallback_name='PROGRAM — saturday: interval')
    .switch(attribute_name=AirwickCtrlCluster.AttributeDefs.program7_enabled.name, cluster_id=AirwickCtrlCluster.cluster_id, entity_type=EntityType.CONFIG, translation_key='program_sun_enabled', fallback_name='PROGRAM — sunday: enabled')
    .number(attribute_name=AirwickCtrlCluster.AttributeDefs.program7_interval_min.name, cluster_id=AirwickCtrlCluster.cluster_id, min_value=1, max_value=1440, step=1, unit=UnitOfTime.MINUTES, device_class=NumberDeviceClass.DURATION, entity_type=EntityType.CONFIG, translation_key='program_sun_interval_min', fallback_name='PROGRAM — sunday: interval')
    .number(attribute_name=AirwickCtrlCluster.AttributeDefs.timezone_min.name, cluster_id=AirwickCtrlCluster.cluster_id, min_value=-12, max_value=14, step=0.5, unit=UnitOfTime.HOURS, multiplier=0.016666666666666666, device_class=NumberDeviceClass.DURATION, entity_type=EntityType.CONFIG, translation_key='timezone_hours', fallback_name='UTC timezone')
    .sensor(attribute_name=AirwickCtrlCluster.AttributeDefs.spray_count.name, cluster_id=AirwickCtrlCluster.cluster_id, entity_type=EntityType.STANDARD, translation_key='spray_count', fallback_name='Spray counter')
    .enum(attribute_name=AirwickCtrlCluster.AttributeDefs.last_spray_reason.name, cluster_id=AirwickCtrlCluster.cluster_id, enum_class=LastSprayReason, entity_platform=EntityPlatform.SENSOR, entity_type=EntityType.DIAGNOSTIC, translation_key='last_spray_reason', fallback_name='Last spray reason')
    .enum(attribute_name=AirwickCtrlCluster.AttributeDefs.time_valid.name, cluster_id=AirwickCtrlCluster.cluster_id, enum_class=TimeValid, entity_platform=EntityPlatform.SENSOR, entity_type=EntityType.DIAGNOSTIC, translation_key='time_valid', fallback_name='Time synchronized')
    .command_button(command_name=OnOff.ServerCommandDefs.on.name, cluster_id=OnOff.cluster_id, entity_type=EntityType.STANDARD, translation_key='spray', fallback_name='Spray', unique_id_suffix='spray')
    # battery: z2m numeric with own fromZigbee converter, not generated
    # program_mon_start: z2m numeric with own fromZigbee converter, not generated
    # program_mon_end: z2m numeric with own fromZigbee converter, not generated
    # program_tue_start: z2m numeric with own fromZigbee converter, not generated
    # program_tue_end: z2m numeric with own fromZigbee converter, not generated
    # program_wed_start: z2m numeric with own fromZigbee converter, not generated
    # program_wed_end: z2m numeric with own fromZigbee converter, not generated
    # program_thu_start: z2m numeric with own fromZigbee converter, not generated
    # program_thu_end: z2m numeric with own fromZigbee converter, not generated
    # program_fri_start: z2m numeric with own fromZigbee converter, not generated
    # program_fri_end: z2m numeric with own fromZigbee converter, not generated
    # program_sat_start: z2m numeric with own fromZigbee converter, not generated
    # program_sat_end: z2m numeric with own fromZigbee converter, not generated
    # program_sun_start: z2m numeric with own fromZigbee converter, not generated
    # program_sun_end: z2m numeric with own fromZigbee converter, not generated
    # last_spray_time: z2m numeric with own fromZigbee converter, not generated
    # next_spray_time: z2m numeric with own fromZigbee converter, not generated
    # reset_counter: z2m's own code, not generated
    .filter(no_builtin_quirk)
    .add_to_registry()
)
