# Software Setup

Flash and configure the Radish ESP32 with ESPHome before connecting it to the HVAC bus. The first install is typically over USB; later updates can be done over-the-air.

## Choose a profile

| File | Role |
| ---- | ---- |
| [`radish.yaml`](https://github.com/vesuvisian/radish/blob/main/radish.yaml) | <ul><li>Simple sniffing</li><li><code>uart.debug</code> RX logging publishes raw hex to MQTT</li><li>Does not join or interact with the CT-485 network</li></ul> |
| [`radish2.yaml`](https://github.com/vesuvisian/radish/blob/main/radish2.yaml) | <ul><li>Sniffing plus the local <code>radish</code> external component (<code>components/</code>)</li><li>Raw hex published via component, rather than <code>uart.debug</code></li><li>Supports optional AutoNet join when enabled</li></ul> |

Start with `radish.yaml` to prove Wi‑Fi, MQTT, and raw capture. It is all that is necessary, along with `mqtt_listener.py`, to get a sense for how messages are passed around the network and to extract live data. Move to `radish2.yaml` when you want the custom component / AutoNet paths in order to actually be able to join the network and send messages — see the [ESPHome Component guide](esphome-component.md).

Both stock profiles target the AtomS3 Lite + Tail485 UART pins. See [Hardware](hardware.md) for parts and assembly.

## Prerequisites

- [ESPHome](https://esphome.io/) (Dashboard via Home Assistant, or the ESPHome CLI)
- An MQTT broker the device can reach (for example Mosquitto on Home Assistant)
- USB access to the ESP32 for the first flash
- If you're using `radish2.yaml`, the repository either needs to be cloned locally (it loads `external_components` from `./components`), or you can point the YAML at the GitHub repo

## Secrets

Create a `secrets.yaml` next to your chosen profile (ESPHome loads it automatically for `!secret` references):

```yaml
wifi_ssid: "your-ssid"
wifi_password: "your-wifi-password"
mqtt_user: "your-mqtt-user"
mqtt_password: "your-mqtt-password"
```

Do not commit real secrets. Keep `secrets.yaml` local or use your ESPHome Dashboard secrets store.

## Configure the YAML

Before flashing, edit the profile as needed:

1. **MQTT broker** — stock configs use `homeassistant.local`; change `mqtt.broker` if yours differs.
2. **API encryption / OTA / fallback AP passwords** — leave the empty placeholder strings so ESPHome can generate values on first compile, or set your own.
3. **Wi‑Fi** — already wired to `!secret wifi_ssid` / `wifi_password`.
4. **`radish2.yaml` only** — confirm `external_components` path is pointed either to the correct local location or to the repo

## First flash (USB)

1. Connect the AtomS3 (or other ESP32) over USB. HVAC wiring is not required for this step.
2. Open the profile in ESPHome Dashboard, or compile/upload with the CLI from the repo root: `esphome run radish.yaml`
3. Select the serial port for the initial install.
4. Wait for compile + upload to finish and for the device to reboot onto Wi‑Fi.

If Wi‑Fi fails, the device opens the **Radish Fallback Hotspot** captive portal so you can reconfigure connectivity.

## Verify the node

With the device powered and on the network (still no HVAC connection required):

1. Confirm it appears online in ESPHome / Home Assistant.
2. Press the AtomS3 button — the status LED should light (stock profiles wire GPIO41 → LED), and the button press should appear in the DEBUG logs.
3. Confirm MQTT connectivity (broker logs or a test subscribe). Raw CT-485 traffic appears on `radish/rs485/raw` only after the bus is wired; see [Wire and Verify](wire-and-verify.md).

## OTA updates

After the first successful flash with the `ota:` platform enabled:

1. Keep the device on the same network as your ESPHome host.
2. Run install again from Dashboard or CLI (`esphome run …`). ESPHome should offer the device over the network instead of requiring USB.
3. Use the OTA password configured in YAML (generated or set by you) when prompted.

USB remains available as a fallback if OTA fails (wrong password, device offline, or broken Wi‑Fi).

## Next steps

Wire to the CT-485 data pair only once Wi‑Fi, MQTT, and basic device checks look good. Continue in [Wire and Verify](wire-and-verify.md).
