// Where the finder reads the device list and what it makes of it: the content branch of this repo on
// raw.githubusercontent.com. state.json at the branch head names the newest content-<n> tag;
// everything else comes from that tag, which never moves, so the files cannot mix two states inside
// raw's cache window. The page never fetches a quirk file. Kept free of the DOM so that tests can
// run it in node with a stand-in fetch.

export const RAW = "https://raw.githubusercontent.com";
// The content formats this page reads. FORMAT of custom_components/xquirks/guard.py is one of them
// (a test ties them); two only while the format changes, the old one and the new one.
export const CONTENT_FORMATS = [1];
// The integration builds the same links (custom_components/xquirks/text.py UPSTREAM_PR).
const UPSTREAM_PR = "https://github.com/zigpy/zha-device-handlers/pull/";

// At most nine digits, as the integration reads content tags.
const NUMBER = /^[1-9][0-9]{0,8}$/;
const DATE = /^[0-9]{4}-[0-9]{2}-[0-9]{2}$/;
const RELEASE = /^[0-9]{4}\.[0-9]{1,2}\.[0-9]{1,2}$/;
// The only files a manifest ships.
const FILE = /^quirks\/z2m_[a-z0-9_]+\.py$/;

// state.json, checked: the content number (required), the date of the content state and the format
// (null when missing or malformed). Nothing else of it is read.
export function readState(value) {
  if (value === null || typeof value !== "object" || Array.isArray(value)) throw new Error("state.json is not an object");
  const { content, date, format } = value;
  if (!Number.isSafeInteger(content) || !NUMBER.test(String(content))) throw new Error("state.json names no content number");
  return {
    content,
    tag: `content-${content}`,
    date: typeof date === "string" && DATE.test(date) ? date : null,
    format: Number.isSafeInteger(format) ? format : null,
  };
}

export const stateUrl = (repo) => `${RAW}/${repo}/refs/heads/content/state.json`;
export const tagUrl = (repo, state, path) => `${RAW}/${repo}/refs/tags/${state.tag}/${path}`;
// The tag's files on GitHub.
export const treeUrl = (repo, state) => `https://github.com/${repo}/tree/${state.tag}`;

// A quirk file on GitHub at the tag (installs by hand download it there), null for a path that is
// no quirk file.
export function fileUrl(repo, state, file) {
  return typeof file === "string" && FILE.test(file) ? `https://github.com/${repo}/blob/${state.tag}/${file}` : null;
}

// The Zigbee2MQTT features an entry's file leaves out (manifest left_out_lines), [] when it names none.
export function leftOutLines(entry) {
  const lines = entry?.left_out_lines;
  return Array.isArray(lines) && lines.every((line) => typeof line === "string") ? lines : [];
}

// An entry's open upstream pull requests, each with its link built from its number; one without a
// number (a positive integer) is left out. The manifest's own url is never used.
export function pullRequests(entry) {
  const prs = Array.isArray(entry?.upstream_open_prs) ? entry.upstream_open_prs : [];
  return prs
    .filter((pr) => Number.isSafeInteger(pr?.number) && pr.number > 0)
    .map((pr) => ({
      number: pr.number,
      url: `${UPSTREAM_PR}${pr.number}`,
      title: typeof pr.title === "string" ? pr.title : "",
      author: typeof pr.author === "string" ? pr.author : "",
    }));
}

// How likely a file is to do something wrong on the device (manifest risk), lowest first.
export const RISKS = ["low", "medium", "high"];
// The reasons for a risk (manifest risk_why) by code, as the integration words them in its change
// list (custom_components/xquirks/text.py RISK_REASONS).
export const RISK_REASONS = Object.freeze({
  cover: "It controls a cover.",
  thermostat: "It controls a thermostat.",
  state_dependency: "One of its settings changes how another value reads.",
  mixed_manufacturer_code: "It writes a setting with a manufacturer code the rest of its cluster does not use.",
  take_over_drops: "It replaces ZHA's own quirk and leaves out features that quirk shows.",
  defect_found: "A device test found a fault. Its fix is not verified yet.",
  number_settings: "It changes number settings. The device may accept a smaller range.",
  local_occupancy: "ZHA shows delay settings for it that never reach the device.",
  take_over: "It replaces ZHA's own quirk.",
  alias_differs: "ZHA's quirk reads one of its values differently.",
});

// An entry's risk: "high" when it states none or one this page does not know.
export function risk(entry) {
  const value = entry?.risk;
  return RISKS.includes(value) ? value : "high";
}

