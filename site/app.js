// The quirk finder page: reads diagnostics or the template's output in the browser, matches them
// with matcher.js against the manifest of the newest content tag (content.js) and links the
// matching quirk files.

import { LOADING, failure, fileUrl, leftOutLines, loadContent, notReady, pullRequests, treeUrl } from "./content.js";
import { TEMPLATE, compareDevices, compareStrings, devicesFromJson, matches } from "./matcher.js";

const REPO = document.documentElement.dataset.repo;
const $ = (id) => document.getElementById(id);

// The integration's sources (custom_components/xquirks/pictures.py PICTURE_URL) and the device
// pages of the Zigbee2MQTT docs.
const PICTURE_URL = "https://www.zigbee2mqtt.io/images/devices/";
const DEVICE_URL = "https://www.zigbee2mqtt.io/devices/";

function el(tag, attrs, ...children) {
  const node = document.createElement(tag);
  for (const [name, value] of Object.entries(attrs || {})) {
    if (value !== null && value !== undefined) node.setAttribute(name, value);
  }
  // Text goes in as text nodes: names from a diagnostics file never become markup.
  node.append(...children.flat(Infinity).filter((child) => child !== null && child !== undefined && child !== false));
  return node;
}

// kind: "problem" shows the message in red, "quiet" only announces it (the results show it).
const say = (text, kind = "", where = "status") => {
  const node = $(where);
  node.className = kind;
  if (text && node.textContent === text) {
    // The same message again: cleared first, so that it shows and is announced once more.
    node.textContent = "";
    requestAnimationFrame(() => {
      node.textContent = text;
    });
    return;
  }
  node.textContent = text;
};

const plural = (count, word) => `${count} ${word}${count === 1 ? "" : "s"}`;
const fileName = (path) => path.slice(path.lastIndexOf("/") + 1);
// Names in quotes where spaces at the ends or emptiness would not show ("AOYAN " is a name of its own).
const shown = (name) => (!name || /^\s|\s$/.test(name) ? JSON.stringify(name) : name);
const deviceText = ([manufacturer, model]) => `${shown(manufacturer)} / ${shown(model)}`;
const title = (entry, slug) => [entry.vendor, entry.model || slug].filter(Boolean).join(" ");
const DOT = " \u00b7 ";

for (const link of document.querySelectorAll("[data-repo-link]")) {
  link.href = `https://github.com/${REPO}${link.dataset.repoLink ? `/${link.dataset.repoLink}` : ""}`;
}
$("template").textContent = TEMPLATE;

// The device page in the Zigbee2MQTT docs: the model with every character other than letters,
// digits and ._()- as "_" ("JT-BZ-01AQ/A" has JT-BZ-01AQ_A.html).
const devicePage = (entry) => (entry.model ? `${DEVICE_URL}${encodeURIComponent(entry.model.replace(/[^A-Za-z0-9._()-]/g, "_"))}.html` : null);

// Device pictures, fetched once per name. Like the integration, the page shows only the bytes
// pinned in the manifest (picture_sha256): no pin, another picture or no answer means no picture.
const pictures = new Map();

const hex = (buffer) => [...new Uint8Array(buffer)].map((byte) => byte.toString(16).padStart(2, "0")).join("");

async function fetchPicture(name, pin) {
  try {
    const response = await fetch(PICTURE_URL + encodeURIComponent(name), { credentials: "omit", referrerPolicy: "no-referrer", redirect: "error" });
    if (!response.ok) return null;
    const bytes = await response.arrayBuffer();
    if (hex(await crypto.subtle.digest("SHA-256", bytes)) !== pin) return null;
    return URL.createObjectURL(new Blob([bytes], { type: "image/png" }));
  } catch {
    return null;
  }
}

function pictureOf(entry) {
  if (!entry.picture || !entry.picture_sha256) return Promise.resolve(null);
  if (!pictures.has(entry.picture)) pictures.set(entry.picture, fetchPicture(entry.picture, entry.picture_sha256));
  return pictures.get(entry.picture);
}

