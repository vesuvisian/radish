"""CT-CIM mapped message implementations."""

from ..maps import NODE_TYPE_MAP
from .base import Message, NoPayloadMessage, parse_db_id_datagram
from .registry import MessageRegistry

__all__ = [
    "GetConfigurationRequest",
    "GetConfigurationResponse",
    "GetStatusRequest",
    "GetStatusResponse",
    "SetControlCommandRequest",
    "SetControlCommandResponse",
    "SetDisplayMessageRequest",
    "SetDisplayMessageResponse",
    "SetDiagnosticsRequest",
    "SetDiagnosticsResponse",
    "GetDiagnosticsRequest",
    "GetDiagnosticsResponse",
    "GetSensorDataRequest",
    "GetSensorDataResponse",
    "SetIdentificationRequest",
    "SetIdentificationResponse",
    "GetIdentificationDataRequest",
    "GetIdentificationDataResponse",
    "SetApplicationSharedDataToNetworkRequest",
    "SetApplicationSharedDataToNetworkResponse",
    "GetApplicationSharedDataFromNetworkRequest",
    "GetApplicationSharedDataFromNetworkResponse",
    "SetManufacturerDeviceDataRequest",
    "SetManufacturerDeviceDataResponse",
    "GetManufacturerDeviceDataRequest",
    "GetManufacturerDeviceDataResponse",
    "SetNetworkNodeListRequest",
    "SetNetworkNodeListResponse",
    "DirectMemoryAccessReadRequest",
    "DirectMemoryAccessReadResponse",
    "SetManufacturerGenericDataRequest",
    "SetManufacturerGenericDataResponse",
    "ManufacturerGenericDataRequest",
    "ManufacturerGenericDataResponse",
    "GetUserMenuRequest",
    "GetUserMenuResponse",
    "SetUserMenuUpdateRequest",
    "SetUserMenuUpdateResponse",
    "SetFactorySharedDataToApplicationRequest",
    "SetFactorySharedDataToApplicationResponse",
    "GetSharedDataFromApplicationRequest",
    "GetSharedDataFromApplicationResponse",
    "EchoRequest",
    "EchoResponse",
]

_FAN_MODE_MAP = {
    0x00: "Auto",
    0x01: "Always On",
    0x02: "Occupied On",
}


def _decode_air_handler_status_db0(value: bytes) -> list[str]:
    """Decode Air Handler Status MDI DB ID 0x00 (20-byte block)."""
    if len(value) != 20:
        return []

    airflow = (value[12] << 8) | value[13]
    return [
        "  Air Handler Interpretation (DB ID 0x00):",
        f"    Critical Fault Code: {value[0]}",
        f"    Minor Fault Code: {value[1]}",
        f"    Heat Requested Demand: {value[2] * 0.5:.1f}%",
        "    Fan Requested Mode: "
        f"{value[3]} ({_FAN_MODE_MAP.get(value[3], 'Refer to Fan Demand Control Command')})",
        f"    Fan Requested Demand: {value[4] * 0.5:.1f}%",
        f"    Fan Requested Rate/Slew: {value[5]} second(s)",
        f"    Fan Requested Delay: {value[6]} second(s)",
        f"    Defrost Requested Demand: {value[7] * 0.5:.1f}%",
        f"    Emergency Requested Demand: {value[8] * 0.5:.1f}%",
        f"    Aux Requested Demand: {value[9] * 0.5:.1f}%",
        f"    Humidification Requested Demand: {value[10] * 0.5:.1f}%",
        f"    Dehumidification Requested Demand: {value[11] * 0.5:.1f}%",
        f"    Current Airflow: {airflow} CFM",
        f"    Current Heat Actual Status: {value[14] * 0.5:.1f}%",
        f"    Current Fan Actual Status: {value[15] * 0.5:.1f}%",
        f"    Fan Current Rate Status: {value[16]} second(s)",
        f"    Fan Current Delay Remaining Status: {value[17]} second(s)",
        f"    Current Humidification Actual Status: {value[18] * 0.5:.1f}%",
        f"    Current Dehumidification Actual Status: {value[19] * 0.5:.1f}%",
    ]


@MessageRegistry.register(0x01)
class GetConfigurationRequest(NoPayloadMessage):
    name = "Get Configuration Request"


