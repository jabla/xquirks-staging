"""DIYRuZ DIYRuZ_Geiger: DiY Geiger counter.

Generated from the Zigbee2MQTT definition.
Data: zigbee-herdsman-converters, MIT, Copyright (c) 2018 Koen Kanters.
Status: generated, not verified on hardware.
Revision: 9a185f6e
"""

import functools
import logging
import pathlib

import zhaquirks
from zha.quirks import DEVICE_REGISTRY, DeviceMatch
import zigpy.types as t
from zigpy.zcl.foundation import ZCLAttributeDef
from zigpy.zcl.clusters.measurement import IlluminanceLevelSensing

from zhaquirks.builder import (
    EntityType,
    QuirkBuilder,
)
from zhaquirks.clusters import CustomCluster


class MsIlluminanceLevelSensingCluster(CustomCluster, IlluminanceLevelSensing):
    """IlluminanceLevelSensing with the attributes z2m adds."""

    class AttributeDefs(IlluminanceLevelSensing.AttributeDefs):
        """Attribute definitions."""

        sensitivity = ZCLAttributeDef(id=0xF000, type=t.uint16_t, manufacturer_code=None)
        led_feedback = ZCLAttributeDef(id=0xF001, type=t.Bool, manufacturer_code=None)
        buzzer_feedback = ZCLAttributeDef(id=0xF002, type=t.Bool, manufacturer_code=None)
        sensors_count = ZCLAttributeDef(id=0xF003, type=t.uint8_t, manufacturer_code=None)
        sensors_type = ZCLAttributeDef(id=0xF004, type=t.enum8, manufacturer_code=None)
        alert_threshold = ZCLAttributeDef(id=0xF005, type=t.uint32_t, manufacturer_code=None)



_LOGGER = logging.getLogger(__name__)
_SHIPPED = pathlib.Path(zhaquirks.__file__).resolve().parent
_STEPPED_BACK: set = set()

# The Zigbee fingerprints (manufacturer, model) this quirk is for; None matches any manufacturer.
FINGERPRINTS = [(None, 'DIYRuZ_Geiger')]
# Names that a model-only fingerprint would catch but Zigbee2MQTT gives to other devices.
CLAIMED_ELSEWHERE = set()
# The endpoints this quirk needs, each with the input clusters it puts there where Zigbee2MQTT names none.
ENDPOINTS = {1: (0x0401,)}


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
    QuirkBuilder(None, 'DIYRuZ_Geiger')
    .replaces(MsIlluminanceLevelSensingCluster)
    .switch(attribute_name=MsIlluminanceLevelSensingCluster.AttributeDefs.led_feedback.name, cluster_id=MsIlluminanceLevelSensingCluster.cluster_id, entity_type=EntityType.STANDARD, translation_key='led_feedback', fallback_name='LED feedback')
    .switch(attribute_name=MsIlluminanceLevelSensingCluster.AttributeDefs.buzzer_feedback.name, cluster_id=MsIlluminanceLevelSensingCluster.cluster_id, entity_type=EntityType.STANDARD, translation_key='buzzer_feedback', fallback_name='Buzzer feedback')
    .number(attribute_name=MsIlluminanceLevelSensingCluster.AttributeDefs.alert_threshold.name, cluster_id=MsIlluminanceLevelSensingCluster.cluster_id, min_value=0, max_value=10000, unit='μR/h', entity_type=EntityType.STANDARD, translation_key='alert_threshold', fallback_name='Alert threshold')
    .number(attribute_name=MsIlluminanceLevelSensingCluster.AttributeDefs.sensors_count.name, cluster_id=MsIlluminanceLevelSensingCluster.cluster_id, min_value=0, max_value=50, entity_type=EntityType.STANDARD, translation_key='sensors_count', fallback_name='Sensors count')
    .number(attribute_name=MsIlluminanceLevelSensingCluster.AttributeDefs.sensitivity.name, cluster_id=MsIlluminanceLevelSensingCluster.cluster_id, min_value=0, max_value=100, entity_type=EntityType.STANDARD, translation_key='sensitivity', fallback_name='Sensitivity')
    # action: standard clusters or z2m's own code, not generated
    # radioactive_events_per_minute: z2m's own code, not generated
    # radiation_dose_per_hour: z2m's own code, not generated
    # sensors_type: z2m's own code, not generated
    .filter(no_builtin_quirk)
    .add_to_registry()
)