// The reason codes of an entry's risk this page knows, each once, in the entry's order; a code it
// does not know is skipped.
export function riskWhy(entry) {
  const codes = Array.isArray(entry?.risk_why) ? entry.risk_why : [];
  return [...new Set(codes.filter((code) => typeof code === "string" && Object.hasOwn(RISK_REASONS, code)))];
}

// What the page shows of an entry's risk: null without a file or for a verified file, else its risk,
// the badge, the badge's tooltip with the reasons and, for a high risk, the note of its device card.
export function riskShown(entry) {
  if (!entry?.file || entry.status === "verified") return null;
  const tier = risk(entry);
  const reasons = riskWhy(entry).map((code) => RISK_REASONS[code]);
  return {
    tier,
    badge: `${tier} risk`,
    title: ["Not verified on a device yet.", ...reasons].join(" "),
    note: tier === "high" ? ["High risk.", ...reasons, 'The integration offers this file only with "Offer high-risk files" on in its options.'].join(" ") : null,
  };
}

// The Home Assistant release a tag's hacs.json names, patch number included; null without one.
export function homeAssistant(hacs) {
  const release = hacs?.homeassistant;
  return typeof release === "string" && RELEASE.test(release) ? release : null;
}

// What loading the device list came to, with the text to show for anything but "ready".
export const LOADING = Object.freeze({ kind: "loading", message: "The device list is still loading, try again in a moment." });

export function failure(error) {
  return { kind: "failed", message: `Could not load the device list (${error?.message ?? error}). Reload the page to try again.` };
}

// Branch and tag move together, so the tag the branch head names exists; raw may still answer 404
// for it until its cache (5 minutes) runs out.
const PUBLISHING = Object.freeze({ kind: "failed", message: "A new device list is being published: reload the page in a few minutes." });

// A content format this page does not read: the list or the page went ahead in an update, the other follows.
const UNSUPPORTED = "This page and the device list are out of sync after an update. Reload the page in a while. The xquirks integration is not affected.";

// What the page answers when it gets devices before the list is there; null once it is ready.
export const notReady = (content) => (content.kind === "ready" ? null : content.message);

class HttpError extends Error {
  constructor(name, status) {
    super(`${name}: ${status}`);
    this.status = status;
  }
}

// How long the page waits for an answer: for a file it needs, and for the optional hacs.json.
const WAIT = { answer: 20000, optional: 5000 };

async function getJson(fetch, url, options, wait) {
  const name = url.slice(url.lastIndexOf("/") + 1);
  const read = async () => {
    const response = await fetch(url, { credentials: "omit", ...options });
    if (!response.ok) throw new HttpError(name, response.status);
    try {
      return await response.json();
    } catch {
      throw new Error(`${name} is not JSON`);
    }
  };
  let timer;
  const late = new Promise((_, reject) => {
    timer = setTimeout(() => reject(new Error(`${name}: no answer`)), wait);
  });
  try {
    return await Promise.race([read(), late]);
  } finally {
    clearTimeout(timer);
  }
}

const isObject = (value) => value !== null && typeof value === "object" && !Array.isArray(value);

// The newest content state of repo through fetch (the browser's, or a stand-in in tests):
// {kind: "ready", state, manifest, homeassistant}, or kind "unsupported" (a content format this page
// does not read) or "failed", both with their message. Never throws. wait: tests shorten WAIT.
export async function loadContent(fetch, repo, wait = WAIT) {
  let value;
  try {
    // The branch head may have moved since the last visit: ask again rather than trust the cache.
    value = await getJson(fetch, stateUrl(repo), { cache: "no-cache" }, wait.answer);
  } catch (error) {
    return failure(error);
  }
  // The format first: another format may shape the rest of state.json differently.
  if (isObject(value) && Number.isSafeInteger(value.format) && !CONTENT_FORMATS.includes(value.format)) return { kind: "unsupported", message: UNSUPPORTED };
  let state;
  try {
    state = readState(value);
  } catch (error) {
    return failure(error);
  }
  if (!CONTENT_FORMATS.includes(state.format)) return { kind: "unsupported", message: UNSUPPORTED };
  // Optional: without it the page keeps its general wording of the release the files need.
  const hacs = getJson(fetch, tagUrl(repo, state, "hacs.json"), {}, wait.optional).catch(() => null);
  let manifest;
  try {
    manifest = await getJson(fetch, tagUrl(repo, state, "manifest.json"), {}, wait.answer);
  } catch (error) {
    return error instanceof HttpError && error.status === 404 ? PUBLISHING : failure(error);
  }
  if (!isObject(manifest)) return failure(new Error("manifest.json is not an object"));
  return { kind: "ready", state, manifest, homeassistant: homeAssistant(await hacs) };
}
