from typing import Optional

from maps import ADDRESS_TYPE_MAP

class Node:
    """Represents a node on the Daikin HVAC network."""
    
    def __init__(self, address: int, name: Optional[str] = None):
        self.address = address
        self.name = name or f"Node_{address:#04x}"
        self.address_type = ADDRESS_TYPE_MAP[address]
    
    def __repr__(self) -> str:
        return f"Node({self.name}, {self.address:#04x})"
    
    def __str__(self) -> str:
        return f"{self.name} ({ADDRESS_TYPE_MAP[self.address]})"
