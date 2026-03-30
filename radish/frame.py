import struct
from dataclasses import dataclass, field
from typing import Self

from .maps import (
    ADDRESS_TYPE_MAP,
    NODE_TYPE_MAP,
    SEND_METHOD_MAP,
    SUBNET_MAP,
    decode_packet_number,
    decode_send_parameters,
)
from .messages import MessageRegistry
from .utils import tabulate

# Packet breakdown:
# Element             Size Offset
# Destination Address    1      0
# Source Address         1      1
# Subnet                 1      2
# Send Method            1      3
# Send Parameters        2      4
# Source Node Type       1      6
# Message Type           1      7
# Packet Number          1      8
# Packet Length          1      9
# Packet Payload     0-240     10
# Message Checksum       2     10 + payload length


@dataclass
class Frame:
    """
    Daikin HVAC Frame
    
    1. Message Header (7 bytes): Routing/Addressing
    2. Packet Header (3 bytes): Message ID, Sequence, Length
    3. Payload (0-240 bytes): Data
    4. Footer (2 bytes): Checksum
    """

    # > = Big Endian
    # B (Dest), B (Src), B (Subnet), B (Method), H (Params), B (Node Type)
    _MSG_HDR_FMT = ">BBBBHB" 
    # B (Msg Type), B (Seq), B (Len)
    _PKT_HDR_FMT = ">BBB"
    MSG_HDR_SIZE = struct.calcsize(_MSG_HDR_FMT)
    PKT_HDR_SIZE = struct.calcsize(_PKT_HDR_FMT)

    # Message Header
    destination_address: int
    source_address: int
    subnet: int = 0x01
    send_method: int = 0x01
    send_parameters: int = 0x0000
    source_node_type: int = 0x01

    # Packet Header (Grouped with payload in docs)
    message_type: int = 0x00
    packet_number: int = 0x00
    
    # Payload
    payload: bytes = b""
    
    # Footer
    checksum: int = field(default=0, repr=False)

    @classmethod
    def from_bytes(cls, data: bytes, *, validate_checksum: bool = False) -> Self:
        """Parses raw bytes following the documented segments."""
        if len(data) < (cls.MSG_HDR_SIZE + cls.PKT_HDR_SIZE + 2):
            raise ValueError("Data too short for headers and footer")

        # Unpack Message Header
        m_hdr = struct.unpack(cls._MSG_HDR_FMT, data[:cls.MSG_HDR_SIZE])
        
        # Unpack Packet Header
        p_start = cls.MSG_HDR_SIZE
        p_hdr = struct.unpack(cls._PKT_HDR_FMT, data[p_start : p_start + cls.PKT_HDR_SIZE])
        p_len = p_hdr[2]
        
        # Unpack Payload and Footer
        payload_start = p_start + cls.PKT_HDR_SIZE
        payload_end = payload_start + p_len
        footer_end = payload_end + 2
        
        if len(data) < footer_end:
            raise ValueError(f"Packet truncated: expected {footer_end} bytes")
        payload = data[payload_start:payload_end]
        checksum_bytes = data[payload_end:footer_end]
        checksum = int.from_bytes(checksum_bytes, "little")
        if validate_checksum and not cls._checksum_valid_for_packet(
            data[:payload_end], checksum_bytes
        ):
            raise ValueError(
                "Checksum mismatch for ClimateTalk Fletcher checksum "
                f"(received {checksum_bytes.hex(':')})"
            )

        return cls(
            destination_address=m_hdr[0], source_address=m_hdr[1], subnet=m_hdr[2], send_method=m_hdr[3], send_parameters=m_hdr[4],
            source_node_type=m_hdr[5], message_type=p_hdr[0], packet_number=p_hdr[1],
            payload=payload, checksum=checksum
        )

    @property
    def calculated_checksum(self) -> int:
        """ClimateTalk Fletcher checksum as a 16-bit little-endian value."""
        body = self._body_bytes
        return int.from_bytes(self._calculate_checksum_bytes(body), "little")

    @property
    def checksum_valid(self) -> bool:
        return self._checksum_valid_for_packet(
            self._body_bytes, self.checksum.to_bytes(2, "little")
        )

    @property
    def _body_bytes(self) -> bytes:
        return struct.pack(
            self._MSG_HDR_FMT,
            self.destination_address,
            self.source_address,
            self.subnet,
            self.send_method,
            self.send_parameters,
            self.source_node_type,
        ) + struct.pack(
            self._PKT_HDR_FMT,
            self.message_type,
            self.packet_number,
            len(self.payload),
        ) + self.payload

    @staticmethod
    def _calculate_checksum_bytes(data: bytes) -> bytes:
        """Compute CT-485 Fletcher checksum bytes (low byte first)."""
        sum1 = 0xAA
        sum2 = 0x00
        for byte in data:
            sum1 = (sum1 + byte) % 0xFF
            sum2 = (sum2 + sum1) % 0xFF

        low = (-(sum1 + sum2)) % 0xFF
        high = (-(sum1 + low)) % 0xFF
        return bytes((low, high))

    @staticmethod
    def _checksum_valid_for_packet(data: bytes, checksum_bytes: bytes) -> bool:
        """Validate CT-485 Fletcher checksum over data + checksum bytes."""
        if len(checksum_bytes) != 2:
            return False
        sum1 = 0xAA
        sum2 = 0x00
        for byte in data + checksum_bytes:
            sum1 = (sum1 + byte) % 0xFF
            sum2 = (sum2 + sum1) % 0xFF
        return sum1 == 0 and sum2 == 0

    def to_bytes(self) -> bytes:
        """Serializes segments into a single byte stream."""
        body = self._body_bytes
        checksum = self._calculate_checksum_bytes(body)
        return body + checksum

    def __str__(self) -> str:
        message = MessageRegistry.parse(self.message_type, self.payload)
        payload_message = message
        dataflow_note = ""
        payload_output = payload_message.pretty_format()
        if self._looks_like_r2r_dataflow():
            payload_message = MessageRegistry.parse(0x00, self.payload)
            if self.message_type != 0x00:
                dataflow_note = (
                    "\nDataflow Note: R2R ACK/request-style payload overlay detected "
                    f"while Message Type remains {self.message_type:#04x}"
                )
                inferred_sender_role = (
                    "coordinator"
                    if self.source_node_type == 165 or self.source_address == 255
                    else "subordinate"
                )
                if hasattr(payload_message, "pretty_format_overlay"):
                    payload_output = payload_message.pretty_format_overlay(
                        inferred_sender_role
                    )
            else:
                if hasattr(payload_message, "pretty_format_standard"):
                    payload_output = payload_message.pretty_format_standard()
        else:
            payload_output = payload_message.pretty_format()
        return (
            f"To: {self.destination_address} ({ADDRESS_TYPE_MAP[self.destination_address]})\n"
            f"From: {self.source_address} ({ADDRESS_TYPE_MAP[self.source_address]})\n"
            f"Subnet: {self.subnet} ({SUBNET_MAP[self.subnet]})\n"
            f"Send Method: {self.send_method} ({SEND_METHOD_MAP[self.send_method]})\n"
            f"Send Parameters: {self.send_parameters:#06x} ({decode_send_parameters(self.send_method, self.send_parameters, self.source_node_type)})\n"
            f"Source Node Type: {self.source_node_type} ({NODE_TYPE_MAP[self.source_node_type]})\n"
            f"Message Type: {self.message_type:#04x} ({message.name})\n"
            f"Packet Number: {self.packet_number} ({decode_packet_number(self.packet_number)})\n"
            f"Packet Length: {len(payload_message.data)}"
            f"{dataflow_note}\n"
            f"Payload:\n{tabulate(payload_output)}\n"
            f"Checksum: 0x{self.checksum:04x} "
            f"(valid: {'yes' if self.checksum_valid else 'no'})"
        )

    def _looks_like_r2r_dataflow(self) -> bool:
        if not (self.packet_number & 0x80):
            return False
        if len(self.payload) != 17:
            return False
        return self.payload[:1] in (b"\x00", b"\x06")


