// The matching rules of the integration (custom_components/xquirks/matching.py) for the quirk
// finder page. Kept free of the DOM so that tests can run it in node and compare it with
// matching.py on the same inputs.

// The template the page shows: in Developer tools > Template it lists every ZHA device as
// "manufacturer||model".
export const TEMPLATE = [
  "{%- set ns = namespace(devices=[]) -%}",
  "{%- for entity in integration_entities('zha') -%}",
  "{%- set device = device_id(entity) -%}",
  "{%- if device -%}{%- set ns.devices = ns.devices + [(device_attr(device, 'manufacturer') or '') ~ '||' ~ (device_attr(device, 'model') or '')] -%}{%- endif -%}",
  "{%- endfor -%}",
  "{{ ns.devices | unique | list | tojson }}",
].join("\n");

const key = (pair) => JSON.stringify(pair);

// Python orders strings by code point; the < operator of JS compares UTF-16 units.
export function compareStrings(a, b) {
  let i = 0;
  while (i < a.length && i < b.length) {
    const x = a.codePointAt(i);
    const y = b.codePointAt(i);
    if (x !== y) return x - y;
    i += x > 0xffff ? 2 : 1;
  }
  return (i < a.length) - (i < b.length);
}

export const compareDevices = (a, b) => compareStrings(a[0], b[0]) || compareStrings(a[1], b[1]);

// Every object with a string "manufacturer" and "model" counts as a device, at any depth
// (integration diagnostics list all devices, a device's diagnostics one).
function collect(value, found) {
  if (Array.isArray(value)) {
    for (const item of value) collect(item, found);
  } else if (value !== null && typeof value === "object") {
    const { manufacturer, model } = value;
    if (typeof manufacturer === "string" && typeof model === "string") found.set(key([manufacturer, model]), [manufacturer, model]);
    for (const item of Object.values(value)) collect(item, found);
  }
  return found;
}

export function devicesIn(value) {
  return [...collect(value, new Map()).values()].sort(compareDevices);
}

// The output of TEMPLATE: "manufacturer||model", split at the first "||", pairs with an empty
// side dropped.
export function devicesFromTemplate(list) {
  const found = new Map();
  for (const item of list) {
    const at = typeof item === "string" ? item.indexOf("||") : -1;
    if (at < 0) continue;
    const pair = [item.slice(0, at), item.slice(at + 2)];
    if (pair[0] && pair[1]) found.set(key(pair), pair);
  }
  return [...found.values()].sort(compareDevices);
}

// A dropped or pasted JSON: diagnostics, the template's output or a list with both.
export function devicesFromJson(value) {
  const found = collect(value, new Map());
  if (Array.isArray(value)) for (const pair of devicesFromTemplate(value)) found.set(key(pair), pair);
  return [...found.values()].sort(compareDevices);
}

// matches(): per manifest entry (by slug) and device, sorted like matching.py. A fingerprint with
// manufacturer null matches any manufacturer except the names in the entry's claimed_elsewhere.
export function matches(manifest, devices) {
  const sorted = [...devices].sort(compareDevices);
  const result = [];
  for (const slug of Object.keys(manifest).sort(compareStrings)) {
    const entry = manifest[slug];
    const claimed = new Set((entry.claimed_elsewhere || []).map(key));
    for (const device of sorted) {
      // One result per device, also when it matches an exact and a model-only fingerprint.
      const fits = entry.fingerprints.some(([manufacturer, model]) => device[1] === model && (manufacturer === null || manufacturer === device[0]));
      if (fits && !claimed.has(key(device))) result.push({ device, slug, entry });
    }
  }
  return result;
}
