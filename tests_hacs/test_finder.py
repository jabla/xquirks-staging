"""The quirk finder page (site/): it matches like the integration, reads the content branch the way
the content format says, keeps to its security policy and ships every file it uses.

Runs the page's modules (site/matcher.js, site/content.js) in node on a small fixture manifest:
the devices read, the matched files and their order are compared with the integration's
matching.py on the same inputs; content.js loads the device list through a stand-in fetch that
records every request. app.js only renders what content.js hands it (checked by reading it).
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from html.parser import HTMLParser
from pathlib import Path

import pytest
import yaml

from .integration import ROOT, const, content, guard, matching, text

SITE = ROOT / "site"
NODE = shutil.which("node")
PAGE = (SITE / "index.html").read_text()
REPO = re.search(r'data-repo="([^"]*)"', PAGE)[1]
MANIFEST = json.loads((Path(__file__).parent / "fixtures" / "finder-manifest.json").read_text())
RAW = "https://raw.githubusercontent.com"


def code(path: Path) -> str:
    """A module of the page without its comment lines."""
    return "\n".join(line for line in path.read_text().splitlines() if not line.lstrip().startswith("//"))


def node() -> str:
    """node runs the page's modules: the tests skip without it, but never in CI (CI is set there)."""
    if NODE is None:
        if os.environ.get("CI"):
            pytest.fail("the finder tests need node")
        pytest.skip("needs node")
    return NODE


DRIVER = """
import { readFileSync } from "node:fs";
const matcher = await import(process.argv[1]);
const content = await import(process.argv[2]);
const input = JSON.parse(readFileSync(0, "utf8"));
const out = { template: matcher.TEMPLATE, formats: content.CONTENT_FORMATS, raw: content.RAW, cases: {}, states: [] };
for (const [name, { kind, value }] of Object.entries(input.cases)) {
  const devices = kind === "template" ? matcher.devicesFromTemplate(value) : matcher.devicesIn(value);
  const found = matcher.matches(input.manifest, devices).map(({ device, slug, entry }) => [device, slug, entry.file]);
  out.cases[name] = { devices, json: matcher.devicesFromJson(value), matches: found };
}
for (const value of input.states) {
  try {
    out.states.push({ state: content.readState(value) });
  } catch (error) {
    out.states.push({ error: error.message });
  }
}
const state = content.readState({ content: 7, date: "2026-01-02", format: 1 });
out.urls = {
  state: content.stateUrl(input.repo),
  manifest: content.tagUrl(input.repo, state, "manifest.json"),
  tree: content.treeUrl(input.repo, state),
  files: input.files.map((file) => content.fileUrl(input.repo, state, file)),
};
out.leftOut = Object.fromEntries(Object.entries(input.manifest).map(([slug, entry]) => [slug, content.leftOutLines(entry)]));
out.leftOutOdd = input.oddEntries.map((entry) => content.leftOutLines(entry));
out.prs = input.prEntries.map((entry) => content.pullRequests(entry));
out.releases = input.hacs.map((hacs) => content.homeAssistant(hacs));
out.risks = input.riskEntries.map((entry) => [content.risk(entry), content.riskWhy(entry)]);
out.riskReasons = content.RISK_REASONS;
out.riskTiers = content.RISKS;

// A stand-in fetch: answers from the scenario's table by URL and records each request.
function stand_in(table, requests) {
  return async (url, options) => {
    requests.push([url, options]);
    const answer = table[url] ?? { status: 404 };
    if (answer.hang) return new Promise(() => {});
    if (answer.network) throw new TypeError("Failed to fetch");
    return {
      ok: answer.status >= 200 && answer.status < 300,
      status: answer.status,
      json: async () => ("text" in answer ? JSON.parse(answer.text) : structuredClone(answer.body)),
    };
  };
}
out.loads = {};
for (const [name, table] of Object.entries(input.loads)) {
  const requests = [];
  // Short waits: a request that never answers ends the load within them.
  const result = await content.loadContent(stand_in(table, requests), input.repo, { answer: 100, optional: 100 });
  out.loads[name] = { result, requests };
}
out.ready = { loading: content.notReady(content.LOADING), ready: content.notReady({ kind: "ready" }), failed: content.notReady(content.failure(new Error("x"))) };
process.stdout.write(JSON.stringify(out));
"""

