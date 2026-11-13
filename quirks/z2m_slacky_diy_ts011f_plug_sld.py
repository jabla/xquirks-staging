"""Slacky-DIY TS011F_plug-SlD: Plug with power monitoring.

Generated from the Zigbee2MQTT definition.
Data: zigbee-herdsman-converters, MIT, Copyright (c) 2018 Koen Kanters.
Status: generated, not verified on hardware.
Revision: 005da720
"""

import functools
import logging
import pathlib

import zhaquirks
from zha.quirks import DEVICE_REGISTRY, DeviceMatch
import zigpy.types as t
from zigpy.zcl.foundation import Direction, ZCLAttributeDef, ZCLCommandDef
from zigpy.zcl.clusters.general import OnOff
from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement
from zigpy.zcl.clusters.smartenergy import Metering

from zhaquirks.builder import (
    EntityType,
    NumberDeviceClass,
    QuirkBuilder,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfPower,
    UnitOfTime,
)
from zhaquirks.clusters import CustomCluster


class GenOnOffCluster(CustomCluster, OnOff):
    """OnOff with the attributes z2m adds."""

    class AttributeDefs(OnOff.AttributeDefs):
        """Attribute definitions."""

        key_lock = ZCLAttributeDef(id=0xF000, type=t.Bool, manufacturer_code=None)
        led_control = ZCLAttributeDef(id=0xF001, type=t.enum8, manufacturer_code=None)


class SeMeteringCluster(CustomCluster, Metering):
    """Metering with the attributes z2m adds."""

    class AttributeDefs(Metering.AttributeDefs):
        """Attribute definitions."""


    class ServerCommandDefs(Metering.ServerCommandDefs):
        """Command definitions (z2m's commands this cluster lacks)."""

        reset_energy_meters = ZCLCommandDef(id=0x80, schema={}, direction=Direction.Client_to_Server, manufacturer_code=None)


class HaElectricalMeasurementCluster(CustomCluster, ElectricalMeasurement):
    """ElectricalMeasurement with the attributes z2m adds."""

    class AttributeDefs(ElectricalMeasurement.AttributeDefs):
        """Attribute definitions."""

        protect_control = ZCLAttributeDef(id=0xF005, type=t.Bool, manufacturer_code=None)
        automatic_restart = ZCLAttributeDef(id=0xF006, type=t.Bool, manufacturer_code=None)
        current_max = ZCLAttributeDef(id=0xF002, type=t.uint16_t, manufacturer_code=None)
        power_max = ZCLAttributeDef(id=0xF003, type=t.int16s, manufacturer_code=None)
        time_reload = ZCLAttributeDef(id=0xF004, type=t.uint16_t, manufacturer_code=None)


class LedControl(t.enum8):
    """led_control values (z2m)."""

    off = 0x00
    on = 0x01
    on_off = 0x02



_LOGGER = logging.getLogger(__name__)
_SHIPPED = pathlib.Path(zhaquirks.__file__).resolve().parent
_STEPPED_BACK: set = set()

# The Zigbee fingerprints (manufacturer, model) this quirk is for; None matches any manufacturer.
FINGERPRINTS = [(None, 'TS011F-SlD')]
# Names that a model-only fingerprint would catch but Zigbee2MQTT gives to other devices.
CLAIMED_ELSEWHERE = set()
# The endpoints this quirk needs, each with the input clusters it puts there where Zigbee2MQTT names none.
ENDPOINTS = {1: (0x0006, 0x0702, 0x0B04)}


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
    QuirkBuilder(None, 'TS011F-SlD')
    .replaces(HaElectricalMeasurementCluster)
    .replaces(SeMeteringCluster)
    .replaces(GenOnOffCluster)
    .switch(attribute_name=GenOnOffCluster.AttributeDefs.key_lock.name, cluster_id=GenOnOffCluster.cluster_id, entity_type=EntityType.STANDARD, translation_key='key_lock', fallback_name='Key lock')
    .enum(attribute_name=GenOnOffCluster.AttributeDefs.led_control.name, cluster_id=GenOnOffCluster.cluster_id, enum_class=LedControl, entity_type=EntityType.STANDARD, translation_key='led_control', fallback_name='LED control')
    .switch(attribute_name=HaElectricalMeasurementCluster.AttributeDefs.protect_control.name, cluster_id=HaElectricalMeasurementCluster.cluster_id, entity_type=EntityType.STANDARD, translation_key='protect_control', fallback_name='Protect control')
    .switch(attribute_name=HaElectricalMeasurementCluster.AttributeDefs.automatic_restart.name, cluster_id=HaElectricalMeasurementCluster.cluster_id, entity_type=EntityType.STANDARD, translation_key='automatic_restart', fallback_name='Automatic restart')
    .number(attribute_name=HaElectricalMeasurementCluster.AttributeDefs.rms_extreme_under_voltage.name, cluster_id=HaElectricalMeasurementCluster.cluster_id, min_value=0, max_value=300, unit=UnitOfElectricPotential.VOLT, multiplier=0.01, device_class=NumberDeviceClass.VOLTAGE, entity_type=EntityType.STANDARD, translation_key='voltage_min', fallback_name='Voltage min')
    .number(attribute_name=HaElectricalMeasurementCluster.AttributeDefs.rms_extreme_over_voltage.name, cluster_id=HaElectricalMeasurementCluster.cluster_id, min_value=0, max_value=300, unit=UnitOfElectricPotential.VOLT, multiplier=0.01, device_class=NumberDeviceClass.VOLTAGE, entity_type=EntityType.STANDARD, translation_key='voltage_max', fallback_name='Voltage max')
    .number(attribute_name=HaElectricalMeasurementCluster.AttributeDefs.current_max.name, cluster_id=HaElectricalMeasurementCluster.cluster_id, min_value=0, max_value=16, step=0.1, unit=UnitOfElectricCurrent.AMPERE, multiplier=0.01, device_class=NumberDeviceClass.CURRENT, entity_type=EntityType.STANDARD, translation_key='current_max', fallback_name='Current max')
    .number(attribute_name=HaElectricalMeasurementCluster.AttributeDefs.power_max.name, cluster_id=HaElectricalMeasurementCluster.cluster_id, min_value=0, max_value=3600, unit=UnitOfPower.WATT, device_class=NumberDeviceClass.POWER, entity_type=EntityType.STANDARD, translation_key='power_max', fallback_name='Power max')
    .number(attribute_name=HaElectricalMeasurementCluster.AttributeDefs.time_reload.name, cluster_id=HaElectricalMeasurementCluster.cluster_id, min_value=5, max_value=60, unit=UnitOfTime.SECONDS, device_class=NumberDeviceClass.DURATION, entity_type=EntityType.STANDARD, translation_key='time_reload', fallback_name='Time reload')
    .command_button(command_name=SeMeteringCluster.ServerCommandDefs.reset_energy_meters.name, cluster_id=SeMeteringCluster.cluster_id, entity_type=EntityType.STANDARD, initially_disabled=True, translation_key='energy_reset', fallback_name='Energy reset', unique_id_suffix='energy_reset')
    # switch: standard clusters, ZHA's own entities
    # power_on_behavior: standard clusters, ZHA's own entities
    # power: standard clusters, ZHA's own entities
    # voltage: standard clusters, ZHA's own entities
    # ac_frequency: standard clusters, ZHA's own entities
    # current: standard clusters, ZHA's own entities
    # energy: standard clusters, ZHA's own entities
    .filter(no_builtin_quirk)
    .add_to_registry()
)
