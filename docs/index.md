# Radish

<p align="center">
  <img src="assets/logo.png" alt="Radish logo" width="280">
</p>

Radish is a project that interfaces with Daikin / ClimateTalk-style HVAC networks over CT-485 (RS-485). An ESPHome device sniffs (and optionally joins) the network and publishes frames to MQTT. Additionally Python tooling on a host is able to decode that traffic for analysis.

## Getting started

Work through these in order. You can stop after sniffing + decoding if you only need visibility into the network.

1. **[Hardware setup](hardware.md)** — assemble the ESP32 + RS-485 kit (leave the HVAC bus disconnected for now).
2. **[Software setup](software.md)** — create secrets, flash `radish.yaml`, confirm Wi‑Fi/MQTT/OTA **before** connecting to the bus.
3. **[Wire and verify](wire-and-verify.md)** — connect A/B to Data 1 / Data 2 only, then confirm raw hex on `radish/rs485/raw`.
4. **[Python decoder](python-decoder.md)** — run `mqtt_listener.py` to pretty-print live frames and filter by message type.
5. **Optional: [ESPHome component / AutoNet](esphome-component.md)** — move to `radish2.yaml` when you want on-device protocol handling and experimental network join. Keep AutoNet off until sniffing is solid.

## What this project includes

- **ESPHome sniffing profile** (`radish.yaml`) — passive UART capture to MQTT
- **ESPHome external component** (`radish2.yaml` + `components/radish`) — on-device frame handling, dataflow replies, optional AutoNet subordinate join, and originated read-only app queries (configuration / status / sensor / identification)
- **Python decoder** (`mqtt_listener.py` + `radish` package) — live decode/inspect of MQTT hex frames
- **Host query helper** (`request_ct_query.py`) — trigger an app query via Home Assistant and print the decoded MQTT response
- **Spec archive** — ClimateTalk PDFs used as the protocol reference

## What works today

- UART/RS-485 capture and publish to MQTT (default topic `radish/rs485/raw`)
- Frame parse/encode and checksum handling in firmware
- Controller queue / dataflow behavior (R2R + Token Offer)
- AutoNet client state machine (discovery, set-address, keepalive/relinquish)
- Subordinate handlers for network node list and shared-data sector read/write (with persistence)
- Optional Get Configuration (`0x01`), Get Status (`0x02`), Get Sensor Data (`0x07`), and Get Identification Data (`0x0E`) after join, triggered from Home Assistant

Network join and subordinate responses are still experimental. Other interrogation (menus, control) is not implemented. See the [ESPHome component guide](esphome-component.md) and [component internals](component-internals.md).

## Documentation

### Setup (operators)

| Page | Contents |
| --- | --- |
| [Hardware setup](hardware.md) | Parts, alternatives, off-bus assembly, photo of the kit |
| [Software setup](software.md) | Secrets, flash, verify, OTA |
| [Wire and verify](wire-and-verify.md) | Bus tap, safety, raw MQTT link check |
| [Python decoder](python-decoder.md) | Listener install, `.env` filters, example decoded output |
| [ESPHome component](esphome-component.md) | `radish2.yaml`, AutoNet join, YAML options |

### Reference (contributors)

| Page | Contents |
| --- | --- |
| [Glossary](glossary.md) | CT-485 / hardware / Radish terms |
| [Component internals](component-internals.md) | Firmware layout, state machines, behavior rules |
| [Message coverage matrix](message_coverage_matrix.md) | Which message IDs the Python parser handles |
| [Protocol specification archive](spec/README.md) | ClimateTalk PDF index and license notes |

## Repository

Source, ESPHome profiles, and issue tracking live on GitHub: [vesuvisian/radish](https://github.com/vesuvisian/radish).

## References

- Thanks to [@rrmayer](https://github.com/rrmayer) for preserving the ClimateTalk specs ([climate-talk-web-api](https://github.com/rrmayer/climate-talk-web-api))
- [ClimateTalk](https://github.com/kdschlosser/ClimateTalk)
- [Net485](https://github.com/kpishere/Net485)
- [esphome-comfortnet](https://github.com/esphome-comfortnet/esphome-comfortnet)
- [ComfortNet-HVAC-ESP32](https://github.com/smurf12345/home-assistant/tree/main/ComfortNet-HVAC-ESP32)
- [Home Assistant community discussion](https://community.home-assistant.io/t/local-comfortnet-hvac-monitoring-via-esp32/821948/16)
- [openHAB community discussion](https://community.openhab.org/t/hvac-climatetalk-protocol/8367/3)