exact_device = ("Acme", "EX-1")
model_only_device = ("Some other vendor", "MO-2")
# tuya_mo_2 leaves this name to other_co_mo_2 (claimed_elsewhere).
claimed_device = ("Other Co", "MO-2")
alias_device = ("_TZE200_alias000", "TS0601")
fileless_device = ("Nofile Co", "NF-4")
# An exact name of acme_ex_1 and the model of tuya_mo_2: two entries.
two_entries_device = ("Acme", "MO-2")
no_match = [("_TZE200_nomatch0", "TS0601"), ("IKEA of Sweden", "TRADFRI bulb E27 WW 806lm"), ("", "")]
# Exact names compare case-sensitively; astral characters sort after U+FF21 by code point.
odd = [("aCME", "EX-1"), ("Ａ", "MO-2"), ("\U0001f600", "MO-2")]
picked = [exact_device, model_only_device, claimed_device, alias_device, fileless_device, two_entries_device, *no_match, *odd]
# Every name in the manifest, model-only fingerprints with a made-up manufacturer.
sweep = sorted({(m or "Any vendor", model) for e in MANIFEST.values() for m, model in e["fingerprints"] + e.get("claimed_elsewhere", [])})


def integration_diagnostics(devices) -> dict:
    """The shape of ZHA's integration diagnostics: devices in a list, other objects around them."""
    return {
        "home_assistant": {"version": "2026.10.2", "installation_type": "Home Assistant OS"},
        "data": {
            "config_entry": {"title": "Zigbee", "data": {"radio_type": "ezsp"}},
            "devices": [{"manufacturer": m, "model": model, "logical_type": "EndDevice"} for m, model in devices],
            "not_devices": [{"manufacturer": 5, "model": "TS0601"}, {"manufacturer": "only a manufacturer"}, None, "text"],
        },
    }


def device_diagnostics(manufacturer: str, model: str) -> dict:
    """The shape of a single device's diagnostics: the pair at the top and in the signature."""
    return {"data": {"manufacturer": manufacturer, "model": model, "signature": {"manufacturer": manufacturer, "model": model, "endpoints": {}}}}


CASES = {
    "picked": {"kind": "json", "value": integration_diagnostics(picked)},
    "device": {"kind": "json", "value": device_diagnostics(*exact_device)},
    "sweep": {"kind": "json", "value": integration_diagnostics(sweep)},
    "template": {"kind": "template", "value": [f"{m}||{model}" for m, model in picked + sweep] + ["||TS0601", "Vendor||", "a||b||c"]},
}

