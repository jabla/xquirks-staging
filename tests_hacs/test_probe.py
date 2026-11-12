"""tools/probe.py against a stand-in for HA's websocket: the setting check and an unreachable device."""

from __future__ import annotations

import importlib.util
import json
import pathlib
import struct

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("probe", ROOT / "tools/probe.py")
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)

SELECT = "select.sensor_mode"


class FakeWS:
    """Keeps one select's or number's state; a Tuya data query fails while the device is away. drops:
    how often the device drops a write of a value before it takes one."""

    def __init__(self, state: str, away: bool = False, drops: dict | None = None, entity_id: str = SELECT) -> None:
        self.state, self.away, self.written, self.drops, self.entity_id = state, away, [], dict(drops or {}), entity_id

    def wait(self, seconds: float) -> None:
        probe.time.sleep(seconds)

    def call(self, message: dict):
        if message["type"] == "get_states":
            return [{"entity_id": self.entity_id, "state": self.state, "attributes": {"options": ["a", "b", "c"]}}]
        if message.get("service") == "issue_zigbee_cluster_command" and self.away:
            raise RuntimeError("call_service: Failed to send request: device did not respond")
        if message.get("service") in ("select_option", "set_value"):
            data = message["service_data"]
            value = data.get("option", data.get("value"))
            self.written.append(value)
            if self.drops.get(value, 0):
                self.drops[value] -= 1
            else:
                self.state = str(int(value)) if isinstance(value, float) else str(value)
        return None


def test_select_check_writes_every_other_option_then_restores(monkeypatch):
    monkeypatch.setattr(probe.time, "sleep", lambda _: None)
    ws = FakeWS("b")
    entity = {"entity_id": SELECT, "original_name": "Sensor mode"}
    lines = probe.check_setting(ws, entity, {"state": "b", "attributes": {"options": ["a", "b", "c"]}}, "ieee", True, 0, None)
    assert ws.written == ["a", "c", "b"]
    assert lines == ["Sensor mode: wrote a, HA shows a", "Sensor mode: wrote c, HA shows c", "Sensor mode: wrote b, HA shows b"]


def test_unreachable_device_stops_the_check_and_still_restores(monkeypatch):
    monkeypatch.setattr(probe.time, "sleep", lambda _: None)
    ws = FakeWS("b", away=True)
    entity = {"entity_id": SELECT, "original_name": "Sensor mode"}
    lines = probe.check_setting(ws, entity, {"state": "b", "attributes": {"options": ["a", "b", "c"]}}, "ieee", True, 0, None)
    assert lines[0].startswith("Sensor mode: stopped, call_service: Failed to send request")
    # The restore went out, only the query after it failed.
    assert lines[1].startswith("Sensor mode: wrote b back, but could not read it back: check that it shows b")
    assert ws.written == ["a", "b"]


def test_restore_that_does_not_go_out_is_flagged(monkeypatch):
    monkeypatch.setattr(probe.time, "sleep", lambda _: None)
    ws = FakeWS("b", away=True)
    calls = []

    def refuse(ws_, entity_id, value):
        calls.append(value)
        if len(calls) > 1:
            raise OSError("timed out")
        ws_.state = value

    monkeypatch.setattr(probe, "set_value", refuse)
    lines = probe.check_setting(ws, {"entity_id": SELECT, "original_name": "Sensor mode"}, {"state": "b", "attributes": {"options": ["a", "b"]}}, "ieee", False, 0, None)
    assert lines == ["Sensor mode: wrote a, HA shows a", "Sensor mode: RESTORE FAILED, set it back to b by hand (timed out)"]


def test_unknown_value_is_never_written(monkeypatch):
    ws = FakeWS("unknown")
    lines = probe.check_setting(ws, {"entity_id": SELECT}, {"state": "unknown", "attributes": {}}, "ieee", True, 0, None)
    assert ws.written == []
    assert lines == [f"{SELECT}: skipped, the current value is unknown and could not be restored"]


def test_a_dropped_write_is_written_again(monkeypatch):
    """Seen on a Tuya presence sensor: a write right after another one did not reach the device."""
    monkeypatch.setattr(probe.time, "sleep", lambda _: None)
    ws = FakeWS("b", drops={"c": 1})
    lines = probe.check_setting(ws, {"entity_id": SELECT, "original_name": "Sensor mode"}, {"state": "b", "attributes": {"options": ["a", "b", "c"]}}, "ieee", True, 0, None)
    assert ws.written == ["a", "c", "c", "b"]
    assert lines == ["Sensor mode: wrote a, HA shows a", "Sensor mode: wrote c, HA shows c (after 2 writes)", "Sensor mode: wrote b, HA shows b"]


