"""Heiman HS2NLV: Smart notifier.

Generated from the Zigbee2MQTT definition.
Data: zigbee-herdsman-converters, MIT, Copyright (c) 2018 Koen Kanters.
Status: generated, not verified on hardware.
Revision: 01fb520e
"""

import functools
import logging
import pathlib

import zhaquirks
from zha.quirks import DEVICE_REGISTRY, DeviceMatch
import zigpy.types as t
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef

from zhaquirks.builder import (
    EntityType,
    QuirkBuilder,
)
from zhaquirks.clusters import CustomCluster


class HeimanClusterSpecialCluster(CustomCluster):
    """heimanClusterSpecial (z2m custom cluster)."""

    cluster_id = 0xFC90

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        sensor_preheating_state = ZCLAttributeDef(id=0x0000, type=t.enum8, manufacturer_code=0x120B)
        sensor_self_check_state = ZCLAttributeDef(id=0x0001, type=t.enum8, manufacturer_code=0x120B)
        sensor_fault_state = ZCLAttributeDef(id=0x0002, type=t.uint16_t, manufacturer_code=0x120B)
        sensor_pollution_level = ZCLAttributeDef(id=0x0003, type=t.uint8_t, manufacturer_code=0x120B)
        sensor_sensitivity_level = ZCLAttributeDef(id=0x0004, type=t.uint8_t, manufacturer_code=0x120B)
        sensor_prealarm_threshold = ZCLAttributeDef(id=0x0005, type=t.enum8, manufacturer_code=0x120B)
        sensor_life_state = ZCLAttributeDef(id=0x0006, type=t.enum8, manufacturer_code=0x120B)
        sensor_life_time = ZCLAttributeDef(id=0x0007, type=t.uint16_t, manufacturer_code=0x120B)
        device_mute_control = ZCLAttributeDef(id=0x0008, type=t.uint8_t, manufacturer_code=0x120B)
        device_mute_state = ZCLAttributeDef(id=0x0009, type=t.bitmap16, manufacturer_code=0x120B)
        device_cascade_control_enable = ZCLAttributeDef(id=0x000A, type=t.bitmap8, manufacturer_code=0x120B)
        device_sound_tone_type = ZCLAttributeDef(id=0x000B, type=t.enum8, manufacturer_code=0x120B)
        # device_sound_control 0x000C: ARRAY, attribute only
        # device_blink_control 0x000D: ARRAY, attribute only
        smoke_ad_value = ZCLAttributeDef(id=0x000E, type=t.uint16_t, manufacturer_code=0x120B)
        smoke_alarm_type = ZCLAttributeDef(id=0x000F, type=t.enum8, manufacturer_code=0x120B)
        smoke_water_mist_state = ZCLAttributeDef(id=0x0010, type=t.enum8, manufacturer_code=0x120B)
        # smoke_sensor_data 0x0011: ARRAY, attribute only
        device_cascade_state = ZCLAttributeDef(id=0x0012, type=t.enum8, manufacturer_code=0x120B)
        sensor_prealarm_state = ZCLAttributeDef(id=0x0013, type=t.enum8, manufacturer_code=0x120B)
        smoke_concentration_level = ZCLAttributeDef(id=0x0016, type=t.uint8_t, access="r", manufacturer_code=0x120B)
        smoke_chamber_contamination_level = ZCLAttributeDef(id=0x0017, type=t.uint8_t, access="r", manufacturer_code=0x120B)
        smoke_concentation_unit = ZCLAttributeDef(id=0x0018, type=t.uint8_t, access="r", manufacturer_code=0x120B)
        emergency_state_control = ZCLAttributeDef(id=0x001C, type=t.uint8_t, manufacturer_code=0x120B)
        sensor_sampling_period = ZCLAttributeDef(id=0x001D, type=t.uint16_t, manufacturer_code=0x120B)
        occupany_sensor_work_mode = ZCLAttributeDef(id=0x001E, type=t.bitmap8, manufacturer_code=0x120B)
        occupied_to_occupied_interval = ZCLAttributeDef(id=0x001F, type=t.uint16_t, manufacturer_code=0x120B)
        occupied_to_occupied_duration = ZCLAttributeDef(id=0x0020, type=t.uint16_t, manufacturer_code=0x120B)
        radar_config_param_of_section1 = ZCLAttributeDef(id=0x0021, type=t.LVBytes, manufacturer_code=0x120B)
        radar_config_param_of_section2 = ZCLAttributeDef(id=0x0022, type=t.LVBytes, manufacturer_code=0x120B)
        radar_config_param_of_section3 = ZCLAttributeDef(id=0x0023, type=t.LVBytes, manufacturer_code=0x120B)
        radar_config_param_of_section4 = ZCLAttributeDef(id=0x0024, type=t.LVBytes, manufacturer_code=0x120B)
        radar_micro_threshold_param = ZCLAttributeDef(id=0x0025, type=t.LVBytes, manufacturer_code=0x120B)
        radar_persence_threshold_param = ZCLAttributeDef(id=0x0026, type=t.LVBytes, manufacturer_code=0x120B)
        radar_learning_control = ZCLAttributeDef(id=0x0027, type=t.uint16_t, manufacturer_code=0x120B)
        radar_learning_state = ZCLAttributeDef(id=0x0028, type=t.enum8, access="r", manufacturer_code=0x120B)
        radar_detection_target_range = ZCLAttributeDef(id=0x0029, type=t.uint16_t, access="r", manufacturer_code=0x120B)
        radar_detection_min_range = ZCLAttributeDef(id=0x002B, type=t.uint16_t, manufacturer_code=0x120B)
        radar_detection_max_range = ZCLAttributeDef(id=0x002C, type=t.uint16_t, manufacturer_code=0x120B)
        shielding_sensor_detection = ZCLAttributeDef(id=0x002D, type=t.uint16_t, manufacturer_code=0x120B)
        dew_point = ZCLAttributeDef(id=0x0033, type=t.int16s, access="r", manufacturer_code=0x120B)
        vpd = ZCLAttributeDef(id=0x0034, type=t.uint16_t, access="r", manufacturer_code=0x120B)
        thi = ZCLAttributeDef(id=0x0035, type=t.uint16_t, access="r", manufacturer_code=0x120B)
        heat_index = ZCLAttributeDef(id=0x0036, type=t.int16s, access="r", manufacturer_code=0x120B)
        sound_volume = ZCLAttributeDef(id=0x0047, type=t.uint8_t, manufacturer_code=0x120B)
        indicator_light_control = ZCLAttributeDef(id=0x1000, type=t.bitmap8, manufacturer_code=0x120B)
        indicator_light_not_disturb_start_time = ZCLAttributeDef(id=0x1001, type=t.uint16_t, manufacturer_code=0x120B)
        indicator_light_not_disturb_end_time = ZCLAttributeDef(id=0x1002, type=t.uint16_t, manufacturer_code=0x120B)
        indicator_light_not_disturb_enable = ZCLAttributeDef(id=0x1003, type=t.uint8_t, manufacturer_code=0x120B)
        indicator_light_level_control_of1 = ZCLAttributeDef(id=0x1004, type=t.uint8_t, manufacturer_code=0x120B)
        indicator_light_level_control_of2 = ZCLAttributeDef(id=0x1005, type=t.uint8_t, manufacturer_code=0x120B)
        indicator_light_level_control_of3 = ZCLAttributeDef(id=0x1006, type=t.uint8_t, manufacturer_code=0x120B)
        interconnectable = ZCLAttributeDef(id=0x1007, type=t.uint8_t, access="r", manufacturer_code=0x120B)
        indicator_light_on_off = ZCLAttributeDef(id=0x1008, type=t.uint8_t, manufacturer_code=0x120B)
        remote_self_test = ZCLAttributeDef(id=0x1009, type=t.uint8_t, access="r", manufacturer_code=0x120B)
        fixed_room_name = ZCLAttributeDef(id=0x100B, type=t.enum8, manufacturer_code=0x120B)
        language = ZCLAttributeDef(id=0x100C, type=t.enum8, manufacturer_code=0x120B)
        floors = ZCLAttributeDef(id=0x100E, type=t.enum8, manufacturer_code=0x120B)
        fixed_voices = ZCLAttributeDef(id=0x100F, type=t.enum8, manufacturer_code=0x120B)
        temperature_offset = ZCLAttributeDef(id=0x100D, type=t.int16s, manufacturer_code=0x120B)
        switch_type = ZCLAttributeDef(id=0x1010, type=t.enum8, manufacturer_code=0x120B)
        humidity_offset = ZCLAttributeDef(id=0x1012, type=t.int16s, manufacturer_code=0x120B)
        rebooted_count = ZCLAttributeDef(id=0x0019, type=t.uint16_t, access="r", manufacturer_code=0x120B)
        rejoined_count = ZCLAttributeDef(id=0x001A, type=t.uint16_t, access="r", manufacturer_code=0x120B)
        reported_packages = ZCLAttributeDef(id=0x001B, type=t.uint16_t, access="r", manufacturer_code=0x120B)
        illuminance_threshold = ZCLAttributeDef(id=0x002A, type=t.uint16_t, manufacturer_code=0x120B)
        mcu_software_version = ZCLAttributeDef(id=0x0030, type=t.uint8_t, access="r", manufacturer_code=0x120B)
        wifi_ssid = ZCLAttributeDef(id=0x2000, type=t.CharacterString, manufacturer_code=0x120B)
        wifi_password = ZCLAttributeDef(id=0x2001, type=t.CharacterString, manufacturer_code=0x120B)
        wifi_ssid_candidate = ZCLAttributeDef(id=0x2002, type=t.CharacterString, manufacturer_code=0x120B)
        wifi_password_candidate = ZCLAttributeDef(id=0x2003, type=t.CharacterString, manufacturer_code=0x120B)
        picture_quantity = ZCLAttributeDef(id=0x2004, type=t.uint8_t, manufacturer_code=0x120B)
        picture_quality = ZCLAttributeDef(id=0x2005, type=t.uint8_t, manufacturer_code=0x120B)
        server_address = ZCLAttributeDef(id=0x2006, type=t.CharacterString, access="r", manufacturer_code=0x120B)
        server_address_candidae = ZCLAttributeDef(id=0x2007, type=t.CharacterString, access="r", manufacturer_code=0x120B)
        server_port = ZCLAttributeDef(id=0x2008, type=t.uint8_t, access="r", manufacturer_code=0x120B)
        auth_token = ZCLAttributeDef(id=0x2009, type=t.CharacterString, access="r", manufacturer_code=0x120B)
        zone_capture_mode = ZCLAttributeDef(id=0x200A, type=t.uint8_t, access="r", manufacturer_code=0x120B)
        sensor_armed = ZCLAttributeDef(id=0x200B, type=t.uint8_t, manufacturer_code=0x120B)
        wifi_status = ZCLAttributeDef(id=0x200C, type=t.uint8_t, access="r", manufacturer_code=0x120B)
        wifi_candidate_status = ZCLAttributeDef(id=0x200D, type=t.uint8_t, access="r", manufacturer_code=0x120B)
        wifi_rssi = ZCLAttributeDef(id=0x200E, type=t.int8s, manufacturer_code=0x120B)
        server_status = ZCLAttributeDef(id=0x200F, type=t.int8s, access="r", manufacturer_code=0x120B)
        server_candidate_status = ZCLAttributeDef(id=0x2010, type=t.int8s, access="r", manufacturer_code=0x120B)
        camera_ready = ZCLAttributeDef(id=0x2013, type=t.int8s, access="r", manufacturer_code=0x120B)
        flash_light_brightness = ZCLAttributeDef(id=0x2012, type=t.int8s, access="r", manufacturer_code=0x120B)
        camera_mode = ZCLAttributeDef(id=0x2014, type=t.int8s, access="r", manufacturer_code=0x120B)
        light_effect = ZCLAttributeDef(id=0x2020, type=t.enum8, manufacturer_code=0x120B)
        light_speed = ZCLAttributeDef(id=0x2021, type=t.uint8_t, manufacturer_code=0x120B)
        light_intensity = ZCLAttributeDef(id=0x2022, type=t.uint8_t, manufacturer_code=0x120B)
        light_palette = ZCLAttributeDef(id=0x2023, type=t.enum8, manufacturer_code=0x120B)
        light_custom1 = ZCLAttributeDef(id=0x2024, type=t.uint8_t, manufacturer_code=0x120B)
        light_custom2 = ZCLAttributeDef(id=0x2025, type=t.uint8_t, manufacturer_code=0x120B)
        light_custom3 = ZCLAttributeDef(id=0x2026, type=t.uint8_t, manufacturer_code=0x120B)
        light_options = ZCLAttributeDef(id=0x2027, type=t.bitmap8, manufacturer_code=0x120B)
        light_effect_count = ZCLAttributeDef(id=0x2028, type=t.uint16_t, access="r", manufacturer_code=0x120B)
        light_pixel_count = ZCLAttributeDef(id=0x2029, type=t.uint16_t, manufacturer_code=0x120B)


