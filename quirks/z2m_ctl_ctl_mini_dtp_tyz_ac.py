"""CTL CTL-Mini-DTP-TYZ/AC: Radar and PIR dual-technology presence sensor.

Generated from the Zigbee2MQTT definition.
Data: zigbee-herdsman-converters, MIT, Copyright (c) 2018 Koen Kanters.
Status: generated, not verified on hardware.
Revision: 150d0b6c
"""

import functools
import logging
import pathlib

import zhaquirks
from zha.quirks import DEVICE_REGISTRY, DeviceMatch
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.measurement import OccupancySensing

from zhaquirks.builder import (
    EntityPlatform,
    EntityType,
    LIGHT_LUX,
    NumberDeviceClass,
    UnitOfLength,
    UnitOfTime,
)
from zhaquirks.tuya import TUYA_CLUSTER_ID
from zhaquirks.tuya.builder import TuyaQuirkBuilder
from zhaquirks.tuya.tuya_motion import TuyaOccupancySensing


class LightLinkageValue(t.enum8):
    """light_linkage wire values (z2m)."""

    on = 0x00
    off = 0x01


class IlluminanceLinkageValue(t.enum8):
    """illuminance_linkage wire values (z2m)."""

    on = 0x00
    off = 0x01


class BreathingIndicatorValue(t.enum8):
    """breathing_indicator wire values (z2m)."""

    on = 0x00
    off = 0x01


class DetectionMethod(t.enum8):
    """detection_method values (z2m)."""

    presence = 0x00
    motion = 0x01


class Sensitivity(t.enum8):
    """sensitivity values (z2m)."""

    LL = 0x00
    L = 0x01
    M = 0x02
    H = 0x03
    HH = 0x04


class ProgramFunction(t.enum8):
    """program_function values (z2m)."""

    null = 0x00
    no_one_1min = 0x01
    no_one_3min = 0x02
    no_one_5min = 0x03
    no_one_10min = 0x04
    no_one_15min = 0x05
    no_one_30min = 0x06
    no_one_1hour = 0x07
    no_one_2hour = 0x08
    no_one_4hour = 0x09
    no_one_8hour = 0x0A
    no_one_12hour = 0x0B
    no_one_24hour = 0x0C
    presence_1min = 0x0D
    presence_3min = 0x0E
    presence_5min = 0x0F
    presence_10min = 0x10
    presence_15min = 0x11
    presence_30min = 0x12
    presence_1hour = 0x13
    presence_2hour = 0x14
    presence_4hour = 0x15
    presence_8hour = 0x16
    presence_12hour = 0x17
    presence_24hour = 0x18


class InstallationMode(t.enum8):
    """installation_mode values (z2m)."""

    ceiling = 0x00
    wall = 0x01


class EnvironmentLearning(t.enum8):
    """environment_learning values (z2m)."""

    none = 0x00
    light = 0x01
    medium = 0x02
    deep = 0x03
    disable = 0x04


class ManualAnnotation(t.enum8):
    """manual_annotation values (z2m)."""

    null = 0x00
    no_one_last_1h = 0x01
    no_one_last_2h = 0x02
    no_one_last_4h = 0x03
    no_one_last_8h = 0x04
    no_one_last_12h = 0x05
    no_one_last_24h = 0x06


class SensorPower(t.enum8):
    """sensor_power values (z2m)."""

    on = 0x00
    off = 0x01
    off_10s_restart = 0x02
    off_30s_restart = 0x03
    off_60s_restart = 0x04
    pause_upload = 0x05
    pause_upload_10s = 0x06
    pause_upload_30s = 0x07
    pause_upload_60s = 0x08
    pause_upload_3min = 0x09
    pause_upload_5min = 0x0A
    pause_upload_10min = 0x0B
    pause_upload_15min = 0x0C
    pause_upload_30min = 0x0D
    pause_upload_1hour = 0x0E


class SystemSetting(t.enum8):
    """system_setting values (z2m)."""

    none = 0x00
    identify_start = 0x01
    identify_stop = 0x02
    check_start = 0x03
    check_stop = 0x04
    restore_factory = 0x05
    state_flip_report = 0x06



_LOGGER = logging.getLogger(__name__)
_SHIPPED = pathlib.Path(zhaquirks.__file__).resolve().parent
_STEPPED_BACK: set = set()

