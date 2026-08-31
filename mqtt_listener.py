"""
MQTT Listener for Radish
Reads and prints MQTT messages from your broker
"""

import os
import sys
import string
from datetime import datetime

import paho.mqtt.client as mqtt
from dotenv import load_dotenv

from radish.frame import parse_frames


def decode_hex_payload(payload: bytes) -> bytes:
    """Decode ASCII-hex MQTT payloads, tolerating spaces/colons/newlines."""
    text = payload.decode("ascii", errors="ignore")
    hex_chars = "".join(ch for ch in text if ch in string.hexdigits)
    if len(hex_chars) % 2 != 0:
        raise ValueError(f"Odd number of hex digits ({len(hex_chars)})")
    if not hex_chars:
        return b""
    return bytes.fromhex(hex_chars)


def parse_message_type_filter(raw_value: str | None) -> set[int] | None:
    """Parse comma-separated message type values (hex or decimal)."""
    if not raw_value:
        return None
    parsed: set[int] = set()
    for token in raw_value.split(","):
        value = token.strip()
        if not value:
            continue
        try:
            parsed.add(int(value, 0))
        except ValueError as exc:
            raise ValueError(
                f"Invalid MQTT_MESSAGE_TYPES value '{value}'. "
                "Use comma-separated integers like 0x87,0xC1 or 135,193."
            ) from exc
    return parsed or None


def parse_bool_env(raw_value: str | None, var_name: str) -> bool:
    """Parse common boolean env-var string values."""
    if raw_value is None or raw_value.strip() == "":
        return False
    normalized = raw_value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(
        f"Invalid {var_name} value '{raw_value}'. Use true/false, yes/no, on/off, or 1/0."
    )


def make_dedupe_key(frame: Frame) -> tuple[int, int, int, int, bytes]:
    """Build a key that ignores hop-specific routing wrappers."""
    return (
        frame.message_type,
        frame.source_node_type,
        frame.send_method,
        frame.send_parameters,
        frame.payload,
    )


def on_connect(client, userdata, flags, reason_code, properties):
    """Callback for when the client connects to the broker"""
    if reason_code == 0:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Connected to MQTT broker")
        # Subscribe to the configured topic
        topic = userdata.get("topic", "radish/#")
        client.subscribe(topic)
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Subscribed to {topic} topic")
    else:
        print(f"Failed to connect, return code {reason_code}")


def on_disconnect(client, userdata, flags, reason_code, properties):
    """Callback for when the client disconnects from the broker"""
    if reason_code != 0:
        print(
            f"[{datetime.now().strftime('%H:%M:%S')}] Unexpected disconnection (code {reason_code})"
        )
    else:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Disconnected from MQTT broker")


def on_message(client, userdata, msg):
    """Callback for when a message is received"""
    frame = Frame.from_bytes(bytes.fromhex(msg.payload))
    if userdata.get("exclude_dataflow") and (frame.packet_number & 0x80):
        return

    allowed_message_types = userdata.get("message_types")
    if allowed_message_types and frame.message_type not in allowed_message_types:
        return

    if userdata.get("dedupe_repeated"):
        dedupe_key = make_dedupe_key(frame)
        if userdata.get("last_dedupe_key") == dedupe_key:
            return
        userdata["last_dedupe_key"] = dedupe_key

    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {msg.topic}:\n{str(frame)}\n")
    # print(msg.topic, msg.payload)


def main():
    # Load environment variables from .env file
    load_dotenv()

    # MQTT broker configuration from .env
    broker_host = os.getenv("MQTT_HOST", "localhost")
    broker_port = int(os.getenv("MQTT_PORT", 1883))
    username = os.getenv("MQTT_USERNAME")
    password = os.getenv("MQTT_PASSWORD")
    topic = os.getenv("MQTT_TOPIC", "radish/#")
    message_type_filter = parse_message_type_filter(os.getenv("MQTT_MESSAGE_TYPES"))
    exclude_dataflow = parse_bool_env(
        os.getenv("MQTT_EXCLUDE_DATAFLOW"), "MQTT_EXCLUDE_DATAFLOW"
    )
    dedupe_repeated = parse_bool_env(
        os.getenv("MQTT_DEDUPE_REPEATED"), "MQTT_DEDUPE_REPEATED"
    )

    # Empty strings from .env are treated as None
    if username == "":
        username = None
    if password == "":
        password = None

    # Create MQTT client
    client = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2,
        userdata={
            "topic": topic,
            "message_types": message_type_filter,
            "exclude_dataflow": exclude_dataflow,
            "dedupe_repeated": dedupe_repeated,
            "last_dedupe_key": None,
        },
    )

    # Set callbacks
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message

    # Set username and password if provided
    if username and password:
        client.username_pw_set(username, password)
        print(f"Connecting to {broker_host}:{broker_port} as {username}...")
    else:
        print(f"Connecting to {broker_host}:{broker_port}...")
    if message_type_filter:
        rendered = ", ".join(f"0x{x:02X}" for x in sorted(message_type_filter))
        print(f"Filtering to message types: {rendered}")
    if exclude_dataflow:
        print("Filtering out dataflow packets (packet number bit 7 set)")
    if dedupe_repeated:
        print("Deduplicating immediately adjacent repeated routed messages")

    # Connect and start the loop
    try:
        client.connect(broker_host, broker_port, keepalive=60)
        client.loop_forever()
    except KeyboardInterrupt:
        print("\n\nShutting down...")
        client.disconnect()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