class LightEffect(t.enum8):
    """light_effect values (z2m)."""

    solid = 0x00
    blink = 0x01
    breathe = 0x02
    wipe = 0x03
    wipe_random = 0x04
    random_colors = 0x05
    sweep = 0x06
    dynamic = 0x07
    colorloop = 0x08
    rainbow = 0x09
    scan = 0x0A
    dual_scan = 0x0B
    fade = 0x0C
    theater = 0x0D
    theater_rainbow = 0x0E
    running = 0x0F
    saw = 0x10
    twinkle = 0x11
    dissolve = 0x12
    dissolve_random = 0x13
    sparkle = 0x14
    dark_sparkle = 0x15
    sparkle_plus = 0x16
    strobe = 0x17
    strobe_rainbow = 0x18
    mega_strobe = 0x19
    blink_rainbow = 0x1A
    android = 0x1B
    chase = 0x1C
    chase_random = 0x1D
    chase_rainbow = 0x1E
    chase_flash = 0x1F
    chase_flash_random = 0x20
    rainbow_runner = 0x21
    colorful = 0x22
    traffic_light = 0x23
    sweep_random = 0x24
    running_2 = 0x25
    aurora = 0x26
    stream = 0x27
    scanner = 0x28
    comet = 0x29
    fireworks = 0x2A
    rain = 0x2B
    tetrix = 0x2C
    fire_flicker = 0x2D
    gradient = 0x2E
    loading = 0x2F
    rolling_balls = 0x30
    fairy = 0x31
    two_dots = 0x32
    fairy_twinkle = 0x33
    running_dual = 0x34
    image = 0x35
    tricolor_chase = 0x36
    tricolor_wipe = 0x37
    tricolor_fade = 0x38
    lightning = 0x39
    icu = 0x3A
    multi_comet = 0x3B
    dual_scanner = 0x3C
    random_chase = 0x3D
    oscillate = 0x3E
    pride_2015 = 0x3F
    juggle = 0x40
    palette = 0x41
    fire_2012 = 0x42
    colorwaves = 0x43
    bpm = 0x44
    fill_noise = 0x45
    noise_1 = 0x46
    noise_2 = 0x47
    noise_3 = 0x48
    noise_4 = 0x49
    color_twinkle = 0x4A
    lake = 0x4B
    meteor = 0x4C
    copy = 0x4D
    railway = 0x4E
    ripple = 0x4F
    twinklefox = 0x50
    twinklecat = 0x51
    halloween_eyes = 0x52
    static_pattern = 0x53
    tri_static_pattern = 0x54
    spots = 0x55
    spots_fade = 0x56
    glitter = 0x57
    candle = 0x58
    starburst = 0x59
    exploding_fireworks = 0x5A
    bouncing_balls = 0x5B
    sinelon = 0x5C
    sinelon_dual = 0x5D
    sinelon_rainbow = 0x5E
    popcorn = 0x5F
    drip = 0x60
    plasma = 0x61
    percent = 0x62
    ripple_rainbow = 0x63
    heartbeat = 0x64
    pacifica = 0x65
    candle_multi = 0x66
    solid_glitter = 0x67
    sunrise = 0x68
    phased = 0x69
    twinkleup = 0x6A
    noisepal = 0x6B
    sinewave = 0x6C
    phased_noise = 0x6D
    flow = 0x6E
    chunchun = 0x6F
    dancing_shadows = 0x70
    washing_machine = 0x71
    Effect_2d_plasma_rotozoom = 0x72
    blends = 0x73
    tv_simulator = 0x74
    dynamic_smooth = 0x75
    Effect_2d_spaceships = 0x76
    Effect_2d_crazy_bees = 0x77
    Effect_2d_ghost_rider = 0x78
    Effect_2d_blobs = 0x79
    Effect_2d_scroll_text = 0x7A
    Effect_2d_drift_rose = 0x7B
    Effect_2d_distortion_waves = 0x7C
    Effect_2d_soap = 0x7D
    Effect_2d_octopus = 0x7E
    Effect_2d_waving_cell = 0x7F
    pixels = 0x80
    pixelwave = 0x81
    juggles = 0x82
    matripix = 0x83
    gravimeter = 0x84
    plasmoid = 0x85
    puddles = 0x86
    midnoise = 0x87
    noisemeter = 0x88
    freqwave = 0x89
    freqmatrix = 0x8A
    Effect_2d_geq = 0x8B
    waterfall = 0x8C
    freqpixels = 0x8D
    binmap = 0x8E
    noisefire = 0x8F
    puddlepeak = 0x90
    noisemove = 0x91
    Effect_2d_noise = 0x92
    perlinmove = 0x93
    ripplepeak = 0x94
    Effect_2d_firenoise = 0x95
    Effect_2d_squared_swirl = 0x96
    pacman = 0x97
    Effect_2d_dna = 0x98
    Effect_2d_matrix = 0x99
    Effect_2d_metaballs = 0x9A
    freqmap = 0x9B
    gravcenter = 0x9C
    gravcentric = 0x9D
    gravfreq = 0x9E
    dj_light = 0x9F
    Effect_2d_funky_plank = 0xA0
    shimmer = 0xA1
    Effect_2d_pulser = 0xA2
    blurz = 0xA3
    Effect_2d_drift = 0xA4
    Effect_2d_waverly = 0xA5
    Effect_2d_sun_radiation = 0xA6
    Effect_2d_colored_bursts = 0xA7
    Effect_2d_julia = 0xA8
    reserved_169 = 0xA9
    reserved_170 = 0xAA
    reserved_171 = 0xAB
    Effect_2d_game_of_life = 0xAC
    Effect_2d_tartan = 0xAD
    Effect_2d_polar_lights = 0xAE
    Effect_2d_swirl = 0xAF
    Effect_2d_lissajous = 0xB0
    Effect_2d_frizzles = 0xB1
    Effect_2d_plasma_ball = 0xB2
    flow_stripe = 0xB3
    Effect_2d_hiphotic = 0xB4
    Effect_2d_sin_dots = 0xB5
    Effect_2d_dna_spiral = 0xB6
    Effect_2d_black_hole = 0xB7
    wavesins = 0xB8
    rocktaves = 0xB9
    Effect_2d_akemi = 0xBA
    particle_volcano = 0xBB
    particle_fire = 0xBC
    particle_fireworks = 0xBD
    particle_vortex = 0xBE
    particle_perlin = 0xBF
    particle_pit = 0xC0
    particle_box = 0xC1
    particle_attractor = 0xC2
    particle_impact = 0xC3
    particle_waterfall = 0xC4
    particle_spray = 0xC5
    particles_geq = 0xC6
    particle_center_geq = 0xC7
    particle_ghost_rider = 0xC8
    particle_blobs = 0xC9
    ps_drip = 0xCA
    ps_pinball = 0xCB
    ps_dancing_shadows = 0xCC
    ps_fireworks_1d = 0xCD
    ps_sparkler = 0xCE
    ps_hourglass = 0xCF
    ps_1d_spray = 0xD0
    ps_balance = 0xD1
    ps_chase = 0xD2
    ps_starburst = 0xD3
    ps_1d_geq = 0xD4
    ps_fire_1d = 0xD5
    ps_1d_sonic_stream = 0xD6
    ps_1d_sonic_boom = 0xD7
    ps_1d_springy = 0xD8
    particle_galaxy = 0xD9
    color_clouds = 0xDA
    slow_transition = 0xDB


