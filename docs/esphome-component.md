# ESPHome Component (AutoNet)

The `radish` external component (used by [`radish2.yaml`](https://github.com/vesuvisian/radish/blob/main/radish2.yaml)) goes beyond passive sniffing: it can parse CT-485 frames on-device, answer dataflow opportunities, and optionally **join the network as a subordinate** via AutoNet.

Use [`radish.yaml`](https://github.com/vesuvisian/radish/blob/main/radish.yaml) first if you only need raw MQTT capture. Switch to this profile when you want network participation. Flash and Wi‑Fi setup are covered in [Software Setup](software.md); bus wiring in [Hardware Setup](hardware.md).

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
- Healthy raw traffic on the bus before enabling join (see [Hardware Setup](hardware.md#verify-the-link))
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
2. Radish waits a random **slot delay**, then may reply with discovery info (MAC, session, node type) if no other device has yet responded.
3. Coordinator may send a **Set Address** assigning an address/subnet; Radish accepts only when write-enabled and MAC/session match.
4. Once addressed, Radish answers **Get Node ID**, **Address Confirmation**, and participates in dataflow (**R2R**, **Token Offer**) so it can send queued replies.
5. Keepalive / confirmation timeouts, node-list mismatch, Set Address to `0/0`, or turning AutoNet off causes **relinquish** back to unaddressed.

Local address and subnet are assigned at runtime by the coordinator — they are not set in YAML.

## What works today vs not yet

**Implemented**

- UART capture, frame codec, TX queue / arbitration
- AutoNet client lifecycle (discovery, set-address, keepalive, relinquish)
- Subordinate handlers for:
    - `SetNetworkNodeList` (`0x14` / `0x94`)
    - `NetworkSharedDataSector` read/write (`0x7D` / `0xFD`) with persistence

**Not implemented (yet)**

- Broad application interrogation (status, sensors, menus, control commands, etc. as an active querier)
- Custom responses for most other application message IDs (they are routed but unanswered)
- Emitting `publish_structured_events` from C++ (option exists; raw MQTT forwarding is what works today)

Treat network join as experimental: useful for learning AutoNet and holding a subordinate slot, not as a full thermostat replacement.

## YAML options

Stock `radish:` block from `radish2.yaml`:

```yaml
radish:
  uart_id: rs485_bus
  mqtt_topic: radish/rs485/raw
  publish_timeout_ms: 100ms
  max_frame_bytes: 256
  hex_delimiter: " "
  enable_raw_mqtt_forwarding: true
  publish_structured_events: true
  local_node_type: 39
  autonet_enabled: false
  autonet_join_switch:
    name: "Radish AutoNet Join"
  autonet_slot_delay_min_ms: 100ms
  autonet_slot_delay_max_ms: 2500ms
  autonet_keepalive_timeout_ms: 120s
  mac_from_device_identity: true
  # local_mac_address: "00:00:09:12:34:56:78:9A"
```

### MQTT / capture

| Option | Default | Notes |
| --- | --- | --- |
| `mqtt_topic` | `radish/rs485/raw` | Raw hex publish topic |
| `enable_raw_mqtt_forwarding` | `true` | Turn off to stop MQTT hex spam while still running the controller |
| `hex_delimiter` | `" "` | Matches the Python listener’s spaced-hex expectation |
| `publish_timeout_ms` | `100ms` | Flush UART buffer to the controller / MQTT |
| `max_frame_bytes` | `256` | Max chunk size before forced flush |
| `publish_structured_events` | `true` | Reserved; not emitted by firmware yet |

### Identity

| Option | Default | Notes |
| --- | --- | --- |
| `local_node_type` | `39` | Node type advertised during AutoNet |
| `mac_from_device_identity` | `true` | Derive 8-byte MAC from device identity when possible |
| `local_mac_address` | unset | Optional override; must be 8 bytes starting with `00:00:09` |

### AutoNet

| Option | Default | Notes |
| --- | --- | --- |
| `autonet_enabled` | `false` | Boot-time join enable; prefer the switch for experiments |
| `autonet_join_switch` | optional | Runtime on/off in HA/ESPHome; off forces relinquish |
| `autonet_slot_delay_min_ms` / `_max_ms` | `100ms` / `2500ms` | Random delay window for discovery / broadcast arbitration |
| `autonet_keepalive_timeout_ms` | `120s` | Relinquish if confirmations lapse while addressed |
| `autonet_deterministic_seed` | unset | Optional seed for deterministic slot-delay behavior (tests / reproducibility) |
| `slot_delay_ms` | `250ms` | Separate controller slot-delay knob (Token Offer path); leave default unless you know you need it |

## Safety notes

- Prefer sniffing-only until raw traffic is understood.
- Enabling AutoNet **transmits** on the HVAC data bus. Start with short join windows and watch for thermostat / air-handler communication faults.
- Turning the join switch **off** should relinquish; if the HVAC still complains, power down the interface and disconnect A/B.
- Do not change MAC / node type casually on a network that already knows this device — duplicates or odd identity changes can confuse coordinators.
- Isolated RS-485 hardware is still recommended; see [Hardware Setup](hardware.md).

## Related docs

- [Software Setup](software.md) — flash `radish2.yaml`, secrets, OTA
- [Python Decoder](python-decoder.md) — watch join traffic live
- [Protocol Specification Archive](spec/README.md) — CT-485 networking / AutoNet PDFs
- [Component Internals](component-internals.md) — state machine, queue rules, spec traceability
