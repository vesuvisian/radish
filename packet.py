import struct
from dataclasses import dataclass

from maps import ADDRESS_TYPE_MAP, NODE_TYPE_MAP, SUBNET_MAP, SEND_METHOD_MAP, decode_packet_number, decode_send_parameters
from messages import MessageRegistry
from node import Node

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
class Packet:
    """
    Represents a Daikin HVAC RS-485 packet
    """
    destination_address: int
    source_address: int
    subnet: int
    send_method: int
    send_parameters: int  # 2 bytes
    source_node_type: int
    message_type: int
    packet_number: int
    packet_length: int
    payload: bytes
    checksum: int  # 2 bytes
    
    @classmethod
    def from_bytes(cls, data: bytes) -> 'Packet':
        """Parse packet from raw bytes"""
        if len(data) < 12:
            raise ValueError("Packet too short")
        
        packet_length = data[9]
        expected_length = 10 + packet_length + 2  # header + payload + checksum
        
        if len(data) < expected_length:
            raise ValueError(f"Incomplete packet: expected {expected_length}, got {len(data)}")
        
        payload = data[10:10 + packet_length]
        checksum = struct.unpack('>H', data[10 + packet_length:10 + packet_length + 2])[0]
        
        return cls(
            destination_address=data[0],
            source_address=data[1],
            subnet=data[2],
            send_method=data[3],
            send_parameters=struct.unpack('>H', data[4:6])[0],
            source_node_type=data[6],
            message_type=data[7],
            packet_number=data[8],
            packet_length=packet_length,
            payload=payload,
            checksum=checksum
        )
    
    def to_bytes(self) -> bytes:
        """Convert packet to raw bytes"""
        data = bytearray()
        data.append(self.destination_address)
        data.append(self.source_address)
        data.append(self.subnet)
        data.append(self.send_method)
        data.extend(struct.pack('>H', self.send_parameters))
        data.append(self.source_node_type)
        data.append(self.message_type)
        data.append(self.packet_number)
        data.append(self.packet_length)
        data.extend(self.payload)
        data.extend(struct.pack('>H', self.checksum))
        return bytes(data)
    
    def __repr__(self) -> str:
        return (
            f"Packet(dst={self.destination_address:#04x}, src={self.source_address:#04x}, "
            f"type={self.message_type:#04x}, payload_len={self.packet_length})"
        )
    
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
            f"Packet Length: {self.packet_length}\n"
            f"Payload: {message}\n"
            f"Checksum: {self.checksum:#06x}"
        )