// A frame that shows the entry's picture once it has loaded; it goes away when there is none.
// The table loads a frame's picture when it scrolls into view, a device card right away.
function frame(entry) {
  if (!entry.picture_sha256) return el("span", { class: "picture none" });
  const node = el("span", { class: "picture" });
  node.load = () => {
    node.load = null;
    pictureOf(entry).then((url) => {
      if (url) node.replaceChildren(el("img", { src: url, alt: "", decoding: "async" }));
      else node.classList.add("none");
    });
  };
  return node;
}

const lazy = new IntersectionObserver(
  (seen) => {
    for (const { isIntersecting, target } of seen) {
      if (!isIntersecting) continue;
      lazy.unobserve(target);
      target.load?.();
    }
  },
  { rootMargin: "300px 0px" },
);

// The badge class of each status the page knows; any other status gets none.
const STATUS_CLASS = { generated: "badge generated", verified: "badge verified", upstream: "badge upstream" };

function status(entry) {
  return el("span", { class: Object.hasOwn(STATUS_CLASS, entry.status) ? STATUS_CLASS[entry.status] : "badge" }, entry.status);
}

// The file's Revision line (the content hash at its top): which content an issue report is about.
function revision(entry) {
  return entry.revision ? el("span", { class: "revision", title: "Revision: the content hash the file states at its top" }, entry.revision) : null;
}

// A file that takes the device over from ZHA's own quirk, which shows fewer features (manifest over_zha).
function overZha(entry) {
  if (!entry.file || !entry.over_zha) return null;
  const adds = entry.over_zha.adds.length ? ` It adds: ${entry.over_zha.adds.join(", ")}.` : "";
  const zhaOnly = entry.over_zha.zha_only.length ? ` Only ZHA's quirk shows: ${entry.over_zha.zha_only.join(", ")}.` : "";
  return el("span", { class: "note" }, `ZHA ships its own quirk for this device, which shows less: this file takes the device over.${adds}${zhaOnly}`);
}

