# Component Internals

Developer reference for contributors changing the `radish` ESPHome external component under [`components/radish/`](https://github.com/vesuvisian/radish/tree/main/components/radish). Operators setting up a device should start with the [ESPHome Component guide](esphome-component.md).

The stack is a UART-facing shell (`radish.cpp`), a protocol/controller core (`ct_controller.cpp`), and two services (`ct_services_autonet_client.cpp`, `ct_services_subordinate.cpp`).

## Architecture

```text
RS-485 UART RX
      │
      ▼
 RadishComponent ──buffer flush──► CtController::on_raw_chunk
      │                                 │
      │                                 ├── parse frames (codec)
      │                                 ├── AutoNetClient  (dataflow / config)
      │                                 ├── SubordinateService (app msgs 0x01..0xDA)
      │                                 └── TX queue / R2R / Token Offer / ACKs
      │                                 │
      │◄──────── TX bytes ──────────────┘
      │
      └── optional MQTT raw hex ──► mqtt_topic (default radish/rs485/raw)

CtController::tick() advances AutoNet slot delays, keepalive, and pending Token Offer windows.
```

## File layout

| File | Role |
| --- | --- |
| [`__init__.py`](https://github.com/vesuvisian/radish/blob/main/components/radish/__init__.py) | ESPHome schema / codegen |
| [`radish.h`](https://github.com/vesuvisian/radish/blob/main/components/radish/radish.h) / [`radish.cpp`](https://github.com/vesuvisian/radish/blob/main/components/radish/radish.cpp) | `Component` + `UARTDevice`: buffer, MQTT forward, UART TX |
| [`ct_types.h`](https://github.com/vesuvisian/radish/blob/main/components/radish/ct_types.h) | Frames, identity, AutoNet config, queue, counters |
| [`ct_frame_codec.*`](https://github.com/vesuvisian/radish/blob/main/components/radish/ct_frame_codec.cpp) | Encode/decode, checksum, sliding resync |
| [`ct_controller.*`](https://github.com/vesuvisian/radish/blob/main/components/radish/ct_controller.cpp) | Parse, dispatch, queue, ACK / R2R / Token Offer |
| [`ct_services_autonet_client.*`](https://github.com/vesuvisian/radish/blob/main/components/radish/ct_services_autonet_client.cpp) | AutoNet join / address lifecycle |
| [`ct_services_subordinate.*`](https://github.com/vesuvisian/radish/blob/main/components/radish/ct_services_subordinate.cpp) | App handlers + shared-data persistence |

## Not implemented (yet)

- Custom responses for most application message IDs (routed to `SubordinateService`, then ignored)
- Active interrogation (device does not originate status/sensor/menu/control queries)
- `publish_structured_events` — accepted in YAML and logged at boot, **not emitted** by C++ today (raw MQTT hex is the working path)

## Runtime behavior

### Dispatch

Incoming frames go to exactly one path (`CTRL-DISPATCH-001`):

- dataflow / configuration → `AutoNetClient`
- application IDs `0x01..0xDA` (excluding R2R) → `SubordinateService`
- non-dataflow ACK handling → `CtController` directly

### Raw MQTT forwarding (`CTRL-RAW-001`)

When `enable_raw_mqtt_forwarding` is true, UART chunks that reach the controller are published as uppercase hex on `mqtt_topic`, separated by `hex_delimiter`. A trailing delimiter is appended only when the delimiter is exactly `" "` (Python listener compatibility).

### Queue and arbitration (`CTRL-QUEUE-*`)

- Bounded TX queue (`std::deque<QueuedTx>`, default max depth `16`); overflow increments `queue_dropped` and rejects enqueue
- Entries tagged by source (`Controller`, `AutoNetClient`)
- Response types (`message_type & 0x80`) prioritized when draining
- Some AutoNet outputs send immediately when possible (`NodeDiscoveryResponse`, `SetAddressResponse`, `AddressConfirmationResponse`); otherwise enqueued

### Local non-dataflow ACK

For locally addressed, non-dataflow frames:

- `GetNodeIdRequest (0x7B)` ACKed **before** service handling
- Other non-R2R / non-AddressConfirmationPush messages ACKed **after** service handling
- ACK payload: code `0x06` + local MAC + local session ID

### R2R (`CTRL-R2R-*`)

Locally addressed R2R: empty queue → R2R ACK; non-empty → send next queued frame instead. Non-addressed R2R ignored for TX decisions.

### Token Offer (`CTRL-TOB-*`)

On `TokenOffer (0x77)` for subnet `0x03` or broadcast subnet, if the queue has work and this node has not already answered this cycle:

- schedule delayed `TokenOfferResponse (0xF7)` using **`slot_delay_ms`** (controller knob; default `250ms`)
- cancel if any new bus chunk arrives before the delay elapses
- at most one response per cycle; cycle resets on `AddressConfirmationPush` on subnet `0x03`, or a 120s timeout fallback

### Slot-delay knobs (do not confuse)

| Option | Used by | Purpose |
| --- | --- | --- |
| `slot_delay_ms` | `CtController` Token Offer path | Fixed delay before `TokenOfferResponse` |
| `autonet_slot_delay_min_ms` / `autonet_slot_delay_max_ms` | `AutoNetClient` | Random window for discovery response and broadcast Address Confirmation arbitration |

User-facing YAML tables: [ESPHome Component guide](esphome-component.md#yaml-options).

## AutoNet client

### State machine (`AUTONET-STATE-001`)

```text
UNADDRESSED
    │  NodeDiscoveryRequest match
    ▼
AWAITING_SLOT_DELAY_FOR_DISCOVERY_RESPONSE
    │  delay elapsed → enqueue 0xF9          │ bus activity → cancel
    ▼                                        └──────────────► UNADDRESSED
AWAITING_SET_ADDRESS
    │  valid SetAddress (MAC/session + write)
    ▼
ADDRESSED_ACTIVE
    │  keepalive miss / node-list mismatch / SetAddress 0/0 / join disabled
    ▼
RELINQUISH_PENDING ──► UNADDRESSED (assignment cleared)
```

### Behavior notes

- Discovery (`0x79`): slot-delay gated (`AUTONET-DISC-001`); any bus traffic during the window cancels and returns to `UNADDRESSED` (`AUTONET-DISC-002`)
- Set Address (`0x7A`): accept only if write-enabled and MAC/session match (`AUTONET-SETADDR-001`); `0/0` forces relinquish (`AUTONET-SETADDR-002`)
- Get Node ID (`0x7B`): addressed request → `0xFB` with node type, MAC, session (`AUTONET-NODEID-001`)
- Address Confirmation (`0x76`): direct → immediate `0xF6` (`AUTONET-ADDRCONF-001`); broadcast → slot-delay arbitration, cancel on bus activity (`AUTONET-ADDRCONF-002`)
- Keepalive / node-list mismatch while addressed on subnet `0x03` → relinquish (`AUTONET-KEEPALIVE-001`)
- Disabling AutoNet (YAML or join switch) forces relinquish and clears assignment
- Effective MAC is fixed at runtime, 8 bytes, prefix `00:00:09` (`AUTONET-MAC-001`); explicit `local_mac_address` wins over device-identity derivation
- Address/subnet are **not** YAML fields — assigned only via AutoNet `SetAddressRequest`

## Subordinate service

Handles locally addressed non-dataflow application space `0x01..0xDA` (excluding R2R).

| Request | Response | Notes |
| --- | --- | --- |
| `SetNetworkNodeList (0x14)` | `0x94` | Echo-style |
| `NetworkSharedDataSector (0x7D)` | `0xFD` | Read/write via payload byte 0 bit 7; ESPHome preferences persistence |

Shared-data sector mapping by requested node type:

| Sector | Node types |
| --- | --- |
| 0 | 1 (thermostat), 21 (zone controller) |
| 1 | 2, 3 |
| 2 | 4, 5, 12 |

Sector 0 gives **node type 21 overwrite priority over node type 1**: if a valid sector image already holds type 21, a write from type 1 is rejected so a zone controller’s shared data is not clobbered by a thermostat write.

## Observability

**ESPHome logs** (component tag `radish` / AutoNet client logs): boot config dump (topic, timeouts, identity, AutoNet on/off), join enable/disable, discovery slot delays, address accept/relinquish, keepalive failures, invalid MAC warnings, MQTT publish failures.

**Controller counters** (`ControllerCounters` in `ct_types.h`): `raw_chunks_seen`, `raw_bytes_seen`, `frames_valid`, `frames_checksum_failed`, `frames_truncated`, `frames_filtered`, `queue_dropped`, `tx_attempted`, `tx_success`, `tx_failed`. Useful when extending firmware or debugging from a debugger; not all are exposed as HA sensors today.

**MQTT**: with forwarding enabled, watch `radish/rs485/raw` (or your topic) via the [Python decoder](python-decoder.md) while testing join.

## Contract tests

From the repo root:

```bash
python -m unittest tests.test_controller_behavior_contract \
  tests.test_autonet_client_state_machine \
  tests.test_subordinate_service_routing_contract -v
```

| Test module | Covers |
| --- | --- |
| [`test_controller_behavior_contract.py`](https://github.com/vesuvisian/radish/blob/main/tests/test_controller_behavior_contract.py) | Raw hex formatting, replay parse parity with controller walk |
| [`test_autonet_client_state_machine.py`](https://github.com/vesuvisian/radish/blob/main/tests/test_autonet_client_state_machine.py) | AutoNet state transitions |
| [`test_subordinate_service_routing_contract.py`](https://github.com/vesuvisian/radish/blob/main/tests/test_subordinate_service_routing_contract.py) | Subordinate routing boundaries / handlers |

These are Python models of the C++ contracts, not on-device ESPHome tests.

## Behavior rule IDs → spec

IDs are referenced in implementation notes and tests. Full Networking Spec: [CT-485 Networking Specification](spec/ClimateTalk_2.0_CT-485_Networking_Specification_R01.pdf) ([archive index](spec/README.md)).

| Rule ID | Summary | Spec §§ |
| --- | --- | --- |
| `CTRL-RAW-001` | Forward UART chunks as spaced uppercase hex when enabled | — |
| `CTRL-DISPATCH-001` | One service path per frame class | — |
| `CTRL-QUEUE-001`–`003` | Bounded queue, source tags, prioritize responses, drop on overflow | `7.5`, `7.6.1`, `7.9` |
| `CTRL-R2R-001`–`003` | Addressed R2R ACK vs dequeue; ignore non-addressed | `7.4.1`, `7.5.3`, `7.8` |
| `CTRL-TOB-001`–`004` | Token Offer slot delay, cancel on bus, once per cycle | `7.5.4`, `11.1`, `11.13` |
| `AUTONET-STATE-001` | Explicit client states | `11.12` |
| `AUTONET-DISC-001`–`002` | Discovery slot delay; cancel on bus activity | `11.1`, `11.12` |
| `AUTONET-SETADDR-001`–`002` | MAC/session/write gate; `0/0` relinquish | `11.12` |
| `AUTONET-NODEID-001` | Addressed Get Node ID → `0xFB` | `11.12` |
| `AUTONET-KEEPALIVE-001` | Confirmation timeout / node-list mismatch → relinquish | `9.1.2` |
| `AUTONET-ADDRCONF-001`–`002` | Direct vs broadcast Address Confirmation | `7.4.2`, `9.1.2`, `11.1` |
| `AUTONET-MAC-001` | Stable 8-byte `00:00:09…` MAC | `11.12` |