@MessageRegistry.register(0x81)
class GetConfigurationResponse(Message):
    name = "Get Configuration Response"

    @property
    def db_id_records(self):
        records, _ = parse_db_id_datagram(self.data)
        return records

    @property
    def parse_warnings(self):
        _, warnings = parse_db_id_datagram(self.data)
        return warnings

    def _format_output(self):
        if not self.data:
            return "Configuration MDI: no payload"

        ret = [f"Configuration MDI Record Count: {len(self.db_id_records)}"]
        for idx, record in enumerate(self.db_id_records, start=1):
            ret.append(
                f"Record {idx}: "
                f"db_id=0x{record['db_id']:02x}, "
                f"length={record['db_len']}, "
                f"value={record['value'].hex(':')}"
            )
        for warning in self.parse_warnings:
            ret.append(f"Parse Warning: {warning}")
        ret.append(f"Raw Payload: {self.data.hex(':')}")
        return "\n".join(ret)


@MessageRegistry.register(0x02)
class GetStatusRequest(NoPayloadMessage):
    name = "Get Status Request"


@MessageRegistry.register(0x82)
class GetStatusResponse(Message):
    name = "Get Status Response"

    @property
    def db_id_records(self):
        records, _ = parse_db_id_datagram(self.data)
        return records

    @property
    def parse_warnings(self):
        _, warnings = parse_db_id_datagram(self.data)
        return warnings

    def _format_output(self):
        if not self.data:
            return "Status MDI: no payload"

        ret = [f"Status MDI Record Count: {len(self.db_id_records)}"]
        for idx, record in enumerate(self.db_id_records, start=1):
            db_id = record["db_id"]
            value = record["value"]
            ret.append(
                f"Record {idx}: "
                f"db_id=0x{db_id:02x}, "
                f"length={record['db_len']}, "
                f"value={value.hex(':')}"
            )
            if db_id == 0x00 and len(value) == 20:
                ret.extend(_decode_air_handler_status_db0(value))
            elif db_id == 0x01 and len(value) == 43:
                ret.append(
                    "  Record 2 Interpretation: 43-byte extended status block "
                    "(currently undocumented/vendor-specific in this parser)"
                )
        for warning in self.parse_warnings:
            ret.append(f"Parse Warning: {warning}")
        ret.append(f"Raw Payload: {self.data.hex(':')}")
        return "\n".join(ret)


@MessageRegistry.register(0x03)
class SetControlCommandRequest(Message):
    name = "Set Control Command Request"

    @property
    def command_code(self):
        if len(self.data) < 2:
            return None
        return int.from_bytes(self.data[0:2], "little")

    @property
    def command_data(self):
        return self.data[2:] if len(self.data) > 2 else b""

    def _format_output(self):
        if len(self.data) < 2:
            return f"Control command payload (partial): {self.data.hex(':')}"
        return (
            f"Command Code (LE): 0x{self.command_code:04x}\n"
            f"Command Data: {self.command_data.hex(':')}\n"
            f"Raw Payload: {self.data.hex(':')}"
        )


@MessageRegistry.register(0x83)
class SetControlCommandResponse(SetControlCommandRequest):
    name = "Set Control Command Response"


@MessageRegistry.register(0x04)
class SetDisplayMessageRequest(Message):
    name = "Set Display Message Request"

    @property
    def node_type(self):
        return self.data[0] if self.data else None

    @property
    def message_length(self):
        return self.data[1] if len(self.data) >= 2 else None

    @property
    def message_bytes(self):
        return self.data[2:] if len(self.data) > 2 else b""

    @property
    def message_text(self):
        return self.message_bytes.decode("ascii", errors="replace")

    def _format_output(self):
        if len(self.data) < 2:
            return f"Set display payload (partial): {self.data.hex(':')}"
        expected_size = 2 + self.message_length
        length_ok = len(self.data) == expected_size
        return (
            f"Node Type: {self.node_type} ({NODE_TYPE_MAP[self.node_type]})\n"
            f"Message Length: {self.message_length} "
            f"(matches payload: {'yes' if length_ok else 'no'})\n"
            f"Message Text: {self.message_text}\n"
            f"Raw Payload: {self.data.hex(':')}"
        )


