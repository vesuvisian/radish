# radish

Radish is a project for interfacing with Daikin/ClimateTalk-style HVAC networks. It includes:

- an ESPHome profile for sniffing bus messages and publishing them to MQTT
- Python tooling for decoding and analysis of messages published on MQTT from the bus
- an ESPHome external component for bus sniffing plus joining (and eventually interrogating) the network as a subordinate device

## Hardware

Known-good setup:

- [AtomS3 Lite](https://shop.m5stack.com/products/atoms3-lite-esp32s3-dev-kit): ESP32 WiFi chip and brain
- [Tail485](https://shop.m5stack.com/products/atom-tail485): RS-485 transceiver
- 5V or 12V power supply

Other ESP32s would also work, as would an RS-485 converter such as the MAX485, but these M5Stack products are cheap enough and have a nice form factor. 

Other RS-485 options from M5Stack:
- The [Atomic 485 Base](https://shop.m5stack.com/products/atomic-rs485-base) allows power through a USB-C cable, though it uses most of the GPIO pins.
- The [RS485 to TTL Converter Unit](https://shop.m5stack.com/products/rs485-module) also avoids blocking the USB-C port.
- The [Isolated RS485 Unit](https://shop.m5stack.com/products/isolated-rs485-unit) is similar but is probably the safest way to make sure you don't break your HVAC system.

## Initial flashing and configuration

1. Set up MQTT broker, create `secrets.yaml` file, and/or edit `radish.yaml` directly.
2. Flash the ESP32 with ESPHome, using `radish.yaml` as a starting point.
3. Bring up the node and verify it is online, checking for activity from a button press.

These initial steps do not require connection to the HVAC system, and future updates can then be done over-the-air.

## Wiring and safety

- Find a suitable location to connect to the bus, such as by running additional wires from the thermostat backplate, out of the air handler itself, or from a splice elsewhere.
- Turn off power to the system while wiring to help avoid any potential shorts.
- Connect RS-485 A/B only to the HVAC data pair (often labeled Data 1 / Data 2).
- Do not connect to thermostat power rails (R/C) with this interface.
- Double-check polarity and grounding before power-up.
- If the HVAC system shows communication faults, disconnect immediately and inspect for shorts, ground loops, etc.

## Verify raw traffic

Subscribe to MQTT and confirm bus frames are flowing:

`mosquitto_sub -h <broker> -u <user> -P <pass> -t radish/rs485/raw`

If mostly `FF` bytes appear, the data pair may need to be swapped, either physically or via the UART RX/TX pin mapping in the YAML.

## Python decode tooling

`mqtt_listener.py` can decode/inspect live traffic. Typical setup:

1. Install Python requirements from `requirements.txt`.
2. Copy `.env.example` to `.env`.
3. Set broker/auth fields and optional filters:
   - `MQTT_MESSAGE_TYPES` to include only selected message types
   - `MQTT_EXCLUDE_DATAFLOW=true` to hide dataflow packets such as ACK messages
   - `MQTT_DEDUPE_REPEATED=true` to collapse adjacent duplicates, such as when messages are being routed from one subordinate to another via the coordinator

## YAML Configuration Comparison

- `radish.yaml`:
  - simple sniffing profile
  - uses `uart.debug` RX logging and publishes raw hex directly from YAML automation
  - does not attempt to interact with the network
- `radish2.yaml`:
  - sniffing + custom component profile
  - loads `external_components` from `components/` and enables the `radish:` block
  - includes AutoNet-related options (`autonet_enabled`, `autonet_join_switch`, slot-delay/keepalive settings) so it can participate in network join flows when enabled
  - still publishes raw MQTT traffic if enabled, but through the C++ `radish` component/controller path instead of plain `uart.debug` sequence logic

## Project docs

- Protocol/specification archive: `docs/spec`
- Message coverage matrix for Python parser: `docs/message_coverage_matrix.md`
- ESPHome component internals: `components/radish/README.md`

## What is implemented now

- UART/RS-485 capture and publish to MQTT (default topic `radish/rs485/raw`)
- Frame parse/encode and checksum handling in firmware (`components/radish`)
- Controller queue/dataflow behavior (R2R + Token Offer handling)
- AutoNet client state machine (discovery, set-address, keepalive/relinquish paths)
- Subordinate service routing with implemented handlers for:
  - network node list response
  - shared data sector read/write with persistence

Detailed firmware behavior is documented in `components/radish/README.md`.

## References

- Special thanks to [@rrmayer](https://github.com/rrmayer) for preserving the ClimateTalk specs [climate-talk-web-api](https://github.com/rrmayer/climate-talk-web-api)
- [ClimateTalk](https://github.com/kdschlosser/ClimateTalk)
- [Net485](https://github.com/kpishere/Net485)
- [esphome-comfortnet](https://github.com/esphome-comfortnet/esphome-comfortnet)
- [ComfortNet-HVAC-ESP32](https://github.com/smurf12345/home-assistant/tree/main/ComfortNet-HVAC-ESP32)
- [This](https://community.home-assistant.io/t/local-comfortnet-hvac-monitoring-via-esp32/821948/16) Home Assistant community discussion