# state.json as the content branch might hold it: (value, the state the page reads or None: refused).
STATES = [
    ({"content": 7, "date": "2026-01-02", "format": 1}, {"content": 7, "tag": "content-7", "date": "2026-01-02", "format": 1}),
    ({"content": 999999999, "date": "2026-01-02", "format": 1, "extra": "<b>x</b>"}, {"content": 999999999, "tag": "content-999999999", "date": "2026-01-02", "format": 1}),
    ({"content": 1, "format": 2}, {"content": 1, "tag": "content-1", "date": None, "format": 2}),
    ({"content": 3, "date": "02.01.2026", "format": "1"}, {"content": 3, "tag": "content-3", "date": None, "format": None}),
    ({"content": 3, "date": "2026-01-02<img src=x>", "format": 1.5}, {"content": 3, "tag": "content-3", "date": None, "format": None}),
    ({"content": 3, "date": 20260102}, {"content": 3, "tag": "content-3", "date": None, "format": None}),
    (None, None),
    ([], None),
    ("content-7", None),
    (7, None),
    ({}, None),
    ({"content": "7"}, None),
    ({"content": "7/../../main"}, None),
    ({"content": 0}, None),
    ({"content": -1}, None),
    ({"content": 7.5}, None),
    ({"content": True}, None),
    ({"content": 1000000000}, None),
    ({"content": 1e21}, None),
    ({"content": [7]}, None),
]
FILES = ["quirks/z2m_acme_ex_1.py", "../quirks/z2m_a.py", "quirks/z2m_A.py", "quirks/sub/z2m_a.py", "quirks/z2m_a.py\n", "quirks/z2m_a.pyc", "https://example.com/quirks/z2m_a.py", "z2m_a.py", 5, None]
ODD_ENTRIES = [{}, {"left_out_lines": "a line"}, {"left_out_lines": ["a", 5]}, {"left_out_lines": None}, {"left_out": 2}]
PULL = "https://github.com/zigpy/zha-device-handlers/pull/"
# (entry, the pull requests the page shows): links come from the number alone.
PR_ENTRIES = [
    ({"upstream_open_prs": [{"number": 4242, "title": "Add MO-2", "author": "someone", "url": "https://attacker.example/login"}]}, [{"number": 4242, "url": f"{PULL}4242", "title": "Add MO-2", "author": "someone"}]),
    ({"upstream_open_prs": [{"number": 7, "title": 5, "author": None}]}, [{"number": 7, "url": f"{PULL}7", "title": "", "author": ""}]),
    ({"upstream_open_prs": [{"number": "4242"}, {"number": True}, {"number": 0}, {"number": -3}, {"number": 1.5}, {"number": 2**53}, None, "x", {"url": f"{PULL}1"}]}, []),
    ({"upstream_open_prs": {"number": 4242}}, []),
    ({}, []),
]
# Entries with a risk in every shape: the page reads them as the integration does.
RISK_ENTRIES = [
    {"risk": "low", "risk_why": []},
    {"risk": "medium", "risk_why": ["number_settings", "take_over"]},
    {"risk": "high", "risk_why": ["cover", "a_new_reason", "cover"]},
    {"risk": "none", "risk_why": "cover"},
    {"risk": "LOW", "risk_why": [5, None, {"code": "cover"}, "thermostat", "__proto__", "toString"]},
    {"risk": ["low"], "risk_why": {"cover": True}},
    {},
    None,
]
HACS = [({"homeassistant": "2026.11.0"}, "2026.11.0"), ({"homeassistant": "2026.11"}, None), ({"homeassistant": "2026.11.0b1"}, None), ({"homeassistant": 2026}, None), ({}, None), (None, None), ([], None)]
# Older or newer than the page reads: the same notice either way.
UNSUPPORTED = "This page and the device list are out of sync after an update. Reload the page in a while. The xquirks integration is not affected."

STATE_URL = f"{RAW}/{REPO}/refs/heads/content/state.json"
TAG = f"{RAW}/{REPO}/refs/tags/content-7"
GOOD_STATE = {"status": 200, "body": {"content": 7, "date": "2026-01-02", "format": 1}}
GOOD = {STATE_URL: GOOD_STATE, f"{TAG}/manifest.json": {"status": 200, "body": MANIFEST}, f"{TAG}/hacs.json": {"status": 200, "body": {"homeassistant": "2026.11.0"}}}
LOADS = {
    "ready": GOOD,
    "no_hacs": {**GOOD, f"{TAG}/hacs.json": {"status": 404}},
    "broken_hacs": {**GOOD, f"{TAG}/hacs.json": {"status": 200, "text": "{"}},
    "other_format": {**GOOD, STATE_URL: {"status": 200, "body": {"content": 7, "format": 2}}},
    "no_format": {**GOOD, STATE_URL: {"status": 200, "body": {"content": 7}}},
    "no_state": {**GOOD, STATE_URL: {"status": 404}},
    "state_not_json": {**GOOD, STATE_URL: {"status": 200, "text": "<html>"}},
    "state_without_number": {**GOOD, STATE_URL: {"status": 200, "body": {"content": "7", "format": 1}}},
    "offline": {STATE_URL: {"network": True}},
    "tag_not_there_yet": {STATE_URL: GOOD_STATE},
    "manifest_error": {**GOOD, f"{TAG}/manifest.json": {"status": 500}},
    "manifest_not_json": {**GOOD, f"{TAG}/manifest.json": {"status": 200, "text": "{"}},
    "manifest_not_an_object": {**GOOD, f"{TAG}/manifest.json": {"status": 200, "body": [1, 2]}},
    # Another format may shape state.json differently: the notice still comes first.
    "other_format_other_shape": {**GOOD, STATE_URL: {"status": 200, "body": {"content": "content-8", "format": 2}}},
    "state_hangs": {STATE_URL: {"hang": True}},
    "manifest_hangs": {**GOOD, f"{TAG}/manifest.json": {"hang": True}},
    "hacs_hangs": {**GOOD, f"{TAG}/hacs.json": {"hang": True}},
}
FAILED = "Could not load the device list ({}). Reload the page to try again."
PUBLISHING = "A new device list is being published: reload the page in a few minutes."


