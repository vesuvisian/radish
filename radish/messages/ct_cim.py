"""CT-CIM mapped message implementations."""

from ..maps import NODE_TYPE_MAP
from .base import Message, NoPayloadMessage, parse_db_id_datagram
from .config_mdi import decode_config_mdi_record
from .identification_mdi import decode_get_identification_data, decode_set_identification_data
from .sensor_mdi import decode_sensor_mdi_potential_values, decode_sensor_mdi_record
from .status_mdi import decode_status_mdi_record
from .registry import MessageRegistry
from .user_menu import decode_user_menu_payload

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
    "DirectMemoryAccessWriteRequest",
    "DirectMemoryAccessWriteResponse",
    "SetManufacturerGenericDataRequest",
    "SetManufacturerGenericDataResponse",
    "GetManufacturerGenericDataRequest",
    "GetManufacturerGenericDataResponse",
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

    @property
    def source_node_type(self):
        return self.parse_context.get("source_node_type")

    @property
    def decoded_records(self):
        decoded = []
        warnings = []
        for record in self.db_id_records:
            decoded_record, warning = decode_config_mdi_record(
                source_node_type=self.source_node_type,
                db_id=record["db_id"],
                value=record["value"],
            )
            decoded.append(decoded_record)
            if warning:
                warnings.append(warning)
        return decoded, warnings

    def _format_output(self):
        if not self.data:
            return "Configuration MDI: no payload"

        ret = [f"Configuration MDI Record Count: {len(self.db_id_records)}"]
        if self.source_node_type is not None:
            ret.append(
                f"Source Node Type: {self.source_node_type} "
                f"({NODE_TYPE_MAP[self.source_node_type]})"
            )

        decoded_records, decode_warnings = self.decoded_records
        for idx, record in enumerate(self.db_id_records, start=1):
            ret.append(
                f"Record {idx}: "
                f"db_id=0x{record['db_id']:02x}, "
                f"length={record['db_len']}, "
                f"value={record['value'].hex(':')}"
            )
            decoded_record = decoded_records[idx - 1]
            if decoded_record:
                ret.append(f"  Configuration: {decoded_record['record_name']}")
                fields = decoded_record.get("decoded_fields") or {}
                for field_name, field_value in fields.items():
                    ret.append(f"    {field_name}: {field_value}")
        for warning in self.parse_warnings:
            ret.append(f"Parse Warning: {warning}")
        for warning in decode_warnings:
            ret.append(f"Decode Warning: {warning}")
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

    @property
    def source_node_type(self):
        return self.parse_context.get("source_node_type")

    @property
    def decoded_records(self):
        decoded = []
        warnings = []
        for record in self.db_id_records:
            decoded_record, warning = decode_status_mdi_record(
                source_node_type=self.source_node_type,
                db_id=record["db_id"],
                value=record["value"],
            )
            decoded.append(decoded_record)
            if warning:
                warnings.append(warning)
        return decoded, warnings

    def _format_output(self):
        if not self.data:
            return "Status MDI: no payload"

        ret = [f"Status MDI Record Count: {len(self.db_id_records)}"]
        if self.source_node_type is not None:
            ret.append(
                f"Source Node Type: {self.source_node_type} "
                f"({NODE_TYPE_MAP[self.source_node_type]})"
            )

        decoded_records, decode_warnings = self.decoded_records
        for idx, record in enumerate(self.db_id_records, start=1):
            db_id = record["db_id"]
            value = record["value"]
            ret.append(
                f"Record {idx}: "
                f"db_id=0x{db_id:02x}, "
                f"length={record['db_len']}, "
                f"value={value.hex(':')}"
            )
            decoded_record = decoded_records[idx - 1]
            if decoded_record:
                ret.append(f"  Status: {decoded_record['record_name']}")
                fields = decoded_record.get("decoded_fields") or {}
                for field_name, field_value in fields.items():
                    ret.append(f"    {field_name}: {field_value}")
        for warning in self.parse_warnings:
            ret.append(f"Parse Warning: {warning}")
        for warning in decode_warnings:
            ret.append(f"Decode Warning: {warning}")
        ret.append(f"Raw Payload: {self.data.hex(':')}")
        return "\n".join(ret)


