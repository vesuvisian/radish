"""
Message registry and base class for Daikin HVAC message types.
Automatically dispatches to the correct message class based on message type byte.
"""

from maps import ADDRESS_TYPE_MAP, NODE_TYPE_MAP, SUBNET_MAP

class MessageRegistry:
    _registry = {}

    @classmethod
    def register(cls, message_type):
        def decorator(subclass):
            cls._registry[message_type] = subclass
            return subclass
        return decorator

    @classmethod
    def get_message_class(cls, message_type):
        return cls._registry.get(message_type, DefaultMessage)

    @classmethod
    def parse(cls, message_type, data):
        msg_cls = cls.get_message_class(message_type)
        return msg_cls.from_bytes(data)


class DefaultMessage:
    def __init__(self, data=None):
        self.data = data

    @property
    def name(self):
        return self.__class__.__name__

    @classmethod
    def from_bytes(cls, data):
        return cls(data)

    def __repr__(self):
        return f"<{self.name} data={self.data!r}>"

# CT-CIM MAPPED MESSAGE REFERENCE
# GET CONFIGURATION - 0X01

@MessageRegistry.register(0x02)
class GetStatusRequest(DefaultMessage):
    name = "Get Status Request"

    def __repr__(self):
        return f"No payload (data={self.data.hex()})"

@MessageRegistry.register(0x82)
class GetStatusResponse(DefaultMessage):
    name = "Get Status Response"

    def __repr__(self):
        return f"Status MDI: {self.data.hex()}"

# SET CONTROL COMMAND - 0X03
# SET DISPLAY MESSAGE - 0X04

@MessageRegistry.register(0x05)
class SetDiagnosticsRequest(DefaultMessage):
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

    def __repr__(self):
        return (
            f"\n\tNode Type: {self.node_type} ({NODE_TYPE_MAP[self.node_type]})\n"
            f"\tMajor Fault Code: {self.major_fault_code}\n"
            f"\tMinor Fault Code: {self.minor_fault_code}\n"
            f"\tFault Message Length: {self.message_length}\n"
            f"\tFault Message: {self.fault_message.hex()}"
        )


@MessageRegistry.register(0x85)
class SetDiagnosticsResponse(DefaultMessage):
    name = "Set Diagnostics Response"

    @property
    def confirmation_code(self):
        return self.data

    def __repr__(self):
        return f"\n\tConfirmation Code: {self.confirmation_code.hex()}"

# GET DIAGNOSTICS - 0X06

@MessageRegistry.register(0x07)
class GetSensorDataRequest(DefaultMessage):
    name = "Get Sensor Data Request"

    def __repr__(self):
        return f"No payload (data={self.data!r})"


@MessageRegistry.register(0x87)
class GetSensorDataResponse(DefaultMessage):
    name = "Get Sensor Data Response"

    def __repr__(self):
        return f"Sensor MDI, per profile spec: {self.data.hex()}"

# SET IDENTIFICATION - 0X0D
# GET IDENTIFICATION - 0X0E
# SET APPLICATION SHARED DATA TO NETWORK - 0X10
# GET APPLICATION SHARED DATA FROM NETWORK - 0X11
# SET MANUFACTURER DEVICE DATA - 0X12
# GET MANUFACTURER DEVICE DATA - 0X13
# SET NETWORK NODE LIST - 0X14
# DIRECT MEMORY ACCESS (DMA) READ - 0X1D
# SET MANUFACTURER GENERIC DATA - 0X1F

@MessageRegistry.register(0x20)
class ManufacturerGenericDataRequest(DefaultMessage):
    name = "Manufacturer Generic Data Request"

@MessageRegistry.register(0xA0)
class ManufacturerGenericDataResponse(DefaultMessage):
    name = "Manufacturer Generic Data Response"

@MessageRegistry.register(0x41)
class GetUserMenuRequest(DefaultMessage):
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

    def __repr__(self):
        return (
            f"\n\tMenu File: {self.menu_file}\n"
            f"\tMain Menu: {self.main_menu}\n"
            f"\tSublevel: {self.sublevel}\n"
            f"\tMax Bytes: {self.max_bytes}\n"
            f"\tDEBUG: {self.data.hex()}"
        )
    
