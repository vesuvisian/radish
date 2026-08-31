# Radish ESPHome Component

This external ESPHome component bridges CT-485 UART/RS-485 traffic to:

- controller-driven ClimateTalk behavior
- optional AutoNet client participation
- MQTT raw frame telemetry

The implementation is split into a UART-facing shell (`radish.cpp`), a protocol/controller core (`ct_controller.cpp`), and two service modules (`ct_services_autonet_client.cpp`, `ct_services_subordinate.cpp`).

---

## File Layout

- `__init__.py`  
  ESPHome config/codegen schema and component wiring.

- `radish.h` / `radish.cpp`  
  ESPHome `Component` + `UARTDevice` wrapper:
  - receives UART bytes into a bounded buffer
  - flushes by timeout (`publish_timeout_ms`) or size (`max_frame_bytes`)
  - forwards chunks to `CtController`
  - publishes raw hex payloads to MQTT when enabled
  - writes controller TX attempts back to UART

- `ct_types.h`  
  Shared protocol constants and models (`CtFrame`, `ControllerIdentity`, `AutoNetConfig`, `QueuedTx`, `ServiceOutput`, counters).

- `ct_frame_codec.h` / `ct_frame_codec.cpp`  
  Frame encode/decode and checksum logic:
  - sliding resync parse on checksum failure
  - truncated-tail counting

- `ct_controller.h` / `ct_controller.cpp`  
  Main control loop:
  - parse incoming chunks into frames
  - service dispatch (`AutoNetClient`, `SubordinateService`)
  - queue ownership and TX arbitration
  - non-dataflow ACK behavior
  - R2R and Token Offer dataflow handling

- `ct_services_autonet_client.h` / `ct_services_autonet_client.cpp`  
  AutoNet join/address lifecycle service with explicit runtime state machine.

- `ct_services_subordinate.h` / `ct_services_subordinate.cpp`  
  Subordinate routing + currently implemented application message behaviors:
  - `SetNetworkNodeList` request/response
  - `NetworkSharedDataSector` read/write + persistence-backed sector images

---

## Runtime Flow

1. `RadishComponent` accumulates UART bytes.
2. Buffered bytes are flushed to `CtController::on_raw_chunk(...)`.
3. Controller parses frames, updates counters/state, and processes service outputs.
4. `RadishComponent` publishes raw payloads to MQTT if forwarding is enabled.
5. TX attempts from `on_raw_chunk(...)` and `tick(...)` are emitted on UART.

`CtController::tick(...)` also advances time-based behavior (AutoNet slot-delay scheduling, keepalive handling, pending Token Offer response windows).

---

## Implemented Controller Behavior

### Raw MQTT forwarding

- Controlled by `enable_raw_mqtt_forwarding`.
- Payload format is uppercase hex.
- Bytes are separated by `hex_delimiter`.
- A trailing delimiter is appended only when delimiter is exactly `" "` (compatibility behavior).

### Queue and arbitration

- One bounded queue (`std::deque<QueuedTx>`, default max depth `16`).
- Queue overflow increments `queue_dropped` and rejects new enqueue.
- Response message types (`message_type & 0x80`) are prioritized when draining queue.
- Some service outputs are sent immediately when possible (`NodeDiscoveryResponse`, `SetAddressResponse`, `AddressConfirmationResponse`), otherwise enqueued.

### Local non-dataflow ACK behavior

For locally addressed, non-dataflow frames:

- `GetNodeIdRequest (0x7B)` is ACKed before service handling.
- Other non-R2R/non-AddressConfirmationPush messages are ACKed after service handling.
- ACK payload includes code `0x06` + local MAC + local session ID.

### R2R behavior

For locally addressed R2R:

- if TX queue is empty: send R2R ACK
- if TX queue has entries: send next queued frame instead

### Token Offer behavior (subnet 3 / broadcast-subnet path)

When `TokenOffer (0x77)` is seen on subnet `0x03` or broadcast subnet:

- if queue has entries and this node has not already responded in current cycle, controller schedules delayed `TokenOfferResponse (0xF7)`
- if any new bus chunk arrives before delay expires, pending response is canceled
- only one response is sent per cycle
- cycle reset occurs on `AddressConfirmationPush` on subnet `0x03`, or a 120s timeout fallback