@MessageRegistry.register(0x03)
class SetControlCommandRequest(Message):
    name = "Set Control Command Request"
    CONTROL_COMMAND_CODE_MAP = {
        0x0001: "Heat Set Point Temperature Modify",
        0x0002: "Cool Set Point Temperature Modify",
        0x0003: "Heat Profile Change",
        0x0004: "Cool Profile Change",
        0x0005: "System Switch Modify",
        0x0006: "Permanent Set Point Temp & Hold Modify",
        0x0008: "Hold Override",
        0x000F: "Real Time/Day Override",
        0x0045: "Restore Factory Defaults",
        0x0050: "Test Mode",
        0x0051: "Subsystem Installation Test",
        0x0052: "Auto-Pairing Request",
        0x0053: "Pair Ownership Request",
        0x0057: "Auto-Pairing Request",
        0x0058: "Pairing Ownership Request",
        0x0059: "Reversing Valve Configuration",
        0x005A: "DEHUM/HUM Configuration",
        0x005B: "Change UV Light Maintenance Timer",
        0x005C: "Change Hum Pad Maintenance Timer",
        0x0060: "Damper Closure Position Demand",
        0x0061: "Subsystem Busy Status",
        0x0062: "Dehumidification Demand",
        0x0063: "Humidification Demand",
        0x0064: "Heat Demand",
        0x0065: "Cool Demand",
        0x0066: "Fan Demand",
        0x0067: "Back-Up Heat Demand",
        0x0068: "Defrost Heat Demand",
        0x0069: "Aux / Alt Heat Demand",
        0x006A: "Set Motor Speed",
        0x006B: "Set Motor Torque",
        0x006C: "Set Airflow Demand",
        0x006D: "Set Control Mode",
        0x006E: "Set Demand Ramp Rate",
        0x006F: "Set Motor Direction",
        0x0070: "Set Motor Torque Percent",
        0x0071: "Set Motor Position Demand",
        0x0072: "Set Blower Coefficient 1",
        0x0073: "Set Blower Coefficient 2",
        0x0074: "Set Blower Coefficient 3",
        0x0075: "Set Blower Coefficient 4",
        0x0076: "Set Blower Coefficient 5",
        0x0077: "Set Blower Identification 0",
        0x0078: "Set Blower Identification 1",
        0x0079: "Set Blower Identification 2",
        0x007A: "Set Blower Identification 3",
        0x007B: "Set Blower Identification 4",
        0x007C: "Set Blower Identification 5",
        0x007F: "Set Speed Limit",
        0x0080: "Set Torque Limit",
        0x0081: "Set Airflow Limit",
        0x0082: "Set Power Output Limit",
        0x0083: "Set Device Temperature Limit",
        0x0085: "STOP Motor by Braking",
        0x0086: "RUN/STOP Motor",
        0x0088: "Set Demand Ramp Time",
        0x0089: "Set Inducer Ramp Rate",
        0x008A: "Set Blower Coefficient 6",
        0x008B: "Set Blower Coefficient 7",
        0x008C: "Set Blower Coefficient 8",
        0x008D: "Set Blower Coefficient 9",
        0x008E: "Set Blower Coefficient 10",
        0x00E0: "Publish Price",
    }
    PERCENT_DEMAND_COMMANDS = {
        0x0060: "Damper Closure Position Demand",
        0x0062: "Dehumidification Demand",
        0x0063: "Humidification Demand",
        0x0064: "Heat Demand",
        0x0065: "Cool Demand",
        0x0067: "Back-Up Heat Demand",
        0x0068: "Defrost Heat Demand",
        0x0069: "Aux / Alt Heat Demand",
    }
    FAN_MODE_MAP = {
        0: "Manual",
        1: "Cool",
        2: "Heat",
        3: "Aux Heat",
        4: "Emer Heat",
        5: "Defrost",
    }

    @property
    def command_code(self):
        if len(self.data) < 2:
            return None
        return int.from_bytes(self.data[0:2], "little")

    @property
    def command_data(self):
        return self.data[2:] if len(self.data) > 2 else b""

    @property
    def command_name(self):
        if self.command_code is None:
            return "Unknown"
        return self.CONTROL_COMMAND_CODE_MAP.get(self.command_code, "Unknown")

    def _decode_refresh_timer(self, timer_byte: int):
        # first 4 bits are minutes, last 4 bits are sixteenths of a minute (3.75 seconds per sixteenth)
        minutes = timer_byte >> 4
        sixteenths = timer_byte & 0x0F
        total_minutes = minutes + (sixteenths / 16.0)
        return {
            "raw": timer_byte,
            "minutes": total_minutes,
        }

    def _decode_percent_demand_command(self, command_label: str):
        decoded = {"command_name": command_label}
        command_data = self.command_data

        if len(command_data) >= 1:
            decoded["refresh_timer"] = self._decode_refresh_timer(command_data[0])

        if len(command_data) >= 2:
            demand_raw = command_data[1]
            decoded["demand_raw"] = demand_raw
            decoded["demand_percent"] = demand_raw * 0.5

        if len(command_data) > 2:
            decoded["unknown_bytes"] = command_data[2:]

        return decoded

    @property
    def decoded_command(self):
        if self.command_code == 0x0066:
            decoded = {"command_name": "Fan Demand"}
            fan_data = self.command_data

            if len(fan_data) >= 1:
                decoded["refresh_timer"] = self._decode_refresh_timer(fan_data[0])

            if len(fan_data) >= 2:
                fan_mode = fan_data[1]
                decoded["fan_mode_raw"] = fan_mode
                decoded["fan_mode_text"] = self.FAN_MODE_MAP.get(fan_mode, "Unknown")

            if len(fan_data) >= 3:
                fan_demand_raw = fan_data[2]
                decoded["fan_demand_raw"] = fan_demand_raw
                decoded["fan_demand_percent"] = fan_demand_raw * 0.5

            if len(fan_data) >= 4:
                decoded["fan_on_off_rate_raw"] = fan_data[3]
            if len(fan_data) > 4:
                decoded["unknown_bytes"] = fan_data[4:]

            return decoded

        if self.command_code == 0x0061:
            decoded = {"command_name": "Subsystem Busy Status"}
            command_data = self.command_data
            if len(command_data) >= 1:
                decoded["refresh_timer"] = self._decode_refresh_timer(command_data[0])
            if len(command_data) >= 2:
                busy_raw = command_data[1]
                decoded["busy_raw"] = busy_raw
                if busy_raw == 0:
                    decoded["busy_text"] = "Ready"
                elif busy_raw == 1:
                    decoded["busy_text"] = "Busy"
                else:
                    decoded["busy_text"] = "Unknown"
            if len(command_data) > 2:
                decoded["unknown_bytes"] = command_data[2:]
            return decoded

        if self.command_code in self.PERCENT_DEMAND_COMMANDS:
            return self._decode_percent_demand_command(
                self.PERCENT_DEMAND_COMMANDS[self.command_code]
            )

        return None

    def _format_output(self):
        if len(self.data) < 2:
            return f"Control command payload (partial): {self.data.hex(':')}"
        ret = [
            f"Command Code (LE): 0x{self.command_code:04x}",
            f"Command Name: {self.command_name}",
            f"Command Data: {self.command_data.hex(':')}",
        ]

        decoded = self.decoded_command
        if decoded and "refresh_timer" in decoded:
            timer = decoded["refresh_timer"]
            ret.append(
                "Refresh Timer: "
                f"0x{timer['raw']:02x} "
                f"({timer['minutes']:.4f} min)"
            )

        if decoded and self.command_code == 0x0066:
            if "fan_mode_raw" in decoded:
                ret.append(
                    "Fan Mode: "
                    f"{decoded['fan_mode_text']} "
                    f"({decoded['fan_mode_raw']})"
                )
            if "fan_demand_raw" in decoded:
                ret.append(
                    "Fan Demand: "
                    f"0x{decoded['fan_demand_raw']:02x} "
                    f"({decoded['fan_demand_percent']:.1f}%)"
                )
            if "fan_on_off_rate_raw" in decoded:
                ret.append(
                    "Fan On/Off Rate: "
                    f"0x{decoded['fan_on_off_rate_raw']:02x} "
                    f"({decoded['fan_on_off_rate_raw']})"
                )
            else:
                ret.append("Fan On/Off Rate: <not present>")
            if "unknown_bytes" in decoded:
                ret.append(
                    f"Fan Demand Remaining Bytes: {decoded['unknown_bytes'].hex(':')} (unknown)"
                )

        if decoded and self.command_code in self.PERCENT_DEMAND_COMMANDS:
            if "demand_raw" in decoded:
                ret.append(
                    f"{decoded['command_name']}: "
                    f"0x{decoded['demand_raw']:02x} "
                    f"({decoded['demand_percent']:.1f}%)"
                )
            if "unknown_bytes" in decoded:
                ret.append(
                    f"{decoded['command_name']} Remaining Bytes: "
                    f"{decoded['unknown_bytes'].hex(':')} (unknown)"
                )
        if decoded and self.command_code == 0x0061:
            if "busy_raw" in decoded:
                ret.append(
                    "Subsystem Busy State: "
                    f"0x{decoded['busy_raw']:02x} "
                    f"({decoded['busy_text']})"
                )
            if "unknown_bytes" in decoded:
                ret.append(
                    f"Subsystem Busy Remaining Bytes: {decoded['unknown_bytes'].hex(':')} (unknown)"
                )

        ret.append(f"Raw Payload: {self.data.hex(':')}")
        return "\n".join(ret)


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
            return b""
        return self.data[4 : 4 + self.message_length]

    @property
    def fault_message_text(self):
        return self.fault_message.decode("ascii", errors="replace")

    def _format_output(self):
        message_length_line = f"Fault Message Length: {self.message_length}"
        if self.message_length == 0:
            message_length_line += " (fault cleared)"

        ret = [
            f"Node Type: {self.node_type} ({NODE_TYPE_MAP[self.node_type]})\n"
            f"Major Fault Code: {self.major_fault_code}\n"
            f"Minor Fault Code: {self.minor_fault_code}\n"
            f"{message_length_line}"
        ]
        if self.message_length > 0:
            ret.append(f"Fault Message: {self.fault_message_text}")
        ret.append(f"Raw Payload: {self.data.hex(':')}")
        return "\n".join(ret)


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

    @property
    def db_id_records(self):
        records, _ = parse_db_id_datagram(self.data)
        return records

    @property
    def parse_warnings(self):
        _, warnings = parse_db_id_datagram(self.data)
        return warnings

    @property
    def source_node_type(self):
        return self.parse_context.get("source_node_type")

    @property
    def decoded_records(self):
        decoded = []
        warnings = []
        for record in self.db_id_records:
            decoded_record, warning = decode_sensor_mdi_record(
                source_node_type=self.source_node_type,
                db_id=record["db_id"],
                value=record["value"],
            )
            decoded.append(decoded_record)
            if warning:
                warnings.append(warning)
        return decoded, warnings

    def _format_output(self):
        if not self.data:
            return "Sensor MDI: no payload"

        ret = [f"Sensor MDI Record Count: {len(self.db_id_records)}"]
        if self.source_node_type is not None:
            ret.append(
                f"Source Node Type: {self.source_node_type} "
                f"({NODE_TYPE_MAP[self.source_node_type]})"
            )

        decoded_records, decode_warnings = self.decoded_records
        for idx, record in enumerate(self.db_id_records, start=1):
            ret.append(
                f"Record {idx}: "
                f"db_id=0x{record['db_id']:02x}, "
                f"length={record['db_len']}, "
                f"value={record['value'].hex(':')}"
            )
            decoded_record = decoded_records[idx - 1]
            if not decoded_record:
                potential_values = decode_sensor_mdi_potential_values(
                    source_node_type=self.source_node_type,
                    db_id=record["db_id"],
                    value=record["value"],
                )
                if potential_values:
                    ret.append("  Potential Decodings (experimental):")
                    for candidate in potential_values:
                        if candidate.get("slot_name") and candidate.get("preferred_units") == "invalid":
                            ret.append(f"    {candidate['slot_name']}: invalid")
                            continue
                        if candidate.get("slot_name") and candidate.get("preferred_value") is not None:
                            preferred_units = candidate["preferred_units"]
                            if preferred_units == "PSI":
                                preferred_text = (
                                    f"{int(candidate['preferred_value'])} {preferred_units}"
                                )
                            else:
                                preferred_text = (
                                    f"{candidate['preferred_value']:.4f} {preferred_units}"
                                )
                            ret.append(
                                f"    {candidate['slot_name']}: "
                                f"{preferred_text}"
                            )
                            continue

                        slot_text = f"Slot {candidate['slot']}"
                        if candidate.get("slot_name"):
                            slot_text += f" ({candidate['slot_name']})"
                        ret.append(
                            f"    {slot_text}: bytes={candidate['bytes']}, "
                            f"u16={candidate['u16_le']}, s16={candidate['s16_le']}, "
                            f"u16/10={candidate['u16_div10']:.1f}, s16/10={candidate['s16_div10']:.1f}, "
                            f"packed_temp_valid={candidate['packed_valid']}, "
                            f"packed_temp={candidate['packed_value_f']:.4f} degF"
                        )
                continue
            fields = decoded_record["decoded_fields"]
            ret.append(f"  Sensor: {decoded_record['sensor_name']}")
            if not fields["valid"]:
                ret.append("  Value: invalid")
                continue
            if "value_f" in fields:
                ret.append(f"  Value: {fields['value_f']:.4f} degF")
            elif "value_percent" in fields:
                ret.append(f"  Value: {fields['value_percent']:.4f} %RH")
        for warning in self.parse_warnings:
            ret.append(f"Parse Warning: {warning}")
        for warning in decode_warnings:
            ret.append(f"Decode Warning: {warning}")
        ret.append(f"Raw Payload: {self.data.hex(':')}")
        return "\n".join(ret)


