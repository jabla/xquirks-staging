"""Tuya ZWT07: Wall-mount thermostat.

Generated from the Zigbee2MQTT definition.
Data: zigbee-herdsman-converters, MIT, Copyright (c) 2018 Koen Kanters.
Status: generated, not verified on hardware.
Revision: 4a4eed18
"""

import functools
import logging
import pathlib

import zhaquirks
from zha.quirks import DEVICE_REGISTRY, DeviceMatch
import zigpy.types as t
from zigpy.zcl.clusters.hvac import RunningState, Thermostat

from zhaquirks.builder import (
    EntityType,
)
from zhaquirks.tuya.builder import TuyaQuirkBuilder
from zhaquirks.tuya.tuya_trv import TuyaThermostatV2


class Z2mThermostat(TuyaThermostatV2):
    """Tuya thermostat with the setpoint range z2m gives (absolute limits 5 to 60 °C)."""

    _CONSTANT_ATTRIBUTES = {
        **TuyaThermostatV2._CONSTANT_ATTRIBUTES,
        Thermostat.AttributeDefs.abs_min_heat_setpoint_limit.id: 500,
        Thermostat.AttributeDefs.abs_max_heat_setpoint_limit.id: 6000,
    }


class Preset(t.enum8):
    """preset values (z2m)."""

    program = 0x00
    manual = 0x01



_LOGGER = logging.getLogger(__name__)
_SHIPPED = pathlib.Path(zhaquirks.__file__).resolve().parent
_STEPPED_BACK: set = set()

# The Zigbee fingerprints (manufacturer, model) this quirk is for; None matches any manufacturer.
FINGERPRINTS = [('_TZE200_g9a3awaj', 'TS0601')]
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
    .applies_to('_TZE200_g9a3awaj', 'TS0601')
    .tuya_dp(dp_id=24, ep_attribute=Z2mThermostat.ep_attribute, attribute_name=Thermostat.AttributeDefs.local_temperature.name, converter=lambda x: x * 10)
    .tuya_dp(dp_id=16, ep_attribute=Z2mThermostat.ep_attribute, attribute_name=Thermostat.AttributeDefs.occupied_heating_setpoint.name, converter=lambda x: x * 10, dp_converter=lambda x: x // 10)
    .tuya_dp(dp_id=1, ep_attribute=Z2mThermostat.ep_attribute, attribute_name=Thermostat.AttributeDefs.system_mode.name, converter=lambda x: {True: Thermostat.SystemMode.Heat, False: Thermostat.SystemMode.Off}[bool(x)], dp_converter=lambda x: {Thermostat.SystemMode.Heat: True, Thermostat.SystemMode.Off: False}[x])
    .tuya_dp(dp_id=36, ep_attribute=Z2mThermostat.ep_attribute, attribute_name=Thermostat.AttributeDefs.running_state.name, converter=lambda x: {1: RunningState.Heat_State_On, 0: RunningState.Idle}[int(x)])
    .adds(Z2mThermostat)
    .tuya_enum(dp_id=2, attribute_name='preset', enum_class=Preset, entity_type=EntityType.STANDARD, translation_key='preset', fallback_name='Preset')
    .tuya_switch(dp_id=10, attribute_name='frost', entity_type=EntityType.CONFIG, translation_key='frost', fallback_name='Frost')
    .skip_configuration()
    .filter(no_builtin_quirk)
    .add_to_registry()
)
