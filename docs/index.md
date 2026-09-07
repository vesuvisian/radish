# Radish

Radish interfaces with Daikin / ClimateTalk-style HVAC networks over CT-485 (RS-485). An ESPHome device sniffs (and optionally joins) the bus and publishes frames to MQTT; Python tooling on a host decodes that traffic for analysis.

## Getting started

Work through these in order. You can stop after sniffing + decoding if you only need visibility into the network.

1. **[Hardware setup](hardware.md)** — assemble the ESP32 + RS-485 kit and plan a safe tap onto the HVAC data pair (Data 1 / Data 2 only).
2. **[Software setup](software.md)** — create secrets, flash `radish.yaml`, confirm Wi‑Fi/MQTT/OTA **before** connecting to the bus.
3. **Wire and verify** — connect A/B per the hardware guide, then confirm raw hex on `radish/rs485/raw`.
4. **[Python decoder](python-decoder.md)** — run `mqtt_listener.py` to pretty-print live frames and filter by message type.
5. **Optional: [ESPHome component / AutoNet](esphome-component.md)** — move to `radish2.yaml` when you want on-device protocol handling and experimental network join. Keep AutoNet off until sniffing is solid.

## What this project includes

- **ESPHome sniffing profile** (`radish.yaml`) — passive UART capture to MQTT
- **ESPHome external component** (`radish2.yaml` + `components/radish`) — on-device frame handling, dataflow replies, optional AutoNet subordinate join
- **Python decoder** (`mqtt_listener.py` + `radish` package) — live decode/inspect of MQTT hex frames
- **Spec archive** — ClimateTalk PDFs used as the protocol reference

## What works today

- UART/RS-485 capture and publish to MQTT (default topic `radish/rs485/raw`)
- Frame parse/encode and checksum handling in firmware
- Controller queue / dataflow behavior (R2R + Token Offer)
- AutoNet client state machine (discovery, set-address, keepalive/relinquish)
- Subordinate handlers for network node list and shared-data sector read/write (with persistence)

Network join and subordinate responses are still experimental. Broad interrogation (actively querying status, sensors, menus, control) is not implemented yet. See the [ESPHome component guide](esphome-component.md) and [component internals](component-internals.md).

## Documentation

| Page | Contents |
| --- | --- |
| [Hardware setup](hardware.md) | Parts, alternatives, wiring, safety, link check |
| [Software setup](software.md) | Secrets, flash, verify, OTA |
| [Python decoder](python-decoder.md) | Listener install, `.env` filters, package layout |
| [ESPHome component](esphome-component.md) | `radish2.yaml`, AutoNet join, YAML options |
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