@MessageRegistry.register(0x84)
class SetDisplayMessageResponse(Message):
    name = "Set Display Message Response"

    @property
    def confirmation_code(self):
        return self.data[0:2] if len(self.data) >= 2 else b""

    @property
    def is_ack(self):
        return self.confirmation_code == b"\xAC\x06"

    def _format_output(self):
        if len(self.data) < 2:
            return f"Display response payload (partial): {self.data.hex(':')}"
        return (
            f"Confirmation Code: {self.confirmation_code.hex(':')}\n"
            f"ACK: {'yes' if self.is_ack else 'no'}\n"
            f"Raw Payload: {self.data.hex(':')}"
        )


@MessageRegistry.register(0x05)
class SetDiagnosticsRequest(Message):
    name = "Set Diagnostics Request"

    @property
    def node_type(self):
        return self.data[0]

    @property
    def major_fault_code(self):
        return self.data[1]

    @property
    def minor_fault_code(self):
        return self.data[2]

    @property
    def message_length(self):
        return self.data[3]

    @property
    def fault_message(self):
        if self.message_length == 0:
            return b"Fault Cleared"
        return self.data[4:]

    def _format_output(self):
        return (
            f"Node Type: {self.node_type} ({NODE_TYPE_MAP[self.node_type]})\n"
            f"Major Fault Code: {self.major_fault_code}\n"
            f"Minor Fault Code: {self.minor_fault_code}\n"
            f"Fault Message Length: {self.message_length}\n"
            f"Fault Message: {self.fault_message.hex(':')}"
        )


@MessageRegistry.register(0x85)
class SetDiagnosticsResponse(Message):
    name = "Set Diagnostics Response"

    @property
    def confirmation_code(self):
        return self.data

    def _format_output(self):
        return f"Confirmation Code: {self.confirmation_code.hex(':')}"


@MessageRegistry.register(0x06)
class GetDiagnosticsRequest(Message):
    name = "Get Diagnostics Request"

    @property
    def fault_type(self):
        return self.data[0] if self.data else None

    @property
    def fault_type_text(self):
        if self.fault_type == 0:
            return "Minor"
        if self.fault_type == 1:
            return "Major"
        return "Unknown"

    @property
    def fault_index(self):
        return self.data[1] if len(self.data) >= 2 else None

    def _format_output(self):
        if len(self.data) < 2:
            return f"Diagnostics request payload (partial): {self.data.hex(':')}"
        scope = "All faults" if self.fault_index == 0 else f"Fault index {self.fault_index}"
        return (
            f"Fault Type: {self.fault_type} ({self.fault_type_text})\n"
            f"Fault Index: {self.fault_index} ({scope})\n"
            f"Raw Payload: {self.data.hex(':')}"
        )


@MessageRegistry.register(0x86)
class GetDiagnosticsResponse(Message):
    name = "Get Diagnostics Response"

    @property
    def fault_records(self):
        records = []
        i = 0
        while i < len(self.data):
            if i + 3 > len(self.data):
                break
            major = self.data[i]
            minor = self.data[i + 1]
            msg_len = self.data[i + 2]
            i += 3
            fault_message = self.data[i : i + msg_len]
            i += msg_len
            records.append(
                {
                    "major_fault_code": major,
                    "minor_fault_code": minor,
                    "fault_message_length": msg_len,
                    "fault_message": fault_message,
                }
            )
            if i < len(self.data) and self.data[i] == 0x00:
                i += 1
        return records

    def _format_output(self):
        if not self.data:
            return "No diagnostics data"
        if not self.fault_records:
            return f"Diagnostics payload (unparsed): {self.data.hex(':')}"
        ret = [f"Fault Record Count: {len(self.fault_records)}"]
        for idx, record in enumerate(self.fault_records, start=1):
            msg_text = record["fault_message"].decode("ascii", errors="replace")
            ret.append(
                f"Fault {idx}: major={record['major_fault_code']}, "
                f"minor={record['minor_fault_code']}, "
                f"msg_len={record['fault_message_length']}, "
                f"msg='{msg_text}'"
            )
        ret.append(f"Raw Payload: {self.data.hex(':')}")
        return "\n".join(ret)


