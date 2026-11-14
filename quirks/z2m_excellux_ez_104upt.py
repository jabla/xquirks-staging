"""Excellux EZ-104UPT: 4-in-1 Environmental sensor.

Generated from the Zigbee2MQTT definition.
Data: zigbee-herdsman-converters, MIT, Copyright (c) 2018 Koen Kanters.
Status: generated, not verified on hardware.
Revision: 564c0c9d
"""

import functools
import logging
import pathlib

import zhaquirks
from zha.quirks import DEVICE_REGISTRY, DeviceMatch
import zigpy.types as t
from zigpy.zcl import foundation

from zhaquirks.builder import (
    EntityPlatform,
    EntityType,
    LIGHT_LUX,
    NumberDeviceClass,
    SensorDeviceClass,
    SensorStateClass,
    UnitOfElectricPotential,
    UnitOfPressure,
    UnitOfTemperature,
    UnitOfTime,
)
from zhaquirks.tuya import TUYA_CLUSTER_ID
from zhaquirks.tuya.builder import TuyaQuirkBuilder


class IlluminanceWarning(t.enum8):
    """illuminance_warning values (z2m)."""

    none = 0x00
    low = 0x01
    high = 0x02


class UvWarning(t.enum8):
    """uv_warning values (z2m)."""

    Low = 0x00
    Moderate = 0x01
    High = 0x02
    Very_High = 0x03
    Extreme = 0x04


class TemperatureWarning(t.enum8):
    """temperature_warning values (z2m)."""

    none = 0x00
    low = 0x01
    high = 0x02


class PressureWarn(t.enum8):
    """pressure_warn values (z2m)."""

    none = 0x00
    low = 0x01
    high = 0x02


class PressureTend(t.enum8):
    """pressure_tend values (z2m)."""

    normal = 0x00
    rise = 0x01
    fall = 0x02



_LOGGER = logging.getLogger(__name__)
_SHIPPED = pathlib.Path(zhaquirks.__file__).resolve().parent
_STEPPED_BACK: set = set()