# The Zigbee fingerprints (manufacturer, model) this quirk is for; None matches any manufacturer.
FINGERPRINTS = [('_TZE284_5qfrnbqs', 'TS0601')]
# Names that a model-only fingerprint would catch but Zigbee2MQTT gives to other devices.
CLAIMED_ELSEWHERE = set()
# The endpoints this quirk needs, each with the input clusters it puts there where Zigbee2MQTT names none.
ENDPOINTS = {1: (0xEF00,)}


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
    TuyaQuirkBuilder()
    .applies_to('_TZE284_5qfrnbqs', 'TS0601')
    .tuya_dp(dp_id=1, ep_attribute=TuyaOccupancySensing.ep_attribute, attribute_name=OccupancySensing.AttributeDefs.occupancy.name, converter=lambda x: x == 1)
    .adds(TuyaOccupancySensing)
    .tuya_illuminance(dp_id=101)
    .tuya_number(dp_id=102, type=t.uint32_t, attribute_name='illuminance_threshold_high', min_value=0, max_value=2000, step=1, unit=LIGHT_LUX, device_class=NumberDeviceClass.ILLUMINANCE, entity_type=EntityType.CONFIG, translation_key='illuminance_threshold_high', fallback_name='Illuminance high threshold')
    .tuya_number(dp_id=103, type=t.uint32_t, attribute_name='illuminance_threshold_low', min_value=0, max_value=1000, step=1, unit=LIGHT_LUX, device_class=NumberDeviceClass.ILLUMINANCE, entity_type=EntityType.CONFIG, translation_key='illuminance_threshold_low', fallback_name='Illuminance low threshold')
    .tuya_number(dp_id=104, type=t.uint32_t, attribute_name='presence_timeout', min_value=5, max_value=3600, step=1, unit=UnitOfTime.SECONDS, device_class=NumberDeviceClass.DURATION, entity_type=EntityType.CONFIG, translation_key='no_presence_delay', fallback_name='No-presence delay')
    .tuya_switch(dp_id=105, attribute_name='light_switch', entity_type=EntityType.STANDARD, translation_key='z2m_light_state', fallback_name='Light state')
    .tuya_dp_attribute(dp_id=106, attribute_name='light_linkage', type=t.Bool, access=foundation.ZCLAttributeAccess.Read | foundation.ZCLAttributeAccess.Write, converter=lambda x: x == 0, dp_converter=lambda x: LightLinkageValue.on if x else LightLinkageValue.off)
    .switch(attribute_name='light_linkage', cluster_id=TUYA_CLUSTER_ID, entity_type=EntityType.CONFIG, translation_key='light_linkage', fallback_name='Light linkage')
    .tuya_dp_attribute(dp_id=107, attribute_name='illuminance_linkage', type=t.Bool, access=foundation.ZCLAttributeAccess.Read | foundation.ZCLAttributeAccess.Write, converter=lambda x: x == 0, dp_converter=lambda x: IlluminanceLinkageValue.on if x else IlluminanceLinkageValue.off)
    .switch(attribute_name='illuminance_linkage', cluster_id=TUYA_CLUSTER_ID, entity_type=EntityType.CONFIG, translation_key='illuminance_linkage', fallback_name='Illuminance linkage')
    .tuya_dp_attribute(dp_id=108, attribute_name='breathing_indicator', type=t.Bool, access=foundation.ZCLAttributeAccess.Read | foundation.ZCLAttributeAccess.Write, converter=lambda x: x == 0, dp_converter=lambda x: BreathingIndicatorValue.on if x else BreathingIndicatorValue.off)
    .switch(attribute_name='breathing_indicator', cluster_id=TUYA_CLUSTER_ID, entity_type=EntityType.CONFIG, translation_key='breathing_indicator', fallback_name='Presence breathing indicator')
    .tuya_enum(dp_id=109, attribute_name='detection_method', enum_class=DetectionMethod, entity_type=EntityType.CONFIG, translation_key='detection_method', fallback_name='Detection method')
    .tuya_enum(dp_id=110, attribute_name='sensitivity', enum_class=Sensitivity, entity_type=EntityType.CONFIG, translation_key='sensitivity', fallback_name='Sensitivity')
    .tuya_dp_attribute(dp_id=111, attribute_name='program_function', type=ProgramFunction, access=foundation.ZCLAttributeAccess.Read | foundation.ZCLAttributeAccess.Report, converter=lambda x: ProgramFunction(int(x)))
    .enum(attribute_name='program_function', enum_class=ProgramFunction, cluster_id=TUYA_CLUSTER_ID, entity_platform=EntityPlatform.SENSOR, entity_type=EntityType.DIAGNOSTIC, translation_key='program_function', fallback_name='Available program function')
    .tuya_enum(dp_id=112, attribute_name='installation_mode', enum_class=InstallationMode, entity_type=EntityType.CONFIG, translation_key='installation_mode', fallback_name='Installation mode')
    .tuya_number(dp_id=113, type=t.uint32_t, attribute_name='installation_height', min_value=2, max_value=3.2, step=0.1, unit=UnitOfLength.METERS, multiplier=0.1, device_class=NumberDeviceClass.DISTANCE, entity_type=EntityType.CONFIG, translation_key='z2m_installation_height', fallback_name='Installation height')
    .tuya_number(dp_id=114, type=t.uint32_t, attribute_name='detection_radius', min_value=1, max_value=5, step=0.1, unit=UnitOfLength.METERS, multiplier=0.1, device_class=NumberDeviceClass.DISTANCE, entity_type=EntityType.CONFIG, translation_key='detection_radius', fallback_name='Ceiling detection radius')
    .tuya_enum(dp_id=115, attribute_name='environment_learning', enum_class=EnvironmentLearning, entity_type=EntityType.CONFIG, translation_key='environment_learning', fallback_name='Environment learning')
    .tuya_enum(dp_id=116, attribute_name='manual_annotation', enum_class=ManualAnnotation, entity_type=EntityType.CONFIG, translation_key='manual_annotation', fallback_name='Manual annotation')
    .tuya_enum(dp_id=117, attribute_name='sensor_power', enum_class=SensorPower, entity_type=EntityType.CONFIG, translation_key='sensor_power', fallback_name='Sensor power control')
    .tuya_enum(dp_id=118, attribute_name='system_setting', enum_class=SystemSetting, entity_type=EntityType.CONFIG, translation_key='system_setting', fallback_name='System setting')
    .tuya_sensor(dp_id=119, attribute_name='system_info', type=t.CharacterString, converter=lambda x: str(x), entity_type=EntityType.DIAGNOSTIC, translation_key='system_info', fallback_name='System information')
    .tuya_number(dp_id=120, type=t.uint32_t, attribute_name='detection_range', min_value=1, max_value=8, step=0.1, unit=UnitOfLength.METERS, multiplier=0.1, device_class=NumberDeviceClass.DISTANCE, entity_type=EntityType.CONFIG, translation_key='z2m_wall_detection_distance', fallback_name='Wall detection distance')
    .skip_configuration()
    .filter(no_builtin_quirk)
    .add_to_registry()
)