@pytest.fixture(scope="module")
def page():
    args = [node(), "--input-type=module", "-e", DRIVER, (SITE / "matcher.js").as_uri(), (SITE / "content.js").as_uri()]
    payload = {
        "manifest": MANIFEST,
        "cases": CASES,
        "states": [value for value, _ in STATES],
        "repo": REPO,
        "files": FILES,
        "oddEntries": ODD_ENTRIES,
        "prEntries": [entry for entry, _ in PR_ENTRIES],
        "hacs": [hacs for hacs, _ in HACS],
        "riskEntries": RISK_ENTRIES,
        "loads": LOADS,
    }
    result = subprocess.run(args, input=json.dumps(payload), capture_output=True, text=True, timeout=60, check=True)
    return json.loads(result.stdout)


def devices_in(value) -> set[tuple[str, str]]:
    """Every object with a string "manufacturer" and "model" is a device, at any depth."""
    found = set()
    if isinstance(value, dict):
        manufacturer, model = value.get("manufacturer"), value.get("model")
        if isinstance(manufacturer, str) and isinstance(model, str):
            found.add((manufacturer, model))
        for item in value.values():
            found |= devices_in(item)
    elif isinstance(value, list):
        for item in value:
            found |= devices_in(item)
    return found


def devices_from_template(items: list) -> set[tuple[str, str]]:
    """The template's output: "manufacturer||model" split at the first "||", pairs with an empty side dropped."""
    pairs = (item.split("||", 1) for item in items if isinstance(item, str) and "||" in item)
    return {(manufacturer, model) for manufacturer, model in pairs if manufacturer and model}


def python_matches(devices) -> list:
    return [[list(device), slug, entry["file"]] for device, slug, entry in matching.matches(MANIFEST, devices)]


@pytest.mark.parametrize("name", ["picked", "device", "sweep"])
def test_diagnostics_match_like_the_integration(page, name):
    devices = devices_in(CASES[name]["value"])
    assert page["cases"][name]["devices"] == [list(d) for d in sorted(devices)]
    assert page["cases"][name]["json"] == page["cases"][name]["devices"]
    assert page["cases"][name]["matches"] == python_matches(devices)


def test_template_output_matches_like_the_integration(page):
    devices = devices_from_template(CASES["template"]["value"])
    assert page["cases"]["template"]["devices"] == [list(d) for d in sorted(devices)]
    assert page["cases"]["template"]["json"] == page["cases"]["template"]["devices"]
    assert page["cases"]["template"]["matches"] == python_matches(devices)


def test_picked_devices(page):
    found = [(tuple(device), slug) for device, slug, _ in page["cases"]["picked"]["matches"]]
    assert (exact_device, "acme_ex_1") in found
    assert (model_only_device, "tuya_mo_2") in found
    assert (claimed_device, "tuya_mo_2") not in found
    assert (claimed_device, "other_co_mo_2") in found
    assert (alias_device, "alias_vendor_al_3") in found
    assert (fileless_device, "nofile_nf_4") in found
    assert [slug for device, slug in found if device == two_entries_device] == ["acme_ex_1", "tuya_mo_2"]
    assert not {device for device, _ in found} & {*no_match, odd[0]}
    devices = [tuple(device) for device in page["cases"]["picked"]["devices"]]
    assert devices.index(odd[1]) < devices.index(odd[2])


