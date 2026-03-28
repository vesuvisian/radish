"""CT-485 specific message implementations."""

from ..maps import ADDRESS_TYPE_MAP, NODE_TYPE_MAP, SUBNET_MAP
from .base import Message, NoPayloadMessage
from .registry import MessageRegistry

__all__ = [
    "RequestToReceive",
    "NetworkStateRequest",
    "NetworkStateResponse",
    "AddressConfirmationPushRequest",
    "AddressConfirmationPushResponse",
    "TokenOffer",
    "TokenOfferResponse",
    "VersionAnnouncement",
    "NodeDiscoveryRequest",
    "NodeDiscoveryResponse",
    "SetAddressRequest",
    "SetAddressResponse",
    "GetNodeIdRequest",
    "GetNodeIdResponse",
    "NetworkSharedDataSectorRequest",
    "NetworkSharedDataSectorResponse",
    "EncapsulationRequest",
    "EncapsulationResponse",
]


@MessageRegistry.register(0x00)
class RequestToReceive(Message):
    name = "Request to Receive (R2R)"

    @property
    def r2r_code(self):
        return self.data[0]

    @property
    def mac_address(self):
        return self.data[1:9]

    @property
    def session_id(self):
        return self.data[9:17]

    def _format_output(self):
        if self.r2r_code == 0x00:
            msg_1 = "R2R Code: Request", "Coordinator"
        elif self.r2r_code == 0x06:
            msg_1 = "R2R Code: ACK", "Subordinate"
        else:
            msg_1 = f"Unknown R2R code (0x{self.r2r_code:02x})", "Unknown"
        msg_2 = f"{msg_1[1]} MAC address: {self.mac_address.hex(':')}"
        msg_3 = f"Session ID: {self.session_id.hex(':')}"
        return f"{msg_1[0]}\n{msg_2}\n{msg_3}\nDEBUG: {self.data.hex(':')}"


@MessageRegistry.register(0x75)
class NetworkStateRequest(NoPayloadMessage):
    name = "Network State Request"


@MessageRegistry.register(0xF5)
class NetworkStateResponse(Message):
    name = "Network State Response"

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


@MessageRegistry.register(0x76)
class AddressConfirmationPushRequest(Message):
    name = "Address Confirmation Push Request"

    @property
    def internal_node_type(self):
        return self.data[0]

    def _format_output(self):
        ret = (
            "Coordinator's virtual internal Subordinate Node Type: "
            f"{self.internal_node_type} ({NODE_TYPE_MAP[self.internal_node_type]})"
        )
        for i, byte in enumerate(self.data[1:], start=1):
            if byte == 0x00:
                break
            ret += f"\nNode type at index {i}: {byte} ({NODE_TYPE_MAP[byte]})"
        return ret


@MessageRegistry.register(0xF6)
class AddressConfirmationPushResponse(AddressConfirmationPushRequest):
    name = "Address Confirmation Push Response"


@MessageRegistry.register(0x77)
class TokenOffer(Message):
    name = "Token Offer"

    @property
    def node_id_filter(self):
        return self.data[0]

    def _format_output(self):
        return f"Node ID Filter: {self.node_id_filter}"


@MessageRegistry.register(0xF7)
class TokenOfferResponse(Message):
    name = "Token Offer Response"

    @property
    def address(self):
        return self.data[0]

    @property
    def subnet(self):
        return self.data[1]

    @property
    def mac_address(self):
        return self.data[2:10]

    @property
    def session_id(self):
        return self.data[10:18]

    def _format_output(self):
        return (
            f"Address: {self.address:#04x} ({ADDRESS_TYPE_MAP[self.address]})\n"
            f"Subnet: {self.subnet} ({SUBNET_MAP[self.subnet]})\n"
            f"ClimateTalk MAC address of addressee: {self.mac_address.hex(':')}\n"
            f"Session ID of addressee: {self.session_id.hex(':')}"
        )


@MessageRegistry.register(0x78)
class VersionAnnouncement(Message):
    name = "Version Announcement"

    @property
    def ct_485_version(self):
        if len(self.data) < 2:
            return None
        return int.from_bytes(self.data[0:2], "big")

    @property
    def ct_485_revision(self):
        if len(self.data) < 4:
            return None
        return int.from_bytes(self.data[2:4], "big")

    @property
    def coordinator_capable(self):
        if len(self.data) < 5:
            return None
        return self.data[4] == 0x01

    def _format_output(self):
        if len(self.data) < 5:
            return f"Version Payload (partial): {self.data.hex(':')}"
        ffd_value = self.data[4]
        ffd_text = "FFD (Coordinator capable)" if self.coordinator_capable else "RFD (Not coordinator capable)"
        return (
            f"CT-485 Version: 0x{self.ct_485_version:04x} ({self.ct_485_version})\n"
            f"CT-485 Revision: 0x{self.ct_485_revision:04x} ({self.ct_485_revision})\n"
            f"CT-485 FFD: 0x{ffd_value:02x} ({ffd_text})\n"
            f"Raw Payload: {self.data.hex(':')}"
        )


@MessageRegistry.register(0x79)
class NodeDiscoveryRequest(TokenOffer):
    name = "Node Discovery Request"


@MessageRegistry.register(0xF9)
class NodeDiscoveryResponse(Message):
    name = "Node Discovery Response"

    @property
    def node_type(self):
        return self.data[0]

    @property
    def mac_address(self):
        return self.data[2:10]

    @property
    def session_id(self):
        return self.data[10:18]

    def _format_output(self):
        return (
            f"Node Type: {self.node_type} ({NODE_TYPE_MAP[self.node_type]})\n"
            f"MAC address: {self.mac_address.hex(':')}\n"
            f"Session ID: {self.session_id.hex(':')}"
        )