@MessageRegistry.register(0x0D)
class SetIdentificationRequest(Message):
    name = "Set Identification Request"

    def _format_output(self):
        decoded, warnings = decode_set_identification_data(self.data)
        ret = [
            f"Date Code (mm/dd/yy): {decoded['date_code_text']}",
            f"Verification/Test Date (mm/dd/yy): {decoded['verification_date_text']}",
            f"Installation Date (mm/dd/yy): {decoded['installation_date_text']}",
            f"Address: {decoded['address']}",
            f"Zip Code: {decoded['zip_code']}",
            f"Manufacturer: {decoded['manufacturer']}",
            f"Control Name: {decoded['control_name']}",
            f"Model: {decoded['model']}",
            f"Model Version: {decoded['model_version']}",
            f"Model Revision: {decoded['model_revision']}",
        ]
        for warning in warnings:
            ret.append(f"Parse Warning: {warning}")
        ret.append(f"Raw Payload: {self.data.hex(':')}")
        return "\n".join(ret)


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
        if not self.data:
            return "Identification MDI: no payload"

        decoded, warnings = decode_get_identification_data(self.data)
        if "manufacturer_id" not in decoded:
            ret = ["Identification MDI: malformed payload"]
            for warning in warnings:
                ret.append(f"Parse Warning: {warning}")
            ret.append(f"Raw Payload: {self.data.hex(':')}")
            return "\n".join(ret)

        ret = [
            f"Manufacturer ID (LE): 0x{decoded['manufacturer_id']:04x}",
            f"ClimateTalk Standard Version: {decoded['ct_version']}",
            f"ClimateTalk Standard Revision: {decoded['ct_revision']}",
            f"Number of Micros: {decoded['number_of_micros']}",
        ]

        micros = decoded.get("micros") or []
        for idx, micro in enumerate(micros, start=1):
            ret.append(
                f"Micro {idx}: sw_version='{micro['sw_version']}', "
                f"sw_revision='{micro['sw_revision']}', serial='{micro['serial_number']}'"
            )

        ret.extend(
            [
                f"Date Code (mm/dd/yy): {decoded['date_code_text']}",
                f"Verification/Test Date (mm/dd/yy): {decoded['verification_date_text']}",
                f"Installation Date (mm/dd/yy): {decoded['installation_date_text']}",
                f"Address: {decoded['address']}",
                f"Zip Code: {decoded['zip_code']}",
                f"Manufacturer: {decoded['manufacturer']}",
                f"Control Name: {decoded['control_name']}",
                f"Model: {decoded['model']}",
                f"Model Version: {decoded['model_version']}",
                f"Model Revision: {decoded['model_revision']}",
            ]
        )

        if decoded.get("trailing_bytes"):
            ret.append(
                f"Trailing Bytes: {decoded['trailing_bytes'].hex(':')}"
            )
        for warning in warnings:
            ret.append(f"Parse Warning: {warning}")
        ret.append(f"Raw Payload: {self.data.hex(':')}")
        return "\n".join(ret)


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