def test_a_restore_the_device_never_takes_is_flagged(monkeypatch):
    monkeypatch.setattr(probe.time, "sleep", lambda _: None)
    number = "number.motion_sensitivity"
    ws = FakeWS("3", drops={3.0: 9}, entity_id=number)
    state = {"state": "3", "attributes": {"min": 0, "max": 7}}
    lines = probe.check_setting(ws, {"entity_id": number, "original_name": "Motion sensitivity"}, state, "ieee", True, 0, None)
    assert ws.written == [0, 7, 3.0, 3.0, 3.0]
    assert lines == [
        "Motion sensitivity: wrote 0, HA shows 0",
        "Motion sensitivity: wrote 7, HA shows 7",
        "Motion sensitivity: wrote 3.0, HA shows 7 (after 3 writes)",
        "Motion sensitivity: RESTORE FAILED, set it back to 3 by hand (the device did not take it)",
    ]


def test_numbers_compare_by_value(monkeypatch):
    monkeypatch.setattr(probe.time, "sleep", lambda _: None)
    number = "number.output_time"
    ws = FakeWS("10", entity_id=number)
    lines = probe.check_setting(ws, {"entity_id": number, "original_name": "Output time"}, {"state": "10", "attributes": {"min": 10, "max": 1800}}, "ieee", True, 0, None)
    assert ws.written == [10, 1800, 10.0]
    assert lines == ["Output time: wrote 10, HA shows 10", "Output time: wrote 1800, HA shows 1800", "Output time: wrote 10.0, HA shows 10"]


def test_any_failure_still_reports_the_restore(monkeypatch):
    """Not only RuntimeError and OSError: whatever stops the check, the report says whether the
    original value went back."""
    monkeypatch.setattr(probe.time, "sleep", lambda _: None)

    def broken(ws_, entity_id, value):
        raise ValueError("unexpected reply")

    monkeypatch.setattr(probe, "set_value", broken)
    lines = probe.check_setting(FakeWS("b"), {"entity_id": SELECT, "original_name": "Sensor mode"}, {"state": "b", "attributes": {"options": ["a", "b"]}}, "ieee", False, 0, None)
    assert lines == ["Sensor mode: stopped, unexpected reply", "Sensor mode: RESTORE FAILED, set it back to b by hand (unexpected reply)"]


def frame(opcode: int, payload: bytes) -> bytes:
    """A frame from HA (unmasked)."""
    length = bytes([len(payload)]) if len(payload) < 126 else bytes([126]) + struct.pack(">H", len(payload))
    return bytes([0x80 | opcode]) + length + payload


def client_frame(data: bytes) -> tuple[int, bytes]:
    """Opcode and payload of a frame from the client (masked)."""
    length, offset = data[1] & 0x7F, 2
    if length == 126:
        length, offset = struct.unpack(">H", data[2:4])[0], 4
    mask, payload = data[offset:offset + 4], data[offset + 4:offset + 4 + length]
    return data[0] & 0x0F, bytes(b ^ mask[i % 4] for i, b in enumerate(payload))


