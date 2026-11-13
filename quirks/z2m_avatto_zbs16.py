"""AVATTO ZBS16: Smart Boiler Switch.

Generated from the Zigbee2MQTT definition.
Data: zigbee-herdsman-converters, MIT, Copyright (c) 2018 Koen Kanters.
Status: generated, not verified on hardware.
Revision: 236a747c
"""

import functools
import logging
import pathlib

import zhaquirks
from zha.quirks import DEVICE_REGISTRY, DeviceMatch
import zigpy.types as t

from zhaquirks.builder import (
    EntityType,
    NumberDeviceClass,
    SensorDeviceClass,
    SensorStateClass,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfFrequency,
    UnitOfPower,
    UnitOfTime,
)
from zhaquirks.tuya.builder import TuyaQuirkBuilder


class SwitchOnTime(t.enum8):
    """switch_on_time values (z2m)."""

    off = 0x00
    Time_30_minutes = 0x01
    Time_60_minutes = 0x02
    Time_90_minutes = 0x03
    Time_120_minutes = 0x04
    on = 0x05



_LOGGER = logging.getLogger(__name__)
_SHIPPED = pathlib.Path(zhaquirks.__file__).resolve().parent
_STEPPED_BACK: set = set()

# The Zigbee fingerprints (manufacturer, model) this quirk is for; None matches any manufacturer.
FINGERPRINTS = [('_TZE284_udaucpdi', 'TS0601')]
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
    TuyaQuirkBuilder()
    .applies_to('_TZE284_udaucpdi', 'TS0601')
    .tuya_onoff(dp_id=1)
    .tuya_sensor(dp_id=20, attribute_name='energy', type=t.uint32_t, divisor=1000, state_class=SensorStateClass.TOTAL_INCREASING, device_class=SensorDeviceClass.ENERGY, unit=UnitOfEnergy.KILO_WATT_HOUR, entity_type=EntityType.STANDARD, fallback_name='Energy')
    .tuya_sensor(dp_id=21, attribute_name='current', type=t.uint32_t, state_class=SensorStateClass.MEASUREMENT, device_class=SensorDeviceClass.CURRENT, unit=UnitOfElectricCurrent.MILLIAMPERE, entity_type=EntityType.STANDARD, fallback_name='Current')
    .tuya_sensor(dp_id=22, attribute_name='power', type=t.uint32_t, divisor=10, state_class=SensorStateClass.MEASUREMENT, device_class=SensorDeviceClass.POWER, unit=UnitOfPower.WATT, entity_type=EntityType.STANDARD, fallback_name='Power')
    .tuya_sensor(dp_id=23, attribute_name='voltage', type=t.uint32_t, divisor=10, state_class=SensorStateClass.MEASUREMENT, device_class=SensorDeviceClass.VOLTAGE, unit=UnitOfElectricPotential.VOLT, entity_type=EntityType.STANDARD, fallback_name='Voltage')
    .tuya_sensor(dp_id=101, attribute_name='ac_frequency', type=t.uint32_t, divisor=10, state_class=SensorStateClass.MEASUREMENT, device_class=SensorDeviceClass.FREQUENCY, unit=UnitOfFrequency.HERTZ, entity_type=EntityType.STANDARD, translation_key='ac_frequency', fallback_name='AC frequency')
    .tuya_enum(dp_id=102, attribute_name='switch_on_time', enum_class=SwitchOnTime, entity_type=EntityType.CONFIG, translation_key='switch_on_time', fallback_name='Switch on time')
    .tuya_number(dp_id=103, type=t.uint32_t, attribute_name='countdown', min_value=0, max_value=7210, step=1, unit=UnitOfTime.SECONDS, device_class=NumberDeviceClass.DURATION, entity_type=EntityType.CONFIG, translation_key='countdown', fallback_name='Countdown')
    .tuya_sensor(dp_id=104, attribute_name='total_switch_on_time', type=t.uint32_t, state_class=SensorStateClass.MEASUREMENT, device_class=SensorDeviceClass.DURATION, unit=UnitOfTime.MINUTES, entity_type=EntityType.STANDARD, translation_key='total_switch_on_time', fallback_name='Total switch on time')
    .skip_configuration()
    .filter(no_builtin_quirk)
    .add_to_registry()
)
