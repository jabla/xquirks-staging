"""Tuya _TZE28C1000000_jaunkx9g: Human presence sensor 2-gang smart switch.

Generated from the Zigbee2MQTT definition.
Data: zigbee-herdsman-converters, MIT, Copyright (c) 2018 Koen Kanters.
Status: generated, not verified on hardware.
Revision: bc4e14ee
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
    UnitOfTime,
)
from zhaquirks.tuya import TUYA_CLUSTER_ID
from zhaquirks.tuya.builder import TuyaQuirkBuilder


class RelayStatus(t.enum8):
    """relay_status values (z2m)."""

    off = 0x00
    on = 0x01
    memory = 0x02


class LightMode(t.enum8):
    """light_mode values (z2m)."""

    relay = 0x00
    none = 0x01
    pos = 0x02


class PresenceState(t.enum8):
    """presence_state values (z2m)."""

    none = 0x00
    presence = 0x01


class TurnOnLightForPerson(t.enum8):
    """turn_on_light_for_person values (z2m)."""

    none = 0x00
    all = 0x01
    on_ch1 = 0x02
    on_ch2 = 0x03


class TurnOffLightForPerson(t.enum8):
    """turn_off_light_for_person values (z2m)."""

    none = 0x00
    all = 0x01
    off_ch1 = 0x02
    off_ch2 = 0x03



_LOGGER = logging.getLogger(__name__)
_SHIPPED = pathlib.Path(zhaquirks.__file__).resolve().parent
_STEPPED_BACK: set = set()

# The Zigbee fingerprints (manufacturer, model) this quirk is for; None matches any manufacturer.
FINGERPRINTS = [('_TZE28C1000000_jaunkx9g', 'TS0601')]
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
    .applies_to('_TZE28C1000000_jaunkx9g', 'TS0601')
    .tuya_switch(dp_id=1, attribute_name='state_l1', entity_type=EntityType.STANDARD, translation_key='z2m_state', fallback_name='State')
    .tuya_switch(dp_id=2, attribute_name='state_l2', entity_type=EntityType.STANDARD, translation_key='z2m_state', fallback_name='State')
    .tuya_number(dp_id=7, type=t.uint32_t, attribute_name='countdown_1', min_value=0, max_value=43200, step=1, unit=UnitOfTime.SECONDS, device_class=NumberDeviceClass.DURATION, entity_type=EntityType.CONFIG, translation_key='countdown_1', fallback_name='Countdown 1')
    .tuya_number(dp_id=8, type=t.uint32_t, attribute_name='countdown_2', min_value=0, max_value=43200, step=1, unit=UnitOfTime.SECONDS, device_class=NumberDeviceClass.DURATION, entity_type=EntityType.CONFIG, translation_key='countdown_2', fallback_name='Countdown 2')
    .tuya_enum(dp_id=14, attribute_name='relay_status', enum_class=RelayStatus, entity_type=EntityType.CONFIG, translation_key='relay_status', fallback_name='Relay status')
    .tuya_enum(dp_id=15, attribute_name='light_mode', enum_class=LightMode, entity_type=EntityType.CONFIG, translation_key='light_mode', fallback_name='Light mode')
    .tuya_dp_attribute(dp_id=101, attribute_name='presence_state', type=PresenceState, access=foundation.ZCLAttributeAccess.Read | foundation.ZCLAttributeAccess.Report, converter=lambda x: PresenceState(int(x)))
    .enum(attribute_name='presence_state', enum_class=PresenceState, cluster_id=TUYA_CLUSTER_ID, entity_platform=EntityPlatform.SENSOR, entity_type=EntityType.STANDARD, translation_key='presence_state', fallback_name='Presence state')
    .tuya_number(dp_id=102, type=t.uint32_t, attribute_name='delays_time', min_value=3, max_value=3600, step=1, unit=UnitOfTime.SECONDS, device_class=NumberDeviceClass.DURATION, entity_type=EntityType.CONFIG, translation_key='delays_time', fallback_name='Delays time')
    .tuya_enum(dp_id=103, attribute_name='turn_on_light_for_person', enum_class=TurnOnLightForPerson, entity_type=EntityType.CONFIG, translation_key='turn_on_light_for_person', fallback_name='Turn on light for person')
    .tuya_number(dp_id=104, type=t.uint32_t, attribute_name='sensitivity', min_value=1, max_value=10, step=1, entity_type=EntityType.CONFIG, translation_key='sensitivity', fallback_name='Sensitivity')
    .tuya_enum(dp_id=105, attribute_name='turn_off_light_for_person', enum_class=TurnOffLightForPerson, entity_type=EntityType.CONFIG, translation_key='turn_off_light_for_person', fallback_name='Turn off light for person')
    .skip_configuration()
    .filter(no_builtin_quirk)
    .add_to_registry()
)
