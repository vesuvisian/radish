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

### Good polarity

Valid CT-485 chunks are structured frames (addresses, message type, payload, checksum) — mixed bytes the [Python decoder](python-decoder.md) can parse, not long runs of nearly identical high values. Example:

```text
FF 01 03 00 00 00 01 F7 00 12 01 03 00 00 09 01 02 03 04 05 01 6F A0 B9 53 CF AC 4D 82 6B 
01 FF 03 00 00 00 A5 00 80 11 00 00 00 09 19 02 0A 40 04 03 F7 DA E2 A2 FF 94 1A B4 E8 
FF 01 03 02 03 00 01 41 00 06 01 06 00 00 00 F0 55 B6 
01 FF 03 02 03 00 A5 41 80 11 06 00 00 09 19 02 0A 40 04 03 F7 DA E2 A2 FF 94 1A 73 DD 
01 FF 03 02 03 00 03 C1 00 73 01 06 00 00 00 F0 B6 53 45 54 55 50 32 B7 C2 E1 47 41 53 20 4C 45 41 4B 20 46 55 4E E0 4F 46 46 E8 4F 4E C3 C2 E1 4C 45 41 4B 20 46 41 4E 20 54 41 50 E0 4C 4C E8 4C E0 4D E0 48 C3 C2 E1 4C 45 41 4B 20 4F 50 20 54 45 53 54 E8 4F 46 46 E0 4F 4E C3 C2 E1 47 41 53 20 53 41 4D 50 4C 45 20 44 41 54 41 20 28 74 69 6D 65 73 29 E0 4C E8 4D E0 48 C3 A7 84 F3 
FF 01 03 02 03 00 01 C1 80 11 06 00 00 09 35 36 66 30 61 01 6F A0 B9 53 CF AC 4D 1A 83 
00 FF 03 00 00 00 A5 77 00 01 00 A7 8C 
02 FF 02 00 00 00 A5 00 80 11 00 00 00 09 19 02 0A 40 04 03 F7 DA E2 A2 FF 94 1A B2 EA 
FF 02 02 02 03 00 05 02 20 00 DD 47 
```

(`53 45 54 55 50 32` / `47 41 53 20 4C 45 41 4B` are ASCII like `SETUP2` / `GAS LEAK` inside a menu payload — another sign the capture is real frames, not bit salad.)

### Reversed A/B

If Data 1/2 polarity is reversed, captures look inverted/noisy: dense `FE`/`FF` runs mixed with other high bytes, and the decoder will not produce clean frames:

```text
6A 34 7E FA FE 12 9A 02 7E FE FE 6A 98 FE 02 F2 FA EA FE FE FE FC FE FE …
00 00 7F 7E FF FF FD 13 81 F9 FD F5 FF FF FF FF FF FF FF FF FF FF …
```

Fix by swapping the physical Data 1 / Data 2 wires (or the RS-485 A/B leads), then power-cycle if the UART stays quiet after the swap.

Do **not** treat UART `tx_pin` / `rx_pin` swaps as a polarity fix. Those pins must match the transceiver (ESP RX ← RO, ESP TX → DI). Wiring them backwards can silence RX or lock up the UART until you restore the correct mapping and power-cycle.

!!! danger
    If enabling later network join causes HVAC communication faults, turn AutoNet off and disconnect A/B. Sniffing-only should not transmit; treat any unexpected bus disruption as a wiring or power-domain problem until proven otherwise.

## Next steps

Once raw hex looks sane, run the [Python decoder](python-decoder.md) to pretty-print frames. Optional on-device join is covered in the [ESPHome Component](esphome-component.md) guide — keep AutoNet disabled until sniffing is solid.

## Official Specification

See [CT-485 Physical Specification](spec/ClimateTalk_2.0_CT-485_Physical_Specification_R01.pdf) for official electrical details.
