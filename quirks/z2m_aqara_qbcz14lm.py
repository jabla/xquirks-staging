"""Aqara QBCZ14LM: Smart wall outlet T1.

Generated from the Zigbee2MQTT definition.
Data: zigbee-herdsman-converters, MIT, Copyright (c) 2018 Koen Kanters.
Status: generated, not verified on hardware.
Revision: a5f987d4
"""

import functools
import logging
import pathlib

import zhaquirks
from zha.quirks import DEVICE_REGISTRY, DeviceMatch
import zigpy.types as t
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef
from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement

from zhaquirks.builder import (
    EntityType,
    QuirkBuilder,
)
from zhaquirks.xiaomi import DeviceTemperatureCluster, ElectricalMeasurementCluster, MeteringCluster, XiaomiAqaraE1Cluster


class ManuSpecificLumiCluster(XiaomiAqaraE1Cluster):
    """manuSpecificLumi (z2m custom cluster) on zhaquirks' Xiaomi base."""

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        mode = ZCLAttributeDef(id=0x0009, type=t.uint8_t, manufacturer_code=0x115F)
        illuminance = ZCLAttributeDef(id=0x0112, type=t.uint32_t, manufacturer_code=0x115F)
        display_unit = ZCLAttributeDef(id=0x0114, type=t.uint8_t, manufacturer_code=0x115F)
        movement = ZCLAttributeDef(id=0x0118, type=t.uint8_t, access="r", manufacturer_code=0x115F)
        air_quality = ZCLAttributeDef(id=0x0129, type=t.uint8_t, manufacturer_code=0x115F)
        curtain_reverse = ZCLAttributeDef(id=0x0400, type=t.Bool, manufacturer_code=0x115F)
        curtain_hand_open = ZCLAttributeDef(id=0x0401, type=t.Bool, manufacturer_code=0x115F)
        curtain_calibrated = ZCLAttributeDef(id=0x0402, type=t.Bool, manufacturer_code=0x115F)
        power_outage_memory = ZCLAttributeDef(id=0x0201, type=t.Bool, manufacturer_code=0x115F)
        led_disabled_night = ZCLAttributeDef(id=0x0203, type=t.Bool, manufacturer_code=0x115F)
        button_lock = ZCLAttributeDef(id=0x0200, type=t.uint8_t, manufacturer_code=0x115F)

    # The struct keys of zhaquirks' Xiaomi base and the endpoint cluster it writes each one to.
    STRUCT_TARGETS = {
        "battery_voltage_mV": "power",
        "battery_percentage": "power",
        "temperature_measurement": "temperature",
        "humidity_measurement": "humidity",
        "pressure_measurement": "pressure",
        "pressure_measurement_precision": "pressure",
        "power": "electrical_measurement",
        "voltage": "electrical_measurement",
        "consumption": "smartenergy_metering",
        "illuminance_measurement": "illuminance",
        "tvoc_measurement": "voc_level",
        "smoke": "ias_zone",
    }

    # z2m's struct tags for this model, under the key the Xiaomi base routes (consumption to
    # metering in kWh, power in W, voltage as 0.1 V) and the factor from the raw value.
    STRUCT_TAGS = {149: ('consumption', 1.0), 150: ('voltage', 1.0), 151: ('current', 0.001), 152: ('power', 1.0)}

    def _parse_aqara_attributes(self, value):
        """Only the struct values whose cluster the endpoint has: the base class stops at a missing one."""
        attributes = super()._parse_aqara_attributes(value)
        for tag, (key, factor) in self.STRUCT_TAGS.items():
            if f"0xff01-{tag}" in attributes:
                attributes[key] = attributes.pop(f"0xff01-{tag}") * factor
        return {key: v for key, v in attributes.items() if key not in self.STRUCT_TARGETS or hasattr(self.endpoint, self.STRUCT_TARGETS[key])}

    def _handle_attribute_event(self, event):
        """The base has no key for the current: rms_current in mA (the cluster divides by 1000)."""
        super()._handle_attribute_event(event)
        if event.attribute_id == 0x00F7 and hasattr(self.endpoint, "electrical_measurement"):
            current = self._parse_aqara_attributes(event.value).get("current")
            if current is not None:
                self.endpoint.electrical_measurement.update_attribute(ElectricalMeasurement.AttributeDefs.rms_current.id, round(current * 1000))


class StructElectricalMeasurement(ElectricalMeasurementCluster):
    """Power, voltage and current from the Aqara struct; the current arrives in mA."""

    _CONSTANT_ATTRIBUTES = {
        **ElectricalMeasurementCluster._CONSTANT_ATTRIBUTES,
        ElectricalMeasurement.AttributeDefs.ac_current_multiplier.id: 1,
        ElectricalMeasurement.AttributeDefs.ac_current_divisor.id: 1000,
    }



_LOGGER = logging.getLogger(__name__)
_SHIPPED = pathlib.Path(zhaquirks.__file__).resolve().parent
_STEPPED_BACK: set = set()

# The Zigbee fingerprints (manufacturer, model) this quirk is for; None matches any manufacturer.
FINGERPRINTS = [(None, 'lumi.plug.sacn02')]
# Names that a model-only fingerprint would catch but Zigbee2MQTT gives to other devices.
CLAIMED_ELSEWHERE = set()
# The endpoints this quirk needs, each with the input clusters it puts there where Zigbee2MQTT names none.
ENDPOINTS = {1: (0xFCC0,)}


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
    QuirkBuilder(None, 'lumi.plug.sacn02')
    .replaces(ManuSpecificLumiCluster)
    .adds(DeviceTemperatureCluster)
    .adds(StructElectricalMeasurement)
    .adds(MeteringCluster)
    .switch(attribute_name=ManuSpecificLumiCluster.AttributeDefs.power_outage_memory.name, cluster_id=ManuSpecificLumiCluster.cluster_id, entity_type=EntityType.CONFIG, translation_key='power_outage_memory', fallback_name='Power outage memory')
    .switch(attribute_name=ManuSpecificLumiCluster.AttributeDefs.led_disabled_night.name, cluster_id=ManuSpecificLumiCluster.cluster_id, entity_type=EntityType.CONFIG, translation_key='led_disabled_night', fallback_name='LED disabled night')
    .switch(attribute_name=ManuSpecificLumiCluster.AttributeDefs.button_lock.name, cluster_id=ManuSpecificLumiCluster.cluster_id, on_value=0, off_value=1, entity_type=EntityType.CONFIG, translation_key='button_lock', fallback_name='Button lock')
    # switch: standard clusters, ZHA's own entities
    # power: Aqara struct (0x00F7), ElectricalMeasurementCluster
    # energy: Aqara struct (0x00F7), MeteringCluster
    # device_temperature: Aqara struct (0x00F7), DeviceTemperatureCluster
    # voltage: Aqara struct (0x00F7), ElectricalMeasurementCluster
    # current: Aqara struct (0x00F7), ElectricalMeasurementCluster
    # overload_protection: standard clusters or z2m's own code, not generated
    .filter(no_builtin_quirk)
    .add_to_registry()
)
