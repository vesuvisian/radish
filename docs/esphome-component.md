# ESPHome Component

The `radish` external component (used by [`radish2.yaml`](https://github.com/vesuvisian/radish/blob/main/radish2.yaml)) goes beyond passive sniffing: it can parse CT-485 frames on-device, answer dataflow opportunities, and optionally **join the network as a subordinate** via AutoNet.

Use [`radish.yaml`](https://github.com/vesuvisian/radish/blob/main/radish.yaml) first if you only need raw MQTT capture. Switch to this profile when you want network participation. Flash and Wi‑Fi setup are covered in [Software Setup](software.md); bus wiring in [Wire and Verify](wire-and-verify.md).

For file-level and protocol-rule detail, see [Component Internals](component-internals.md).

## What you get

| Capability | With `radish.yaml` | With `radish2.yaml` + component |
| --- | --- | --- |
| Publish raw hex to MQTT | Yes (`uart.debug`) | Yes (component path) |
| On-device frame parse / checksum | No | Yes |
| Reply to R2R / Token Offer when addressed | No | Yes (when participating) |
| AutoNet discovery → address assignment | No | Optional (`autonet_enabled` / join switch) |
| Answer selected application messages | No | Partial (see below) |

Default stock config keeps AutoNet **off** (`autonet_enabled: false`) so the device can sniff like `radish.yaml` until you opt in.

## Prerequisites

- Repo cloned locally — `radish2.yaml` loads `external_components` from `./components`
- Device already online on Wi‑Fi/MQTT per [Software Setup](software.md)
- Healthy raw traffic on the bus before enabling join (see [Wire and Verify](wire-and-verify.md#verify-the-link))
- Comfort with experimental firmware: joining sends frames on a live HVAC network

## Recommended workflow

1. **Prove sniffing** with `radish.yaml` (or `radish2.yaml` with AutoNet left off). Confirm `radish/rs485/raw` looks sane in MQTT or the [Python decoder](python-decoder.md).
2. **Flash `radish2.yaml`** from the repo root so the local `components/` tree is available: `esphome run radish2.yaml`
3. **Leave AutoNet disabled** at first. Stock YAML sets `autonet_enabled: false` and exposes a Home Assistant / ESPHome switch named **Radish AutoNet Join**.
4. **Enable join only when ready** — turn on the join switch (or set `autonet_enabled: true` and reflash). Watch HVAC communication status and MQTT traffic. If the system faults, turn the switch off, and the system should eventually reset itself.
5. **Keep the Python decoder running** while joining so you can see discovery / set-address / confirmation exchanges.

## How AutoNet join works (plain language)

Note: see [CT-485 Networking Specification](spec/ClimateTalk_2.0_CT-485_Networking_Specification_R01.pdf) for full details.

When AutoNet is enabled, Radish acts as an AutoNet **client** (subordinate), not a coordinator:

1. Coordinator periodically broadcasts a **Node Discovery** request.
2. Radish waits a **Slot Delay** (same generator used for Token Offer responses), then may reply with discovery info (MAC, session, node type) if no other device has yet responded. By default the delay is a CT-485 pseudorandom value in 100–2500 ms; YAML may override with a fixed `slot_delay_ms`.
3. Coordinator may send a **Set Address** assigning an address/subnet; Radish accepts only when write-enabled and MAC/session match.
4. Once addressed, Radish answers **Get Node ID**, **Address Confirmation**, and participates in dataflow (**R2R**, **Token Offer**) so it can send queued replies.
5. At any time, if an **Address Confirmation Broadcast** is not seen for **120 s**, or the subordinate’s **Expected Node Position** in that confirmation does not match (node-list / node-type mismatch), Radish **relinquishes** its address and subnet, re-enters the network, and waits to be addressed again. Set Address to `0/0` or turning AutoNet off also forces relinquish.

Local address and subnet are assigned at runtime by the coordinator — they are not set in YAML.

## What works today vs not yet

**Implemented**

- UART capture, frame codec, TX queue / arbitration
- AutoNet client lifecycle (discovery, set-address, keepalive, relinquish)
- Subordinate handlers for:
    - `SetNetworkNodeList` (`0x14` / `0x94`)
    - `NetworkSharedDataSector` read/write (`0x7D` / `0xFD`) with persistence
- Originated application queries after join: **Get Configuration** (`0x01`), **Get Status** (`0x02`), **Get Sensor Data** (`0x07`), and **Get Identification Data** (`0x0E`). See [Requesting application queries](#requesting-application-queries).

**Not implemented (yet)**

- Other application interrogation (menus, control commands, and further polls beyond the four above)
- Custom responses for most other application message IDs (they are routed but unanswered)

Treat network join as experimental: useful for learning AutoNet and holding a subordinate slot, not as a full thermostat replacement.

## YAML options

Stock `radish:` block from `radish2.yaml`:

```yaml
radish:
  uart_id: rs485_bus
  mqtt_topic: radish/rs485/raw
  app_query_mqtt_topic: radish/app_query
  publish_timeout_ms: 100ms
  max_frame_bytes: 256
  hex_delimiter: " "
  enable_raw_mqtt_forwarding: true
  local_node_type: 39
  autonet_enabled: false
  autonet_join_switch:
    name: "Radish AutoNet Join"
  # slot_delay_ms: 250ms  # optional fixed override (100ms..2500ms); omit to derive per CT-485
  mac_from_device_identity: true
  # local_mac_address: "00:00:09:12:34:56:78:9A"
```

### MQTT / capture

| Option | Default | Notes |
| --- | --- | --- |
| `mqtt_topic` | `radish/rs485/raw` | Raw hex publish topic |
| `app_query_mqtt_topic` | `radish/app_query` | Hex publish for a matching Get Configuration / Status / Sensor / Identification response |
| `enable_raw_mqtt_forwarding` | `true` | Turn off to stop MQTT hex spam while still running the controller |
| `hex_delimiter` | `" "` | Matches the Python listener’s spaced-hex expectation |
| `publish_timeout_ms` | `100ms` | Flush UART buffer to the controller / MQTT |
| `max_frame_bytes` | `256` | Max chunk size before forced flush |

### Identity

| Option | Default | Notes |
| --- | --- | --- |
| `local_node_type` | `39` | Node type advertised during AutoNet |
| `mac_from_device_identity` | `true` | Derive 8-byte MAC from device identity when possible |
| `local_mac_address` | unset | Optional override; must be 8 bytes starting with `00:00:09`<br>(`00:09` being the Daikin manufacturer ID) |

### AutoNet

| Option | Default | Notes |
| --- | --- | --- |
| `autonet_enabled` | `false` | Boot-time join enable; prefer the switch for experiments |
| `autonet_join_switch` | optional | Runtime on/off in HA/ESPHome; off forces relinquish |
| `slot_delay_ms` | unset | Optional fixed Slot Delay (100–2500 ms). When omitted, derived per CT-485: pseudorandom uniform in that range |
| `autonet_deterministic_seed` | unset | Optional external PRNG seed for Slot Delay (tests / reproducibility). When unset, device MAC seeds the generator |

Keepalive is fixed by the CT-485 spec (not configurable): if an Address Confirmation Broadcast is missing for **120 s**, or Expected Node Position does not match, the subordinate must relinquish and wait to be re-addressed.

Stock `radish2.yaml` also sets `custom_services: true` under `api:` so Home Assistant can call `get_app_query`. The component forces the matching compile defines when loaded, so a missing YAML flag does not break the build; keep the flag in YAML for clarity.

## Requesting application queries

After AutoNet join, Home Assistant can ask radish to enqueue a read-only application poll through one service: `esphome.<device_name>_get_app_query`. With `esphome.name: radish` that is `esphome.radish_get_app_query`.

| `kind` (canonical) | Also accepted | Request / response | Label |
| --- | --- | --- | --- |
| `config` | `configuration` | `0x01` / `0x81` | Get Configuration |
| `status` | — | `0x02` / `0x82` | Get Status |
| `sensor` | `sensor_data` | `0x07` / `0x87` | Get Sensor Data |
| `id` | `identification`, `ident` | `0x0E` / `0x8E` | Get Identification Data |

`kind` matching is case-insensitive. `request_ct_query.py` uses the canonical names only.

```yaml
action: esphome.radish_get_app_query
data:
  kind: config   # or status, sensor, or id
  node_type: 5   # heat pump; 3 is the air handler
```

Or from the repo root (reads `HA_TOKEN` / `HA_URL` / MQTT settings from `.env`; see `.env.example`):

```bash
python request_ct_query.py 5 --kind config
python request_ct_query.py 3 --kind status
python request_ct_query.py 5 --kind sensor
python request_ct_query.py 5 --kind id
```

The script subscribes to `APP_QUERY_MQTT_TOPIC` (default `radish/app_query`), calls the HA service, waits for a matching response hex frame, parses it with the Python decoder, prints it, and exits. Use `--timeout` / `APP_QUERY_TIMEOUT` if the bus is slow.

The HA call does not write to the bus immediately. Radish builds the same routed request the thermostat uses (destination `255`, send method 2, targeted node type in the low byte of the send parameters, empty payload) and waits for the next Token Offer / R2R turn. When a matching non-dataflow response arrives for the pending node type, the full frame hex is published on `app_query_mqtt_topic`. The call is ignored if radish is not addressed, if `kind` is unknown, if `node_type` is outside `1..255`, or if the transmit queue is full.

This is a second querier on a live bus. The stock identity is still a temperature sensor (node type 39), not a thermostat. Prefer a short join window, and do not send control commands this way.

## Safety notes

- Prefer sniffing-only until raw traffic is understood.
- Set system mode to off/idle before joining to avoid potential for sudden shutdowns from communication faults.
- Enabling AutoNet **transmits** on the HVAC data bus. Start with short join windows and watch for thermostat / air-handler communication faults.
- Turning the join switch **off** should relinquish; if the HVAC still complains, power down the interface and disconnect A/B.
- Do not change MAC / node type casually on a network that already knows this device — duplicates or odd identity changes can confuse coordinators.
- Isolated RS-485 hardware is still recommended; see [Hardware Setup](hardware.md) and [Wire and Verify](wire-and-verify.md).

## Related docs

- [Software Setup](software.md) — flash `radish2.yaml`, secrets, OTA
- [Python Decoder](python-decoder.md) — watch join traffic live; `request_ct_query.py` for app polls
- [Protocol Specification Archive](spec/README.md) — CT-485 networking / AutoNet PDFs
- [Component Internals](component-internals.md) — state machine, queue rules, app-query path, spec traceability