---

## Implemented AutoNet Client Behavior

`AutoNetClient` states:

- `UNADDRESSED`
- `AWAITING_SLOT_DELAY_FOR_DISCOVERY_RESPONSE`
- `AWAITING_SET_ADDRESS`
- `ADDRESSED_ACTIVE`
- `RELINQUISH_PENDING`

Behavior currently implemented:

- `NodeDiscoveryRequest (0x79)` match starts slot-delay timer and generates a new session ID.
- Any intervening bus activity cancels discovery response window and returns to `UNADDRESSED`.
- Slot-delay expiry enqueues `NodeDiscoveryResponse (0xF9)`.
- Valid `SetAddressRequest (0x7A)` (write-enabled + MAC/session match) enqueues `SetAddressResponse (0xFA)` and updates local address/subnet.
- `SetAddressRequest` assigning `0x00/0x00` triggers relinquish back to `UNADDRESSED`.
- `GetNodeIdRequest (0x7B)` for local address/subnet enqueues `GetNodeIdResponse (0xFB)`.
- `AddressConfirmationPush (0x76)`:
  - addressed: immediate `AddressConfirmationResponse (0xF6)`
  - broadcast: delayed response with slot-delay arbitration
- In `ADDRESSED_ACTIVE` on subnet `0x03`, keepalive timeout or node-list mismatch relinquishes assignment.
- Runtime disable of AutoNet (`autonet_enabled=false` or switch off) forces relinquish and clears assignment.

---

## Implemented Subordinate Service Behavior

`SubordinateService` handles locally addressed non-dataflow application message space (`0x01..0xDA`, excluding R2R).

Currently implemented message handlers:

- `SetNetworkNodeListRequest (0x14)` -> `SetNetworkNodeListResponse (0x94)` echo-style response.
- `NetworkSharedDataSectorRequest (0x7D)` -> `NetworkSharedDataSectorResponse (0xFD)`:
  - supports read/write operation bit in payload byte 0
  - maps node types into 3 persisted sector groups
  - persists sector writes through ESPHome preferences
  - applies overwrite priority rule for sector 0 (node type 21 retained over node type 1)

Other application message IDs are currently routed here but have no custom response yet.

---

## YAML Configuration (`__init__.py`)

Supported options:

- `mqtt_topic` (default `radish/rs485/raw`)
- `publish_timeout_ms` (default `100ms`)
- `max_frame_bytes` (default `256`)
- `hex_delimiter` (default `" "`)
- `enable_raw_mqtt_forwarding` (default `true`)
- `local_node_type` (default `39`)
- `slot_delay_ms` (default `250ms`)
- `publish_structured_events` (default `true`, currently not emitted by C++ component)
- `autonet_enabled` (default `false`)
- `autonet_join_switch` (optional runtime switch)
- `autonet_slot_delay_min_ms` (default `100ms`)
- `autonet_slot_delay_max_ms` (default `2500ms`)
- `autonet_keepalive_timeout_ms` (default `120s`)
- `autonet_deterministic_seed` (optional)
- `local_mac_address` (optional explicit 8-byte MAC)
- `mac_from_device_identity` (default `true`)

MAC behavior:

- effective MAC is always 8 bytes and must start with `00:00:09`
- valid `local_mac_address` takes precedence
- otherwise MAC is derived from device identity (ESP32 STA MAC when available), with deterministic fallback

Address behavior:

- runtime local address/subnet are managed through AutoNet assignment (`SetAddressRequest`)
- address/subnet are not exposed in component YAML schema

---

## Tests Covering This Component Contract

Current Python-side contract tests:

- `tests/test_controller_behavior_contract.py`
- `tests/test_autonet_client_state_machine.py`
- `tests/test_subordinate_service_routing_contract.py`

These tests validate parser/formatting parity, AutoNet state transitions, and subordinate routing boundaries against the C++ behavior model.

---

## Controller Behavior Rule IDs

Behavior IDs are used by implementation notes and tests (see `tests/test_controller_behavior_contract.py`).

### Raw forwarding and dispatch

