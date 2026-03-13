from enum import Enum


class AddressType(Enum):
    """Address type categories for Daikin HVAC network."""
    BROADCAST = "Broadcast"
    CT1_0_SUBORDINATE = "CT1.0 Subnet 2 Subordinate Address"
    RESERVED_OVERHEAD = "Reserved for Future Use (Overhead Validation)"
    SUBORDINATE_3 = ">CT1.0 Subnet 3 Subordinate Address"
    # RESERVED_OVERHEAD
    RESERVED_INTERNET = "Reserved for Future Use (Internet Access)"
    RESTRICTED_DIAGNOSTIC = "Restricted Address Range (Diagnostic Use)"
    RESERVED_WIRELESS = "Reserved for Future Use (Wireless Address Range)"
    RESTRICTED_NETWORK = "Restricted Address (Network Analysis)"
    RESERVED_AUTHENTICATION = "Reserved for Future Use (System Authentication)"
    RESERVED_BRIDGE_ROUTING = "Reserved for Future Use (Bridge/Routing Address Range)"
    RESERVED_RFD = "Reserved for Future Use (RFD Devices)"
    COORDINATOR_ARBITRATION = "Coordinator Arbitration Address"
    NETWORK_COORDINATOR = "Network Coordinator Address"
    UNKNOWN = "Unknown Address Type"


class AddressMap:
    """Maps RS-485 addresses to their purposes."""
    
    _ADDRESS_RANGES = [
        (0, 0, AddressType.BROADCAST),
        (1, 14, AddressType.CT1_0_SUBORDINATE),
        (15, 15, AddressType.RESERVED_OVERHEAD),
        (16, 62, AddressType.SUBORDINATE_3),
        (63, 63, AddressType.RESERVED_OVERHEAD),
        (64, 84, AddressType.RESERVED_INTERNET),
        (85, 90, AddressType.RESTRICTED_DIAGNOSTIC),
        (91, 191, AddressType.RESERVED_WIRELESS),
        (192, 192, AddressType.RESTRICTED_NETWORK),
        (193, 207, AddressType.RESERVED_AUTHENTICATION),
        (208, 239, AddressType.RESERVED_BRIDGE_ROUTING),
        (240, 253, AddressType.RESERVED_RFD),
        (254, 254, AddressType.COORDINATOR_ARBITRATION),
        (255, 255, AddressType.NETWORK_COORDINATOR),
    ]
    
    @classmethod
    def get_address_type(cls, address: int) -> AddressType:
        """Get the type/purpose of an address."""
        for start, end, addr_type in cls._ADDRESS_RANGES:
            if start <= address <= end:
                return addr_type
        return AddressType.UNKNOWN
    
    @classmethod
    def get_address_description(cls, address: int) -> str:
        """Get a human-readable description of an address."""
        return cls.get_address_type(address).value


class SubnetType(Enum):
    """Subnet type categories for Daikin HVAC network."""
    SUBNET_0 = "All subnets"
    SUBNET_2 = "v1.0 Subordinates"
    SUBNET_3 = ">v1.0 Subordinates"
    RESERVED = "Reserved for future use"

class SubnetMap:
    """Maps subnet numbers to their purposes."""
    
    _SUBNET_DICT = {
        0: SubnetType.SUBNET_0,
        2: SubnetType.SUBNET_2,
        3: SubnetType.SUBNET_3,
    }
    
    @classmethod
    def get_subnet_type(cls, subnet: int) -> SubnetType:
        """Get the type/purpose of a subnet."""
        return cls._SUBNET_DICT.get(subnet, SubnetType.RESERVED)

    @classmethod
    def get_subnet_description(cls, subnet: int) -> str:
        """Get a human-readable description of a subnet."""
        return cls.get_subnet_type(subnet).value