class Language(t.enum8):
    """language values (z2m)."""

    english = 0x00
    german = 0x01
    french = 0x02
    italian = 0x03
    spanish = 0x04


class Room(t.enum8):
    """room values (z2m)."""

    no_location = 0x00
    attic = 0x01
    basement = 0x02
    bedroom = 0x03
    child_room = 0x04
    den = 0x05
    dining_room = 0x06
    entryway = 0x07
    family_room = 0x08
    guest_bedroom = 0x09
    hallway = 0x0A
    kitchen = 0x0B
    living_room = 0x0C
    master_bedroom = 0x0D
    office = 0x0E
    utility_room = 0x0F
    other_room = 0x10


class Floor(t.enum8):
    """floor values (z2m)."""

    no_floor = 0x00
    ground_floor = 0x01
    first_floor = 0x02
    second_floor = 0x03
    third_floor = 0x04
    fourth_floor = 0x05


class Voice(t.enum8):
    """voice values (z2m)."""

    unset = 0x00
    boot_ready = 0x01
    test_intro = 0x02
    smoke_warning = 0x03
    smoke_silenced = 0x04
    co_warning = 0x05
    co_silenced = 0x06
    smoke_cannot_be_silenced = 0x07
    co_cannot_be_silenced = 0x08
    low_battery = 0x09
    smoke_sensor_malfunction = 0x0A
    co_sensor_open_circuit = 0x0B
    co_sensor_short_circuit = 0x0C
    end_of_life = 0x0D
    room_selection_instructions = 0x0E
    floor_selection_instructions = 0x0F
    room_saved = 0x10
    floor_saved = 0x11
    no_room_saved = 0x12
    no_floor_saved = 0x13
    language_change = 0x14
    selected = 0x15
    evacuate = 0x16
    count_five = 0x17
    count_four = 0x18
    count_three = 0x19
    count_two = 0x1A
    count_one = 0x1B
    communication_mode_matter = 0x1C
    communication_mode_zigbee = 0x1D
    network_joined = 0x1E
    network_join_failed = 0x1F
    language_set = 0x20



