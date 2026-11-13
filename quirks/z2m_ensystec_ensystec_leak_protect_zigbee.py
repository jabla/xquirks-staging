"""Ensystec Ensystec-Leak-Protect-Zigbee: Leak protect controller with Zigbee module.

Generated from the Zigbee2MQTT definition.
Data: zigbee-herdsman-converters, MIT, Copyright (c) 2018 Koen Kanters.
Status: generated, not verified on hardware.
Revision: 104de491
"""

import functools
import logging
import pathlib

import zhaquirks
from zha.quirks import DEVICE_REGISTRY, DeviceMatch
import zigpy.types as t
from zigpy.zcl.foundation import BaseAttributeDefs, BaseCommandDefs, Direction, ZCLAttributeDef, ZCLCommandDef
from zigpy.zcl.clusters.general import Basic
from zigpy.zcl.clusters.general import OnOff

from zhaquirks.builder import (
    EntityPlatform,
    EntityType,
    PERCENTAGE,
    QuirkBuilder,
    SensorStateClass,
)
from zhaquirks.clusters import CustomCluster


class GenOnOffCluster(CustomCluster, OnOff):
    """OnOff with the attributes z2m adds."""

    class AttributeDefs(OnOff.AttributeDefs):
        """Attribute definitions."""

        position_percent = ZCLAttributeDef(id=0x6600, type=t.uint8_t, access="r", manufacturer_code=0x6666)
        electric_valve_connection = ZCLAttributeDef(id=0x6601, type=t.Bool, access="r", manufacturer_code=0x6666)


class EnsystecLeakProtectCluster(CustomCluster):
    """EnsystecLeakProtect (z2m custom cluster)."""

    cluster_id = 0x6604

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        on_line = ZCLAttributeDef(id=0x6601, type=t.Bool, access="r", manufacturer_code=0x6666)
        leak_detect = ZCLAttributeDef(id=0x6602, type=t.Bool, access="r", manufacturer_code=0x6666)
        input_config = ZCLAttributeDef(id=0x6607, type=t.uint8_t, manufacturer_code=0x6666)
        battery_low = ZCLAttributeDef(id=0x6612, type=t.Bool, access="r", manufacturer_code=0x6666)

    class ServerCommandDefs(BaseCommandDefs):
        """Command definitions (z2m's commands this cluster lacks)."""

        reset_alarm = ZCLCommandDef(id=0x00, schema={}, direction=Direction.Client_to_Server, manufacturer_code=0x6666)


class Power(t.enum8):
    """power values (z2m)."""

    unknown = 0x00
    mains_single_phase = 0x01
    mains_3_phase = 0x02
    battery = 0x03


class Input1Config(t.enum8):
    """input_1_config values (z2m)."""

    deactivated = 0x00
    sensor = 0x01
    meter = 0x02


class Input2Config(t.enum8):
    """input_2_config values (z2m)."""

    deactivated = 0x00
    sensor = 0x01
    meter = 0x02


class Input3Config(t.enum8):
    """input_3_config values (z2m)."""

    deactivated = 0x00
    sensor = 0x01
    meter = 0x02


class Input4Config(t.enum8):
    """input_4_config values (z2m)."""

    deactivated = 0x00
    sensor = 0x01
    meter = 0x02


class Input5Config(t.enum8):
    """input_5_config values (z2m)."""

    deactivated = 0x00
    sensor = 0x01
    meter = 0x02


class Input6Config(t.enum8):
    """input_6_config values (z2m)."""

    deactivated = 0x00
    sensor = 0x01
    meter = 0x02


class Input7Config(t.enum8):
    """input_7_config values (z2m)."""

    deactivated = 0x00
    sensor = 0x01
    meter = 0x02


class Input8Config(t.enum8):
    """input_8_config values (z2m)."""

    deactivated = 0x00
    sensor = 0x01
    meter = 0x02