def test_template_writes_what_the_page_reads(page):
    """Every ZHA device as "manufacturer||model", the shape devicesFromTemplate reads."""
    assert "integration_entities('zha')" in page["template"]
    assert "(device_attr(device, 'manufacturer') or '') ~ '||' ~ (device_attr(device, 'model') or '')" in page["template"]


def test_state_json_is_checked_before_use(page):
    """Only a content number of one to nine digits makes a tag name; a date or format of another
    shape reads as none. Nothing else of state.json is passed on."""
    assert len(page["states"]) == len(STATES)
    for (value, expected), got in zip(STATES, page["states"], strict=True):
        if expected is None:
            assert "error" in got, value
        else:
            assert got == {"state": expected}, value


def test_state_from_the_branch_files_from_the_tag(page):
    assert page["raw"] == RAW
    assert page["urls"]["state"] == STATE_URL
    assert page["urls"]["manifest"] == f"{TAG}/manifest.json"
    assert page["urls"]["tree"] == f"https://github.com/{REPO}/tree/content-7"
    # A link to the file on GitHub at the tag, only for a path the manifest may ship.
    assert page["urls"]["files"] == [f"https://github.com/{REPO}/blob/content-7/quirks/z2m_acme_ex_1.py"] + [None] * (len(FILES) - 1)


def test_loading_asks_the_branch_head_then_the_tag(page):
    """state.json past the browser's cache, then hacs.json and manifest.json at the tag it names:
    three requests without cookies, no quirk file among them."""
    load = page["loads"]["ready"]
    assert load["result"] == {"kind": "ready", "state": {"content": 7, "tag": "content-7", "date": "2026-01-02", "format": 1}, "manifest": MANIFEST, "homeassistant": "2026.11.0"}
    assert load["requests"] == [
        [STATE_URL, {"credentials": "omit", "cache": "no-cache"}],
        [f"{TAG}/hacs.json", {"credentials": "omit"}],
        [f"{TAG}/manifest.json", {"credentials": "omit"}],
    ]


def test_loading_never_fetches_a_quirk_file(page):
    for name, load in page["loads"].items():
        urls = [url for url, _ in load["requests"]]
        assert urls and all(url.startswith(f"{RAW}/{REPO}/refs/") for url in urls), name
        assert not [url for url in urls if "/quirks/" in url or url.endswith(".py")], name


def test_hacs_json_is_optional(page):
    for name in ("no_hacs", "broken_hacs", "hacs_hangs"):
        assert page["loads"][name]["result"]["kind"] == "ready", name
        assert page["loads"][name]["result"]["homeassistant"] is None, name
    assert [page_release for page_release in page["releases"]] == [release for _, release in HACS]


def test_another_content_format_shows_a_notice_instead_of_the_list(page):
    for name in ("other_format", "no_format", "other_format_other_shape"):
        load = page["loads"][name]
        assert load["result"]["kind"] == "unsupported", name
        assert load["result"]["message"] == UNSUPPORTED, name
        # Nothing is read from a tag in a format the page does not know.
        assert [url for url, _ in load["requests"]] == [STATE_URL], name


def test_a_failed_load_says_why(page):
    expected = {
        "no_state": FAILED.format("state.json: 404"),
        "state_not_json": FAILED.format("state.json is not JSON"),
        "state_without_number": FAILED.format("state.json names no content number"),
        "offline": FAILED.format("Failed to fetch"),
        "manifest_error": FAILED.format("manifest.json: 500"),
        "manifest_not_json": FAILED.format("manifest.json is not JSON"),
        "manifest_not_an_object": FAILED.format("manifest.json is not an object"),
        "state_hangs": FAILED.format("state.json: no answer"),
        "manifest_hangs": FAILED.format("manifest.json: no answer"),
    }
    for name, message in expected.items():
        assert page["loads"][name]["result"] == {"kind": "failed", "message": message}, name