class NodeType(Enum):
    """Node type categories for Daikin HVAC network."""
    UNKNOWN = "Unknown"
    THERMOSTAT = "Thermostat"
    GAS_FURNACE = "Gas Furnace"
    AIR_HANDLER = "Air Handler"
    AIR_CONDITIONER = "Air Conditioner"
    HEAT_PUMP = "Heat Pump"
    ELECTRIC_FURNACE = "Electric Furnace"
    PACKAGE_SYSTEM_GAS = "Package System - Gas"
    PACKAGE_SYSTEM_ELECTRIC = "Package System - Electric"
    CROSSOVER_OBBI = "Crossover (aka OBBI)"
    SECONDARY_COMPRESSOR = "Secondary Compressor"
    AIR_EXCHANGER = "Air Exchanger"
    UNITARY_CONTROL = "Unitary Control"
    DEHUMIDIFIER = "Dehumidifier"
    ELECTRONIC_AIR_CLEANER = "Electronic Air Cleaner"
    ERV = "ERV"
    HUMIDIFIER_EVAPORATIVE = "Humidifier (Evaporative)"
    HUMIDIFIER_STEAM = "Humidifier (Steam)"
    HRV = "HRV"
    IAQ_ANALYZER = "IAQ Analyzer"
    MEDIA_AIR_CLEANER = "Media Air Cleaner"
    ZONE_CONTROL = "Zone Control"
    ZONE_USER_INTERFACE = "Zone User Interface"
    BOILER = "Boiler"
    WATER_HEATER_GAS = "Water Heater - Gas"
    WATER_HEATER_ELECTRIC = "Water Heater - Electric"
    WATER_HEATER_COMMERCIAL = "Water Heater - Commercial"
    POOL_HEATER = "Pool Heater"
    CEILING_FAN = "Ceiling Fan"
    GATEWAY = "Gateway"
    DIAGNOSTIC_DEVICE = "Diagnostic Device"
    LIGHTING_CONTROL = "Lighting Control"
    SECURITY_SYSTEM = "Security System"
    UV_LIGHT = "UV Light"
    WEATHER_DATA_DEVICE = "Weather Data Device"
    WHOLE_HOUSE_FAN = "Whole House Fan"
    SOLAR_INVERTER = "Solar Inverter"
    ZONE_DAMPER = "Zone Damper"
    ZONE_TEMPERATURE_CONTROL = "Zone Temperature Control (ZTC)"
    TEMPERATURE_SENSOR = "Temperature Sensor"
    OCCUPANCY_SENSOR = "Occupancy Sensor"
    NETWORK_COORDINATOR = "Network Coordinator"
    RESERVED = "Reserved"


# NodeMap for lookup and description
class NodeMap:
    """Maps node type values to their descriptions."""
    _NODETYPE_MAP = {
        1: NodeType.THERMOSTAT,
        2: NodeType.GAS_FURNACE,
        3: NodeType.AIR_HANDLER,
        4: NodeType.AIR_CONDITIONER,
        5: NodeType.HEAT_PUMP,
        6: NodeType.ELECTRIC_FURNACE,
        7: NodeType.PACKAGE_SYSTEM_GAS,
        8: NodeType.PACKAGE_SYSTEM_ELECTRIC,
        9: NodeType.CROSSOVER_OBBI,
        10: NodeType.SECONDARY_COMPRESSOR,
        11: NodeType.AIR_EXCHANGER,
        12: NodeType.UNITARY_CONTROL,
        13: NodeType.DEHUMIDIFIER,
        14: NodeType.ELECTRONIC_AIR_CLEANER,
        15: NodeType.ERV,
        16: NodeType.HUMIDIFIER_EVAPORATIVE,
        17: NodeType.HUMIDIFIER_STEAM,
        18: NodeType.HRV,
        19: NodeType.IAQ_ANALYZER,
        20: NodeType.MEDIA_AIR_CLEANER,
        21: NodeType.ZONE_CONTROL,
        22: NodeType.ZONE_USER_INTERFACE,
        23: NodeType.BOILER,
        24: NodeType.WATER_HEATER_GAS,
        25: NodeType.WATER_HEATER_ELECTRIC,
        26: NodeType.WATER_HEATER_COMMERCIAL,
        27: NodeType.POOL_HEATER,
        28: NodeType.CEILING_FAN,
        29: NodeType.GATEWAY,
        30: NodeType.DIAGNOSTIC_DEVICE,
        31: NodeType.LIGHTING_CONTROL,
        32: NodeType.SECURITY_SYSTEM,
        33: NodeType.UV_LIGHT,
        34: NodeType.WEATHER_DATA_DEVICE,
        35: NodeType.WHOLE_HOUSE_FAN,
        36: NodeType.SOLAR_INVERTER,
        37: NodeType.ZONE_DAMPER,
        38: NodeType.ZONE_TEMPERATURE_CONTROL,
        39: NodeType.TEMPERATURE_SENSOR,
        40: NodeType.OCCUPANCY_SENSOR,
        165: NodeType.NETWORK_COORDINATOR,
    }

    @classmethod
    def get_node_type(cls, value: int) -> NodeType:
        return cls._NODETYPE_MAP.get(value, NodeType.RESERVED)

    @classmethod
    def get_node_description(cls, value: int) -> str:
        return cls.get_node_type(value).value