# The Zigbee fingerprints (manufacturer, model) this quirk is for; None matches any manufacturer.
FINGERPRINTS = [('AIRPRS1', 'Excellux')]
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
    .applies_to('AIRPRS1', 'Excellux')
    .tuya_battery(dp_id=4, scale=2)
    .tuya_temperature(dp_id=5, scale=1)
    .tuya_illuminance(dp_id=20)
    .tuya_number(dp_id=101, type=t.uint32_t, attribute_name='sampling_interval', min_value=5, max_value=1200, step=5, unit=UnitOfTime.SECONDS, device_class=NumberDeviceClass.DURATION, entity_type=EntityType.CONFIG, translation_key='sampling_interval', fallback_name='Sampling interval')
    .tuya_number(dp_id=104, type=t.uint32_t, attribute_name='illuminance_v0', min_value=0, max_value=10000, step=1, unit=LIGHT_LUX, device_class=NumberDeviceClass.ILLUMINANCE, entity_type=EntityType.CONFIG, translation_key='illuminance_v0', fallback_name='Illuminance v0')
    .tuya_number(dp_id=105, type=t.uint32_t, attribute_name='illuminance_v1', min_value=0, max_value=10000, step=1, unit=LIGHT_LUX, device_class=NumberDeviceClass.ILLUMINANCE, entity_type=EntityType.CONFIG, translation_key='illuminance_v1', fallback_name='Illuminance v1')
    .tuya_number(dp_id=106, type=t.int32s, attribute_name='illuminance_calibration', min_value=-1000, max_value=1000, step=1, unit=LIGHT_LUX, device_class=NumberDeviceClass.ILLUMINANCE, entity_type=EntityType.CONFIG, translation_key='illuminance_calibration', fallback_name='Illuminance calibration')
    .tuya_dp_attribute(dp_id=107, attribute_name='illuminance_warning', type=IlluminanceWarning, access=foundation.ZCLAttributeAccess.Read | foundation.ZCLAttributeAccess.Report, converter=lambda x: IlluminanceWarning(int(x)))
    .enum(attribute_name='illuminance_warning', enum_class=IlluminanceWarning, cluster_id=TUYA_CLUSTER_ID, entity_platform=EntityPlatform.SENSOR, entity_type=EntityType.STANDARD, translation_key='illuminance_warning', fallback_name='Illuminance warning')
    .tuya_sensor(dp_id=108, attribute_name='uv', type=t.uint32_t, state_class=SensorStateClass.MEASUREMENT, device_class=SensorDeviceClass.VOLTAGE, unit=UnitOfElectricPotential.VOLT, entity_type=EntityType.STANDARD, translation_key='uv', fallback_name='UV')
    .tuya_sensor(dp_id=109, attribute_name='uv_level', type=t.uint32_t, divisor=10, entity_type=EntityType.STANDARD, translation_key='uv_level', fallback_name='UV level')
    .tuya_number(dp_id=110, type=t.int32s, attribute_name='uv_calibration', min_value=-1, max_value=1, step=0.1, multiplier=0.1, entity_type=EntityType.CONFIG, translation_key='uv_calibration', fallback_name='UV calibration')
    .tuya_dp_attribute(dp_id=111, attribute_name='uv_warning', type=UvWarning, access=foundation.ZCLAttributeAccess.Read | foundation.ZCLAttributeAccess.Report, converter=lambda x: UvWarning(int(x)))
    .enum(attribute_name='uv_warning', enum_class=UvWarning, cluster_id=TUYA_CLUSTER_ID, entity_platform=EntityPlatform.SENSOR, entity_type=EntityType.STANDARD, translation_key='uv_warning', fallback_name='UV warning')
    .tuya_number(dp_id=114, type=t.int32s, attribute_name='temperature_calibration', min_value=-2, max_value=2, step=0.01, unit=UnitOfTemperature.CELSIUS, multiplier=0.01, device_class=NumberDeviceClass.TEMPERATURE_DELTA, entity_type=EntityType.CONFIG, translation_key='temperature_calibration', fallback_name='Temperature calibration')
    .tuya_number(dp_id=115, type=t.int32s, attribute_name='temperature_v0_set', min_value=-40, max_value=85, step=0.01, unit=UnitOfTemperature.CELSIUS, multiplier=0.01, device_class=NumberDeviceClass.TEMPERATURE, entity_type=EntityType.CONFIG, translation_key='temperature_v0_set', fallback_name='Temperature v0 set')
    .tuya_number(dp_id=116, type=t.int32s, attribute_name='temperature_v1_set', min_value=-40, max_value=85, step=0.01, unit=UnitOfTemperature.CELSIUS, multiplier=0.01, device_class=NumberDeviceClass.TEMPERATURE, entity_type=EntityType.CONFIG, translation_key='temperature_v1_set', fallback_name='Temperature v1 set')
    .tuya_dp_attribute(dp_id=117, attribute_name='temperature_warning', type=TemperatureWarning, access=foundation.ZCLAttributeAccess.Read | foundation.ZCLAttributeAccess.Report, converter=lambda x: TemperatureWarning(int(x)))
    .enum(attribute_name='temperature_warning', enum_class=TemperatureWarning, cluster_id=TUYA_CLUSTER_ID, entity_platform=EntityPlatform.SENSOR, entity_type=EntityType.STANDARD, translation_key='temperature_warning', fallback_name='Temperature warning')
    .tuya_sensor(dp_id=124, attribute_name='pressure', type=t.uint32_t, divisor=100, state_class=SensorStateClass.MEASUREMENT, device_class=SensorDeviceClass.PRESSURE, unit=UnitOfPressure.HPA, entity_type=EntityType.STANDARD, fallback_name='Pressure')
    .tuya_number(dp_id=125, type=t.int32s, attribute_name='pressure_calibration', min_value=-10, max_value=10, step=0.01, unit=UnitOfPressure.HPA, multiplier=0.01, device_class=NumberDeviceClass.PRESSURE, entity_type=EntityType.CONFIG, translation_key='pressure_calibration', fallback_name='Pressure calibration')
    .tuya_number(dp_id=126, type=t.uint32_t, attribute_name='pressure_v0_set', min_value=300, max_value=1100, step=0.01, unit=UnitOfPressure.HPA, multiplier=0.01, device_class=NumberDeviceClass.PRESSURE, entity_type=EntityType.CONFIG, translation_key='pressure_v0_set', fallback_name='Pressure v0 set')
    .tuya_number(dp_id=127, type=t.uint32_t, attribute_name='pressure_v1_set', min_value=300, max_value=1100, step=0.01, unit=UnitOfPressure.HPA, multiplier=0.01, device_class=NumberDeviceClass.PRESSURE, entity_type=EntityType.CONFIG, translation_key='pressure_v1_set', fallback_name='Pressure v1 set')
    .tuya_dp_attribute(dp_id=128, attribute_name='pressure_warn', type=PressureWarn, access=foundation.ZCLAttributeAccess.Read | foundation.ZCLAttributeAccess.Report, converter=lambda x: PressureWarn(int(x)))
    .enum(attribute_name='pressure_warn', enum_class=PressureWarn, cluster_id=TUYA_CLUSTER_ID, entity_platform=EntityPlatform.SENSOR, entity_type=EntityType.STANDARD, translation_key='pressure_warn', fallback_name='Pressure warn')
    .tuya_dp_attribute(dp_id=129, attribute_name='pressure_tend', type=PressureTend, access=foundation.ZCLAttributeAccess.Read | foundation.ZCLAttributeAccess.Report, converter=lambda x: PressureTend(int(x)))
    .enum(attribute_name='pressure_tend', enum_class=PressureTend, cluster_id=TUYA_CLUSTER_ID, entity_platform=EntityPlatform.SENSOR, entity_type=EntityType.STANDARD, translation_key='pressure_tend', fallback_name='Pressure tend')
    .skip_configuration()
    .filter(no_builtin_quirk)
    .add_to_registry()
)