_LOGGER = logging.getLogger(__name__)
_SHIPPED = pathlib.Path(zhaquirks.__file__).resolve().parent
_STEPPED_BACK: set = set()

# The Zigbee fingerprints (manufacturer, model) this quirk is for; None matches any manufacturer.
FINGERPRINTS = [(None, 'HS2NLV')]
# Names that a model-only fingerprint would catch but Zigbee2MQTT gives to other devices.
CLAIMED_ELSEWHERE = set()
# The endpoints this quirk needs, each with the input clusters it puts there where Zigbee2MQTT names none.
ENDPOINTS = {1: (0xFC90,)}


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
    QuirkBuilder(None, 'HS2NLV')
    .replaces(HeimanClusterSpecialCluster)
    .enum(attribute_name=HeimanClusterSpecialCluster.AttributeDefs.light_effect.name, cluster_id=HeimanClusterSpecialCluster.cluster_id, enum_class=LightEffect, entity_type=EntityType.STANDARD, translation_key='light_effect', fallback_name='Light effect')
    .number(attribute_name=HeimanClusterSpecialCluster.AttributeDefs.light_speed.name, cluster_id=HeimanClusterSpecialCluster.cluster_id, min_value=0, max_value=255, entity_type=EntityType.STANDARD, translation_key='light_speed', fallback_name='Light speed')
    .number(attribute_name=HeimanClusterSpecialCluster.AttributeDefs.light_intensity.name, cluster_id=HeimanClusterSpecialCluster.cluster_id, min_value=0, max_value=255, entity_type=EntityType.STANDARD, translation_key='light_intensity', fallback_name='Light intensity')
    .number(attribute_name=HeimanClusterSpecialCluster.AttributeDefs.light_palette.name, cluster_id=HeimanClusterSpecialCluster.cluster_id, min_value=0, max_value=255, entity_type=EntityType.STANDARD, translation_key='light_palette', fallback_name='Light palette')
    .number(attribute_name=HeimanClusterSpecialCluster.AttributeDefs.light_options.name, cluster_id=HeimanClusterSpecialCluster.cluster_id, min_value=0, max_value=255, entity_type=EntityType.STANDARD, translation_key='light_options', fallback_name='Light options')
    .sensor(attribute_name=HeimanClusterSpecialCluster.AttributeDefs.light_effect_count.name, cluster_id=HeimanClusterSpecialCluster.cluster_id, entity_type=EntityType.STANDARD, translation_key='light_effect_count', fallback_name='Light effect count')
    .number(attribute_name=HeimanClusterSpecialCluster.AttributeDefs.light_pixel_count.name, cluster_id=HeimanClusterSpecialCluster.cluster_id, min_value=0, max_value=1000, entity_type=EntityType.STANDARD, translation_key='light_pixel_count', fallback_name='Light pixel count')
    .number(attribute_name=HeimanClusterSpecialCluster.AttributeDefs.sound_volume.name, cluster_id=HeimanClusterSpecialCluster.cluster_id, min_value=0, max_value=100, entity_type=EntityType.STANDARD, translation_key='sound_volume', fallback_name='Sound volume')
    .enum(attribute_name=HeimanClusterSpecialCluster.AttributeDefs.language.name, cluster_id=HeimanClusterSpecialCluster.cluster_id, enum_class=Language, entity_type=EntityType.STANDARD, translation_key='language', fallback_name='Language')
    .enum(attribute_name=HeimanClusterSpecialCluster.AttributeDefs.fixed_room_name.name, cluster_id=HeimanClusterSpecialCluster.cluster_id, enum_class=Room, entity_type=EntityType.STANDARD, translation_key='room', fallback_name='Room')
    .enum(attribute_name=HeimanClusterSpecialCluster.AttributeDefs.floors.name, cluster_id=HeimanClusterSpecialCluster.cluster_id, enum_class=Floor, entity_type=EntityType.STANDARD, translation_key='floor', fallback_name='Floor')
    .enum(attribute_name=HeimanClusterSpecialCluster.AttributeDefs.fixed_voices.name, cluster_id=HeimanClusterSpecialCluster.cluster_id, enum_class=Voice, entity_type=EntityType.STANDARD, translation_key='voice', fallback_name='Voice')
    .number(attribute_name=HeimanClusterSpecialCluster.AttributeDefs.temperature_offset.name, cluster_id=HeimanClusterSpecialCluster.cluster_id, min_value=-15, max_value=15, step=0.1, multiplier=0.01, entity_type=EntityType.STANDARD, translation_key='temperature_offset', fallback_name='Temperature offset')
    .number(attribute_name=HeimanClusterSpecialCluster.AttributeDefs.humidity_offset.name, cluster_id=HeimanClusterSpecialCluster.cluster_id, min_value=-15, max_value=15, step=0.1, multiplier=0.01, entity_type=EntityType.STANDARD, translation_key='humidity_offset', fallback_name='Humidity offset')
    .sensor(attribute_name=HeimanClusterSpecialCluster.AttributeDefs.reported_packages.name, cluster_id=HeimanClusterSpecialCluster.cluster_id, entity_type=EntityType.STANDARD, translation_key='reported_packages', fallback_name='Reported packages')
    .sensor(attribute_name=HeimanClusterSpecialCluster.AttributeDefs.rejoined_count.name, cluster_id=HeimanClusterSpecialCluster.cluster_id, entity_type=EntityType.STANDARD, translation_key='rejoin_count', fallback_name='Rejoin count')
    .sensor(attribute_name=HeimanClusterSpecialCluster.AttributeDefs.rebooted_count.name, cluster_id=HeimanClusterSpecialCluster.cluster_id, entity_type=EntityType.STANDARD, translation_key='reboot_count', fallback_name='Reboot count')
    # identify: standard clusters, ZHA's own entities
    # light: standard clusters, ZHA's own entities
    # power_on_behavior: standard clusters, ZHA's own entities
    # temperature: standard clusters, ZHA's own entities
    # humidity: standard clusters, ZHA's own entities
    .filter(no_builtin_quirk)
    .add_to_registry()
)