@MessageRegistry.register(0x1E)
class DirectMemoryAccessWriteRequest(Message):
    name = "Direct Memory Access Write Request"

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
    def db_values(self):
        return self.data[3:] if len(self.data) > 3 else b""

    def _format_output(self):
        if len(self.data) < 3:
            return f"DMA write request payload (partial): {self.data.hex(':')}"
        return (
            f"MDI Code: 0x{self.mdi_code:02x} ({self.mdi_name})\n"
            f"MDI Packet Number: 0x{self.mdi_packet_number:02x}\n"
            f"Start DB ID: {self.start_db_id}\n"
            f"DB Values ({len(self.db_values)} byte(s)): {self.db_values.hex(':')}\n"
            f"Raw Payload: {self.data.hex(':')}"
        )


@MessageRegistry.register(0x9E)
class DirectMemoryAccessWriteResponse(DirectMemoryAccessWriteRequest):
    name = "Direct Memory Access Write Response"

    @property
    def confirmation_code(self):
        return self.data[0:2] if len(self.data) >= 2 else b""

    @property
    def is_ack(self):
        return self.confirmation_code == b"\xAC\x06"

    def _format_output(self):
        # Response may be either ACK bytes or an echoed request payload.
        if len(self.data) == 2:
            return (
                f"Confirmation Code: {self.confirmation_code.hex(':')}\n"
                f"ACK: {'yes' if self.is_ack else 'no'}\n"
                f"Raw Payload: {self.data.hex(':')}"
            )
        return super()._format_output()