@MessageRegistry.register(0x07)
class GetSensorDataRequest(NoPayloadMessage):
    name = "Get Sensor Data Request"


@MessageRegistry.register(0x87)
class GetSensorDataResponse(Message):
    name = "Get Sensor Data Response"

    def _format_output(self):
        return f"Sensor MDI, per profile spec: {self.data.hex(':')}"


@MessageRegistry.register(0x0D)
class SetIdentificationRequest(Message):
    name = "Set Identification Request"

    def _format_output(self):
        return f"Identification MDI: {self.data.hex(':')}"


@MessageRegistry.register(0x8D)
class SetIdentificationResponse(Message):
    name = "Set Identification Response"

    @property
    def confirmation_code(self):
        return self.data[0:2] if len(self.data) >= 2 else b""

    @property
    def is_ack(self):
        return self.confirmation_code == b"\xAC\x06"

    def _format_output(self):
        if len(self.data) < 2:
            return f"Identification response payload (partial): {self.data.hex(':')}"
        return (
            f"Confirmation Code: {self.confirmation_code.hex(':')}\n"
            f"ACK: {'yes' if self.is_ack else 'no'}\n"
        )


@MessageRegistry.register(0x0E)
class GetIdentificationDataRequest(NoPayloadMessage):
    name = "Get Identification Data Request"


@MessageRegistry.register(0x8E)
class GetIdentificationDataResponse(Message):
    name = "Get Identification Data Response"

    def _format_output(self):
        return f"Identification MDI: {self.data.hex(':')}"


@MessageRegistry.register(0x10)
class SetApplicationSharedDataToNetworkRequest(Message):
    name = "Set Application Shared Data To Network Request"

    @property
    def sector_node_type(self):
        return self.data[0] if self.data else None

    @property
    def shared_data(self):
        return self.data[1:] if len(self.data) > 1 else b""

    @property
    def shared_data_length(self):
        return self.shared_data[0] if self.shared_data else None

    @property
    def control_id(self):
        if len(self.shared_data) < 3:
            return None
        return int.from_bytes(self.shared_data[1:3], "little")

    @property
    def manufacturer_id(self):
        if len(self.shared_data) < 5:
            return None
        return int.from_bytes(self.shared_data[3:5], "little")

    @property
    def app_node_type(self):
        if len(self.shared_data) < 6:
            return None
        return self.shared_data[5]

    @property
    def app_data(self):
        return self.shared_data[6:] if len(self.shared_data) > 6 else b""

    def _format_output(self):
        if len(self.data) < 7:
            return f"Shared data payload (partial): {self.data.hex(':')}"
        return (
            f"Sector Node Type: {self.sector_node_type} "
            f"({NODE_TYPE_MAP[self.sector_node_type]})\n"
            f"Shared Data Length: {self.shared_data_length}\n"
            f"Control ID (LE): 0x{self.control_id:04x}\n"
            f"Manufacturer ID (LE): 0x{self.manufacturer_id:04x}\n"
            f"App Node Type: {self.app_node_type} ({NODE_TYPE_MAP[self.app_node_type]})\n"
            f"Application Data: {self.app_data.hex(':')}\n"
            f"Raw Payload: {self.data.hex(':')}"
        )


@MessageRegistry.register(0x90)
class SetApplicationSharedDataToNetworkResponse(
    SetApplicationSharedDataToNetworkRequest
):
    name = "Set Application Shared Data To Network Response"


@MessageRegistry.register(0x11)
class GetApplicationSharedDataFromNetworkRequest(Message):
    name = "Get Application Shared Data From Network Request"

    @property
    def sector_node_type(self):
        return self.data[0] if self.data else None

    def _format_output(self):
        if len(self.data) < 1:
            return f"Shared data query payload (partial): {self.data.hex(':')}"
        return (
            f"Sector Node Type: {self.sector_node_type} "
            f"({NODE_TYPE_MAP[self.sector_node_type]})\n"
            f"Raw Payload: {self.data.hex(':')}"
        )


@MessageRegistry.register(0x91)
class GetApplicationSharedDataFromNetworkResponse(
    SetApplicationSharedDataToNetworkRequest
):
    name = "Get Application Shared Data From Network Response"