def test_a_tag_raw_does_not_serve_yet_is_being_published(page):
    """The branch head names a tag raw still answers 404 for (its cache): no older tag instead."""
    load = page["loads"]["tag_not_there_yet"]
    assert load["result"] == {"kind": "failed", "message": PUBLISHING}
    assert [url for url, _ in load["requests"]] == [STATE_URL, f"{TAG}/hacs.json", f"{TAG}/manifest.json"]


def test_devices_before_the_list_get_the_load_state(page):
    """A file dropped before the list is there gets the reason, not a wait that never ends."""
    assert page["ready"] == {"loading": "The device list is still loading, try again in a moment.", "ready": None, "failed": FAILED.format("x")}
    app = code(SITE / "app.js")
    # Files and pasted text both ask first; a failed render leaves the list unavailable.
    assert app.count("const waiting = notReady(content);") == 2 and "content = loaded;" in app
    assert "unavailable(failure(error));" in app and "content = outcome;" in app


def test_left_out_lines_come_from_the_manifest(page):
    assert page["leftOut"] == {slug: entry.get("left_out_lines", []) for slug, entry in MANIFEST.items()}
    assert page["leftOutOdd"] == [[]] * len(ODD_ENTRIES)


def test_pull_request_links_come_from_their_numbers(page):
    assert page["prs"] == [prs for _, prs in PR_ENTRIES]


def test_risks_read_like_the_integration(page):
    """A missing or unknown risk is high, an unknown reason is skipped (CONTENT.md): the same tiers
    and codes as content.py."""
    assert tuple(page["riskTiers"]) == content.RISKS
    assert tuple(page["riskReasons"]) == content.RISK_REASONS
    # The finder words each reason as the integration's change list does.
    assert page["riskReasons"] == text.RISK_REASONS
    assert page["risks"] == [[content.risk(entry or {}), list(content.risk_why(entry or {}))] for entry in RISK_ENTRIES]
    assert page["risks"][2] == ["high", ["cover"]] and page["risks"][4] == ["high", ["thermostat"]]


def test_the_page_reads_the_content_format_of_this_release(page):
    """content.js reads the format the integration's guard names (FORMAT); two formats only while
    the format changes."""
    assert guard.FORMAT in page["formats"]
    assert 1 <= len(page["formats"]) <= 2


def test_app_renders_what_content_js_hands_it():
    """app.js fetches pictures itself, the device list only through loadContent; every link it
    builds comes from content.js or the page's own forms, never straight from the manifest."""
    app = code(SITE / "app.js")
    assert re.findall(r"\bfetch\(\s*([^\s,)]+)", app) == ["PICTURE_URL", "url"]
    assert "loadContent((url, options) => fetch(url, options), REPO)" in app
    assert sorted(set(re.findall(r"\bhref: ([^,}]+?)\s*[,}]", app))) == ["pr.url", "treeUrl(REPO", "url", "url.href"]
    assert sorted(re.findall(r"const url = (.+);", app)) == ["devicePage(entry)", "fileUrl(REPO, state, entry.file)", "new URL(`https://github.com/${REPO}/issues/new`)"]
    assert not re.search(r"upstream_open_prs|left_out_lines|raw\.githubusercontent|refs/(heads|tags)", app)
    # The raw base is a constant: no attribute of the page or its address can point it elsewhere.
    assert set(re.findall(r"documentElement\.dataset\.(\w+)", app)) == {"repo"}
    assert not re.search(r"\b(location|URLSearchParams|getAttribute|localStorage|sessionStorage)\b", app)
    assert not re.search(r"\b(document|window|location)\b", code(SITE / "content.js"))


