#!/usr/bin/env python3
"""Enqueue a CT-485 app query via Home Assistant and await the MQTT response hex."""

from __future__ import annotations

import argparse
import json
import os
import string
import sys
import threading
import urllib.error
import urllib.request

import paho.mqtt.client as mqtt
from dotenv import load_dotenv

from radish.frame import Frame


DEFAULT_HA_URL = "http://homeassistant.local:8123"
DEFAULT_SERVICE = "esphome/radish_get_app_query"
DEFAULT_TOPIC = "radish/app_query"
DEFAULT_TIMEOUT_S = 60.0

KINDS = {
    "config": {
        "label": "Get Configuration",
        "response_type": 0x81,
    },
    "status": {
        "label": "Get Status",
        "response_type": 0x82,
    },
    "sensor": {
        "label": "Get Sensor Data",
        "response_type": 0x87,
    },
    "id": {
        "label": "Get Identification Data",
        "response_type": 0x8E,
    },
}


def decode_hex_payload(payload: bytes) -> bytes:
    """Decode ASCII-hex MQTT payloads, tolerating spaces/colons/newlines."""
    text = payload.decode("ascii", errors="ignore")
    hex_chars = "".join(ch for ch in text if ch in string.hexdigits)
    if len(hex_chars) % 2 != 0:
        raise ValueError(f"Odd number of hex digits ({len(hex_chars)})")
    if not hex_chars:
        return b""
    return bytes.fromhex(hex_chars)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Call Home Assistant esphome.radish_get_app_query, wait for the "
            "matching response hex on MQTT, parse it, and print."
        )
    )
    parser.add_argument(
        "node_type",
        type=int,
        help="Targeted CT-485 node type (e.g. 5=heat pump, 3=air handler)",
    )
    parser.add_argument(
        "--kind",
        choices=tuple(KINDS.keys()),
        required=True,
        help=(
            "Query kind: config (0x01/0x81), status (0x02/0x82), "
            "sensor (0x07/0x87), or id (0x0E/0x8E)"
        ),
    )
    parser.add_argument(
        "--url",
        default=None,
        help=f"Home Assistant base URL (default: HA_URL or {DEFAULT_HA_URL})",
    )
    parser.add_argument(
        "--service",
        default=None,
        help=f"Service path under /api/services/ (default: HA_APP_QUERY_SERVICE or {DEFAULT_SERVICE})",
    )
    parser.add_argument(
        "--topic",
        default=None,
        help=f"MQTT response topic (default: APP_QUERY_MQTT_TOPIC or {DEFAULT_TOPIC})",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=None,
        help=f"Seconds to wait for MQTT response (default: APP_QUERY_TIMEOUT or {DEFAULT_TIMEOUT_S:g})",
    )
    return parser