@MessageRegistry.register(0x12)
class SetManufacturerDeviceDataRequest(Message):
    name = "Set Manufacturer Device Data Request"

    def _format_output(self):
        return f"Manufacturer Device Data: {self.data.hex(':')}"


@MessageRegistry.register(0x92)
class SetManufacturerDeviceDataResponse(SetManufacturerDeviceDataRequest):
    name = "Set Manufacturer Device Data Response"


@MessageRegistry.register(0x13)
class GetManufacturerDeviceDataRequest(NoPayloadMessage):
    name = "Get Manufacturer Device Data Request"


@MessageRegistry.register(0x93)
class GetManufacturerDeviceDataResponse(Message):
    name = "Get Manufacturer Device Data Response"

    def _format_output(self):
        return f"Manufacturer device data payload: {self.data.hex(':')}"


@MessageRegistry.register(0x14)
class SetNetworkNodeListRequest(Message):
    name = "Set Network Node List Request"

    @property
    def coordinator_internal_node_type(self):
        return self.data[0] if self.data else None

    @property
    def node_types(self):
        return list(self.data[1:])

    @property
    def active_node_types(self):
        return [node_type for node_type in self.node_types if node_type != 0x00]

    def _format_output(self):
        if not self.data:
            return "No node list payload"
        ret = (
            "Coordinator's virtual internal Subordinate Node Type: "
            f"{self.coordinator_internal_node_type} "
            f"({NODE_TYPE_MAP[self.coordinator_internal_node_type]})"
        )
        for i, node_type in enumerate(self.node_types, start=1):
            ret += f"\nNode type at index {i}: {node_type} ({NODE_TYPE_MAP[node_type]})"
        return f"{ret}\nActive node count: {len(self.active_node_types)}"


@MessageRegistry.register(0x94)
class SetNetworkNodeListResponse(SetNetworkNodeListRequest):
    name = "Set Network Node List Response"


@MessageRegistry.register(0x1D)
class DirectMemoryAccessReadRequest(Message):
    name = "Direct Memory Access Read Request"

    @property
    def mdi_code(self):
        return self.data[0] if self.data else None

    @property
    def mdi_name(self):
        return {
            0x01: "Configuration",
            0x02: "Status",
            0x07: "Sensor",
            0x0E: "Identification",
        }.get(self.mdi_code, "Unknown")

    @property
    def mdi_packet_number(self):
        return self.data[1] if len(self.data) >= 2 else None

    @property
    def start_db_id(self):
        return self.data[2] if len(self.data) >= 3 else None

    @property
    def db_id_range(self):
        return self.data[3] if len(self.data) >= 4 else None

    def _format_output(self):
        if len(self.data) < 4:
            return f"DMA read request payload (partial): {self.data.hex(':')}"
        return (
            f"MDI Code: 0x{self.mdi_code:02x} ({self.mdi_name})\n"
            f"MDI Packet Number: 0x{self.mdi_packet_number:02x}\n"
            f"Start DB ID: {self.start_db_id}\n"
            f"DB ID Range: {self.db_id_range}\n"
            f"Raw Payload: {self.data.hex(':')}"
        )


@MessageRegistry.register(0x9D)
class DirectMemoryAccessReadResponse(DirectMemoryAccessReadRequest):
    name = "Direct Memory Access Read Response"

    def _format_output(self):
        return f"DMA read data payload: {self.data.hex(':')}"


# Direct Memory Access Write - 0x1E
# Mentioned in table but not fleshed out


@MessageRegistry.register(0x1F)
class SetManufacturerGenericDataRequest(Message):
    name = "Set Manufacturer Generic Data Request"

    @property
    def manufacturer_id(self):
        if len(self.data) < 2:
            return None
        return int.from_bytes(self.data[0:2], "little")

    @property
    def manufacturer_data(self):
        return self.data[2:] if len(self.data) > 2 else b""

    def _format_output(self):
        if len(self.data) < 2:
            return f"Manufacturer generic payload (partial): {self.data.hex(':')}"
        return (
            f"Manufacturer ID (LE): 0x{self.manufacturer_id:04x}\n"
            f"Manufacturer Data: {self.manufacturer_data.hex(':')}\n"
            f"Raw Payload: {self.data.hex(':')}"
        )


