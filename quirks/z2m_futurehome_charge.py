"""Futurehome Charge: Futurehome Charge (EV Charger).

Generated from the Zigbee2MQTT definition.
Data: zigbee-herdsman-converters, MIT, Copyright (c) 2018 Koen Kanters.
Status: generated, not verified on hardware.
Revision: 54b16336
"""

import functools
import logging
import pathlib

import zhaquirks
from zha.quirks import DEVICE_REGISTRY, DeviceMatch
import zigpy.types as t
from zigpy.zcl.foundation import ZCLAttributeDef
from zigpy.zcl.clusters.closures import DoorLock
from zigpy.zcl.clusters.general import AnalogOutput
from zigpy.zcl.clusters.general import ApplianceControl

from zhaquirks.builder import (
    EntityPlatform,
    EntityType,
    NumberDeviceClass,
    QuirkBuilder,
    UnitOfElectricCurrent,
)
from zhaquirks.clusters import CustomCluster


class GenAnalogOutputCluster(CustomCluster, AnalogOutput):
    """AnalogOutput with the attributes z2m adds."""

    class AttributeDefs(AnalogOutput.AttributeDefs):
        """Attribute definitions."""

        max_present_value = ZCLAttributeDef(id=0x0041, type=t.Single, manufacturer_code=0x133D)


class HaApplianceControlCluster(CustomCluster, ApplianceControl):
    """ApplianceControl with the attributes z2m adds."""

    class AttributeDefs(ApplianceControl.AttributeDefs):
        """Attribute definitions."""

        charging_session_start_time = ZCLAttributeDef(id=0xEF01, type=t.uint32_t, access="r", manufacturer_code=0x133D)
        charging_session_end_time = ZCLAttributeDef(id=0xEF02, type=t.uint32_t, access="r", manufacturer_code=0x133D)
        energy_meter_start = ZCLAttributeDef(id=0xEF03, type=t.uint32_t, access="r", manufacturer_code=0x133D)
        energy_meter_now = ZCLAttributeDef(id=0xEF04, type=t.uint32_t, access="r", manufacturer_code=0x133D)
        status = ZCLAttributeDef(id=0xEF09, type=t.uint8_t, manufacturer_code=0x133D)
        auto_charge = ZCLAttributeDef(id=0xEF0C, type=t.uint8_t, manufacturer_code=0x133D)


class ClosuresDoorLockCluster(CustomCluster, DoorLock):
    """DoorLock with the attributes z2m adds."""

    class AttributeDefs(DoorLock.AttributeDefs):
        """Attribute definitions."""

        operating_mode = ZCLAttributeDef(id=0x0025, type=t.enum8, manufacturer_code=0x133D)


class Status(t.enum8):
    """status values (z2m)."""

    plugged_out = 0x00
    off = 0x01
    plugged_in_charging = 0x02
    plugged_in_paused = 0x03
    plugged_in = 0x04
    stopped = 0x05



_LOGGER = logging.getLogger(__name__)
_SHIPPED = pathlib.Path(zhaquirks.__file__).resolve().parent
_STEPPED_BACK: set = set()

# The Zigbee fingerprints (manufacturer, model) this quirk is for; None matches any manufacturer.
FINGERPRINTS = [(None, 'Charge')]
# Names that a model-only fingerprint would catch but Zigbee2MQTT gives to other devices.
CLAIMED_ELSEWHERE = set()
# The endpoints this quirk needs, each with the input clusters it puts there where Zigbee2MQTT names none.
ENDPOINTS = {1: (0x000D, 0x001B, 0x0101)}


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
    QuirkBuilder(None, 'Charge')
    .replaces(ClosuresDoorLockCluster)
    .replaces(HaApplianceControlCluster)
    .replaces(GenAnalogOutputCluster)
    .enum(attribute_name=HaApplianceControlCluster.AttributeDefs.status.name, cluster_id=HaApplianceControlCluster.cluster_id, enum_class=Status, entity_platform=EntityPlatform.SENSOR, entity_type=EntityType.STANDARD, translation_key='status', fallback_name='Status')
    .switch(attribute_name=HaApplianceControlCluster.AttributeDefs.auto_charge.name, cluster_id=HaApplianceControlCluster.cluster_id, entity_type=EntityType.CONFIG, translation_key='auto_charge', fallback_name='Auto charge')
    .switch(attribute_name=ClosuresDoorLockCluster.AttributeDefs.operating_mode.name, cluster_id=ClosuresDoorLockCluster.cluster_id, on_value=2, off_value=0, entity_type=EntityType.STANDARD, translation_key='plug_locked_permanently', fallback_name='Plug locked when not charging')
    .number(attribute_name=GenAnalogOutputCluster.AttributeDefs.max_present_value.name, cluster_id=GenAnalogOutputCluster.cluster_id, min_value=6, max_value=32, step=1, unit=UnitOfElectricCurrent.AMPERE, device_class=NumberDeviceClass.CURRENT, entity_type=EntityType.CONFIG, translation_key='charging_current_limit', fallback_name='Charging current limit')
    # setpoint_charging_current: standard clusters, ZHA's own entities
    # power: standard clusters, ZHA's own entities
    # plug_lock_state: standard clusters, ZHA's own entities
    # charging_start: z2m's own code, not generated
    # charging_stop: z2m's own code, not generated
    # charging_pause: z2m's own code, not generated
    # state: z2m's own code, not generated
    # session_energy: z2m's own code, not generated
    # energy_meter_start: z2m's own code, not generated
    # energy_meter_now: z2m's own code, not generated
    # charging_duration: z2m's own code, not generated
    # voltage: standard clusters, ZHA's own entities
    # current: standard clusters, ZHA's own entities
    # energy: standard clusters, ZHA's own entities
    # voltage_phase_b: standard clusters, ZHA's own entities
    # voltage_phase_c: standard clusters, ZHA's own entities
    # current_phase_b: standard clusters, ZHA's own entities
    # current_phase_c: standard clusters, ZHA's own entities
    # is_charging: z2m's own code, not generated
    # charging_start_datetime: z2m's own code, not generated
    # charging_end_datetime: z2m's own code, not generated
    # is_plug_connected: z2m's own code, not generated
    # connected_start_datetime: z2m's own code, not generated
    # connected_end_datetime: z2m's own code, not generated
    .filter(no_builtin_quirk)
    .add_to_registry()
)