def parse_frames(
    data: bytes, *, validate_checksum: bool = False
) -> tuple[list[Frame], list[str]]:
    """Parse one or more back-to-back ClimateTalk frames from a byte stream."""
    frames: list[Frame] = []
    warnings: list[str] = []
    i = 0

    min_frame_size = Frame.MSG_HDR_SIZE + Frame.PKT_HDR_SIZE + 2

    while i < len(data):
        if len(data) - i < min_frame_size:
            warnings.append(
                f"Trailing incomplete bytes at offset {i}: "
                f"{len(data) - i} byte(s) remain"
            )
            break

        packet_header_start = i + Frame.MSG_HDR_SIZE
        payload_len = data[packet_header_start + 2]
        frame_len = min_frame_size + payload_len
        frame_end = i + frame_len

        if frame_end > len(data):
            warnings.append(
                f"Truncated frame at offset {i}: "
                f"declared length {frame_len}, only {len(data) - i} available"
            )
            i += 1
            continue

        frame_bytes = data[i:frame_end]
        try:
            frame = Frame.from_bytes(frame_bytes, validate_checksum=validate_checksum)
            frames.append(frame)
            i = frame_end
        except ValueError as exc:
            # Try to recover by advancing one byte and searching for the next valid frame.
            warnings.append(f"Invalid frame at offset {i}: {exc}")
            i += 1

    return frames, warnings
