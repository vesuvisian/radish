"""
Message registry and base class for Daikin HVAC message types.
Automatically dispatches to the correct message class based on message type byte.
"""

from .maps import ADDRESS_TYPE_MAP, NODE_TYPE_MAP, SUBNET_MAP
from .utils import tabulate


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
        return cls._registry.get(message_type, Message)

    @classmethod
    def parse(cls, message_type, data):
        msg_cls = cls.get_message_class(message_type)
        return msg_cls.from_bytes(data)


class Message:
    def __init__(self, data=None):
        self.data = data

    @property
    def name(self):
        return self.__class__.__name__

    @classmethod
    def from_bytes(cls, data):
        return cls(data)

    def __repr__(self):
        return f"{self.name}: {self.data.hex(':')}"

    def pretty_format(self, title=False):
        output = self._format_output()
        if title:
            output = f"{self.name}:\n{tabulate(output)}"
        return output

    def _format_output(self):
        return f"{self.data.hex(':')}"


# CT-CIM MAPPED MESSAGE REFERENCE


@MessageRegistry.register(0x01)
class GetConfigurationRequest(Message):
    name = "Get Configuration Request"

    def _format_output(self):
        return f"No payload (data={self.data.hex(':')})"


@MessageRegistry.register(0x81)
class GetConfigurationResponse(Message):
    name = "Get Configuration Response"

    def _format_output(self):
        return f"Configuration MDI: {self.data.hex(':')}"


@MessageRegistry.register(0x02)
class GetStatusRequest(Message):
    name = "Get Status Request"

    def _format_output(self):
        return f"No payload (data={self.data.hex(':')})"


@MessageRegistry.register(0x82)
class GetStatusResponse(Message):
    name = "Get Status Response"

    def _format_output(self):
        return f"Status MDI: {self.data.hex(':')}"


# SET CONTROL COMMAND - 0X03
# SET DISPLAY MESSAGE - 0X04


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


# GET DIAGNOSTICS - 0X06


@MessageRegistry.register(0x07)
class GetSensorDataRequest(Message):
    name = "Get Sensor Data Request"

    def _format_output(self):
        return f"No payload (data={self.data.hex(':')})"


@MessageRegistry.register(0x87)
class GetSensorDataResponse(Message):
    name = "Get Sensor Data Response"

    def _format_output(self):
        return f"Sensor MDI, per profile spec: {self.data.hex(':')}"


# SET IDENTIFICATION - 0X0D


@MessageRegistry.register(0x0E)
class GetIdentificationDataRequest(Message):
    name = "Get Identification Data Request"

    def _format_output(self):
        return f"No payload (data={self.data.hex(':')})"


@MessageRegistry.register(0x8E)
class GetIdentificationDataResponse(Message):
    name = "Get Identification Data Response"

    def _format_output(self):
        return f"Identification MDI: {self.data.hex(':')}"


# SET APPLICATION SHARED DATA TO NETWORK - 0X10
# GET APPLICATION SHARED DATA FROM NETWORK - 0X11
# SET MANUFACTURER DEVICE DATA - 0X12
# GET MANUFACTURER DEVICE DATA - 0X13
# SET NETWORK NODE LIST - 0X14
# DIRECT MEMORY ACCESS (DMA) READ - 0X1D
# SET MANUFACTURER GENERIC DATA - 0X1F


@MessageRegistry.register(0x20)
class ManufacturerGenericDataRequest(Message):
    name = "Manufacturer Generic Data Request"


@MessageRegistry.register(0xA0)
class ManufacturerGenericDataResponse(Message):
    name = "Manufacturer Generic Data Response"


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


# SET USER MENU UPDATE - 0X42
# SET FACTORY SHARED DATA TO APPLICATION - 0X43

# CT-485-SPECIFIC MESSAGE TYPES


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


# NETWORK STATE REQUEST - 0X75


@MessageRegistry.register(0x76)
class AddressConfirmationPushRequest(Message):
    name = "Address Confirmation Push Request"

    @property
    def internal_node_type(self):
        return self.data[0]

    def _format_output(self):
        ret = f"Coordinator's virtual internal Subordinate Node Type: {self.internal_node_type} ({NODE_TYPE_MAP[self.internal_node_type]})"
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


# VERSION ANNOUNCEMENT - 0X78
# NODE DISCOVERY - 0X79
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


# SET ADDRESS - 0X7A
# GET NODE ID - 0X7B
# NETWORK SHARED DATA SECTOR IMAGE READ / WRITE REQUEST - 0X7D
# NETWORK ENCAPSULATION REQUEST - 0X7E

# Usage example:
# msg = MessageRegistry.parse(message_type_byte, data)
# print(msg)
