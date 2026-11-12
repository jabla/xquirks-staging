"""Collect evidence for a device: what HA shows, the ZHA diagnostics, optional setting checks.

Usage:
    HASS_URL=http://homeassistant.local:8123 HASS_TOKEN=... python tools/probe.py DEVICE [--query] [--write ENTITY ...] [--out DIR]

DEVICE is the device name in HA, its model or its IEEE address. Python's standard library is
enough; HASS_TOKEN is a long-lived access token (your profile, Security tab).

By default the probe only reads: the device and its entities from HA's registries, their
states, and HA's device diagnostics. `--query` asks the device for its current values: a Tuya
device gets a Tuya data query (it sends all its datapoints), any other device a read of each
attribute behind the quirk's entities; that changes nothing on the device. `--write ENTITY`
checks one setting: only configuration numbers and selects, written to their limits (numbers)
or to each other option (selects), read back, then set back to the value they had. Switches, buttons,
sirens and alarms are never written.

The report (`DIR/report.md`) lists every entity with a box to tick when the value matches the
device (its display or app, or what it does); attach it with `DIR/diagnostics.json` to an issue.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import pathlib
import re
import socket
import ssl
import struct
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

TUYA_CLUSTER = 0xEF00
WRITABLE = {"number", "select"}
# Seconds between the pings wait() sends; HA's heartbeat pings after 55 s without a frame.
KEEPALIVE = 30


class HAWebSocket:
    """A minimal client for HA's websocket API (text frames, no extensions). HA's heartbeat
    (aiohttp, heartbeat=55) pings a client it got no frame from for 55 s and drops the connection,
    without a close frame, when none comes within another 27.5 s. wait() pings HA every 30 s, so
    a --wait of any length keeps the connection; receive() answers HA's ping all the same. A close
    frame from HA raises ConnectionError."""

    def __init__(self, url: str, token: str) -> None:
        parts = urllib.parse.urlsplit(url)
        secure = parts.scheme in ("https", "wss")
        port = parts.port or (443 if secure else 80)
        sock = socket.create_connection((parts.hostname, port), timeout=60)  # zigpy waits up to 28 s for a sleepy device
        if secure:
            sock = ssl.create_default_context().wrap_socket(sock, server_hostname=parts.hostname)
        key = base64.b64encode(os.urandom(16)).decode()
        request = (
            f"GET /api/websocket HTTP/1.1\r\nHost: {parts.hostname}:{port}\r\nUpgrade: websocket\r\n"
            f"Connection: Upgrade\r\nSec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n"
        )
        sock.sendall(request.encode())
        response = b""
        while b"\r\n\r\n" not in response:
            chunk = sock.recv(4096)
            if not chunk:
                raise ConnectionError("websocket handshake failed")
            response += chunk
        if b" 101 " not in response.split(b"\r\n", 1)[0]:
            raise ConnectionError(response.split(b"\r\n", 1)[0].decode())
        self.sock, self.buffer, self.next_id = sock, response.split(b"\r\n\r\n", 1)[1], 1
        self.receive()  # auth_required
        self.send({"type": "auth", "access_token": token})
        reply = self.receive()
        if reply.get("type") != "auth_ok":
            raise PermissionError(f"HA refused the token: {reply.get('message', reply.get('type'))}")

    def send(self, message: dict) -> None:
        self._send_frame(0x1, json.dumps(message).encode())

    def wait(self, seconds: float) -> None:
        """Sleep, with a ping to HA every KEEPALIVE seconds: any frame restarts HA's heartbeat.
        receive() skips HA's pongs."""
        while seconds > KEEPALIVE:
            time.sleep(KEEPALIVE)
            self._send_frame(0x9, b"")
            seconds -= KEEPALIVE
        time.sleep(seconds)

    def _send_frame(self, opcode: int, data: bytes) -> None:
        header = bytearray([0x80 | opcode])
        if len(data) < 126:
            header.append(0x80 | len(data))
        elif len(data) < 65536:
            header += bytes([0x80 | 126]) + struct.pack(">H", len(data))
        else:
            header += bytes([0x80 | 127]) + struct.pack(">Q", len(data))
        mask = os.urandom(4)
        self.sock.sendall(bytes(header) + mask + bytes(b ^ mask[i % 4] for i, b in enumerate(data)))

    def _read(self, n: int) -> bytes:
        while len(self.buffer) < n:
            chunk = self.sock.recv(65536)
            if not chunk:
                raise ConnectionError("websocket closed")
            self.buffer += chunk
        data, self.buffer = self.buffer[:n], self.buffer[n:]
        return data

    def receive(self) -> dict:
        payload = b""
        while True:
            first, second = self._read(2)
            length = second & 0x7F
            if length == 126:
                length = struct.unpack(">H", self._read(2))[0]
            elif length == 127:
                length = struct.unpack(">Q", self._read(8))[0]
            data = self._read(length)
            opcode = first & 0x0F
            if opcode == 0x9:  # ping: a pong with the same payload answers it (RFC 6455, 5.5.2)
                self._send_frame(0xA, data)
            elif opcode == 0x8:  # close: HA's status code and reason, if it sent them
                status = str(struct.unpack(">H", data[:2])[0]) if len(data) >= 2 else "no status"
                reason = data[2:].decode(errors="replace")
                raise ConnectionError(f"websocket closed by Home Assistant ({status}{': ' + reason if reason else ''})")
            elif opcode < 0x8:  # a message or a part of it; control frames may come in between
                payload += data
                if first & 0x80:  # final frame
                    return json.loads(payload)

    def call(self, message: dict):
        message = {**message, "id": self.next_id}
        self.next_id += 1
        self.send(message)
        while True:
            reply = self.receive()
            if reply.get("id") == message["id"]:
                if not reply.get("success", True):
                    raise RuntimeError(f"{message['type']}: {reply.get('error')}")
                return reply.get("result")