@MessageRegistry.register(0x9F)
class SetManufacturerGenericDataResponse(SetManufacturerGenericDataRequest):
    name = "Set Manufacturer Generic Data Response"


@MessageRegistry.register(0x20)
class ManufacturerGenericDataRequest(Message):
    name = "Manufacturer Generic Data Request"


@MessageRegistry.register(0xA0)
class ManufacturerGenericDataResponse(Message):
    name = "Manufacturer Generic Data Response"

    def _format_output(self):
        return f"Manufacturer generic response payload: {self.data.hex(':')}"


# Manufacturer Generic Reply - 0x21
# Mentioned in table but not fleshed out


@MessageRegistry.register(0x41)
class GetUserMenuRequest(Message):
    name = "Get User Menu Request"

    @property
    def menu_file(self):
        return self.data[0]

    @property
    def main_menu(self):
        return self.data[1]

    @property
    def sublevel(self):
        return self.data[2]

    @property
    def max_bytes(self):
        return self.data[5]

    def _format_output(self):
        return (
            f"Menu File: {self.menu_file}\n"
            f"Main Menu: {self.main_menu}\n"
            f"Sublevel: {self.sublevel}\n"
            f"Max Bytes: {self.max_bytes}\n"
            f"DEBUG: {self.data.hex(':')}"
        )


@MessageRegistry.register(0xC1)
class GetUserMenuResponse(GetUserMenuRequest):
    name = "Get User Menu Response"

    @property
    def menu_data(self):
        return self.data[6:]

    def _format_output(self):
        return (
            f"Menu File: {self.menu_file}\n"
            f"Main Menu: {self.main_menu}\n"
            f"Sublevel: {self.sublevel}\n"
            f"Max Bytes: {self.max_bytes}\n"
            f"Menu Data: {self.menu_data}\n"
            f"DEBUG: {self.data.hex(':')}"
        )


@MessageRegistry.register(0x42)
class SetUserMenuUpdateRequest(Message):
    name = "Set User Menu Update Request"

    @property
    def menu_file(self):
        return self.data[0] if len(self.data) >= 1 else None

    @property
    def main_menu(self):
        return self.data[1] if len(self.data) >= 2 else None

    @property
    def sublevel(self):
        return self.data[2] if len(self.data) >= 3 else None

    @property
    def opening_file_security_code(self):
        return self.data[3] if len(self.data) >= 4 else None

    @property
    def updated_value_raw(self):
        return self.data[4:6] if len(self.data) >= 6 else b""

    @property
    def updated_value_be(self):
        if len(self.updated_value_raw) < 2:
            return None
        return int.from_bytes(self.updated_value_raw, "big")

    @property
    def closing_file_security_code(self):
        return self.data[6] if len(self.data) >= 7 else None

    def _format_output(self):
        if len(self.data) < 7:
            return f"User menu update payload (partial): {self.data.hex(':')}"
        opening_ok = self.opening_file_security_code == 0x55
        closing_ok = self.closing_file_security_code == 0xAA
        return (
            f"Menu File: {self.menu_file}\n"
            f"Main Menu: {self.main_menu}\n"
            f"Sublevel: {self.sublevel}\n"
            f"Opening File Security Code: 0x{self.opening_file_security_code:02x} "
            f"(expected 0x55: {'yes' if opening_ok else 'no'})\n"
            f"Updated Value: {self.updated_value_raw.hex(':')} "
            f"(big-endian int: {self.updated_value_be})\n"
            f"Closing File Security Code: 0x{self.closing_file_security_code:02x} "
            f"(expected 0xAA: {'yes' if closing_ok else 'no'})\n"
            f"Raw Payload: {self.data.hex(':')}"
        )


@MessageRegistry.register(0xC2)
class SetUserMenuUpdateResponse(SetUserMenuUpdateRequest):
    name = "Set User Menu Update Response"

    @property
    def result_code(self):
        return self.data[7] if len(self.data) >= 8 else None

    @property
    def result_text(self):
        if self.result_code == 0x06:
            return "ACK"
        if self.result_code == 0x15:
            return "NAK"
        return "Unknown"

    def _format_output(self):
        if len(self.data) < 8:
            return f"User menu update response payload (partial): {self.data.hex(':')}"
        return (
            f"{super()._format_output()}\n"
            f"Result Code: 0x{self.result_code:02x} ({self.result_text})"
        )


