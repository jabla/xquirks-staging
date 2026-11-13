# Contributing

Thanks for helping. Most help needs no code: you report what a device you own does. The quirk files
are generated from the Zigbee2MQTT device library, so nobody edits them by hand: I turn reports into
corrections, which reach you with a later state of the files.

Reports go through the issue forms of this repository. The finder and the integration open them
prefilled.

## A wrong or missing value

Use the "Wrong or missing value" form for a wrong value, a missing entity or a setting that does not
stick. What helps most:

- the quirk file and its revision (the `Revision:` line at its top or the integration's
  diagnostics)
- for a wrong value, two or three pairs of what Home Assistant and the device's display or app show
  at the same time: they become the expected values of the fix
- the device's diagnostics (the device's page > three-dot menu > Download diagnostics) or better a
  probe report.

## A device test ("verified")

A file becomes "verified" when someone checked its entities against the device itself: its display,
its app or what it does. `tools/probe.py` collects what that needs. Run it from a clone of this
repository. It needs Python's standard library only. `HASS_TOKEN` is a long-lived access token
(your profile > Security > Long-lived access tokens):

```bash
HASS_URL=http://homeassistant.local:8123 HASS_TOKEN=... python tools/probe.py "<device name>" --query
```

The probe reads the device, its entities, their states and the device diagnostics (IEEE addresses
removed). `--query` asks the device for its current values, which changes nothing on it. It writes
only with `--write <entity id>`: it sets one configuration number or select to its limits or
another option, reads it back and sets it back. It never writes a switch, button, siren or alarm.
Tick the boxes in `probe-report/report.md` that match the device, then attach it with
`probe-report/diagnostics.json` to the "Device test" form.

## A file that does not fit your device

When a quirk does not fit your device, the integration says so in a notice. It links the "Device
layout" form with the device's endpoints and clusters filled in, without its name or address: submit
it as it is. Without the integration, paste the device's diagnostics into that form. The issue shows
the whole file, so check it first.

## A device without a file

Look it up in the [finder](https://jabla.github.io/xquirks/) first. If Zigbee2MQTT supports it and it
has no file here, use the "Device without a file" form with its Zigbee2MQTT device page. Some kinds
of devices get no file yet.

## Translations

The integration's texts are in `custom_components/xquirks/translations/<language>.json`. Pull
requests that add or improve a language are welcome. CI checks that each file has the keys and
placeholders of `en.json`. A change to the English text goes into both `en.json` and `strings.json`.

## The integration or the finder

Report bugs in `custom_components/xquirks/` or `site/` as issues or send a pull request. Tests:
`pip install -r tests_hacs/requirements.txt`, then `python -m pytest tests_hacs` (the finder's tests
need node).

## Upstream

Missing or wrong values of a quirk that ships with ZHA belong to
[zha-device-handlers](https://github.com/zigpy/zha-device-handlers/issues).
