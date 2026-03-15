class MissingKeyDict(dict):
    """A dictionary that returns a default value for missing keys instead of raising KeyError."""

    def __init__(self, *args, default_value=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.default_value = default_value

    def __getitem__(self, key):
        return super().get(key, self.default_value)


class RangeDict(MissingKeyDict):
    """A dictionary that maps ranges of integers to values, returns default_value if not found."""

    def __getitem__(self, key):
        for (start, end), value in self.items():
            if start <= key <= end:
                return value
        return self.default_value


ADDRESS_TYPE_MAP = RangeDict(
    {
        (0, 0): "Broadcast",
        (1, 14): "CT1.0 Subnet 2 Subordinate Address",
        (15, 15): "Reserved for Future Use (Overhead Validation)",
        (16, 62): ">CT1.0 Subnet 3 Subordinate Address",
        (63, 63): "Reserved for Future Use (Overhead Validation)",
        (64, 84): "Reserved for Future Use (Internet Access)",
        (85, 90): "Restricted Address Range (Diagnostic Use)",
        (91, 191): "Reserved for Future Use (Wireless Address Range)",
        (192, 192): "Restricted Address (Network Analysis)",
        (193, 207): "Reserved for Future Use (System Authentication)",
        (208, 239): "Reserved for Future Use (Bridge/Routing Address Range)",
        (240, 253): "Reserved for Future Use (RFD Devices)",
        (254, 254): "Coordinator Arbitration Address",
        (255, 255): "Network Coordinator Address",
    },
    default_value="Unknown Address Type",
)

SUBNET_MAP = MissingKeyDict(
    {
        0: "All subnets",
        2: "v1.0 Subordinates",
        3: ">v1.0 Subordinates",
    },
    default_value="Reserved for future use",
)

NODE_TYPE_MAP = MissingKeyDict(
    {
        1: "Thermostat",
        2: "Gas Furnace",
        3: "Air Handler",
        4: "Air Conditioner",
        5: "Heat Pump",
        6: "Electric Furnace",
        7: "Package System - Gas",
        8: "Package System - Electric",
        9: "Crossover (aka OBBI)",
        10: "Secondary Compressor",
        11: "Air Exchanger",
        12: "Unitary Control",
        13: "Dehumidifier",
        14: "Electronic Air Cleaner",
        15: "ERV",
        16: "Humidifier (Evaporative)",
        17: "Humidifier (Steam)",
        18: "HRV",
        19: "IAQ Analyzer",
        20: "Media Air Cleaner",
        21: "Zone Control",
        22: "Zone User Interface",
        23: "Boiler",
        24: "Water Heater - Gas",
        25: "Water Heater - Electric",
        26: "Water Heater - Commercial",
        27: "Pool Heater",
        28: "Ceiling Fan",
        29: "Gateway",
        30: "Diagnostic Device",
        31: "Lighting Control",
        32: "Security System",
        33: "UV Light",
        34: "Weather Data Device",
        35: "Whole House Fan",
        36: "Solar Inverter",
        37: "Zone Damper",
        38: "Zone Temperature Control (ZTC)",
        39: "Temperature Sensor",
        40: "Occupancy Sensor",
        165: "Network Coordinator",
    },
    default_value="Reserved",
)


SEND_METHOD_MAP = MissingKeyDict(
    {
        0: "Non-Routed",
        1: "Routing by Priority Control Command Device",
        2: "Routing by Priority Node Type",
        3: "Routing by Socket",
    },
    default_value="Unknown Send Method",
)


def decode_send_parameters(
    send_method: int, send_parameters: int, source_node_type: int
) -> str:
    """Decode send parameters based on the send method."""
    if send_method == 0:  # Non-Routed
        if send_parameters >= 0x0100:
            return "Error: Invalid Non-Routed Send Parameters"
        if source_node_type != 165:  # Not Network Coordinator
            if send_parameters != 0x0000:
                return "Error: Invalid Non-Routed Send Parameters from Non-Coordinator"
            return "Non-Routed Send Parameters from Non-Coordinator"
        return f"Requesting device's index among its node type: {int(send_parameters)}"  # 'Index of Source Node among nodes of its own type'
    elif send_method == 1:  # Routing by Priority Control Command Device
        return "TBD"
    elif send_method == 2:  # Routing by Priority Node Type
        node_type = send_parameters >> 8
        param_2 = send_parameters & 0xFF
        if param_2 != 0x00:
            msg_2 = f"Requesting device's index among its node type: {int(param_2)}"  # 'Index of Source Node among nodes of its own type'
        else:
            msg_2 = "Source node index 0, or initial request to or response from coordinator"
        return f"Targeted node type: {node_type} ({NODE_TYPE_MAP[node_type]}), {msg_2}"
    elif send_method == 3:  # Routing by Socket
        return "TBD"
    else:
        return f"Unknown Send Method (0x{send_parameters:04x})"


def decode_packet_number(packet_number: int) -> str:
    """Decode packet number to determine if it's a request or response and its sequence."""
    if packet_number & 128:  # Check if bit 7 is set
        msg_1 = "Dataflow packet (R2R or ACK);"
    else:
        msg_1 = "Not a dataflow packet;"
    if packet_number & 32:  # Check if bit 5 is set
        msg_2 = "Node discovery request or CT1.0 device"
    else:
        msg_2 = "Not a node discovery request, or is a CT2.0 device"
    return f"{msg_1} {msg_2}"


MESSAGE_TYPE_MAP = MissingKeyDict(
    {
        0x01: "Get Configuration Request",
        0x81: "Get Configuration Response",
        0x02: "Get Status Request",
        0x82: "Get Status Response",
        0x03: "Set Control Command",
        0x83: "Set Control Command Response",
        0x04: "Set Display",
        0x84: "Set Display Response",
        0x05: "Set Diagnostics",
        0x85: "Set Diagnostics Response",
        0x06: "Get Diagnostics",
        0x86: "Get Diagnostics Response",
        0x07: "Get Sensor Data",
        0x87: "Get Sensor Data Response",
        0x0D: "Set Identification",
        0x8D: "Set Identification Response",
        0x0E: "Get Identification",
        0x8E: "Get Identification Response",
        0x10: "Application Set Network Shared Data to Network Request",
        0x90: "Application Set Network Shared Data to Network Response",
        0x11: "Application Get Network Shared Data from Network Request",
        0x91: "Application Get Network Shared Data from Network Response",
        0x12: "Set Manufacturer Device Data",
        0x92: "Set Manufacturer Device Data Response",
        0x13: "Get Manufacturer Device Data",
        0x93: "Get Manufacturer Device Data Response",
        0x14: "Set Network Node List",
        0x94: "Set Network Node List Response",
        0x1D: "Direct Memory Access Request",
        0x9D: "Direct Memory Access Response",
        # CT-485-specific Message Types
        0x00: "Request to Receive (R2R)",
        0x75: "Network State Request",
        0xF5: "Network State Response",
        0x76: "Address Confirmation Push Request",
        0xF6: "Address Confirmation Push Response",
        0x77: "Token Offer",
        0x78: "Version Announcement",
    },
    default_value="Unknown Message Type",
)