def rest_get(url: str, token: str, path: str, tries: int = 3):
    request = urllib.request.Request(f"{url.rstrip('/')}{path}", headers={"Authorization": f"Bearer {token}"})
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                return json.loads(response.read())
        except urllib.error.HTTPError as error:  # 500 while ZHA is still starting
            if error.code != 500 or attempt == tries - 1:
                raise
            time.sleep(10)


def wait_for_zha(ws: HAWebSocket, timeout: float = 120) -> None:
    """Return once ZHA's config entry is loaded (it is not right after a reload or restart)."""
    deadline = time.monotonic() + timeout
    while True:
        states = [entry["state"] for entry in ws.call({"type": "config_entries/get", "domain": "zha"})]
        if states and all(state == "loaded" for state in states):
            return
        if time.monotonic() > deadline:
            sys.exit(f"ZHA is not loaded (state: {', '.join(states) or 'no ZHA entry'}); try again once it runs")
        time.sleep(5)


def find_device(devices: list[dict], wanted: str) -> dict:
    low = wanted.lower()
    hits = [
        d for d in devices
        if any(i[0] == "zha" for i in d.get("identifiers", []))
        and (low in {(d.get("name_by_user") or "").lower(), (d.get("name") or "").lower(), (d.get("model") or "").lower()}
             or any(i[1].lower() == low for i in d["identifiers"]))
    ]
    if len(hits) != 1:
        names = ", ".join(sorted(d.get("name_by_user") or d.get("name") or d["id"] for d in hits)) or "none"
        sys.exit(f"{len(hits)} ZHA devices match {wanted!r} ({names}); use the exact name or the IEEE address")
    return hits[0]


def states_of(ws: HAWebSocket, entity_ids: set[str]) -> dict[str, dict]:
    return {s["entity_id"]: s for s in ws.call({"type": "get_states"}) if s["entity_id"] in entity_ids}


