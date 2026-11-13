"""Excellux EZ-500FL: Split-type sensor for detecting soil moisture, soil fertility, temperature and humidity.

Generated from the Zigbee2MQTT definition.
Data: zigbee-herdsman-converters, MIT, Copyright (c) 2018 Koen Kanters.
Status: generated, not verified on hardware.
Revision: debf852e
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
    NumberDeviceClass,
    PERCENTAGE,
    SensorDeviceClass,
    SensorStateClass,
    UnitOfTemperature,
    UnitOfTime,
)
from zhaquirks.tuya import TUYA_CLUSTER_ID
from zhaquirks.tuya.builder import TuyaQuirkBuilder


class ProbeTemperatureWarning(t.enum8):
    """probe_temperature_warning values (z2m)."""

    none = 0x00
    low = 0x01
    high = 0x02


class TemperatureWarning(t.enum8):
    """temperature_warning values (z2m)."""

    none = 0x00
    low = 0x01
    high = 0x02


class HumidityWarning(t.enum8):
    """humidity_warning values (z2m)."""

    none = 0x00
    low = 0x01
    high = 0x02


class FertilityWarning(t.enum8):
    """fertility_warning values (z2m)."""

    none = 0x00
    low = 0x01
    high = 0x02


class MoistureWarning(t.enum8):
    """moisture_warning values (z2m)."""

    none = 0x00
    low = 0x01
    high = 0x02



_LOGGER = logging.getLogger(__name__)
_SHIPPED = pathlib.Path(zhaquirks.__file__).resolve().parent
_STEPPED_BACK: set = set()

# The Zigbee fingerprints (manufacturer, model) this quirk is for; None matches any manufacturer.
FINGERPRINTS = [('EZ500FL', 'Excellux')]
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
    .applies_to('EZ500FL', 'Excellux')
    .tuya_sensor(dp_id=1, attribute_name='probe_temperature', type=t.int32s, divisor=10, state_class=SensorStateClass.MEASUREMENT, device_class=SensorDeviceClass.TEMPERATURE, unit=UnitOfTemperature.CELSIUS, entity_type=EntityType.STANDARD, translation_key='probe_temperature', fallback_name='Probe temperature')
    .tuya_battery(dp_id=4, scale=2)
    .tuya_temperature(dp_id=5, scale=1)
    .tuya_number(dp_id=101, type=t.uint32_t, attribute_name='sampling_interval', min_value=5, max_value=1200, step=5, unit=UnitOfTime.SECONDS, device_class=NumberDeviceClass.DURATION, entity_type=EntityType.CONFIG, translation_key='sampling_interval', fallback_name='Sampling interval')
    .tuya_humidity(dp_id=118, scale=1)
    .tuya_number(dp_id=108, type=t.int32s, attribute_name='probe_temperature_calibration', min_value=-2, max_value=2, step=0.1, unit=UnitOfTemperature.CELSIUS, multiplier=0.1, device_class=NumberDeviceClass.TEMPERATURE_DELTA, entity_type=EntityType.CONFIG, translation_key='probe_temperature_calibration', fallback_name='Probe temperature calibration')
    .tuya_number(dp_id=109, type=t.int32s, attribute_name='probe_temperature_v0_set', min_value=-40, max_value=125, step=0.1, unit=UnitOfTemperature.CELSIUS, multiplier=0.1, device_class=NumberDeviceClass.TEMPERATURE, entity_type=EntityType.CONFIG, translation_key='probe_temperature_v0_set', fallback_name='Probe temperature v0 set')
    .tuya_number(dp_id=110, type=t.int32s, attribute_name='probe_temperature_v1_set', min_value=-40, max_value=125, step=0.1, unit=UnitOfTemperature.CELSIUS, multiplier=0.1, device_class=NumberDeviceClass.TEMPERATURE, entity_type=EntityType.CONFIG, translation_key='probe_temperature_v1_set', fallback_name='Probe temperature v1 set')
    .tuya_dp_attribute(dp_id=112, attribute_name='probe_temperature_warning', type=ProbeTemperatureWarning, access=foundation.ZCLAttributeAccess.Read | foundation.ZCLAttributeAccess.Report, converter=lambda x: ProbeTemperatureWarning(int(x)))
    .enum(attribute_name='probe_temperature_warning', enum_class=ProbeTemperatureWarning, cluster_id=TUYA_CLUSTER_ID, entity_platform=EntityPlatform.SENSOR, entity_type=EntityType.STANDARD, translation_key='probe_temperature_warning', fallback_name='Probe temperature warning')
    .tuya_number(dp_id=114, type=t.int32s, attribute_name='temperature_calibration', min_value=-2, max_value=2, step=0.01, unit=UnitOfTemperature.CELSIUS, multiplier=0.01, device_class=NumberDeviceClass.TEMPERATURE_DELTA, entity_type=EntityType.CONFIG, translation_key='temperature_calibration', fallback_name='Temperature calibration')
    .tuya_number(dp_id=115, type=t.int32s, attribute_name='temperature_v0_set', min_value=-40, max_value=85, step=0.01, unit=UnitOfTemperature.CELSIUS, multiplier=0.01, device_class=NumberDeviceClass.TEMPERATURE, entity_type=EntityType.CONFIG, translation_key='temperature_v0_set', fallback_name='Temperature v0 set')
    .tuya_number(dp_id=116, type=t.int32s, attribute_name='temperature_v1_set', min_value=-40, max_value=85, step=0.01, unit=UnitOfTemperature.CELSIUS, multiplier=0.01, device_class=NumberDeviceClass.TEMPERATURE, entity_type=EntityType.CONFIG, translation_key='temperature_v1_set', fallback_name='Temperature v1 set')
    .tuya_dp_attribute(dp_id=117, attribute_name='temperature_warning', type=TemperatureWarning, access=foundation.ZCLAttributeAccess.Read | foundation.ZCLAttributeAccess.Report, converter=lambda x: TemperatureWarning(int(x)))
    .enum(attribute_name='temperature_warning', enum_class=TemperatureWarning, cluster_id=TUYA_CLUSTER_ID, entity_platform=EntityPlatform.SENSOR, entity_type=EntityType.STANDARD, translation_key='temperature_warning', fallback_name='Temperature warning')
    .tuya_number(dp_id=119, type=t.int32s, attribute_name='humidity_calibration', min_value=-10, max_value=10, step=0.01, unit=PERCENTAGE, multiplier=0.01, entity_type=EntityType.CONFIG, translation_key='humidity_calibration', fallback_name='Humidity calibration')
    .tuya_number(dp_id=120, type=t.uint32_t, attribute_name='humidity_v0_set', min_value=0, max_value=100, step=0.01, unit=PERCENTAGE, multiplier=0.01, entity_type=EntityType.CONFIG, translation_key='humidity_v0_set', fallback_name='Humidity v0 set')
    .tuya_number(dp_id=121, type=t.uint32_t, attribute_name='humidity_v1_set', min_value=0, max_value=100, step=0.01, unit=PERCENTAGE, multiplier=0.01, entity_type=EntityType.CONFIG, translation_key='humidity_v1_set', fallback_name='Humidity v1 set')
    .tuya_dp_attribute(dp_id=122, attribute_name='humidity_warning', type=HumidityWarning, access=foundation.ZCLAttributeAccess.Read | foundation.ZCLAttributeAccess.Report, converter=lambda x: HumidityWarning(int(x)))
    .enum(attribute_name='humidity_warning', enum_class=HumidityWarning, cluster_id=TUYA_CLUSTER_ID, entity_platform=EntityPlatform.SENSOR, entity_type=EntityType.STANDARD, translation_key='humidity_warning', fallback_name='Humidity warning')
    .tuya_sensor(dp_id=124, attribute_name='fertility', type=t.uint32_t, state_class=SensorStateClass.MEASUREMENT, unit='μS/cm', entity_type=EntityType.STANDARD, translation_key='fertility', fallback_name='Fertility')
    .tuya_number(dp_id=125, type=t.uint32_t, attribute_name='fertility_v0_set', min_value=0, max_value=5000, step=1, unit='μS/cm', entity_type=EntityType.CONFIG, translation_key='fertility_v0_set', fallback_name='Fertility v0 set')
    .tuya_number(dp_id=126, type=t.uint32_t, attribute_name='fertility_v1_set', min_value=0, max_value=5000, step=1, unit='μS/cm', entity_type=EntityType.CONFIG, translation_key='fertility_v1_set', fallback_name='Fertility v1 set')
    .tuya_dp_attribute(dp_id=127, attribute_name='fertility_warning', type=FertilityWarning, access=foundation.ZCLAttributeAccess.Read | foundation.ZCLAttributeAccess.Report, converter=lambda x: FertilityWarning(int(x)))
    .enum(attribute_name='fertility_warning', enum_class=FertilityWarning, cluster_id=TUYA_CLUSTER_ID, entity_platform=EntityPlatform.SENSOR, entity_type=EntityType.STANDARD, translation_key='fertility_warning', fallback_name='Fertility warning')
    .tuya_number(dp_id=128, type=t.uint32_t, attribute_name='fertility_calibration', min_value=0.5, max_value=2, step=0.01, multiplier=0.001, entity_type=EntityType.CONFIG, translation_key='fertility_calibration', fallback_name='Fertility calibration')
    .tuya_sensor(dp_id=3, attribute_name='moisture', type=t.uint32_t, state_class=SensorStateClass.MEASUREMENT, unit=PERCENTAGE, entity_type=EntityType.STANDARD, translation_key='moisture', fallback_name='Moisture')
    .tuya_number(dp_id=129, type=t.uint32_t, attribute_name='moisture_v0_set', min_value=0, max_value=100, step=1, unit=PERCENTAGE, entity_type=EntityType.CONFIG, translation_key='moisture_v0_set', fallback_name='Moisture v0 set')
    .tuya_number(dp_id=130, type=t.uint32_t, attribute_name='moisture_v1_set', min_value=0, max_value=100, step=1, unit=PERCENTAGE, entity_type=EntityType.CONFIG, translation_key='moisture_v1_set', fallback_name='Moisture v1 set')
    .tuya_number(dp_id=131, type=t.uint32_t, attribute_name='moisture_calibration', min_value=0.2, max_value=1.5, step=0.01, multiplier=0.01, entity_type=EntityType.CONFIG, translation_key='moisture_calibration', fallback_name='Moisture calibration')
    .tuya_dp_attribute(dp_id=132, attribute_name='moisture_warning', type=MoistureWarning, access=foundation.ZCLAttributeAccess.Read | foundation.ZCLAttributeAccess.Report, converter=lambda x: MoistureWarning(int(x)))
    .enum(attribute_name='moisture_warning', enum_class=MoistureWarning, cluster_id=TUYA_CLUSTER_ID, entity_platform=EntityPlatform.SENSOR, entity_type=EntityType.STANDARD, translation_key='moisture_warning', fallback_name='Moisture warning')
    .skip_configuration()
    .filter(no_builtin_quirk)
    .add_to_registry()
)