class Input9Config(t.enum8):
    """input_9_config values (z2m)."""

    deactivated = 0x00
    sensor = 0x01
    meter = 0x02


class Input10Config(t.enum8):
    """input_10_config values (z2m)."""

    deactivated = 0x00
    sensor = 0x01
    meter = 0x02



_LOGGER = logging.getLogger(__name__)
_SHIPPED = pathlib.Path(zhaquirks.__file__).resolve().parent
_STEPPED_BACK: set = set()

# The Zigbee fingerprints (manufacturer, model) this quirk is for; None matches any manufacturer.
FINGERPRINTS = [(None, 'Ensystec.ELPC')]
# Names that a model-only fingerprint would catch but Zigbee2MQTT gives to other devices.
CLAIMED_ELSEWHERE = set()
# The endpoints this quirk needs, each with the input clusters it puts there where Zigbee2MQTT names none.
ENDPOINTS = {1: (0x0000, 0x6604), 2: (), 3: (), 7: (), 8: (), 9: (), 10: (), 11: (), 12: (), 13: (), 14: (), 15: (), 16: (), 17: (), 18: (), 19: (), 20: (), 21: (), 22: (), 23: (), 24: (), 25: (), 26: ()}


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
    QuirkBuilder(None, 'Ensystec.ELPC')
    .replaces(EnsystecLeakProtectCluster)
    .replaces(EnsystecLeakProtectCluster, endpoint_id=7)
    .replaces(EnsystecLeakProtectCluster, endpoint_id=8)
    .replaces(EnsystecLeakProtectCluster, endpoint_id=9)
    .replaces(EnsystecLeakProtectCluster, endpoint_id=10)
    .replaces(EnsystecLeakProtectCluster, endpoint_id=11)
    .replaces(EnsystecLeakProtectCluster, endpoint_id=12)
    .replaces(EnsystecLeakProtectCluster, endpoint_id=13)
    .replaces(EnsystecLeakProtectCluster, endpoint_id=14)
    .replaces(EnsystecLeakProtectCluster, endpoint_id=15)
    .replaces(EnsystecLeakProtectCluster, endpoint_id=16)
    .replaces(EnsystecLeakProtectCluster, endpoint_id=17)
    .replaces(EnsystecLeakProtectCluster, endpoint_id=18)
    .replaces(EnsystecLeakProtectCluster, endpoint_id=19)
    .replaces(EnsystecLeakProtectCluster, endpoint_id=20)
    .replaces(EnsystecLeakProtectCluster, endpoint_id=21)
    .replaces(EnsystecLeakProtectCluster, endpoint_id=22)
    .replaces(EnsystecLeakProtectCluster, endpoint_id=23)
    .replaces(EnsystecLeakProtectCluster, endpoint_id=24)
    .replaces(EnsystecLeakProtectCluster, endpoint_id=25)
    .replaces(EnsystecLeakProtectCluster, endpoint_id=26)
    .replaces(GenOnOffCluster, endpoint_id=2)
    .replaces(GenOnOffCluster, endpoint_id=3)
    .binary_sensor(attribute_name=EnsystecLeakProtectCluster.AttributeDefs.battery_low.name, cluster_id=EnsystecLeakProtectCluster.cluster_id, entity_type=EntityType.STANDARD, translation_key='battery_low', fallback_name='Battery low')
    .enum(attribute_name=Basic.AttributeDefs.power_source.name, cluster_id=Basic.cluster_id, enum_class=Power, entity_platform=EntityPlatform.SENSOR, entity_type=EntityType.STANDARD, translation_key='power', fallback_name='Power')
    .sensor(attribute_name=GenOnOffCluster.AttributeDefs.position_percent.name, cluster_id=GenOnOffCluster.cluster_id, endpoint_id=2, state_class=SensorStateClass.MEASUREMENT, unit=PERCENTAGE, entity_type=EntityType.STANDARD, translation_key='position_percent_2', fallback_name='Position percent 2')
    .binary_sensor(attribute_name=GenOnOffCluster.AttributeDefs.electric_valve_connection.name, cluster_id=GenOnOffCluster.cluster_id, endpoint_id=2, entity_type=EntityType.STANDARD, translation_key='electric_valve_connection_out1', fallback_name='Electric valve connection out1')
    .sensor(attribute_name=GenOnOffCluster.AttributeDefs.position_percent.name, cluster_id=GenOnOffCluster.cluster_id, endpoint_id=3, state_class=SensorStateClass.MEASUREMENT, unit=PERCENTAGE, entity_type=EntityType.STANDARD, translation_key='position_percent_3', fallback_name='Position percent 3')
    .binary_sensor(attribute_name=GenOnOffCluster.AttributeDefs.electric_valve_connection.name, cluster_id=GenOnOffCluster.cluster_id, endpoint_id=3, entity_type=EntityType.STANDARD, translation_key='electric_valve_connection_out2', fallback_name='Electric valve connection out2')
    .enum(attribute_name=EnsystecLeakProtectCluster.AttributeDefs.input_config.name, cluster_id=EnsystecLeakProtectCluster.cluster_id, endpoint_id=7, enum_class=Input1Config, entity_type=EntityType.STANDARD, translation_key='input_1_config', fallback_name='Input 1 config')
    .enum(attribute_name=EnsystecLeakProtectCluster.AttributeDefs.input_config.name, cluster_id=EnsystecLeakProtectCluster.cluster_id, endpoint_id=8, enum_class=Input2Config, entity_type=EntityType.STANDARD, translation_key='input_2_config', fallback_name='Input 2 config')
    .enum(attribute_name=EnsystecLeakProtectCluster.AttributeDefs.input_config.name, cluster_id=EnsystecLeakProtectCluster.cluster_id, endpoint_id=9, enum_class=Input3Config, entity_type=EntityType.STANDARD, translation_key='input_3_config', fallback_name='Input 3 config')
    .enum(attribute_name=EnsystecLeakProtectCluster.AttributeDefs.input_config.name, cluster_id=EnsystecLeakProtectCluster.cluster_id, endpoint_id=10, enum_class=Input4Config, entity_type=EntityType.STANDARD, translation_key='input_4_config', fallback_name='Input 4 config')
    .enum(attribute_name=EnsystecLeakProtectCluster.AttributeDefs.input_config.name, cluster_id=EnsystecLeakProtectCluster.cluster_id, endpoint_id=11, enum_class=Input5Config, entity_type=EntityType.STANDARD, translation_key='input_5_config', fallback_name='Input 5 config')
    .enum(attribute_name=EnsystecLeakProtectCluster.AttributeDefs.input_config.name, cluster_id=EnsystecLeakProtectCluster.cluster_id, endpoint_id=12, enum_class=Input6Config, entity_type=EntityType.STANDARD, translation_key='input_6_config', fallback_name='Input 6 config')
    .enum(attribute_name=EnsystecLeakProtectCluster.AttributeDefs.input_config.name, cluster_id=EnsystecLeakProtectCluster.cluster_id, endpoint_id=13, enum_class=Input7Config, entity_type=EntityType.STANDARD, translation_key='input_7_config', fallback_name='Input 7 config')
    .enum(attribute_name=EnsystecLeakProtectCluster.AttributeDefs.input_config.name, cluster_id=EnsystecLeakProtectCluster.cluster_id, endpoint_id=14, enum_class=Input8Config, entity_type=EntityType.STANDARD, translation_key='input_8_config', fallback_name='Input 8 config')
    .enum(attribute_name=EnsystecLeakProtectCluster.AttributeDefs.input_config.name, cluster_id=EnsystecLeakProtectCluster.cluster_id, endpoint_id=15, enum_class=Input9Config, entity_type=EntityType.STANDARD, translation_key='input_9_config', fallback_name='Input 9 config')
    .enum(attribute_name=EnsystecLeakProtectCluster.AttributeDefs.input_config.name, cluster_id=EnsystecLeakProtectCluster.cluster_id, endpoint_id=16, enum_class=Input10Config, entity_type=EntityType.STANDARD, translation_key='input_10_config', fallback_name='Input 10 config')
    .binary_sensor(attribute_name=EnsystecLeakProtectCluster.AttributeDefs.leak_detect.name, cluster_id=EnsystecLeakProtectCluster.cluster_id, endpoint_id=7, entity_type=EntityType.STANDARD, translation_key='input_1_leak_detect', fallback_name='Input 1 leak detect')
    .binary_sensor(attribute_name=EnsystecLeakProtectCluster.AttributeDefs.leak_detect.name, cluster_id=EnsystecLeakProtectCluster.cluster_id, endpoint_id=8, entity_type=EntityType.STANDARD, translation_key='input_2_leak_detect', fallback_name='Input 2 leak detect')
    .binary_sensor(attribute_name=EnsystecLeakProtectCluster.AttributeDefs.leak_detect.name, cluster_id=EnsystecLeakProtectCluster.cluster_id, endpoint_id=9, entity_type=EntityType.STANDARD, translation_key='input_3_leak_detect', fallback_name='Input 3 leak detect')
    .binary_sensor(attribute_name=EnsystecLeakProtectCluster.AttributeDefs.leak_detect.name, cluster_id=EnsystecLeakProtectCluster.cluster_id, endpoint_id=10, entity_type=EntityType.STANDARD, translation_key='input_4_leak_detect', fallback_name='Input 4 leak detect')
    .binary_sensor(attribute_name=EnsystecLeakProtectCluster.AttributeDefs.leak_detect.name, cluster_id=EnsystecLeakProtectCluster.cluster_id, endpoint_id=11, entity_type=EntityType.STANDARD, translation_key='input_5_leak_detect', fallback_name='Input 5 leak detect')
    .binary_sensor(attribute_name=EnsystecLeakProtectCluster.AttributeDefs.leak_detect.name, cluster_id=EnsystecLeakProtectCluster.cluster_id, endpoint_id=12, entity_type=EntityType.STANDARD, translation_key='input_6_leak_detect', fallback_name='Input 6 leak detect')
    .binary_sensor(attribute_name=EnsystecLeakProtectCluster.AttributeDefs.leak_detect.name, cluster_id=EnsystecLeakProtectCluster.cluster_id, endpoint_id=13, entity_type=EntityType.STANDARD, translation_key='input_7_leak_detect', fallback_name='Input 7 leak detect')
    .binary_sensor(attribute_name=EnsystecLeakProtectCluster.AttributeDefs.leak_detect.name, cluster_id=EnsystecLeakProtectCluster.cluster_id, endpoint_id=14, entity_type=EntityType.STANDARD, translation_key='input_8_leak_detect', fallback_name='Input 8 leak detect')
    .binary_sensor(attribute_name=EnsystecLeakProtectCluster.AttributeDefs.leak_detect.name, cluster_id=EnsystecLeakProtectCluster.cluster_id, endpoint_id=15, entity_type=EntityType.STANDARD, translation_key='input_9_leak_detect', fallback_name='Input 9 leak detect')
    .binary_sensor(attribute_name=EnsystecLeakProtectCluster.AttributeDefs.leak_detect.name, cluster_id=EnsystecLeakProtectCluster.cluster_id, endpoint_id=16, entity_type=EntityType.STANDARD, translation_key='input_10_leak_detect', fallback_name='Input 10 leak detect')
    .binary_sensor(attribute_name=EnsystecLeakProtectCluster.AttributeDefs.on_line.name, cluster_id=EnsystecLeakProtectCluster.cluster_id, endpoint_id=7, entity_type=EntityType.STANDARD, translation_key='input_1_wire_break_control', fallback_name='Input 1 wire break control')
    .binary_sensor(attribute_name=EnsystecLeakProtectCluster.AttributeDefs.on_line.name, cluster_id=EnsystecLeakProtectCluster.cluster_id, endpoint_id=8, entity_type=EntityType.STANDARD, translation_key='input_2_wire_break_control', fallback_name='Input 2 wire break control')
    .binary_sensor(attribute_name=EnsystecLeakProtectCluster.AttributeDefs.on_line.name, cluster_id=EnsystecLeakProtectCluster.cluster_id, endpoint_id=9, entity_type=EntityType.STANDARD, translation_key='input_3_wire_break_control', fallback_name='Input 3 wire break control')
    .binary_sensor(attribute_name=EnsystecLeakProtectCluster.AttributeDefs.on_line.name, cluster_id=EnsystecLeakProtectCluster.cluster_id, endpoint_id=10, entity_type=EntityType.STANDARD, translation_key='input_4_wire_break_control', fallback_name='Input 4 wire break control')
    .binary_sensor(attribute_name=EnsystecLeakProtectCluster.AttributeDefs.on_line.name, cluster_id=EnsystecLeakProtectCluster.cluster_id, endpoint_id=11, entity_type=EntityType.STANDARD, translation_key='input_5_wire_break_control', fallback_name='Input 5 wire break control')
    .binary_sensor(attribute_name=EnsystecLeakProtectCluster.AttributeDefs.on_line.name, cluster_id=EnsystecLeakProtectCluster.cluster_id, endpoint_id=12, entity_type=EntityType.STANDARD, translation_key='input_6_wire_break_control', fallback_name='Input 6 wire break control')
    .binary_sensor(attribute_name=EnsystecLeakProtectCluster.AttributeDefs.on_line.name, cluster_id=EnsystecLeakProtectCluster.cluster_id, endpoint_id=13, entity_type=EntityType.STANDARD, translation_key='input_7_wire_break_control', fallback_name='Input 7 wire break control')
    .binary_sensor(attribute_name=EnsystecLeakProtectCluster.AttributeDefs.on_line.name, cluster_id=EnsystecLeakProtectCluster.cluster_id, endpoint_id=14, entity_type=EntityType.STANDARD, translation_key='input_8_wire_break_control', fallback_name='Input 8 wire break control')
    .binary_sensor(attribute_name=EnsystecLeakProtectCluster.AttributeDefs.on_line.name, cluster_id=EnsystecLeakProtectCluster.cluster_id, endpoint_id=15, entity_type=EntityType.STANDARD, translation_key='input_9_wire_break_control', fallback_name='Input 9 wire break control')
    .binary_sensor(attribute_name=EnsystecLeakProtectCluster.AttributeDefs.on_line.name, cluster_id=EnsystecLeakProtectCluster.cluster_id, endpoint_id=16, entity_type=EntityType.STANDARD, translation_key='input_10_wire_break_control', fallback_name='Input 10 wire break control')
    .binary_sensor(attribute_name=EnsystecLeakProtectCluster.AttributeDefs.on_line.name, cluster_id=EnsystecLeakProtectCluster.cluster_id, endpoint_id=17, entity_type=EntityType.STANDARD, translation_key='channel_1_connection_control', fallback_name='Channel 1 connection control')
    .binary_sensor(attribute_name=EnsystecLeakProtectCluster.AttributeDefs.on_line.name, cluster_id=EnsystecLeakProtectCluster.cluster_id, endpoint_id=18, entity_type=EntityType.STANDARD, translation_key='channel_2_connection_control', fallback_name='Channel 2 connection control')
    .binary_sensor(attribute_name=EnsystecLeakProtectCluster.AttributeDefs.on_line.name, cluster_id=EnsystecLeakProtectCluster.cluster_id, endpoint_id=19, entity_type=EntityType.STANDARD, translation_key='channel_3_connection_control', fallback_name='Channel 3 connection control')
    .binary_sensor(attribute_name=EnsystecLeakProtectCluster.AttributeDefs.on_line.name, cluster_id=EnsystecLeakProtectCluster.cluster_id, endpoint_id=20, entity_type=EntityType.STANDARD, translation_key='channel_4_connection_control', fallback_name='Channel 4 connection control')
    .binary_sensor(attribute_name=EnsystecLeakProtectCluster.AttributeDefs.on_line.name, cluster_id=EnsystecLeakProtectCluster.cluster_id, endpoint_id=21, entity_type=EntityType.STANDARD, translation_key='channel_5_connection_control', fallback_name='Channel 5 connection control')
    .binary_sensor(attribute_name=EnsystecLeakProtectCluster.AttributeDefs.on_line.name, cluster_id=EnsystecLeakProtectCluster.cluster_id, endpoint_id=22, entity_type=EntityType.STANDARD, translation_key='channel_6_connection_control', fallback_name='Channel 6 connection control')
    .binary_sensor(attribute_name=EnsystecLeakProtectCluster.AttributeDefs.on_line.name, cluster_id=EnsystecLeakProtectCluster.cluster_id, endpoint_id=23, entity_type=EntityType.STANDARD, translation_key='channel_7_connection_control', fallback_name='Channel 7 connection control')
    .binary_sensor(attribute_name=EnsystecLeakProtectCluster.AttributeDefs.on_line.name, cluster_id=EnsystecLeakProtectCluster.cluster_id, endpoint_id=24, entity_type=EntityType.STANDARD, translation_key='channel_8_connection_control', fallback_name='Channel 8 connection control')
    .binary_sensor(attribute_name=EnsystecLeakProtectCluster.AttributeDefs.on_line.name, cluster_id=EnsystecLeakProtectCluster.cluster_id, endpoint_id=25, entity_type=EntityType.STANDARD, translation_key='channel_9_connection_control', fallback_name='Channel 9 connection control')
    .binary_sensor(attribute_name=EnsystecLeakProtectCluster.AttributeDefs.on_line.name, cluster_id=EnsystecLeakProtectCluster.cluster_id, endpoint_id=26, entity_type=EntityType.STANDARD, translation_key='channel_10_connection_control', fallback_name='Channel 10 connection control')
    .binary_sensor(attribute_name=EnsystecLeakProtectCluster.AttributeDefs.leak_detect.name, cluster_id=EnsystecLeakProtectCluster.cluster_id, endpoint_id=17, entity_type=EntityType.STANDARD, translation_key='channel_1_leak_detect', fallback_name='Channel 1 leak detect')
    .binary_sensor(attribute_name=EnsystecLeakProtectCluster.AttributeDefs.leak_detect.name, cluster_id=EnsystecLeakProtectCluster.cluster_id, endpoint_id=18, entity_type=EntityType.STANDARD, translation_key='channel_2_leak_detect', fallback_name='Channel 2 leak detect')
    .binary_sensor(attribute_name=EnsystecLeakProtectCluster.AttributeDefs.leak_detect.name, cluster_id=EnsystecLeakProtectCluster.cluster_id, endpoint_id=19, entity_type=EntityType.STANDARD, translation_key='channel_3_leak_detect', fallback_name='Channel 3 leak detect')
    .binary_sensor(attribute_name=EnsystecLeakProtectCluster.AttributeDefs.leak_detect.name, cluster_id=EnsystecLeakProtectCluster.cluster_id, endpoint_id=20, entity_type=EntityType.STANDARD, translation_key='channel_4_leak_detect', fallback_name='Channel 4 leak detect')
    .binary_sensor(attribute_name=EnsystecLeakProtectCluster.AttributeDefs.leak_detect.name, cluster_id=EnsystecLeakProtectCluster.cluster_id, endpoint_id=21, entity_type=EntityType.STANDARD, translation_key='channel_5_leak_detect', fallback_name='Channel 5 leak detect')
    .binary_sensor(attribute_name=EnsystecLeakProtectCluster.AttributeDefs.leak_detect.name, cluster_id=EnsystecLeakProtectCluster.cluster_id, endpoint_id=22, entity_type=EntityType.STANDARD, translation_key='channel_6_leak_detect', fallback_name='Channel 6 leak detect')
    .binary_sensor(attribute_name=EnsystecLeakProtectCluster.AttributeDefs.leak_detect.name, cluster_id=EnsystecLeakProtectCluster.cluster_id, endpoint_id=23, entity_type=EntityType.STANDARD, translation_key='channel_7_leak_detect', fallback_name='Channel 7 leak detect')
    .binary_sensor(attribute_name=EnsystecLeakProtectCluster.AttributeDefs.leak_detect.name, cluster_id=EnsystecLeakProtectCluster.cluster_id, endpoint_id=24, entity_type=EntityType.STANDARD, translation_key='channel_8_leak_detect', fallback_name='Channel 8 leak detect')
    .binary_sensor(attribute_name=EnsystecLeakProtectCluster.AttributeDefs.leak_detect.name, cluster_id=EnsystecLeakProtectCluster.cluster_id, endpoint_id=25, entity_type=EntityType.STANDARD, translation_key='channel_9_leak_detect', fallback_name='Channel 9 leak detect')
    .binary_sensor(attribute_name=EnsystecLeakProtectCluster.AttributeDefs.leak_detect.name, cluster_id=EnsystecLeakProtectCluster.cluster_id, endpoint_id=26, entity_type=EntityType.STANDARD, translation_key='channel_10_leak_detect', fallback_name='Channel 10 leak detect')
    .binary_sensor(attribute_name=EnsystecLeakProtectCluster.AttributeDefs.battery_low.name, cluster_id=EnsystecLeakProtectCluster.cluster_id, endpoint_id=17, entity_type=EntityType.STANDARD, translation_key='channel_1_battery_low', fallback_name='Channel 1 battery low')
    .binary_sensor(attribute_name=EnsystecLeakProtectCluster.AttributeDefs.battery_low.name, cluster_id=EnsystecLeakProtectCluster.cluster_id, endpoint_id=18, entity_type=EntityType.STANDARD, translation_key='channel_2_battery_low', fallback_name='Channel 2 battery low')
    .binary_sensor(attribute_name=EnsystecLeakProtectCluster.AttributeDefs.battery_low.name, cluster_id=EnsystecLeakProtectCluster.cluster_id, endpoint_id=19, entity_type=EntityType.STANDARD, translation_key='channel_3_battery_low', fallback_name='Channel 3 battery low')
    .binary_sensor(attribute_name=EnsystecLeakProtectCluster.AttributeDefs.battery_low.name, cluster_id=EnsystecLeakProtectCluster.cluster_id, endpoint_id=20, entity_type=EntityType.STANDARD, translation_key='channel_4_battery_low', fallback_name='Channel 4 battery low')
    .binary_sensor(attribute_name=EnsystecLeakProtectCluster.AttributeDefs.battery_low.name, cluster_id=EnsystecLeakProtectCluster.cluster_id, endpoint_id=21, entity_type=EntityType.STANDARD, translation_key='channel_5_battery_low', fallback_name='Channel 5 battery low')
    .binary_sensor(attribute_name=EnsystecLeakProtectCluster.AttributeDefs.battery_low.name, cluster_id=EnsystecLeakProtectCluster.cluster_id, endpoint_id=22, entity_type=EntityType.STANDARD, translation_key='channel_6_battery_low', fallback_name='Channel 6 battery low')
    .binary_sensor(attribute_name=EnsystecLeakProtectCluster.AttributeDefs.battery_low.name, cluster_id=EnsystecLeakProtectCluster.cluster_id, endpoint_id=23, entity_type=EntityType.STANDARD, translation_key='channel_7_battery_low', fallback_name='Channel 7 battery low')
    .binary_sensor(attribute_name=EnsystecLeakProtectCluster.AttributeDefs.battery_low.name, cluster_id=EnsystecLeakProtectCluster.cluster_id, endpoint_id=24, entity_type=EntityType.STANDARD, translation_key='channel_8_battery_low', fallback_name='Channel 8 battery low')
    .binary_sensor(attribute_name=EnsystecLeakProtectCluster.AttributeDefs.battery_low.name, cluster_id=EnsystecLeakProtectCluster.cluster_id, endpoint_id=25, entity_type=EntityType.STANDARD, translation_key='channel_9_battery_low', fallback_name='Channel 9 battery low')
    .binary_sensor(attribute_name=EnsystecLeakProtectCluster.AttributeDefs.battery_low.name, cluster_id=EnsystecLeakProtectCluster.cluster_id, endpoint_id=26, entity_type=EntityType.STANDARD, translation_key='channel_10_battery_low', fallback_name='Channel 10 battery low')
    .command_button(command_name=EnsystecLeakProtectCluster.ServerCommandDefs.reset_alarm.name, cluster_id=EnsystecLeakProtectCluster.cluster_id, entity_type=EntityType.STANDARD, translation_key='alarm_reset', fallback_name='Alarm reset', unique_id_suffix='alarm_reset')
    # switch: standard clusters, ZHA's own entities
    # water_leak: standard clusters, ZHA's own entities
    # force_open_6: z2m's own code, not generated
    # input_1_water_meter_7: standard clusters or z2m's own code, not generated
    # input_1_divisor_7: standard clusters or z2m's own code, not generated
    # input_1_multiplier_7: standard clusters or z2m's own code, not generated
    # input_2_water_meter_8: standard clusters or z2m's own code, not generated
    # input_2_divisor_8: standard clusters or z2m's own code, not generated
    # input_2_multiplier_8: standard clusters or z2m's own code, not generated
    # input_3_water_meter_9: standard clusters or z2m's own code, not generated
    # input_3_divisor_9: standard clusters or z2m's own code, not generated
    # input_3_multiplier_9: standard clusters or z2m's own code, not generated
    # input_4_water_meter_10: standard clusters or z2m's own code, not generated
    # input_4_divisor_10: standard clusters or z2m's own code, not generated
    # input_4_multiplier_10: standard clusters or z2m's own code, not generated
    # input_5_water_meter_11: standard clusters or z2m's own code, not generated
    # input_5_divisor_11: standard clusters or z2m's own code, not generated
    # input_5_multiplier_11: standard clusters or z2m's own code, not generated
    # input_6_water_meter_12: standard clusters or z2m's own code, not generated
    # input_6_divisor_12: standard clusters or z2m's own code, not generated
    # input_6_multiplier_12: standard clusters or z2m's own code, not generated
    # input_7_water_meter_13: standard clusters or z2m's own code, not generated
    # input_7_divisor_13: standard clusters or z2m's own code, not generated
    # input_7_multiplier_13: standard clusters or z2m's own code, not generated
    # input_8_water_meter_14: standard clusters or z2m's own code, not generated
    # input_8_divisor_14: standard clusters or z2m's own code, not generated
    # input_8_multiplier_14: standard clusters or z2m's own code, not generated
    # input_9_water_meter_15: standard clusters or z2m's own code, not generated
    # input_9_divisor_15: standard clusters or z2m's own code, not generated
    # input_9_multiplier_15: standard clusters or z2m's own code, not generated
    # input_10_water_meter_16: standard clusters or z2m's own code, not generated
    # input_10_divisor_16: standard clusters or z2m's own code, not generated
    # input_10_multiplier_16: standard clusters or z2m's own code, not generated
    # switch: standard clusters, ZHA's own entities
    # switch: standard clusters, ZHA's own entities
    .filter(no_builtin_quirk)
    .add_to_registry()
)
