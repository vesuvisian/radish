# Hardware Setup

Radish talks to ClimateTalk networks over RS-485. You need an ESP32 (or compatible) device running ESPHome, plus an RS-485 transceiver wired only to the HVAC data pair.

## Recommended kit

Known-good setup:

| Role | Part | Notes |
| --- | --- | --- |
| MCU | [AtomS3 Lite](https://shop.m5stack.com/products/atoms3-lite-esp32s3-dev-kit) | ESP32-S3 Wi‑Fi “brain” used by the stock `radish.yaml` / `radish2.yaml` profiles |
| Transceiver | [Tail485](https://shop.m5stack.com/products/atom-tail485) | RS-485 adapter that plugs onto the Atom |
| Power | 5V or 12V supply | Enough current for the Atom + transceiver; do not power the interface from thermostat R/C |

These M5Stack parts are inexpensive and compact. Other ESP32 boards and a generic RS-485 converter (for example a MAX485 breakout) also work if you map UART TX/RX and DE/RE correctly in YAML.

## Alternative M5Stack RS-485 options

| Module | Notes |
| --- | --- |
| [Atomic 485 Base](https://shop.m5stack.com/products/atomic-rs485-base) | Allows powering setup via USB‑C<br>Has convienient mounting holes<br>However, uses most of the Atom’s GPIO pins. |
| [RS485 to TTL Converter Unit](https://shop.m5stack.com/products/rs485-module) | Leaves the Atom USB‑C port and GPIO pins available<br>Less of a single package form-factor due to ribbon connector |
| [Isolated RS485 Unit](https://shop.m5stack.com/products/isolated-rs485-unit) | Galvanic isolation — the safest choice to reduce risk of damaging HVAC electronics or creating ground loops |

Prefer an **isolated** transceiver whenever the ESP32 and the HVAC share different power domains or long cable runs.

## Wiring and safety

CT-485 is a two-wire differential data bus. Radish only needs that data pair — not thermostat power.

1. Pick an access point: thermostat backplate, air handler board, an existing splice, etc.
2. **Turn off power** to the HVAC equipment before connecting anything.
3. Connect RS-485 **A/B only** to the HVAC data pair (often labeled **Data 1**/**Data 2** and/or colored **green/yellow**). Confirm against actual equipment connections, as wires may be mislabeled/miscolored.
4. **Do not** connect this interface to thermostat power rails (**R**/**C**) or other 24 VAC terminals.
5. Double-check polarity and grounding before power-up. Prefer isolated RS-485 if unsure about grounds.
6. Power the ESP32/transceiver from its own supply (USB or dedicated 5V/12V), separate from the HVAC control transformer unless you know that is safe for your hardware.
7. If the HVAC system reports communication faults after reconnecting, **disconnect immediately** and inspect for shorts, reversed polarity, or ground loops.

## Verify the link

After flashing, and with the node online and wired to the bus, subscribe to raw frames:

```bash
mosquitto_sub -h <broker> -u <user> -P <pass> -t radish/rs485/raw
```

If captured traffic is mostly `FF` bytes or otherwise garbled, inverty polarity either by:

1. swapping the physical A/B (Data 1 / Data 2) wires, or
2. swapping the UART RX/TX pin mapping in YAML

## Official Specification

See [CT-485 Physical Specification](spec/ClimateTalk_2.0_CT-485_Physical_Specification_R01.pdf) for official electrical details.