def test_policy_lets_the_page_reach_only_raw_and_the_pictures():
    policy = re.search(r'<meta http-equiv="Content-Security-Policy" content="([^"]+)">', PAGE)[1]
    directives = {name: values for name, *values in (part.split() for part in policy.split(";") if part.strip())}
    assert directives == {
        "default-src": ["'self'"],
        "img-src": ["'self'", "data:", "blob:"],
        "connect-src": [RAW, "https://www.zigbee2mqtt.io"],
        "object-src": ["'none'"],
        "base-uri": ["'none'"],
        "form-action": ["'none'"],
    }


class Page(HTMLParser):
    """The local files index.html loads, its inline scripts and event handler attributes."""

    def __init__(self) -> None:
        super().__init__()
        self.files: set[str] = set()
        self.inline_scripts = 0
        self.handlers: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        self.handlers += [name for name, _ in attrs if name.startswith("on")]
        if tag == "script":
            if values.get("src"):
                self.files.add(values["src"])
            else:
                self.inline_scripts += 1
        if tag == "link" and values.get("rel") == "stylesheet":
            self.files.add(values["href"])
        if tag == "meta" and values.get("property") == "og:image":
            self.files.add(values["content"].rsplit("/", 1)[1])


def test_the_page_ships_every_file_it_loads_and_nothing_else():
    """pages.yml publishes site/ as it is (package.json only lets node load the modules)."""
    parsed = Page()
    parsed.feed(PAGE)
    assert parsed.inline_scripts == 0 and parsed.handlers == []
    used, todo = {"index.html"} | parsed.files, [f for f in parsed.files if f.endswith(".js")]
    while todo:
        for name in re.findall(r'^import .* from "\./([\w.-]+)";$', (SITE / todo.pop()).read_text(), re.M):
            if name not in used:
                used.add(name)
                todo.append(name)
    assert used == {path.name for path in SITE.iterdir()} - {"package.json"}


def test_the_page_offers_no_downloads():
    """The integration installs the files; by hand they come from GitHub, so no zip and no download links."""
    scripts = "".join(path.read_text() for path in SITE.glob("*.js"))
    assert not re.search(r"\bdownload\b\s*:", scripts)
    assert not re.search(r"<a\b[^>]*\bdownload\b", PAGE)
    assert "zip" not in PAGE.lower() and not re.search(r"\bzip\b", scripts)


def test_the_page_names_this_repo():
    """site/index.html names the repository the integration reads (const.py): the finder's data-repo
    and the link preview URLs under that repository's Pages address."""
    owner, name = const.REPOSITORY.split("/")
    assert re.findall(r'data-repo="([^"]*)"', PAGE) == [const.REPOSITORY]
    previews = re.findall(r'content="(https://[^"]*github\.io/[^"]*)"', PAGE)
    assert previews and all(url.startswith(f"https://{owner.lower()}.github.io/{name}/") for url in previews), previews


def test_pages_deploys_the_site_as_it_is():
    """The page reads the content itself: pages.yml publishes site/ without a build step, on a push
    to main that changes it or by hand from main, never on content."""
    workflow = yaml.safe_load((ROOT / ".github/workflows/pages.yml").read_text())
    # YAML 1.1 reads the key "on" as true.
    assert workflow[True] == {"push": {"branches": ["main"], "paths": ["site/**"]}, "workflow_dispatch": None}
    assert workflow["permissions"] == {"contents": "read"}
    build, deploy = workflow["jobs"]["build"], workflow["jobs"]["deploy"]
    assert build["if"] == "github.ref == 'refs/heads/main'" and "permissions" not in build
    assert deploy["needs"] == "build" and deploy["permissions"] == {"pages": "write", "id-token": "write"}
    assert deploy["environment"]["name"] == "github-pages"
    steps = build["steps"] + deploy["steps"]
    assert not [step for step in steps if "run" in step]
    uploads = [step for step in steps if step.get("uses", "").startswith("actions/upload-pages-artifact@")]
    assert [step["with"] for step in uploads] == [{"path": "site"}]
    for step in steps:
        if step.get("uses", "").startswith("actions/checkout@"):
            assert step["with"]["persist-credentials"] is False
