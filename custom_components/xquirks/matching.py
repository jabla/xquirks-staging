"""Which manifest entries match which devices.

A device is a (manufacturer, model) pair as the device registry shows it. An entry matches when
one of its fingerprints has the device's model and either no manufacturer (any) or the device's
manufacturer, unless the entry leaves that exact pair to another device (claimed_elsewhere).
The finder page (site/matcher.js) matches the same way; tests_hacs/test_finder.py compares both.
"""

from __future__ import annotations

Pair = tuple[str, str]


def matches(manifest: dict, devices: set[Pair]) -> list[tuple[Pair, str, dict]]:
    result = []
    for slug, entry in sorted(manifest.items()):
        claimed = {tuple(fp) for fp in entry.get("claimed_elsewhere", [])}
        for device in sorted(devices):
            # One line per device, also when it matches an exact and a model-only fingerprint.
            if device not in claimed and any(device[1] == model and manufacturer in (None, device[0]) for manufacturer, model in entry["fingerprints"]):
                result.append((device, slug, entry))
    return result