- `CTRL-RAW-001`: When `enable_raw_mqtt_forwarding=true`, every incoming UART chunk that reaches the controller is forwarded to MQTT topic `radish/rs485/raw` as uppercase hex bytes with trailing space compatibility.
- `CTRL-DISPATCH-001`: The controller routes frame handling to exactly one service module based on frame class:
  - dataflow/configuration path -> `AutoNetClient`
  - application message IDs in the `0x01..0xDA` range -> `SubordinateService`
  - non-dataflow ACK handling is performed directly by `CtController`

### Queue ownership and arbitration

- `CTRL-QUEUE-001`: The controller owns a bounded TX queue and tags entries by source (`Controller`, `AutoNetClient`).
- `CTRL-QUEUE-002`: Dataflow/system responses take precedence over application-layer queued traffic.
- `CTRL-QUEUE-003`: Queue overflow increments drop counters and does not block controller progress.

### R2R behavior

- `CTRL-R2R-001`: If an addressed `R2R` is received and TX queue is empty, the controller sends an `R2R-ACK`.
- `CTRL-R2R-002`: If an addressed `R2R` is received and TX queue is non-empty, the controller sends the next queued message in that transmission opportunity (no `R2R-ACK` in that slot).
- `CTRL-R2R-003`: Non-addressed `R2R` messages are ignored for transmission decisions.

### Token Offer behavior (Subnet 3)

- `CTRL-TOB-001`: If on Subnet 3 and queue is non-empty, a `Token Offer Broadcast` may be answered with `Token Offer Response` after slot delay.
- `CTRL-TOB-002`: During slot-delay wait, the controller keeps listening; if any transmission starts, it aborts the response attempt.
- `CTRL-TOB-003`: The controller responds to Token Offer at most once per dataflow cycle.
- `CTRL-TOB-004`: After it has responded once in-cycle, additional Token Offers are suppressed until cycle reset.

### AutoNet client behavior

- `AUTONET-STATE-001`: AutoNet client tracks explicit runtime states (`UNADDRESSED`, `AWAITING_SLOT_DELAY_FOR_DISCOVERY_RESPONSE`, `AWAITING_SET_ADDRESS`, `ADDRESSED_ACTIVE`, `RELINQUISH_PENDING`).
- `AUTONET-DISC-001`: Matching Node Discovery Request does not respond immediately; response is slot-delay gated.
- `AUTONET-DISC-002`: Any bus traffic during slot-delay window cancels the pending discovery response.
- `AUTONET-SETADDR-001`: Set Address is accepted only if write-enabled and MAC/session match.
- `AUTONET-SETADDR-002`: Set Address `0/0` forces relinquish to unaddressed state.
- `AUTONET-NODEID-001`: Addressed `Get Node ID` requests (`0x7B`) are answered with `0xFB` containing local node type, MAC, and session ID.
- `AUTONET-KEEPALIVE-001`: Address Confirmation timeout or node-list mismatch causes relinquish/rejoin-ready transition.
- `AUTONET-ADDRCONF-001`: Address Confirmation Push addressed directly to the node is echoed with `0xF6` response.
- `AUTONET-ADDRCONF-002`: Broadcast Address Confirmation Push is handled with slot-delay arbitration; pending response is canceled if any bus traffic starts before slot-delay expiry.
- `AUTONET-MAC-001`: Effective MAC is invariant at runtime and always 8 bytes prefixed `00:00:09`, sourced from YAML or deterministic device-identity derivation.

## Spec Traceability (Networking Spec)

- `7.4.1`, `7.5.3`: addressed request/response acknowledgement behavior.
- `7.5`, `7.6.1`, `7.9`: subordinate send-opportunity gating with coordinator dataflow.
- `7.5.4`, `11.1`, `11.13`: Token Offer arbitration, slot delay, once-per-cycle behavior.
- `7.4.2`, `11.1`: broadcast response arbitration for Address Confirmation behavior.
- `7.8`: timeout context for R2R/ACK behavior and observability.
- `9.1.2`: Address Confirmation-based address retention/relinquish behavior.
- `11.1`: slot delay requirements used by discovery arbitration.
- `11.12`: AutoNet client discovery/set-address procedure basis.