def zcl_attributes(ws: HAWebSocket, ieee: str, data: dict) -> dict[tuple[str, str], tuple[int, int, object]]:
    """(endpoint, attribute name) to (cluster id, attribute id, stored value).

    The names come from ZHA's cluster definitions, so attributes that never reported are found
    too; the stored value comes from the diagnostics (None when ZHA has none). Tuya datapoints
    live on the device's MCU, not in readable attributes: the Tuya cluster is left out. Names that
    two clusters of an endpoint share are left out too."""
    stored = {}
    for endpoint, details in (data.get("endpoints") or {}).items():
        for cluster in details.get("in_clusters", []):
            for attribute in cluster.get("attributes", []):
                stored[(str(endpoint), int(cluster["cluster_id"], 16), int(attribute["id"], 16))] = attribute.get("value")
    found, shared = {}, set()
    for cluster in ws.call({"type": "zha/devices/clusters", "ieee": ieee}):
        if cluster.get("type") != "in" or cluster["id"] == TUYA_CLUSTER:
            continue
        endpoint = str(cluster["endpoint_id"])
        for attribute in ws.call({"type": "zha/devices/clusters/attributes", "ieee": ieee, "endpoint_id": cluster["endpoint_id"],
                                  "cluster_id": cluster["id"], "cluster_type": "in"}):
            key = (endpoint, attribute["name"])
            if key in found:
                shared.add(key)
            found[key] = (cluster["id"], attribute["id"], stored.get((endpoint, cluster["id"], attribute["id"])))
    return {key: value for key, value in found.items() if key not in shared}


def quirk_attribute(entity: dict, attributes: dict) -> tuple[str, int, int, object] | None:
    """The attribute behind a quirk entity: its unique id ends in <endpoint>-<attribute name>."""
    endpoint, _, name = entity["unique_id"].split("-", 1)[-1].partition("-")
    hit = attributes.get((endpoint, name))
    return (endpoint, *hit) if hit else None


def read_attribute(ws: HAWebSocket, ieee: str, endpoint: str, cluster_id: int, attribute_id: int) -> str:
    """Read one attribute from the device itself, not from ZHA's cache."""
    try:
        value = ws.call({"type": "zha/devices/clusters/attributes/value", "ieee": ieee, "endpoint_id": int(endpoint),
                         "cluster_id": cluster_id, "cluster_type": "in", "attribute": attribute_id})
    except (RuntimeError, OSError) as error:  # OSError: the socket timed out or closed
        return f"no answer ({error})"
    return "no answer" if value in (None, "None") else raw_value(str(value))


def raw_value(text: str) -> str:
    """ZHA returns zigpy's text for enums and booleans (Bool.true, enum8.undefined_0x01): the number."""
    if match := re.fullmatch(r"\w+\.undefined_0x([0-9a-fA-F]+)", text):
        return str(int(match.group(1), 16))
    return {"Bool.false": "0", "Bool.true": "1"}.get(text, text)


def tuya_query(ws: HAWebSocket, ieee: str) -> None:
    ws.call({"type": "call_service", "domain": "zha", "service": "issue_zigbee_cluster_command",
             "service_data": {"ieee": ieee, "endpoint_id": 1, "cluster_id": TUYA_CLUSTER, "cluster_type": "in",
                              "command": 3, "command_type": "server", "params": {}}})


def set_value(ws: HAWebSocket, entity_id: str, value) -> None:
    domain = entity_id.split(".", 1)[0]
    if domain == "number":
        ws.call({"type": "call_service", "domain": "number", "service": "set_value", "service_data": {"entity_id": entity_id, "value": value}})
    else:
        ws.call({"type": "call_service", "domain": "select", "service": "select_option", "service_data": {"entity_id": entity_id, "option": value}})


# Writes of one value before a check gives up on it.
WRITES = 3