class MessageType(Enum):
    """Message type categories for Daikin HVAC network."""
    GET_CONFIGURATION = "Get Configuration Request"
    GET_CONFIGURATION_RESPONSE = "Get Configuration Response"
    GET_STATUS = "Get Status Request"
    GET_STATUS_RESPONSE = "Get Status Response"
    SET_CONTROL_COMMAND = "Set Control Command"
    SET_CONTROL_COMMAND_RESPONSE = "Set Control Command Response"
    SET_DISPLAY = "Set Display"
    SET_DISPLAY_RESPONSE = "Set Display Response"
    SET_DIAGNOSTICS = "Set Diagnostics"
    SET_DIAGNOSTICS_RESPONSE = "Set Diagnostics Response"
    GET_DIAGNOSTICS = "Get Diagnostics"
    GET_DIAGNOSTICS_RESPONSE = "Get Diagnostics Response"
    GET_SENSOR_DATA = "Get Sensor Data"
    GET_SENSOR_DATA_RESPONSE = "Get Sensor Data Response"
    SET_IDENTIFICATION = "Set Identification"
    SET_IDENTIFICATION_RESPONSE = "Set Identification Response"
    GET_IDENTIFICATION = "Get Identification"
    GET_IDENTIFICATION_RESPONSE = "Get Identification Response"
    SET_APPLICATION = "Application Set Network Shared Data to Network Request"
    SET_APPLICATION_RESPONSE = "Application Set Network Shared Data to Network Response"
    GET_APPLICATION = "Application Get Network Shared Data from Network Request"
    GET_APPLICATION_RESPONSE = "Application Get Network Shared Data from Network Response"
    SET_MANUFACTURER_DEVICE = "Set Manufacturer Device Data"
    SET_MANUFACTURER_DEVICE_RESPONSE = "Set Manufacturer Device Data Response"
    GET_MANUFACTURER_DEVICE = "Get Manufacturer Device Data"
    GET_MANUFACTURER_DEVICE_RESPONSE = "Get Manufacturer Device Data Response"
    SET_NETWORK = "Set Network Node List"
    SET_NETWORK_RESPONSE = "Set Network Node List Response"
    DMA_READ = "Direct Memory Access Read Request"
    DMA_READ_RESPONSE = "Direct Memory Access Read Response"
    UNKNOWN = "Unknown Message Type"


class MessageMap:
    """Maps message type values to their descriptions."""
    _MESSAGETYPE_MAP = {
        0x01: MessageType.GET_CONFIGURATION,
        0x81: MessageType.GET_CONFIGURATION_RESPONSE,
        0x02: MessageType.GET_STATUS,
        0x82: MessageType.GET_STATUS_RESPONSE,
        0x03: MessageType.SET_CONTROL_COMMAND,
        0x83: MessageType.SET_CONTROL_COMMAND_RESPONSE,
        0x04: MessageType.SET_DISPLAY,
        0x84: MessageType.SET_DISPLAY_RESPONSE,
        0x05: MessageType.SET_DIAGNOSTICS,
        0x85: MessageType.SET_DIAGNOSTICS_RESPONSE,
        0x06: MessageType.GET_DIAGNOSTICS,
        0x86: MessageType.GET_DIAGNOSTICS_RESPONSE,
        0x07: MessageType.GET_SENSOR_DATA,
        0x87: MessageType.GET_SENSOR_DATA_RESPONSE,
        0x0D: MessageType.SET_IDENTIFICATION,
        0x8D: MessageType.SET_IDENTIFICATION_RESPONSE,
        0x0E: MessageType.GET_IDENTIFICATION,
        0x8E: MessageType.GET_IDENTIFICATION_RESPONSE,
        0x10: MessageType.SET_APPLICATION,
        0x90: MessageType.SET_APPLICATION_RESPONSE,
        0x11: MessageType.GET_APPLICATION,
        0x91: MessageType.GET_APPLICATION_RESPONSE,
        0x12: MessageType.SET_MANUFACTURER_DEVICE,
        0x92: MessageType.SET_MANUFACTURER_DEVICE_RESPONSE,
        0x13: MessageType.GET_MANUFACTURER_DEVICE,
        0x93: MessageType.GET_MANUFACTURER_DEVICE_RESPONSE,
        0x14: MessageType.SET_NETWORK,
        0x94: MessageType.SET_NETWORK_RESPONSE,
        0x1D: MessageType.DMA_READ,
        0x9D: MessageType.DMA_READ_RESPONSE,
    }

    @classmethod
    def get_message_type(cls, value: int) -> MessageType:
        return cls._MESSAGETYPE_MAP.get(value, MessageType.UNKNOWN)

    @classmethod
    def get_message_description(cls, value: int) -> str:
        return cls.get_message_type(value).value
