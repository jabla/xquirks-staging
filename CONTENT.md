# Content format

The format of the quirk files this repository publishes, as the xquirks integration and the quirk
finder read them. This describes format 1.

## Branch and tags

- The orphan branch `content` holds one commit per published state, each on top of the previous
  one. It is never rewritten.
- Each of these commits carries a lightweight tag `content-<n>`. `n` starts at 1 and grows by one
  with each state. A tag never moves. The branch head is the commit of the newest tag; both are
  pushed together.
- Commit messages are not part of the format.

## Files at a tag

| Path | Content |
| --- | --- |
| `quirks/z2m_<name>.py` | the quirk files: exactly those `manifest.json` names |
| `manifest.json` | one entry per device (below) |
| `content.json` | `{"guard": "<64 hex digits>"}`: the guard the files were built for (below) |
| `hacs.json` | `"homeassistant"`: the Home Assistant release the files need (below) |
| `data/withdrawn.toml` | revisions that turned out wrong (below) |
| `state.json` | `{"content": <n>, "date": "YYYY-MM-DD", "format": <FORMAT>}`: the tag's number, the date the files were generated (UTC) and the format, for the finder |
| `LICENSE`, `THIRD_PARTY.md` | the licenses |

## Guard and format

`content.json` names `guard.identity` (in `custom_components/xquirks/guard.py`) of the integration
release the files were built for. It covers `FORMAT`, `guard.py` and `fixed_code.json`, the fixed
code the guard compares every statement of a quirk file against. A release takes only a state that
names its own guard, so it never reads a format it does not know and never checks files against
fixed code it does not ship. `FORMAT` rises when a change to these files would make an older release
misread them. A new field does not raise it: readers ignore fields they do not know.

## Home Assistant release

At a tag, `"homeassistant"` in `hacs.json` is the exact release the files were built for, patch
number included. A release takes the state only on that Home Assistant release or newer; other keys
are not read. The `hacs.json` on `main` is a different file: HACS reads it to install the
integration.

## manifest.json

An object of entries by slug. Every entry has:

- `fingerprints`: `[[manufacturer or null, model], ...]`, the device names it is for;
- `claimed_elsewhere` (optional, same shape): exact names it leaves to another entry;
- `file`: `"quirks/z2m_<name>.py"`, or null when no file is shipped;
- `status`: `"generated"`, `"verified"` or `"upstream"`;
- `swap` (optional): `{"ours": rows, "zha": rows}`, the entities of a file that takes a device over
  and those of ZHA's own quirk, each row `[cluster id, attribute id, platform, unique id suffix,
  name]`.

An entry matches a device (manufacturer, model) when one fingerprint has the device's model with its
manufacturer or null, unless that exact pair is in `claimed_elsewhere`.

An entry with a file also has:

- `sha256` (64 hex digits) and `revision` (8 hex digits, the file's `Revision:` line);
- `vendor`, `model`, `description` (optional);
- `picture` and `picture_sha256` (optional; a picture without its sha256 is not shown);
- `upstream_open_prs` (optional): `[{"number": <n>, "title": ..., "author": ...}]`, open
  zha-device-handlers pull requests for the device;
- `sources` (optional): the zigbee-herdsman-converters and zha-device-handlers versions;
- `over_zha` (optional): `{"adds": [...], "zha_only": [...]}`, entity names of a file that takes a
  device over;
- `endpoints` (optional): `{"<endpoint>": [cluster ids]}`, what the file's own check needs on the
  device.

Only the finder reads `left_out_lines` (the Zigbee2MQTT features a file leaves out), `path` and
`target` (an alias file and the device it points to), `differs` and `not_built`. Fields not listed
here are not part of the format.

## data/withdrawn.toml

```toml
[[withdrawn]]
file = "z2m_<name>.py"
revision = "<8 hex digits>"
reason = "Why it must not be used."
```

These three fields never change, not even with a new format: every release reads the withdrawals of
a newer state it cannot use otherwise.

## How the integration reads it

1. It lists the `content-<n>` tags through the GitHub API; annotated tags do not count.
2. From the newest tag down to the state it uses, it reads `content.json` and `hacs.json` at each
   tag's commit and takes the first state it can use (guard and Home Assistant release, above).
   Otherwise it keeps the state it has.
3. It reads `manifest.json` and `data/withdrawn.toml` of that commit, plus `data/withdrawn.toml` of
   a newer tag it cannot use.
4. It reads a quirk file only when its change list would write it, checked against `sha256` and the
   guard.

It reads every file at the commit a tag points to, never by the tag's name.

## How the finder reads it

1. `https://raw.githubusercontent.com/jabla/xquirks/refs/heads/content/state.json` names `n`.
2. `manifest.json` and `hacs.json` come from
   `https://raw.githubusercontent.com/jabla/xquirks/refs/tags/content-<n>/`.

The tag never moves, so both files belong to one state even while raw's cache still serves an older
`state.json`. A format the page does not read gets a notice instead of the device list. The finder
reads no quirk file; it links each one on GitHub at its tag.