def check_setting(ws: HAWebSocket, entity: dict, state: dict, ieee: str, tuya: bool, wait: float, attribute) -> list[str]:
    """Write the limits (numbers) or each other option (selects), read back, restore."""
    entity_id, attributes, original = entity["entity_id"], state["attributes"], state["state"]
    if original in ("unknown", "unavailable"):
        return [f"{entity_id}: skipped, the current value is {original} and could not be restored"]
    number = entity_id.startswith("number.")
    if number:
        targets = [attributes.get("min"), attributes.get("max")]
    else:
        targets = [o for o in attributes.get("options", []) if o != original]
    name, lines, sent = entity.get("original_name") or entity_id, [], []

    def shows(now: str, target) -> bool:
        if not number:
            return now == target
        try:
            return float(now) == float(target)
        except ValueError:
            return False

    def write(target) -> str:
        """Write, read back, write again while HA shows another value: a device can drop a write
        that comes right after another one. What HA shows in the end."""
        for attempt in range(1, WRITES + 1):
            set_value(ws, entity_id, target)
            sent.append(target)
            ws.wait(wait)
            if tuya:
                tuya_query(ws, ieee)
                ws.wait(wait)
            now = states_of(ws, {entity_id}).get(entity_id, {}).get("state", "no state (entity gone)")
            if shows(now, target):
                break
        device = f", the device reports {read_attribute(ws, ieee, *attribute[:3])} (raw)" if attribute else ""
        tries = f" (after {attempt} writes)" if attempt > 1 else ""
        lines.append(f"{name}: wrote {target}, HA shows {now}{device}{tries}")
        return now

    try:
        for target in [t for t in targets if t is not None]:
            write(target)
    except Exception as error:  # noqa: BLE001 - whatever stopped it, the restore below runs and the report says so
        lines.append(f"{name}: stopped, {error}")
    finally:
        # Always put the original value back, also when a write or read above failed.
        restore = float(original) if number else original
        try:
            if not shows(write(restore), restore):
                lines.append(f"{name}: RESTORE FAILED, set it back to {original} by hand (the device did not take it)")
        except Exception as error:  # noqa: BLE001 - a restore that failed in any way is reported, never lost
            if sent and sent[-1] == restore:
                lines.append(f"{name}: wrote {original} back, but could not read it back: check that it shows {original} ({error})")
            else:
                lines.append(f"{name}: RESTORE FAILED, set it back to {original} by hand ({error})")
    return lines


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("device")
    parser.add_argument("--query", action="store_true", help="ask the device for its current values (changes nothing on the device)")
    parser.add_argument("--write", nargs="*", default=[], metavar="ENTITY", help="configuration numbers/selects to check, restored afterwards")
    parser.add_argument("--wait", type=float, default=5.0, help="seconds to wait after a write or a query")
    parser.add_argument("--out", default="probe-report")
    args = parser.parse_args()
    url, token = os.environ.get("HASS_URL"), os.environ.get("HASS_TOKEN")
    if not url or not token:
        sys.exit("set HASS_URL and HASS_TOKEN")

    ws = HAWebSocket(url.replace("http", "ws", 1), token)
    wait_for_zha(ws)
    device = find_device(ws.call({"type": "config/device_registry/list"}), args.device)
    ieee = next(i[1] for i in device["identifiers"] if i[0] == "zha")
    entities = [e for e in ws.call({"type": "config/entity_registry/list"}) if e.get("device_id") == device["id"] and not e.get("disabled_by")]
    tuya = (device.get("model") or "").startswith("TS0601") or (device.get("manufacturer") or "").startswith("_T")
    unreachable = None
    if args.query and tuya:
        try:
            tuya_query(ws, ieee)
        except (RuntimeError, OSError) as error:  # OSError: the socket timed out or closed
            unreachable = str(error)
        ws.wait(args.wait)
    states = states_of(ws, {e["entity_id"] for e in entities})

    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    entry_id = next(iter(device.get("config_entries", [])), None)
    diagnostics = rest_get(url, token, f"/api/diagnostics/config_entry/{entry_id}/device/{device['id']}")
    # The IEEE address identifies the device and its owner; upstream needs the signature, not it.
    text = re.sub(r"\b[0-9a-fA-F]{2}(:[0-9a-fA-F]{2}){7}\b", "xx:xx:xx:xx:xx:xx:xx:xx", json.dumps(diagnostics, indent=1))
    (out / "diagnostics.json").write_text(text)
    data = diagnostics.get("data", diagnostics)
    attributes = {} if tuya or not args.query and not args.write else zcl_attributes(ws, ieee, data)
    behind = {e["entity_id"]: quirk_attribute(e, attributes) for e in entities}
    # Read from the device before any write, so the table shows what it reported on its own.
    read = {entity_id: read_attribute(ws, ieee, *hit[:3]) for entity_id, hit in behind.items() if hit and args.query}

    by_id = {e["entity_id"]: e for e in entities}
    write_lines = []
    for entity_id in args.write:
        entity = by_id.get(entity_id)
        if entity is None:
            write_lines.append(f"{entity_id}: not an entity of this device, skipped")
        elif entity_id.split(".", 1)[0] not in WRITABLE or entity.get("entity_category") != "config":
            write_lines.append(f"{entity_id}: only configuration numbers and selects are written, skipped")
        elif unreachable:
            write_lines.append(f"{entity_id}: skipped, the device did not answer the Tuya data query")
        else:
            write_lines += check_setting(ws, entity, states.get(entity_id, {"state": "unknown", "attributes": {}}), ieee, tuya, args.wait, behind.get(entity_id))

    lines = [
        f"# Probe report: {device.get('manufacturer')} {device.get('model')}",
        "",
        f"- Firmware: {device.get('sw_version') or 'unknown'}",
        f"- Quirk: {data.get('quirk_class') or data.get('quirk') or 'see diagnostics.json'}",
        f"- Asked the device: {('Tuya data query' if tuya else 'read of each quirk attribute') if args.query else 'no'}",
        *([f"- **The device did not answer** ({unreachable}): the states below are what ZHA stored earlier. Wake it up or check its signal, then probe again."] if unreachable else []),
        "",
        "Tick each value that matches the device (its display or app, or what it does); note what you see otherwise.",
        "\"Device (raw)\" is the attribute read from the device; it differs from ZHA's stored value where marked.",
        "",
        "| Matches | Entity | Unique id suffix | Category | State | Unit | Device (raw) |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    # Entity names and unique id suffixes only: entity ids carry area names, unique ids the IEEE.
    for entity in sorted(entities, key=lambda e: e["unique_id"].split("-", 1)[-1]):
        state = states.get(entity["entity_id"], {})
        unit = state.get("attributes", {}).get("unit_of_measurement", "")
        name = f"{entity['entity_id'].split('.', 1)[0]}: {entity.get('original_name') or entity.get('translation_key') or ''}"
        suffix = entity["unique_id"].split("-", 1)[-1]
        raw = read.get(entity["entity_id"], "")
        hit = behind.get(entity["entity_id"])
        # A named enum member (AqaraOperationMode.Relay) does not compare with the stored number.
        if raw and hit and hit[3] is None:
            raw += " (ZHA had no value)"
        elif raw and hit and raw != str(hit[3]) and not re.fullmatch(r"[A-Za-z_]\w*\.[A-Za-z_]\w*", raw):
            raw += f" (stored: {hit[3]})"
        lines.append(f"| [ ] | {name} | {suffix} | {entity.get('entity_category') or ''} | {state.get('state', '')} | {unit} | {raw} |")
    if write_lines:
        lines += ["", "## Settings checked (each restored)", ""] + [f"- {line}" for line in write_lines]
    (out / "report.md").write_text("\n".join(lines) + "\n")
    print(f"{len(entities)} entities, report in {out / 'report.md'}, diagnostics in {out / 'diagnostics.json'}")
    if unreachable:
        print(f"the device did not answer the Tuya data query: {unreachable}")
    for line in write_lines:
        print(line)


if __name__ == "__main__":
    main()