@MessageRegistry.register(0x1F)
class _ManufacturerGenericDataDecodeMixin:
    SUBTYPE_02_BYTE_LABELS = [
        "ctOutdoorFrequencyInPercent",
        "Cooling rated power",
        "Unknown",
        "Heating rated power",
        "Unknown",
        "Outdoor power",
        "Unknown",
        "Unknown",
        "Unknown",
        "Unknown",
        "Unknown",
        "Current compressor RPS",
        "Compressor current",
        "Unknown",
        "Unknown",
        "Inverter current",
        "Unknown",
        "Target compressor speed",
        "Unknown",
        "(Target?) OD fan RPM",
        "Unknown",
        "Unknown",
        "Unknown",
        "Unknown",
        "(Target?) OD fan RPM",
    ]

    @property
    def manufacturer_id(self):
        if len(self.data) < 2:
            return None
        return int.from_bytes(self.data[0:2], "little")

    @property
    def manufacturer_subtype(self):
        if len(self.data) < 3:
            return None
        return self.data[2]

    @property
    def decoded_payload(self):
        """Decode known OEM payload variants when the shape matches."""
        if len(self.data) < 3:
            return None

        if (
            self.manufacturer_id == 0x0009
            and self.manufacturer_subtype == 0x03
            and len(self.data) == 9
        ):
            return {
                "manufacturer_id": self.manufacturer_id,
                "subtype": self.manufacturer_subtype,
                "air_handler_fan_motor_rpm": int.from_bytes(self.data[3:5], "little"),
                "air_handler_eev_open_rate": int.from_bytes(self.data[5:7], "little"),
                "unknown_word_3": int.from_bytes(self.data[7:9], "little"),
            }

        if self.manufacturer_id == 0x0009 and self.manufacturer_subtype == 0x02:
            value_block = self.data[3:]
            decoded_bytes = []
            for idx, raw_value in enumerate(value_block):
                label = (
                    self.SUBTYPE_02_BYTE_LABELS[idx]
                    if idx < len(self.SUBTYPE_02_BYTE_LABELS)
                    else "Unknown"
                )
                decoded_bytes.append(
                    {
                        "index": idx,
                        "label": label,
                        "value": raw_value,
                    }
                )
            return {
                "manufacturer_id": self.manufacturer_id,
                "subtype": self.manufacturer_subtype,
                "value_block_len": len(value_block),
                "decoded_bytes": decoded_bytes,
            }
        return None

    def _format_output(self):
        if len(self.data) < 2:
            return f"Manufacturer generic payload (partial): {self.data.hex(':')}"

        decoded = self.decoded_payload
        if not decoded:
            return (
                f"Manufacturer ID (LE): 0x{self.manufacturer_id:04x}\n"
                f"Manufacturer Data: {self.data[2:].hex(':')}\n"
                f"Raw Payload: {self.data.hex(':')}"
            )

        if decoded["subtype"] == 0x02:
            lines = [
                f"Manufacturer ID (LE): 0x{decoded['manufacturer_id']:04x}",
                f"Manufacturer Subtype: 0x{decoded['subtype']:02x}",
                f"Subtype 0x02 Value Length: {decoded['value_block_len']} byte(s)",
                "Subtype 0x02 Byte Breakdown:",
            ]
            for byte_def in decoded["decoded_bytes"]:
                lines.append(
                    f"  Byte {byte_def['index']:02d}: {byte_def['label']} = "
                    f"0x{byte_def['value']:02x} ({byte_def['value']})"
                )
            lines.append(f"Raw Payload: {self.data.hex(':')}")
            return "\n".join(lines)

        return (
            f"Manufacturer ID (LE): 0x{decoded['manufacturer_id']:04x}\n"
            f"Manufacturer Subtype: 0x{decoded['subtype']:02x}\n"
            f"Air Handler Fan Motor RPM: {decoded['air_handler_fan_motor_rpm']}\n"
            f"Air Handler EEV Open Rate: {decoded['air_handler_eev_open_rate']}\n"
            f"Unknown Word 3 (LE): 0x{decoded['unknown_word_3']:04x} "
            f"({decoded['unknown_word_3']})\n"
            f"Raw Payload: {self.data.hex(':')}"
        )