// The manifest's not_built reason in plain words, null when there is none for it.
const KIND_PLURALS = { light: "lights", lock: "locks", fan: "fans" };
function notBuiltText(reason) {
  if (reason.startsWith("endpoint unclear")) return "it is not clear which endpoint each feature is on";
  if (reason.startsWith("datapoints that cannot be translated yet")) return "some of its datapoints cannot be translated yet";
  // "complex kind: cover (no position datapoint)": a cover or thermostat that cannot be translated yet.
  const plan = /^complex kind: (cover|climate) \(/.exec(reason);
  if (plan) return `this ${plan[1] === "cover" ? "cover" : "thermostat"} cannot be translated yet`;
  // "complex kind: ['light']": a kind that gets no file yet.
  const kinds = /^complex kind: \[(.*)\]$/.exec(reason)?.[1].match(/\w+/g) || [];
  if (kinds.length === 1 && KIND_PLURALS[kinds[0]]) return `${KIND_PLURALS[kinds[0]]} are not generated yet`;
  return null;
}

// Why an entry has no file. The raw reason stays in the tooltip for reports.
function noFile(entry) {
  if (entry.status === "upstream") return "No file: zha-device-handlers covers this device, nothing to install.";
  if (entry.not_built) {
    const why = notBuiltText(entry.not_built);
    return el("span", { title: entry.not_built }, why ? `No file yet: ${why}.` : "No file yet.");
  }
  return "No file shipped for this device.";
}

// The Zigbee2MQTT features a file leaves out, as its comment lines name them (the manifest lists them).
function leftOut(entry) {
  const lines = entry.file ? leftOutLines(entry) : [];
  if (!lines.length) return null;
  // "fault_status: z2m's own code, not generated" reads "fault_status: z2m's own code".
  const shownLines = lines.map((line) => line.replace(/,? not generated( yet)?$/, ""));
  return el(
    "details",
    { class: "more" },
    el("summary", {}, `${plural(lines.length, "Zigbee2MQTT feature")} not in this file`),
    el("ul", {}, shownLines.map((line) => el("li", {}, line))),
  );
}

// What loading the device list came to (content.js loadContent); the state and manifest it brought.
let content = LOADING;
let state = null;
let manifest = null;

// The file on GitHub at the content tag: no download here, the integration installs the files.
function fileLink(entry) {
  const url = fileUrl(REPO, state, entry.file);
  const name = fileName(entry.file);
  return url ? el("a", { href: url, title: "Opens the file on GitHub" }, name) : el("span", {}, name);
}

// Alias entries: datapoints the shipped quirk reads differently than Zigbee2MQTT.
function differs(entry) {
  if (!entry.differs?.length) return null;
  return el(
    "details",
    { class: "more" },
    el("summary", {}, `ZHA's quirk reads ${plural(new Set(entry.differs.map((d) => d.dp)).size, "datapoint")} differently than Zigbee2MQTT`),
    el("ul", {}, entry.differs.map((d) => el("li", {}, `DP ${d.dp}: ${d.reason}`))),
  );
}

function pageLink(entry) {
  const url = devicePage(entry);
  return url ? el("a", { href: url, class: "z2m" }, "Zigbee2MQTT page") : null;
}

// A link to one of the repo's issue forms (.github/ISSUE_TEMPLATE), its fields filled in from the
// query (GitHub fills a form field from the parameter with its id). Nothing is sent until the
// person submits the form on GitHub.
function issueLink(text, template, fields) {
  const url = new URL(`https://github.com/${REPO}/issues/new`);
  url.searchParams.set("template", template);
  for (const [name, value] of Object.entries(fields)) if (value) url.searchParams.set(name, value);
  return el("a", { href: url.href, title: "Opens the form on GitHub, filled in" }, text);
}

// The Home Assistant version of the diagnostics read last (ZHA diagnostics name it at the top).
let haVersion = null;

function reports(entry, device) {
  const name = title(entry, "");
  if (!entry.file) {
    const fields = { title: `Missing: ${name}`, z2m: devicePage(entry), fingerprint: deviceText(device) };
    return el("span", { class: "reports" }, issueLink("Report your device", "missing-device.yml", fields));
  }
  const fields = { file: entry.file, revision: entry.revision, ha: haVersion };
  return el(
    "span",
    { class: "reports" },
    issueLink("Report a problem", "wrong-value.yml", { title: `${name}: `, ...fields }),
    DOT,
    issueLink("Report a device test", "verify.yml", { title: `Verify: ${name}`, ...fields }),
  );
}

function fileItem(entry, device) {
  if (!entry.file) return el("li", {}, el("span", { class: "badge" }, "no file"), " ", noFile(entry), entry.not_built ? reports(entry, device) : null);
  return el(
    "li",
    {},
    fileLink(entry),
    " ",
    revision(entry),
    " ",
    status(entry),
    entry.path === "alias" ? el("span", { class: "note" }, `Alias: lets the quirk that ships with ZHA for ${entry.target.join(" / ")} claim this name too.`) : null,
    overZha(entry),
    leftOut(entry),
    differs(entry),
    reports(entry, device),
  );
}

// pr: one of content.js pullRequests, its link built from its number.
function prLink(pr) {
  return el("a", { href: pr.url }, `#${pr.number} ${pr.title}`);
}

// The open upstream PRs of every entry a device matched, each once.
function prsOf(entries) {
  const prs = new Map();
  for (const entry of entries) for (const pr of pullRequests(entry)) prs.set(pr.number, pr);
  return [...prs.values()].sort((a, b) => a.number - b.number);
}

function deviceCard(device, entries) {
  const prs = prsOf(entries);
  const names = [...new Set(entries.map((entry) => title(entry, "")).filter(Boolean))];
  const descriptions = [...new Set(entries.map((entry) => entry.description).filter(Boolean))];
  const links = [...new Map(entries.map((entry) => [devicePage(entry), entry])).values()].map(pageLink).filter(Boolean);
  const picture = frame(entries.find((entry) => entry.picture_sha256) || entries[0]);
  picture.load?.();
  return el(
    "article",
    { class: "device" },
    picture,
    el(
      "div",
      { class: "body" },
      el("h3", {}, names.join(", ") || deviceText(device)),
      descriptions.length ? el("p", { class: "what" }, descriptions.join(" / ")) : null,
      el("p", { class: "zigbee" }, "Your device: ", el("code", {}, deviceText(device)), links.length ? [DOT, links.map((link, i) => (i ? [" ", link] : link))] : null),
      el("ul", {}, entries.map((entry) => fileItem(entry, device))),
      prs.length
        ? el(
            "div",
            { class: "prs" },
            el("p", {}, prs.length === 1 ? "An open zha-device-handlers pull request adds this device." : "Open zha-device-handlers pull requests add this device.", " Testing it and reporting there helps more than a file from here."),
            el("ul", {}, prs.map((pr) => el("li", {}, prLink(pr), pr.author ? ` by ${pr.author}` : ""))),
          )
        : null,
    ),
  );
}

let wanted = [];

function show(devices, source) {
  const found = matches(manifest, devices);
  const byDevice = new Map();
  for (const { device, entry } of found) {
    const key = JSON.stringify(device);
    if (!byDevice.has(key)) byDevice.set(key, { device, entries: [] });
    byDevice.get(key).entries.push(entry);
  }
  const groups = [...byDevice.values()].sort((a, b) => compareDevices(a.device, b.device));
  const rest = devices.filter((device) => !byDevice.has(JSON.stringify(device)));
  wanted = [...new Set(found.map(({ entry }) => entry.file).filter(Boolean))].sort(compareStrings);

  $("summary").textContent = `${plural(devices.length, "device")} read from ${source}: ${groups.length} with an entry here, ${rest.length} without.`;
  $("matched").replaceChildren(...groups.map(({ device, entries }) => deviceCard(device, entries)));
  $("install").hidden = wanted.length === 0;
  $("unmatched").hidden = rest.length === 0;
  $("unmatched-list").replaceChildren(
    ...rest.map((device) => el("li", {}, deviceText(device), DOT, issueLink("report", "missing-device.yml", { title: `Missing: ${device[0]} ${device[1]}`, fingerprint: deviceText(device) }))),
  );
  $("results").hidden = false;
  say(groups.length ? `Found entries for ${plural(groups.length, "device")}.` : `None of your ${plural(devices.length, "device")} has a file here.`, "quiet");
  $("results-heading").focus();
}

// The devices in a JSON text, null (and a message) when it is no JSON.
function read(text, what) {
  try {
    const value = JSON.parse(text.replace(/^\uFEFF/, ""));
    const version = value?.home_assistant?.version;
    if (typeof version === "string" && /^\d{4}\.\d{1,2}\.\d+/.test(version)) haVersion = version;
    return devicesFromJson(value);
  } catch {
    say(`${what} is not JSON. Use the ZHA diagnostics file or the template's result.`, "problem");
    return null;
  }
}

function useDevices(devices, source) {
  if (!devices) return;
  if (!devices.length) {
    say(`No devices in ${source}: it needs objects with "manufacturer" and "model", as in ZHA diagnostics, or the template's result.`, "problem");
    $("results").hidden = true;
    return;
  }
  try {
    show(devices, source);
  } catch (error) {
    say(`Could not show the results (${error?.message ?? error}). Please report this.`, "problem");
  }
}

async function readFiles(files) {
  if (!files.length) return;
  const waiting = notReady(content);
  if (waiting) {
    say(waiting, "problem");
    return;
  }
  const found = new Map();
  haVersion = null;
  for (const file of files) {
    const devices = read(await file.text(), file.name);
    if (!devices) return;
    for (const device of devices) found.set(JSON.stringify(device), device);
  }
  useDevices([...found.values()].sort(compareDevices), files.length === 1 ? files[0].name : plural(files.length, "file"));
}

$("file").addEventListener("change", (event) => {
  readFiles([...event.target.files]);
  event.target.value = "";
});

// Drops anywhere on the page count, so a near miss does not open the file in the browser.
const drop = $("drop");
document.addEventListener("dragover", (event) => {
  event.preventDefault();
  drop.classList.add("over");
});
document.addEventListener("dragleave", (event) => {
  if (!event.relatedTarget) drop.classList.remove("over");
});
document.addEventListener("drop", (event) => {
  event.preventDefault();
  drop.classList.remove("over");
  readFiles([...(event.dataTransfer?.files || [])]);
});

$("paste-go").addEventListener("click", () => {
  const waiting = notReady(content);
  if (waiting) {
    say(waiting, "problem");
    return;
  }
  const text = $("paste").value.trim();
  if (!text) {
    say("Paste the template's result first.", "problem");
    return;
  }
  haVersion = null;
  useDevices(read(text, "The pasted text"), "the pasted text");
});

$("copy-template").addEventListener("click", async () => {
  try {
    await navigator.clipboard.writeText(TEMPLATE);
    say("Template copied.");
  } catch {
    getSelection().selectAllChildren($("template"));
    say("Copying is blocked here: the template is selected, copy it with Ctrl+C.");
  }
});

// The table of all devices: one row each, filtered in place.
function cell(label, className, ...children) {
  return el("td", { "data-label": label, class: className, role: "cell" }, el("div", {}, ...children));
}

// What the "Show" choice keeps.
const KINDS = {
  all: () => true,
  file: (entry) => Boolean(entry.file),
  verified: (entry) => entry.status === "verified",
  prs: (entry) => pullRequests(entry).length > 0,
  nofile: (entry) => !entry.file,
};

function row(slug, entry) {
  const fingerprints = entry.fingerprints.map(([manufacturer, model]) => el("span", {}, `${manufacturer === null ? "any manufacturer" : shown(manufacturer)} / ${shown(model)}`));
  const claimed = (entry.claimed_elsewhere || []).map(([manufacturer, model]) => el("span", { class: "except" }, `except ${shown(manufacturer)} / ${shown(model)}`));
  const prs = pullRequests(entry);
  const picture = frame(entry);
  const tr = el(
    "tr",
    { role: "row" },
    el("td", { class: "picture-cell", role: "cell" }, picture),
    cell("Device", "device-cell", el("strong", {}, title(entry, slug)), entry.description ? el("span", { class: "what" }, entry.description) : null, pageLink(entry)),
    cell("Fingerprints", "fingerprints", fingerprints, claimed),
    cell("Status", null, entry.file ? status(entry) : el("span", { class: "badge" }, "no file"), entry.path === "alias" ? el("span", { class: "note" }, "alias") : null,
      entry.file && entry.over_zha ? el("span", { class: "note" }, "over ZHA's quirk") : null),
    cell("File", "file-cell", entry.file ? [fileLink(entry), " ", revision(entry)] : noFile(entry)),
    cell("Upstream PRs", null, prs.length ? el("span", { class: "prlist" }, prs.map((pr) => el("a", { href: pr.url, title: pr.title }, `#${pr.number}`))) : "none"),
  );
  const words = [slug, entry.vendor, entry.model, entry.description, entry.file, entry.revision, ...entry.fingerprints.flat(), ...prs.map((pr) => `#${pr.number}`)];
  tr.dataset.search = words.filter(Boolean).join(" ").toLowerCase();
  tr.kinds = Object.keys(KINDS).filter((kind) => KINDS[kind](entry));
  lazy.observe(picture);
  return tr;
}

// The rows that pass search and "Show", shown PAGE at a time.
const PAGE = 25;
let page = 0;

function render() {
  const terms = $("search").value.toLowerCase().split(/\s+/).filter(Boolean);
  const kind = $("show").value;
  const rows = [...$("all-rows").rows];
  const found = rows.filter((tr) => tr.kinds.includes(kind) && terms.every((term) => tr.dataset.search.includes(term)));
  const pages = Math.max(1, Math.ceil(found.length / PAGE));
  page = Math.min(page, pages - 1);
  const visible = new Set(found.slice(page * PAGE, (page + 1) * PAGE));
  for (const tr of rows) tr.hidden = !visible.has(tr);

  const all = found.length === rows.length ? "" : ` (${rows.length} in all)`;
  if (!found.length) $("count").textContent = `No device matches${all}.`;
  else if (pages === 1) $("count").textContent = `${plural(found.length, "device")}${all}.`;
  else $("count").textContent = `${page * PAGE + 1} to ${page * PAGE + visible.size} of ${plural(found.length, "device")}${all}.`;
  $("pager").hidden = pages === 1;
  $("page").replaceChildren(...Array.from({ length: pages }, (_, i) => el("option", { value: i }, `${i + 1}`)));
  $("page").value = page;
  $("pages").textContent = `of ${pages}`;
  $("prev").disabled = page === 0;
  $("next").disabled = page === pages - 1;
}

const filter = () => {
  page = 0;
  render();
};

// Back to the top of the table when the new page starts above the screen.
function turn(to) {
  page = to;
  render();
  if ($("all").getBoundingClientRect().top < 0) $("all-heading").scrollIntoView();
}

// The footer: the content tag the page shows (state.json at the content branch head) and the
// data versions it was built from.
function sources() {
  const versions = Object.values(manifest).find((entry) => entry.sources)?.sources;
  const parts = [];
  const tag = el("a", { href: treeUrl(REPO, state) }, state.tag);
  parts.push("Quirk files: ", tag, state.date ? ` (${state.date})` : "", ".");
  // "dev <40 hex digits>" as the README writes it: "dev 1d6598c".
  const short = (version) => version.replace(/\b([0-9a-f]{7})[0-9a-f]{33}\b/, "$1");
  if (versions) parts.push(` Data: Zigbee2MQTT (zigbee-herdsman-converters) ${short(versions["zigbee-herdsman-converters"])}, zha-device-handlers ${short(versions["zha-device-handlers"])}.`);
  $("sources").replaceChildren(...parts);
}

// The Home Assistant release the files need (hacs.json at the tag): the release they were built
// for, patch number included.
function needs(release) {
  if (!release) return;
  for (const node of document.querySelectorAll("[data-ha-needs]")) node.textContent = `needs Home Assistant ${release} or newer`;
}

$("search").addEventListener("input", filter);
$("show").addEventListener("change", filter);
$("page").addEventListener("change", () => turn(Number($("page").value)));
$("prev").addEventListener("click", () => turn(page - 1));
$("next").addEventListener("click", () => turn(page + 1));

// The list could not load or render: its reason stays in the table's place too.
function unavailable(outcome) {
  content = outcome;
  say(outcome.message, "problem");
  $("count").textContent = outcome.message;
}

loadContent((url, options) => fetch(url, options), REPO)
  .then((loaded) => {
    if (loaded.kind !== "ready") {
      unavailable(loaded);
      return;
    }
    ({ state, manifest } = loaded);
    const name = (slug) => [(manifest[slug].vendor || "").toLowerCase(), (manifest[slug].model || slug).toLowerCase(), slug];
    const slugs = Object.keys(manifest).sort((a, b) => name(a).reduce((order, part, i) => order || compareStrings(part, name(b)[i]), 0));
    $("all-rows").replaceChildren(...slugs.map((slug) => row(slug, manifest[slug])));
    filter();
    sources();
    needs(loaded.homeassistant);
    // Only a list that rendered takes devices.
    content = loaded;
    for (const id of ["file", "paste-go", "search", "show"]) $(id).disabled = false;
    if ($("status").textContent === LOADING.message) say("");
  })
  .catch((error) => {
    state = manifest = null;
    $("all-rows").replaceChildren();
    unavailable(failure(error));
  });