class HASocket:
    """HA's end of the websocket: the handshake, the auth, then FakeWS answers each call. HA's
    heartbeat (aiohttp, every 55 s without traffic) pings before each answer when ping is set.
    close_after: the calls answered before HA closes the connection (a close frame, then nothing).
    clock: a clock the test's time.sleep moves on; with it HA, like aiohttp's heartbeat, pings a client
    it got no frame from for 55 s and drops it, without a close frame, after another 27.5 s without one."""

    def __init__(self, ha: FakeWS, ping: bool = True, close_after: int | None = None, clock: list[float] | None = None) -> None:
        self.ha, self.ping, self.close_after, self.clock = ha, ping, close_after, clock
        self.incoming, self.upgraded, self.closed, self.calls, self.pongs = b"", False, False, 0, []
        self.last = clock[0] if clock else 0.0

    def sendall(self, data: bytes) -> None:
        if self.clock:
            if self.clock[0] - self.last > 55 + 27.5:
                self.closed = True
            elif self.clock[0] - self.last > 55:
                self.incoming += frame(0x9, b"")
            self.last = self.clock[0]
        if self.closed:
            raise BrokenPipeError(32, "Broken pipe")
        if not self.upgraded:
            self.upgraded = True
            self.incoming += b"HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n\r\n" + frame(0x1, b'{"type": "auth_required"}')
            return
        opcode, payload = client_frame(data)
        if opcode == 0xA:
            self.pongs.append(payload)
            return
        if opcode == 0x9:  # aiohttp answers a ping from the client with a pong
            self.incoming += frame(0xA, payload)
            return
        message = json.loads(payload)
        if message["type"] == "auth":
            self.incoming += frame(0x1, b'{"type": "auth_ok"}')
        elif self.close_after is not None and self.calls == self.close_after:
            self.incoming += frame(0x8, struct.pack(">H", 1001) + b"going away")
            self.closed = True
        else:
            self.calls += 1
            reply = {"id": message["id"], "type": "result", "success": True, "result": self.ha.call(message)}
            self.incoming += (frame(0x9, b"hb") if self.ping else b"") + frame(0x1, json.dumps(reply).encode())

    def recv(self, n: int) -> bytes:
        data, self.incoming = self.incoming[:n], self.incoming[n:]
        return data


def connect(monkeypatch, ha_socket: HASocket):
    monkeypatch.setattr(probe.socket, "create_connection", lambda address, timeout: ha_socket)
    return probe.HAWebSocket("ws://homeassistant.local:8123", "token")


def test_the_heartbeat_ping_gets_its_pong(monkeypatch):
    """HA pings a client that sent nothing for 55 s (a --wait of 55 or more): the probe answers
    and goes on."""
    monkeypatch.setattr(probe.time, "sleep", lambda _: None)
    ha = HASocket(FakeWS("b"))
    lines = probe.check_setting(connect(monkeypatch, ha), {"entity_id": SELECT, "original_name": "Sensor mode"}, {"state": "b", "attributes": {"options": ["a", "b", "c"]}}, "ieee", False, 0, None)
    assert lines == ["Sensor mode: wrote a, HA shows a", "Sensor mode: wrote c, HA shows c", "Sensor mode: wrote b, HA shows b"]
    assert ha.ha.written == ["a", "c", "b"]
    assert ha.pongs == [b"hb"] * ha.calls


@pytest.mark.parametrize("close_after", [1, 2])
def test_a_closed_connection_is_reported_with_the_restore(monkeypatch, close_after):
    """HA closes the connection instead of answering a read-back or the next write: the check stops, and the
    report says that the original value could not be written back."""
    monkeypatch.setattr(probe.time, "sleep", lambda _: None)
    ha = HASocket(FakeWS("b"), ping=False, close_after=close_after)
    lines = probe.check_setting(connect(monkeypatch, ha), {"entity_id": SELECT, "original_name": "Sensor mode"}, {"state": "b", "attributes": {"options": ["a", "b", "c"]}}, "ieee", False, 0, None)
    assert lines[:-2] == ["Sensor mode: wrote a, HA shows a"][:close_after - 1]
    assert lines[-2] == "Sensor mode: stopped, websocket closed by Home Assistant (1001: going away)"
    assert lines[-1].startswith("Sensor mode: RESTORE FAILED, set it back to b by hand (")


@pytest.mark.parametrize("tuya", [False, True])
def test_a_wait_longer_than_the_heartbeat_keeps_the_connection(monkeypatch, tuya):
    """HA drops a client it got nothing from for 55 + 27.5 s (aiohttp's heartbeat): a --wait of
    90 s still reads every value back and restores the original one."""
    clock = [0.0]
    monkeypatch.setattr(probe.time, "sleep", lambda seconds: clock.__setitem__(0, clock[0] + seconds))
    ha = HASocket(FakeWS("b"), ping=False, clock=clock)
    lines = probe.check_setting(connect(monkeypatch, ha), {"entity_id": SELECT, "original_name": "Sensor mode"}, {"state": "b", "attributes": {"options": ["a", "b", "c"]}}, "ieee", tuya, 90, None)
    assert lines == ["Sensor mode: wrote a, HA shows a", "Sensor mode: wrote c, HA shows c", "Sensor mode: wrote b, HA shows b"]
    assert ha.ha.written == ["a", "c", "b"]
    assert clock[0] == (6 if tuya else 3) * 90