@MessageRegistry.register(0x1F)
class SetManufacturerGenericDataRequest(_ManufacturerGenericDataDecodeMixin, Message):
    name = "Set Manufacturer Generic Data Request"


@MessageRegistry.register(0x9F)
class SetManufacturerGenericDataResponse(SetManufacturerGenericDataRequest):
    name = "Set Manufacturer Generic Data Response"


@MessageRegistry.register(0x20)
class GetManufacturerGenericDataRequest(Message):
    name = "Get Manufacturer Generic Data Request"


@MessageRegistry.register(0xA0)
class GetManufacturerGenericDataResponse(_ManufacturerGenericDataDecodeMixin, Message):
    name = "Get Manufacturer Generic Data Response"

    def _format_output(self):
        decoded = self.decoded_payload
        if not decoded:
            return f"Manufacturer generic response payload: {self.data.hex(':')}"

        if decoded["subtype"] == 0x02:
            lines = [
                f"Manufacturer ID (LE): 0x{decoded['manufacturer_id']:04x}",
                f"Manufacturer Subtype: 0x{decoded['subtype']:02x}",
                f"Subtype 0x02 Value Length: {decoded['value_block_len']} byte(s)",
                "Subtype 0x02 Byte Breakdown:",
            ]
            for byte_def in decoded["decoded_bytes"]:
                lines.append(
                    f"  Byte {byte_def['index']:02d}: {byte_def['label']} = "
                    f"0x{byte_def['value']:02x} ({byte_def['value']})"
                )
            lines.append(f"Raw Payload: {self.data.hex(':')}")
            return "\n".join(lines)

        return (
            f"Manufacturer ID (LE): 0x{decoded['manufacturer_id']:04x}\n"
            f"Manufacturer Subtype: 0x{decoded['subtype']:02x}\n"
            f"Air Handler Fan Motor RPM: {decoded['air_handler_fan_motor_rpm']}\n"
            f"Air Handler EEV Open Rate: {decoded['air_handler_eev_open_rate']}\n"
            f"Unknown Word 3 (LE): 0x{decoded['unknown_word_3']:04x} "
            f"({decoded['unknown_word_3']})\n"
            f"Raw Payload: {self.data.hex(':')}"
        )