@MessageRegistry.register(0x43)
class SetFactorySharedDataToApplicationRequest(Message):
    name = "Set Factory Shared Data To Application Request"

    @property
    def shared_data_length(self):
        return self.data[0] if self.data else None

    @property
    def control_id(self):
        if len(self.data) < 3:
            return None
        return int.from_bytes(self.data[1:3], "little")

    @property
    def manufacturer_id(self):
        if len(self.data) < 5:
            return None
        return int.from_bytes(self.data[3:5], "little")

    @property
    def app_node_type(self):
        return self.data[5] if len(self.data) >= 6 else None

    @property
    def app_data(self):
        return self.data[6:] if len(self.data) > 6 else b""

    def _format_output(self):
        if len(self.data) < 6:
            return (
                "Factory-to-application shared data payload (partial): "
                f"{self.data.hex(':')}"
            )
        return (
            f"Shared Data Length: {self.shared_data_length}\n"
            f"Control ID (LE): 0x{self.control_id:04x}\n"
            f"Manufacturer ID (LE): 0x{self.manufacturer_id:04x}\n"
            f"App Node Type: {self.app_node_type} ({NODE_TYPE_MAP[self.app_node_type]})\n"
            f"Application Data: {self.app_data.hex(':')}\n"
            f"Raw Payload: {self.data.hex(':')}"
        )


@MessageRegistry.register(0xC3)
class SetFactorySharedDataToApplicationResponse(
    SetFactorySharedDataToApplicationRequest
):
    name = "Set Factory Shared Data To Application Response"


@MessageRegistry.register(0x44)
class GetSharedDataFromApplicationRequest(NoPayloadMessage):
    name = "Get Shared Data From Application Request"


@MessageRegistry.register(0xC4)
class GetSharedDataFromApplicationResponse(
    Message
):
    name = "Get Shared Data From Application Response"

    @property
    def response_app_node_type(self):
        return self.data[0] if self.data else None

    @property
    def shared_data_length(self):
        return self.data[1] if len(self.data) >= 2 else None

    @property
    def control_id(self):
        if len(self.data) < 4:
            return None
        return int.from_bytes(self.data[2:4], "little")

    @property
    def manufacturer_id(self):
        if len(self.data) < 6:
            return None
        return int.from_bytes(self.data[4:6], "little")

    @property
    def data_app_node_type(self):
        return self.data[6] if len(self.data) >= 7 else None

    @property
    def app_data(self):
        return self.data[7:] if len(self.data) > 7 else b""

    def _format_output(self):
        if not self.data:
            return "No shared data payload"
        if len(self.data) == 1:
            return (
                "No shared data payload (node type only): "
                f"{self.response_app_node_type} "
                f"({NODE_TYPE_MAP[self.response_app_node_type]})\n"
                f"Raw Payload: {self.data.hex(':')}"
            )
        if len(self.data) < 7:
            return f"Shared data from application payload (partial): {self.data.hex(':')}"
        return (
            f"Response App Node Type: {self.response_app_node_type} "
            f"({NODE_TYPE_MAP[self.response_app_node_type]})\n"
            f"Shared Data Length: {self.shared_data_length}\n"
            f"Control ID (LE): 0x{self.control_id:04x}\n"
            f"Manufacturer ID (LE): 0x{self.manufacturer_id:04x}\n"
            f"Data App Node Type: {self.data_app_node_type} "
            f"({NODE_TYPE_MAP[self.data_app_node_type]})\n"
            f"Application Data: {self.app_data.hex(':')}\n"
            f"Raw Payload: {self.data.hex(':')}"
        )


@MessageRegistry.register(0x5A)
class EchoRequest(Message):
    name = "Echo Request"

    def _format_output(self):
        return f"Known data to verify echo: {self.data.hex(':')}"


@MessageRegistry.register(0xDA)
class EchoResponse(Message):
    name = "Echo Response"

    def _format_output(self):
        return f"Echo of request payload: {self.data.hex(':')}"