def call_ha_service(*, base_url: str, service: str, token: str, kind: str, node_type: int) -> None:
    endpoint = f"{base_url}/api/services/{service}"
    body = json.dumps({"kind": kind, "node_type": node_type}).encode("utf-8")
    request = urllib.request.Request(
        endpoint,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = response.read().decode("utf-8", errors="replace")
        print(f"HTTP {response.status} {endpoint}")
        if payload.strip():
            print(payload)


def frame_matches_request(frame: Frame, *, node_type: int, response_type: int) -> bool:
    if frame.message_type != response_type:
        return False
    if frame.packet_number & 0x80:
        return False
    if frame.send_method != 0x02:
        return False
    return (frame.send_parameters & 0xFF) == node_type


class AppQueryWaiter:
    """MQTT helper that is ready before the HA service call."""

    def __init__(self, *, topic: str, node_type: int, response_type: int, label: str) -> None:
        self.topic = topic
        self.node_type = node_type
        self.response_type = response_type
        self.label = label
        self._ready = threading.Event()
        self._done = threading.Event()
        self._frame: Frame | None = None
        self._error: BaseException | None = None
        self._client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self._client.on_connect = self._on_connect
        self._client.on_message = self._on_message

    def _on_connect(self, client, userdata, flags, reason_code, properties) -> None:
        if reason_code != 0:
            self._error = RuntimeError(f"MQTT connect failed (code {reason_code})")
            self._done.set()
            return
        client.subscribe(self.topic)
        self._ready.set()

    def _on_message(self, client, userdata, msg) -> None:
        try:
            raw = decode_hex_payload(msg.payload)
            frame = Frame.from_bytes(raw, validate_checksum=True)
        except Exception as exc:  # noqa: BLE001 - deliver to waiter
            self._error = exc
            self._done.set()
            return
        if not frame_matches_request(
            frame, node_type=self.node_type, response_type=self.response_type
        ):
            return
        self._frame = frame
        self._done.set()

    def start(
        self,
        *,
        broker_host: str,
        broker_port: int,
        username: str | None,
        password: str | None,
    ) -> None:
        if username and password:
            self._client.username_pw_set(username, password)
        self._client.connect(broker_host, broker_port, keepalive=60)
        self._client.loop_start()

    def wait_until_ready(self, timeout_s: float) -> None:
        if not self._ready.wait(timeout=timeout_s):
            raise TimeoutError(f"Timed out connecting/subscribing to MQTT topic {self.topic}")
        if self._error is not None:
            raise self._error

    def wait_for_frame(self, timeout_s: float) -> Frame:
        if not self._done.wait(timeout=timeout_s):
            raise TimeoutError(
                f"Timed out after {timeout_s:g}s waiting for {self.label} "
                f"response on {self.topic} (node_type={self.node_type})"
            )
        if self._error is not None:
            raise self._error
        if self._frame is None:
            raise RuntimeError("MQTT wait finished without a frame")
        return self._frame

    def stop(self) -> None:
        self._client.loop_stop()
        self._client.disconnect()


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    args = build_parser().parse_args(argv)
    kind = KINDS[args.kind]

    if args.node_type < 1 or args.node_type > 255:
        print(f"node_type must be in 1..255 (got {args.node_type})", file=sys.stderr)
        return 2

    token = os.getenv("HA_TOKEN", "").strip()
    if not token:
        print("HA_TOKEN is missing. Set it in .env (see .env.example).", file=sys.stderr)
        return 2

    base_url = (args.url or os.getenv("HA_URL") or DEFAULT_HA_URL).rstrip("/")
    service = (args.service or os.getenv("HA_APP_QUERY_SERVICE") or DEFAULT_SERVICE).lstrip("/")
    topic = args.topic or os.getenv("APP_QUERY_MQTT_TOPIC") or DEFAULT_TOPIC
    timeout_raw = os.getenv("APP_QUERY_TIMEOUT") or os.getenv("SENSOR_DATA_TIMEOUT")
    timeout_s = args.timeout if args.timeout is not None else float(timeout_raw or DEFAULT_TIMEOUT_S)
    if timeout_s <= 0:
        print("--timeout / APP_QUERY_TIMEOUT must be positive", file=sys.stderr)
        return 2

    broker_host = os.getenv("MQTT_HOST", "localhost")
    broker_port = int(os.getenv("MQTT_PORT", "1883"))
    username = os.getenv("MQTT_USERNAME") or None
    password = os.getenv("MQTT_PASSWORD") or None
    if username == "":
        username = None
    if password == "":
        password = None

    waiter = AppQueryWaiter(
        topic=topic,
        node_type=args.node_type,
        response_type=kind["response_type"],
        label=kind["label"],
    )
    try:
        waiter.start(
            broker_host=broker_host,
            broker_port=broker_port,
            username=username,
            password=password,
        )
        waiter.wait_until_ready(timeout_s=min(10.0, timeout_s))

        try:
            call_ha_service(
                base_url=base_url,
                service=service,
                token=token,
                kind=args.kind,
                node_type=args.node_type,
            )
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            print(f"HTTP {exc.code} {base_url}/api/services/{service}", file=sys.stderr)
            if detail.strip():
                print(detail, file=sys.stderr)
            return 1
        except urllib.error.URLError as exc:
            print(f"Request failed: {exc.reason}", file=sys.stderr)
            return 1

        frame = waiter.wait_for_frame(timeout_s=timeout_s)
    except (TimeoutError, RuntimeError, ValueError) as exc:
        print(f"Failed to receive {kind['label'].lower()}: {exc}", file=sys.stderr)
        return 1
    finally:
        waiter.stop()

    print(frame)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