# Manufacturer Generic Reply - 0x21
# Mentioned in table but not fleshed out

# Backward-compatible aliases for older references.
ManufacturerGenericDataRequest = GetManufacturerGenericDataRequest
ManufacturerGenericDataResponse = GetManufacturerGenericDataResponse


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
        decoded = decode_user_menu_payload(self.menu_data)
        item_lines = []
        for idx, item in enumerate(decoded["items"], start=1):
            item_lines.append(f"Item {idx}: {item['label'] or '<unnamed>'}")
            item_lines.append(
                f"  Options: {', '.join(item['options']) if item['options'] else '<none>'}"
            )
            if item["selected_option"] is not None:
                item_lines.append(f"  Selected: {item['selected_option']}")
        warning_lines = [f"Menu Decode Warning: {warning}" for warning in decoded["warnings"]]
        detail_lines = item_lines + warning_lines
        detail_block = "\n".join(detail_lines)
        if detail_block:
            detail_block = f"{detail_block}\n"
        directory_lines = []
        if decoded["directory_entries"] and not decoded["items"]:
            directory_lines.append(
                f"Menu Directory Count: {len(decoded['directory_entries'])}"
            )
            for idx, entry in enumerate(decoded["directory_entries"], start=1):
                directory_lines.append(f"Directory Entry {idx}: {entry}")
        directory_block = "\n".join(directory_lines)
        if directory_block:
            directory_block = f"{directory_block}\n"

        return (
            f"Menu File: {self.menu_file}\n"
            f"Main Menu: {self.main_menu}\n"
            f"Sublevel: {self.sublevel}\n"
            f"Max Bytes: {self.max_bytes}\n"
            f"Menu Title: {decoded['title'] or '<none>'}\n"
            f"Menu Item Count: {len(decoded['items'])}\n"
            f"{directory_block}"
            f"{detail_block}"
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