@MessageRegistry.register(0xC1)
class GetUserMenuResponse(GetUserMenuRequest):
    name = "Get User Menu Response"

    @property
    def menu_data(self):
        return self.data[6:]

    def __repr__(self):
        return (
            f"\n\tMenu File: {self.menu_file}\n"
            f"\tMain Menu: {self.main_menu}\n"
            f"\tSublevel: {self.sublevel}\n"
            f"\tMax Bytes: {self.max_bytes}\n"
            f"\tMenu Data: {self.menu_data}\n"
            f"\tDEBUG: {self.data.hex()}"
        )

# SET USER MENU UPDATE - 0X42
# SET FACTORY SHARED DATA TO APPLICATION - 0X43

# CT-485-SPECIFIC MESSAGE TYPES

@MessageRegistry.register(0x00)
class RequestToReceive(DefaultMessage):
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

    def __repr__(self):
        if self.r2r_code == 0x00:
            msg_1 = "Request", "Coordinator"
        elif self.r2r_code == 0x06:
            msg_1 = "ACK", "Subordinate"
        else:
            msg_1 = f"Unknown R2R code (0x{self.r2r_code:02x})", "Unknown"
        msg_2 = f"{msg_1[1]} MAC address: {self.mac_address.hex()}"
        msg_3 = f"Session ID: {self.session_id.hex()}"
        return f"\n\t{msg_1[0]}\n\t{msg_2}\n\t{msg_3}\n\tDEBUG: {self.data.hex()}"


# NETWORK STATE REQUEST - 0X75

@MessageRegistry.register(0x76)
class AddressConfirmationPushRequest(DefaultMessage):
    name = "Address Confirmation Push Request"

    @property
    def internal_node_type(self):
        return self.data[0]

    def __repr__(self):
        ret = f"\n\tCoordinator's virtual internal Subordinate Node Type: {self.internal_node_type} ({NODE_TYPE_MAP[self.internal_node_type]})"
        for i, byte in enumerate(self.data[1:], start=1):
            if byte == 0x00:
                break
            ret += f"\n\tNode type at index {i}: {byte} ({NODE_TYPE_MAP[byte]})"
        return ret

@MessageRegistry.register(0xF6)
class AddressConfirmationPushResponse(AddressConfirmationPushRequest):
    name = "Address Confirmation Push Response"

@MessageRegistry.register(0x77)
class TokenOffer(DefaultMessage):
    name = "Token Offer"

    @property
    def node_id_filter(self):
        return self.data[0]

    def __repr__(self):
        return f"\n\tNode ID Filter: {self.node_id_filter}"

@MessageRegistry.register(0xF7)
class TokenOfferResponse(DefaultMessage):
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
    
    def __repr__(self):
        return (
            f"\n\tAddress: {self.address:#04x} ({ADDRESS_TYPE_MAP[self.address]})\n"
            f"\tSubnet: {self.subnet} ({SUBNET_MAP[self.subnet]})\n"
            f"\tClimateTalk MAC address of addressee: {self.mac_address.hex()}\n"
            f"\tSession ID of addressee: {self.session_id.hex()}"
        )

# VERSION ANNOUNCEMENT - 0X78
# NODE DISCOVERY - 0X79
@MessageRegistry.register(0x79)
class NodeDiscoveryRequest(TokenOffer):
    name = "Node Discovery Request"

@MessageRegistry.register(0xF9)
class NodeDiscoveryResponse(DefaultMessage):
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

    def __repr__(self):
        return (
            f"\n\tNode Type: {self.node_type} ({NODE_TYPE_MAP[self.node_type]})\n"
            f"\tMAC address: {self.mac_address.hex()}\n"
            f"\tSession ID: {self.session_id.hex()}"
        )

# SET ADDRESS - 0X7A
# GET NODE ID - 0X7B
# NETWORK SHARED DATA SECTOR IMAGE READ / WRITE REQUEST - 0X7D
# NETWORK ENCAPSULATION REQUEST - 0X7E

# Usage example:
# msg = MessageRegistry.parse(message_type_byte, data)
# print(msg)
