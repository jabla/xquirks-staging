"""Markdown for the repair issues and fix flows (English, like the quirks' entity names).

Strings from the manifest, withdrawn.toml and the device registry go in as plain text (plain()) or
as known values only: the dialogs render markdown, images and links included.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from urllib.parse import quote, urlencode

from . import plan as plans
from .changes import LIMIT, Summary, plain
from .const import REPOSITORY
from .plan import Device, Lost, Misfit, Plan

UPSTREAM_PR = "https://github.com/zigpy/zha-device-handlers/pull/{number}"
# A new issue in this collection's repository through its "Device layout" form
# (.github/ISSUE_TEMPLATE/device-layout.yml): GitHub fills the form's fields from the query by their ids.
REPORT = f"https://github.com/{REPOSITORY}/issues/new"
REPORT_FORM = "device-layout.yml"
# GitHub answers a longer address with 414: past this the signature leaves its output clusters out,
# then gives way to a note.
REPORT_LIMIT = 6000
# Manage Zigbee device > Signature shows the quirk's signature on a device that runs one; the device's
# diagnostics hold the one before the quirk (original_signature), which a device layout report needs.
REPORT_TOO_LONG = ("Too long for the link: paste the device's diagnostics here (the device's page > three-dot menu > Download diagnostics;"
                   " they also hold its network address and attribute values, which this issue then shows);"
                   " for a device that runs no quirk, Manage Zigbee device > Signature in that menu is enough.")

STATUS = {
    "generated": "generated from Zigbee2MQTT, not verified on a device yet",
    "verified": "verified on a device",
}

# Why a file of ours goes.
REMOVALS = {
    plans.MOVED: "another file of this collection is for one of its devices",
    plans.SHIPPED: "ZHA ships a quirk for this device now, this file steps back",
    plans.HANDED_BACK: "ZHA can handle this device by itself now, xquirks is no longer needed for it",
    plans.LEFT_OUT: "the devices that used it are left out (disabled, or excluded in the options)",
    plans.UNUSED: "none of your ZHA devices uses it any more",
    plans.OUTSIDE: "it is in a folder ZHA no longer loads custom quirks from",
}


def status(entry: dict) -> str:
    return STATUS.get(entry["status"], "unknown")


def label(entry: dict | None, name: str) -> str:
    """How the notices name a quirk file: the device it is for, the file name when the state in use no longer has it."""
    if not entry:
        return name
    device = f"{entry['vendor']} {entry['model']}"
    return f"{device}: {entry['description']}" if entry.get("description") else device


def offer_title(entry: dict, count: int) -> dict[str, str]:
    return {"vendor": entry["vendor"], "model": entry["model"], "count": str(count), "quirk": label(entry, "")}


def runs(device: Device, ours: frozenset[str] = frozenset()) -> str:
    """What ZHA runs on the device, for the dialogs (ours: the names of the files of ours in the folder)."""
    quirk = device.quirk
    if quirk is None:
        return "not known yet"
    if quirk == "":
        return "no quirk"
    if quirk.startswith("zhaquirks."):
        return f"the quirk ZHA ships (`{quirk}`)"
    if f"{quirk}.py" in ours:
        return f"`{quirk}` from this collection"
    if quirk.startswith(plans.PREFIX):
        return f"`{quirk}`, a file this integration does not manage (yours, or gone since ZHA loaded the folder)"
    return f"the custom quirk `{quirk}`"


def device_list(ids, devices: dict[str, Device], ours: frozenset[str] = frozenset()) -> str:
    lines = [
        f"- {plain(devices[i].name)} ({plain(devices[i].manufacturer)} {plain(devices[i].model)}), runs {runs(devices[i], ours)}"
        for i in sorted(ids, key=lambda i: devices[i].name)
        if i in devices
    ]
    return "\n".join(lines) or "- no device"


def report_url(entry: dict, name: str, device: Device, signature: dict, why: str, version: str) -> str:
    """A prefilled "Device layout" issue that reports a device a file does not fit: the file and its
    revision, why, the Home Assistant version and the device's signature as it joined (zigpy's
    original signature: manufacturer, model, endpoints with their clusters, as compact JSON). Nothing
    that names the device in the user's home: no address, no name. A link past REPORT_LIMIT leaves
    the output clusters out, then the signature (with a note on where to find it)."""

    def layout(outputs: bool) -> str:
        return json.dumps({
            "manufacturer": device.manufacturer,
            "model": device.model,
            "class": "zigpy.device.Device",
            "endpoints": {
                str(ep): {
                    # None where zigpy does not know them (manager._signature).
                    "profile_id": f"0x{data['profile_id']:04x}" if data["profile_id"] is not None else None,
                    "device_type": f"0x{data['device_type']:04x}" if data["device_type"] is not None else None,
                    "input_clusters": [f"0x{c:04x}" for c in data["input_clusters"]],
                    "output_clusters": [f"0x{c:04x}" for c in data["output_clusters"]] if outputs else [],
                }
                for ep, data in sorted(signature.items())
            },
        }, separators=(",", ":"))

    def link(text: str) -> str:
        query = {
            "template": REPORT_FORM,
            "title": f"Device layout: {device.manufacturer} {device.model}",
            "file": f"{name} (revision {entry.get('revision') or 'unknown'})",
            "reason": why,
            "ha": version,
            "signature": text,
        }
        return f"{REPORT}?{urlencode(query, quote_via=quote, safe='')}"

    for text in (layout(True), layout(False), REPORT_TOO_LONG):
        url = link(text)
        if len(url) <= REPORT_LIMIT:
            return url
    return url


def misfit_list(misfit: Misfit, devices: dict[str, Device], links: Mapping[str, str]) -> str:
    """The devices a file does not fit, each with why and its report link (links: device id -> URL)."""
    lines = []
    for device_id, why in sorted(misfit.devices, key=lambda item: devices[item[0]].name if item[0] in devices else ""):
        if device_id not in devices:
            continue
        device = devices[device_id]
        link = f" [Report this device]({links[device_id]})" if device_id in links else ""
        lines.append(f"- {plain(device.name)} ({plain(device.manufacturer)} {plain(device.model)}): {plain(why)}.{link}")
    return "\n".join(lines) or "- no device"


def name_list(names: list[str]) -> str:
    return "\n".join(f"- {name}" for name in names) or "- nothing"


def _sentence(text: str) -> str:
    """The text with one full stop at its end (a withdrawal's reason may bring its own)."""
    return text if text.endswith((".", "!", "?")) else f"{text}."


def _names(ids, devices: dict[str, Device]) -> str:
    return ", ".join(plain(devices[i].name) for i in sorted(ids, key=lambda i: devices[i].name) if i in devices) or "no device"


def _lost(lost: Lost, devices: dict[str, Device]) -> str:
    why = {
        plans.NO_FILE: "this collection no longer has a quirk for it",
        plans.TWO_FILES: "two files of this collection claim it",
        plans.FILE_WITHDRAWN: f"the revision of `{lost.file}` on offer is withdrawn",
        plans.FILE_REFUSED: f"`{lost.file}` cannot be written: the guard refused it or it cannot be downloaded (see its repair issue)",
        plans.FILE_CONFLICT: f"`{lost.file}` stays out: two files of this collection claim one of its devices",
        plans.USERS_NAME: f"a file of yours is named `{lost.file}`",
        plans.USERS_QUIRK: f"`{lost.file}` would also claim {_names(lost.others, devices)}, on a custom quirk of yours",
        plans.FILE_MISFIT: f"its endpoints do not fit `{lost.file}` (see the notice for that file)",
        plans.FILE_NO_TAKE_OVER: f"`{lost.file}` does not take it over from ZHA's own quirk",
    }[lost.reason] + ("; ZHA's own quirk takes it back" if lost.back else "")
    line = f"    - {_names([lost.device], devices)} gets no quirk of this collection: {why}"
    return "\n".join([line, *("    " + item for item in _new_ids(lost.new_ids))])


def _moves(moves: tuple[tuple[str, str], ...], devices: dict[str, Device]) -> list[str]:
    return [f"    - {_names([device], devices)} moves to `{file}`" for device, file in moves]


def _left_out(ids: tuple[str, ...], devices: dict[str, Device]) -> list[str]:
    return [f"    - also applies to {_names(ids, devices)}, which you left out: ZHA applies a file to every device it lists"] if ids else []


def _listed(names: list[str]) -> str:
    """At most LIMIT entity names (as many as an update's changes), the rest counted."""
    shown = [plain(name) for name in names[:LIMIT]]
    more = len(names) - len(shown)
    return ", ".join(shown) + (f" and {more} more" if more else "")


def _new_ids(names) -> list[str]:
    """The entities that get another ID in Home Assistant when ZHA's own quirk and the file swap."""
    return [f"    - new IDs in Home Assistant for {_listed(list(names))}: automations that use them need updating"] if names else []


def _taken_over(ids: tuple[str, ...], entry: dict | None, devices: dict[str, Device], new_ids: tuple[str, ...] = ()) -> list[str]:
    """For a file that takes these devices over from ZHA's own quirk: what each side shows; how to keep ZHA's quirk."""
    over = (entry or {}).get("over_zha")
    if not ids or over is None:
        return []
    line = f"    - replaces ZHA's own quirk on {_names(ids, devices)}, which shows less"
    if over["adds"]:
        line += f". Adds: {_listed(over['adds'])}"
    if over["zha_only"]:
        line += f". Only in ZHA's quirk: {_listed(over['zha_only'])}"
    return [line, *_new_ids(new_ids), f"    - to keep ZHA's quirk, leave {_names(ids, devices)} out in the xquirks options"]


def _pull_requests(entry: dict | None) -> list[str]:
    """The open upstream pull requests of an entry in one line; each link is built from the pull
    request's number (an int, content.check_entry), never taken from the manifest."""
    links = [f"[#{number}]({UPSTREAM_PR.format(number=number)})" for number in (int(pr["number"]) for pr in (entry or {}).get("upstream_open_prs", []))]
    if len(links) == 1:
        return [f"    - an open zha-device-handlers pull request adds this device, testing it helps more: {links[0]}"]
    if links:
        return [f"    - open zha-device-handlers pull requests add this device, testing them helps more: {', '.join(links)}"]
    return []


def change_list(
    plan: Plan,
    devices: dict[str, Device],
    label: Callable[[str], str],
    withdrawn: Mapping[tuple[str, str], str],
    summaries: Mapping[str, Summary | None],
    entry: Callable[[str], dict | None] = lambda name: None,
) -> str:
    """The change list for its dialog: one bullet per change, with its devices and why."""
    lines = []
    for removal in plan.remove:
        if removal.withdrawn and removal.reason != plans.OUTSIDE:
            why = f"its revision {removal.revision} is withdrawn: {plain(withdrawn.get((removal.name, removal.revision), ''))}"
        else:
            why = REMOVALS[removal.reason]
        lines.append(f"- **Remove** `{removal.name}` ({plain(label(removal.name))}): {_sentence(why)}")
        lines += _new_ids(removal.new_ids) + _moves(removal.moves, devices) + [_lost(lost, devices) for lost in removal.lost]
    for update in plan.update:
        line = f"- **Update** `{update.name}` ({plain(label(update.name))}) for {_names(update.devices, devices)}."
        if update.withdrawn:
            line += f" The installed revision {update.revision} is withdrawn: {plain(withdrawn.get((update.name, update.revision), ''))}"
        lines.append(line)
        if summary := summaries.get(update.path):
            items = summary.items()
            lines += [f"    - {item}" for item in items[:LIMIT]]
            if len(items) > LIMIT:
                lines.append(f"    - and {len(items) - LIMIT} more (all of them in the diagnostics)")
        lines += _moves(update.moves, devices) + [_lost(lost, devices) for lost in update.lost] + _left_out(update.left_out, devices)
        lines += _taken_over(update.took_over, entry(update.name), devices, update.new_ids)
    for install in plan.install:
        found = entry(install.name)
        known = f" Status: {status(found)}." if found else ""
        lines.append(f"- **Install** `{install.name}` ({plain(label(install.name))}) for {_names(install.devices, devices)}.{known}")
        lines += _taken_over(install.took_over, found, devices, install.new_ids) + _left_out(install.left_out, devices) + _pull_requests(found)
    return "\n".join(lines)