@MessageRegistry.register(0x7A)
class SetAddressRequest(Message):
    name = "Set Address Request"

    @property
    def address(self):
        return self.data[0] if len(self.data) >= 1 else None

    @property
    def subnet(self):
        return self.data[1] if len(self.data) >= 2 else None

    @property
    def mac_address(self):
        return self.data[2:10] if len(self.data) >= 10 else b""

    @property
    def session_id(self):
        return self.data[10:18] if len(self.data) >= 18 else b""

    @property
    def reserved(self):
        return self.data[18] if len(self.data) >= 19 else None

    @property
    def has_expected_length(self):
        return len(self.data) == 19

    def _format_output(self):
        if len(self.data) < 19:
            return f"Set Address Payload (partial): {self.data.hex(':')}"
        reserved_ok = "yes" if self.reserved == 0x01 else "no"
        return (
            f"Address: {self.address:#04x} ({ADDRESS_TYPE_MAP[self.address]})\n"
            f"Subnet: {self.subnet} ({SUBNET_MAP[self.subnet]})\n"
            f"MAC address of addressee: {self.mac_address.hex(':')}\n"
            f"Session ID of addressee: {self.session_id.hex(':')}\n"
            f"Reserved: 0x{self.reserved:02x} (expected 0x01: {reserved_ok})\n"
            f"Raw Payload: {self.data.hex(':')}"
        )


@MessageRegistry.register(0xFA)
class SetAddressResponse(SetAddressRequest):
    name = "Set Address Response"


@MessageRegistry.register(0x7B)
class GetNodeIdRequest(NoPayloadMessage):
    name = "Get Node ID Request"


@MessageRegistry.register(0xFB)
class GetNodeIdResponse(Message):
    name = "Get Node ID Response"

    @property
    def node_type(self):
        return self.data[0] if self.data else None

    @property
    def mac_address(self):
        return self.data[1:9] if len(self.data) >= 9 else b""

    @property
    def session_id(self):
        return self.data[9:17] if len(self.data) >= 17 else b""

    def _format_output(self):
        if not self.data:
            return "No payload"
        if len(self.data) < 17:
            return f"Get Node ID payload (partial): {self.data.hex(':')}"
        return (
            f"Node Type: {self.node_type} ({NODE_TYPE_MAP[self.node_type]})\n"
            f"MAC address: {self.mac_address.hex(':')}\n"
            f"Session ID: {self.session_id.hex(':')}\n"
            f"Raw Payload: {self.data.hex(':')}"
        )


@MessageRegistry.register(0x7D)
class NetworkSharedDataSectorRequest(Message):
    name = "Network Shared Data Sector Request"

    @property
    def operation_and_node_type(self):
        return self.data[0] if len(self.data) >= 1 else None

    @property
    def is_read_operation(self):
        if self.operation_and_node_type is None:
            return None
        return bool(self.operation_and_node_type & 0x80)

    @property
    def operation(self):
        if self.is_read_operation is None:
            return "unknown"
        return "read" if self.is_read_operation else "write"

    @property
    def shared_data_node_type(self):
        if self.operation_and_node_type is None:
            return None
        return self.operation_and_node_type & 0x7F

    @property
    def shared_data_payload(self):
        return self.data[1:] if len(self.data) > 1 else b""

    def _format_output(self):
        if len(self.data) < 1:
            return "Network shared data payload: <empty>"
        return (
            f"Operation: {self.operation} "
            f"(bit7={'1' if self.is_read_operation else '0'})\n"
            f"Shared Data Node Type: {self.shared_data_node_type} "
            f"({NODE_TYPE_MAP[self.shared_data_node_type]})\n"
            f"Shared Data Payload: {self.shared_data_payload.hex(':')}\n"
            f"Raw Payload: {self.data.hex(':')}"
        )


@MessageRegistry.register(0xFD)
class NetworkSharedDataSectorResponse(Message):
    name = "Network Shared Data Sector Response"

    @property
    def shared_data_node_type(self):
        return self.data[0] if self.data else None

    @property
    def shared_data_records(self):
        return self.data[1:] if len(self.data) > 1 else b""

    def _format_output(self):
        if not self.data:
            return "No shared data payload"
        return (
            f"Shared Data Node Type: {self.shared_data_node_type} "
            f"({NODE_TYPE_MAP[self.shared_data_node_type]})\n"
            f"Shared Data Records: {self.shared_data_records.hex(':')}\n"
            f"Raw Payload: {self.data.hex(':')}"
        )


@MessageRegistry.register(0x7E)
class EncapsulationRequest(Message):
    name = "Encapsulation Request"

    @property
    def opcode(self):
        return self.data[0] if self.data else None

    @property
    def operands(self):
        if len(self.data) < 4:
            return tuple(self.data[1:])
        return (self.data[1], self.data[2], self.data[3])

    @property
    def encapsulated_payload(self):
        return self.data[4:] if len(self.data) > 4 else b""

    def _format_output(self):
        if self.opcode is None:
            return f"No payload (data={self.data.hex(':')})"
        return (
            f"OpCode: 0x{self.opcode:02x}\n"
            f"Operands: {[f'0x{x:02x}' for x in self.operands]}\n"
            f"Encapsulated Payload: {self.encapsulated_payload.hex(':')}\n"
            "Note: optional supplement-data boundary is protocol-specific\n"
            f"Raw Payload: {self.data.hex(':')}"
        )


@MessageRegistry.register(0xFE)
class EncapsulationResponse(EncapsulationRequest):
    name = "Encapsulation Response"
