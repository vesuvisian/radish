# Wire and Verify

Connect the flashed Radish node to the CT-485 data pair and confirm raw frames on MQTT. Complete [Software Setup](software.md) first — Wi‑Fi, MQTT, and basic device checks should already look good.

## Preconditions

- ESP32 online in ESPHome / Home Assistant
- MQTT broker reachable (a test subscribe may still be empty until the bus is wired)
- MCU + RS-485 transceiver assembled per [Hardware Setup](hardware.md)
- AutoNet left **off** if you are on `radish2.yaml` (sniff-only until this step succeeds)

## Wiring and safety

CT-485 is a two-wire differential data bus. Radish only needs that data pair — not thermostat power.

1. Pick an access point: thermostat backplate, air handler board, an existing splice, etc.
2. **Turn off power** to the HVAC equipment before connecting anything.
3. Connect RS-485 **A/B only** to the HVAC data pair (often labeled **Data 1**/**Data 2** and/or colored **green/yellow**). Confirm against actual equipment connections, as wires may be mislabeled/miscolored.
4. **Do not** connect the RS-485 data leads to thermostat power rails (**R**/**C**) or other 24 VAC terminals — data pair only.
5. Double-check polarity and grounding before power-up. Prefer isolated RS-485 if unsure about grounds.
6. Power the ESP32/transceiver from USB or a dedicated 5V/12V supply for bring-up. R/C→DC is possible but can disturb the bus (a **24T1812** converter caused communication faults in testing); see [Hardware Setup — Power](hardware.md#power).
7. Restore HVAC power. If the system reports communication faults after reconnecting, **disconnect immediately** and inspect for shorts, reversed polarity, ground loops, or a noisy R/C-derived supply.

!!! warning
    Prefer an **isolated** RS-485 transceiver whenever the ESP32 and the HVAC share different power domains or long cable runs. See [Hardware Setup](hardware.md) for module options.

## Verify the link

With the node online and wired to the bus, subscribe to raw frames:

```bash
mosquitto_sub -h <broker> -u <user> -P <pass> -t radish/rs485/raw
```

You should see spaced uppercase hex arriving as the network talks. Traffic volume depends on the system; a quiet bus may only publish occasionally.

If captured traffic is mostly `FF` bytes or otherwise garbled, invert polarity either by:

1. swapping the physical A/B (Data 1 / Data 2) wires, or
2. swapping the UART RX/TX pin mapping in YAML

!!! danger
    If enabling later network join causes HVAC communication faults, turn AutoNet off and disconnect A/B. Sniffing-only should not transmit; treat any unexpected bus disruption as a wiring or power-domain problem until proven otherwise.

## Next steps

Once raw hex looks sane, run the [Python decoder](python-decoder.md) to pretty-print frames. Optional on-device join is covered in the [ESPHome Component](esphome-component.md) guide — keep AutoNet disabled until sniffing is solid.

## Official Specification

See [CT-485 Physical Specification](spec/ClimateTalk_2.0_CT-485_Physical_Specification_R01.pdf) for official electrical details.
