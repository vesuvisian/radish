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
    _FOOTER_FMT = ">H"
    
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
    def from_bytes(cls, data: bytes) -> Self:
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
        checksum = struct.unpack(cls._FOOTER_FMT, data[payload_end:footer_end])[0]

        return cls(
            destination_address=m_hdr[0], source_address=m_hdr[1], subnet=m_hdr[2], send_method=m_hdr[3], send_parameters=m_hdr[4],
            source_node_type=m_hdr[5], message_type=p_hdr[0], packet_number=p_hdr[1],
            payload=payload, checksum=checksum
        )

    def to_bytes(self) -> bytes:
        """Serializes segments into a single byte stream."""
        # Build headers
        m_hdr = struct.pack(
            self._MSG_HDR_FMT,
            self.destination_address, self.source_address, self.subnet, self.send_method, self.send_parameters, self.source_node_type
        )
        p_hdr = struct.pack(
            self._PKT_HDR_FMT,
            self.message_type, self.packet_number, len(self.payload)
        )
        
        # Combine for checksum calculation
        body = m_hdr + p_hdr + self.payload
        chk = sum(body) & 0xFFFF
        
        return body + struct.pack(self._FOOTER_FMT, chk)

    # def __str__(self) -> str:
    #     msg_logic = MessageRegistry.parse(self.msg_type, self.payload)
    #     return (
    #         f"[{self.src:#04x} -> {self.dst:#04x}] {msg_logic.name}\n"
    #         f"  Route: Method={SEND_METHOD_MAP[self.method]}, Subnet={SUBNET_MAP[self.subnet]}\n"
    #         f"  Node:  Type={NODE_TYPE_MAP[self.node_type]}, Params={self.params:#06x}\n"
    #         f"  Data:  {msg_logic}"
    #     )

    def __str__(self) -> str:
        message = MessageRegistry.parse(self.message_type, self.payload)
        return (
            f"To: {self.destination_address} ({ADDRESS_TYPE_MAP[self.destination_address]})\n"
            f"From: {self.source_address} ({ADDRESS_TYPE_MAP[self.source_address]})\n"
            f"Subnet: {self.subnet} ({SUBNET_MAP[self.subnet]})\n"
            f"Send Method: {self.send_method} ({SEND_METHOD_MAP[self.send_method]})\n"
            f"Send Parameters: {self.send_parameters:#06x} ({decode_send_parameters(self.send_method, self.send_parameters, self.source_node_type)})\n"
            f"Source Node Type: {self.source_node_type} ({NODE_TYPE_MAP[self.source_node_type]})\n"
            f"Message Type: {self.message_type:#04x} ({message.name})\n"
            f"Packet Number: {self.packet_number} ({decode_packet_number(self.packet_number)})\n"
            f"Packet Length: {len(message.data)}\n"
            f"Payload:\n{tabulate(message.pretty_format())}\n"
            f"Checksum: {self.checksum:#06x}"
        )
