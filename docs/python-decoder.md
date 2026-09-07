# Python Decoder

Live CT-485 traffic published by the Radish device can be decoded on a host PC with `mqtt_listener.py` and the `radish` Python package. The listener subscribes to the raw MQTT topic, parses frames, and pretty-prints known message types.

You need a working ESPHome node publishing hex frames (see [Software Setup](software.md)) and, for useful traffic, a bus connection (see [Hardware Setup](hardware.md)).

## What it does

1. Connects to your MQTT broker using settings from `.env`.
2. Subscribes to the configured topic (default `radish/rs485/raw`).
3. Parses each payload into a `Frame` (addresses, send method, message type, payload, checksum).
4. Dispatches the payload through `MessageRegistry` so known CT-485 / CT-CIM types get structured decoding.
5. Optionally filters by message type, hides dataflow packets, and collapses adjacent routed duplicates.

Parser coverage by message ID is tracked in the [Message Coverage Matrix](message_coverage_matrix.md).

## Install

From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Dependencies today: `paho-mqtt` and `python-dotenv`.

## Configure `.env`

Copy the example and edit broker / filter settings:

```bash
cp .env.example .env
```

| Variable | Purpose |
| --- | --- |
| `MQTT_HOST` | Broker hostname (default `localhost`) |
| `MQTT_PORT` | Broker port (default `1883`) |
| `MQTT_USERNAME` / `MQTT_PASSWORD` | Auth if required; leave empty for anonymous |
| `MQTT_TOPIC` | Subscribe topic (default `radish/rs485/raw`) |
| `MQTT_MESSAGE_TYPES` | Optional comma-separated allowlist, hex or decimal (e.g. `0x87,0xC1`) |
| `MQTT_EXCLUDE_DATAFLOW` | `true` to skip dataflow packets (packet number bit 7 set), such as ACKs |
| `MQTT_DEDUPE_REPEATED` | `true` to suppress immediately adjacent repeats of the same logical message (common when frames are relayed via the coordinator) |

Boolean env values accept `true`/`false`, `yes`/`no`, `on`/`off`, or `1`/`0`.

## Run the listener

With the venv active and `.env` filled in:

```bash
python mqtt_listener.py
```

On connect you should see subscription confirmation, then timestamped frame dumps as traffic arrives. Stop with Ctrl+C.

Example filter for sensor and user-menu responses only:

```env
MQTT_MESSAGE_TYPES=0x87,0xC1
MQTT_EXCLUDE_DATAFLOW=true
MQTT_DEDUPE_REPEATED=true
```

If nothing prints, confirm the ESP is online, the topic matches what the device publishes, and (for bus sniffing) that raw hex is flowing — see [Hardware Setup](hardware.md#verify-the-link).

## Package layout

| Path | Role |
| --- | --- |
| `mqtt_listener.py` | MQTT client entrypoint |
| `radish/frame.py` | CT-485 frame parse/encode and checksum |
| `radish/messages/` | Registered message classes (`ct_485`, `ct_cim`, MDI helpers) |
| `radish/messages/registry.py` | Maps message type IDs → decoder classes |
| `radish/maps.py` | Address / node-type / send-method lookups |
| `tests/` | Unit tests for frames, messages, and related contracts |

Importing `radish.messages` registers known types as a side effect. Unknown message IDs still decode as a generic `Message` with a raw payload.

## Tests

```bash
python -m unittest discover -s tests -v
```

## Related docs

- [Message Coverage Matrix](message_coverage_matrix.md) — which IDs are fully / partially parsed
- [Protocol Specification Archive](spec/README.md) — ClimateTalk PDFs used as the decode reference
- [Software Setup](software.md) — get frames onto MQTT from the ESP32
