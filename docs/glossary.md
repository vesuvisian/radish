# Glossary

Short definitions for terms that show up in Radish docs, decoder output, and the ClimateTalk / CT-485 specs. For full protocol detail, see the [specification archive](spec/README.md).

## A–C

**A/B (Data 1 / Data 2)**  
The two-wire differential RS-485 pair used by CT-485. Equipment often labels these **Data 1** / **Data 2**. If following the spec, they may be colored green / yellow. Reversed polarity produces inverted/noisy hex (`FE`/`FF`-heavy); swap the wires. See [Wire and Verify](wire-and-verify.md).

**Address Confirmation**  
Coordinator messages that push or confirm the network node list (who is on the bus and at which node types). Subordinates answer with a matching response. Missing or mismatched confirmations drive AutoNet keepalive / relinquish behavior.

**App query**  
A read-only CT-CIM poll Radish originates after AutoNet join: Get Configuration (`0x01`), Get Status (`0x02`), Get Sensor Data (`0x07`), or Get Identification Data (`0x0E`). Triggered from Home Assistant via `get_app_query`; matching response hex is published on `app_query_mqtt_topic`. See [Requesting application queries](esphome-component.md#requesting-application-queries).

**Air Handler**  
Indoor blower / coil equipment (node type `3` in CT-485). Often co-located with the network coordinator function on Daikin / ComfortNet systems.

**AtomS3 Lite**  
M5Stack ESP32-S3 board used by the stock `radish.yaml` / `radish2.yaml` profiles.

**AutoNet**  
ClimateTalk mechanism for a device to **join** the network as a subordinate: discovery → set-address → keepalive. Radish implements an AutoNet **client** in the ESPHome component (`radish2.yaml`). Keep it off until passive sniffing is solid. See [ESPHome Component](esphome-component.md).

**ClimateTalk**  
OEM communicating HVAC protocol family (Daikin / Amana / Goodman / related ComfortNet-style systems). Specs cover application messages (often called CT-CIM) and the CT-485 network/physical layers.

**ComfortNet**  
Marketing name for many ClimateTalk-based residential communicating systems (thermostat + air handler / outdoor unit on a data bus).

**Coordinator (Network Coordinator)**  
Device that runs the CT-485 network (address `255`, node type `165`): discovery, addressing, token / dataflow, and node-list pushes. Usually the air handler / control board, not Radish.

**CT-485**  
ClimateTalk’s RS-485 network and framing layer: addresses, subnets, send methods, message types, checksums. This is what Radish sniffs on the wire and publishes as hex.

**CT-CIM**  
ClimateTalk application / information-model messages carried inside CT-485 frames (status, sensors, menus, control, and so on).

## D–M

**Dataflow**  
Bus arbitration so a subordinate can transmit: typically **R2R** and **Token Offer**. Packets with packet-number bit 7 set are often ACKs / dataflow traffic; the Python listener can hide them with `MQTT_EXCLUDE_DATAFLOW`.

**DE/RE**  
Driver Enable / Receiver Enable pins on many RS-485 chips. Some modules (including Tail485) handle direction automatically; breakout boards may need GPIO control in YAML.

**DI / RO**  
Transceiver pins: **DI** = driver input (ESP TX → DI), **RO** = receiver output (ESP RX ← RO).

**ESPHome**  
Firmware framework Radish uses on the ESP32. Profiles live in `radish.yaml` (sniff) and `radish2.yaml` (component + optional AutoNet).

**Frame**  
One CT-485 packet: addressing header, message type, payload, checksum. Parsed by `radish/frame.py` and the on-device codec.

**Heat Pump**  
Outdoor / heat-pump equipment (node type `5`).

**MDI**  
Message Data Item — structured records inside some CT-CIM payloads (for example status records with `db_id`, length, and value).

**MQTT**  
Publish/subscribe messaging. Radish publishes raw hex on `radish/rs485/raw` (by default); `mqtt_listener.py` subscribes and decodes.

## N–R

**Node Discovery**  
Coordinator broadcast asking devices to announce themselves (message type `0x79` and related). First step of AutoNet join.

**Node type**  
Numeric identity for the kind of device (thermostat `1`, air handler `3`, heat pump `5`, temperature sensor `39`, network coordinator `165`, …). See `radish/maps.py`.

**OTA**  
Over-the-air firmware update via ESPHome after the first USB flash.

**Packet number**  
CT-485 header field distinguishing requests/responses and dataflow/ACK styles. Bit 7 set usually marks dataflow-related packets.

**Polarity**  
Which physical wire is A vs B (Data 1 vs Data 2). Wrong polarity garbles UART bytes; correct by swapping the data pair.

**R/C**  
Thermostat power rails: **R** (24 VAC hot) and **C** (common). Radish only needs the **data** pair for sniffing; do not tie RS-485 A/B to R/C.

**R2R (Request to Receive / Ready to Receive)**  
Dataflow handshake message that helps a subordinate get a turn to send. The ESPHome component can answer when participating.

**`radish.yaml`**  
Passive sniffing profile: `uart.debug` RX → MQTT hex. Does not join the network.

**`radish2.yaml`**  
Profile that loads the local `radish` ESPHome component: on-device framing, dataflow replies, optional AutoNet, and originated app queries (configuration / status / sensor / identification).

**Relinquish**  
AutoNet client drops its assigned address/subnet (for example after keepalive failure or AutoNet turned off) and waits to be rediscovered.

**RS-485**  
Differential serial bus standard. CT-485 runs on RS-485 at 9600 baud in the stock configs.

## S–Z

**Send method**  
How a frame is addressed/routed (non-routed, by priority node type, by socket, …). Shown in decoder output.

**Session ID**  
Identifier used with the ClimateTalk MAC during discovery / addressing so Set Address applies to the right device.

**Set Address**  
Coordinator message that assigns a subordinate its network address and subnet during AutoNet.

**Slot Delay**  
Randomized wait (100–2500 ms per CT-485, or a fixed YAML override) before answering Node Discovery so multiple devices do not collide.

**Sniffing**  
Listen-only capture of bus traffic (no AutoNet join, no intentional TX beyond what the transceiver path allows for RX).

**Subnet**  
CT-485 grouping: `0` = all, `2` = v1.0 subordinates, `3` = >v1.0 subordinates (common on modern gear).

**Subordinate**  
Any addressed device that is not the coordinator (thermostat, heat pump, sensor, …). AutoNet joins Radish as a subordinate.

**Tail485**  
M5Stack RS-485 “tail” that plugs onto the Atom. Stock YAML maps UART **RX = GPIO1**, **TX = GPIO2**.

**Thermostat**  
User interface / zone controller (node type `1`). Often priority subordinate address `1`.

**Token Offer**  
Coordinator dataflow offer allowing a filtered node to transmit. Paired with Token Offer Response from subordinates.

**UART**  
Serial link between the ESP32 and the RS-485 transceiver. Stock baud rate is 9600 8N1.
