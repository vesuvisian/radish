import unittest

from radish.messages.base import parse_db_id_datagram
from radish.messages.ct_cim import (
    DirectMemoryAccessWriteRequest,
    DirectMemoryAccessWriteResponse,
    GetConfigurationResponse,
    GetIdentificationDataResponse,
    GetManufacturerGenericDataResponse,
    SetManufacturerGenericDataRequest,
    SetIdentificationRequest,
    SetDiagnosticsRequest,
    GetSensorDataResponse,
    SetControlCommandRequest,
    SetControlCommandResponse,
    GetStatusResponse,
)
from radish.messages.registry import MessageRegistry


class TestDbIdDatagramParser(unittest.TestCase):
    def test_parse_valid_multi_record_payload(self):
        payload = bytes.fromhex("00 02 12 34 04 01 AA")
        records, warnings = parse_db_id_datagram(payload)

        self.assertEqual(warnings, [])
        self.assertEqual(len(records), 2)
        self.assertEqual(records[0]["db_id"], 0x00)
        self.assertEqual(records[0]["db_len"], 0x02)
        self.assertEqual(records[0]["value"], bytes.fromhex("12 34"))
        self.assertEqual(records[1]["db_id"], 0x04)
        self.assertEqual(records[1]["db_len"], 0x01)
        self.assertEqual(records[1]["value"], bytes.fromhex("AA"))

    def test_parse_zero_length_record(self):
        payload = bytes.fromhex("09 00 04 01 FF")
        records, warnings = parse_db_id_datagram(payload)

        self.assertEqual(warnings, [])
        self.assertEqual(len(records), 2)
        self.assertEqual(records[0]["db_id"], 0x09)
        self.assertEqual(records[0]["db_len"], 0x00)
        self.assertEqual(records[0]["value"], b"")
        self.assertEqual(records[1]["db_id"], 0x04)
        self.assertEqual(records[1]["db_len"], 0x01)
        self.assertEqual(records[1]["value"], b"\xFF")

    def test_parse_truncated_record_warns(self):
        payload = bytes.fromhex("01 04 AA BB")
        records, warnings = parse_db_id_datagram(payload)

        self.assertEqual(records, [])
        self.assertEqual(len(warnings), 1)
        self.assertIn("Truncated record value", warnings[0])


class TestConfigAndStatusMdiFormatting(unittest.TestCase):
    def test_configuration_response_formats_records(self):
        msg = GetConfigurationResponse(bytes.fromhex("00 01 7F"))
        output = msg.pretty_format()

        self.assertIn("Configuration MDI Record Count: 1", output)
        self.assertIn("Record 1: db_id=0x00, length=1, value=7f", output)
        self.assertIn("Raw Payload: 00:01:7f", output)

    def test_configuration_response_decodes_heat_pump_db_00_table_156(self):
        msg = GetConfigurationResponse(
            bytes.fromhex("00 05 f0 ff 02 01 04"),
            parse_context={"source_node_type": 5},
        )
        output = msg.pretty_format()

        self.assertIn("Source Node Type: 5 (Heat Pump)", output)
        self.assertIn("Configuration: Heat Pump Configuration Data (Table 156)", output)
        self.assertIn("Fan Speeds: Variable/Modulating", output)
        self.assertIn("Heat Stages: Variable/Modulating", output)
        self.assertIn("Cool Stages: Variable/Modulating", output)
        self.assertIn("HVAC Operation: Combo Operation", output)
        self.assertIn("Dehumidification Capable: Yes", output)
        self.assertIn("Nominal Capacity: 2 tons", output)

    def test_configuration_response_decodes_heat_pump_db_01_trim_data(self):
        msg = GetConfigurationResponse(
            bytes.fromhex("01 02 f6 0a"),
            parse_context={"source_node_type": 5},
        )
        output = msg.pretty_format()

        self.assertIn("Record 1: db_id=0x01, length=2, value=f6:0a", output)
        self.assertIn("Configuration: Heat Pump Configuration Trim Data (Table 156)", output)
        self.assertIn("Cool Speed Trim Adjustment: -10%", output)
        self.assertIn("Heat Speed Trim Adjustment: 10%", output)

    def test_configuration_response_decodes_heat_pump_db_02_outdoor_motor_data(self):
        msg = GetConfigurationResponse(
            bytes.fromhex("02 04 09 0c dc 05"),
            parse_context={"source_node_type": 5},
        )
        output = msg.pretty_format()

        self.assertIn("Record 1: db_id=0x02, length=4, value=09:0c:dc:05", output)
        self.assertIn("Configuration: Heat Pump Outdoor Motor Data (Table 156)", output)
        self.assertIn("Outdoor Motor Manufacturer: 9", output)
        self.assertIn("Outdoor Fan Motor Size: 1 HP", output)
        self.assertIn("Outdoor Maximum Airflow: 1500 CFM", output)

    def test_configuration_response_decodes_air_conditioner_db_00_table_155(self):
        msg = GetConfigurationResponse(
            bytes.fromhex("00 05 f0 0f 02 01 04"),
            parse_context={"source_node_type": 4},
        )
        output = msg.pretty_format()

        self.assertIn("Source Node Type: 4 (Air Conditioner)", output)
        self.assertIn(
            "Configuration: Air Conditioner Configuration Data (Table 155)", output
        )
        self.assertIn("Outdoor Fan Speeds: Variable/Modulating", output)
        self.assertIn("Cool Stages: Variable/Modulating", output)
        self.assertIn("HVAC Operation: Combo Operation", output)
        self.assertIn("Dehumidification Capable: Yes", output)
        self.assertIn("Nominal Capacity: 2 tons", output)

    def test_configuration_response_decodes_air_conditioner_db_01_trim_data(self):
        msg = GetConfigurationResponse(
            bytes.fromhex("01 01 f6"),
            parse_context={"source_node_type": 4},
        )
        output = msg.pretty_format()

        self.assertIn("Record 1: db_id=0x01, length=1, value=f6", output)
        self.assertIn(
            "Configuration: Air Conditioner Configuration Trim Data (Table 155)",
            output,
        )
        self.assertIn("Cool Speed Trim Adjustment: -10%", output)

    def test_configuration_response_decodes_air_conditioner_db_02_outdoor_motor_data(self):
        msg = GetConfigurationResponse(
            bytes.fromhex("02 04 09 06 b0 04"),
            parse_context={"source_node_type": 4},
        )
        output = msg.pretty_format()

        self.assertIn("Record 1: db_id=0x02, length=4, value=09:06:b0:04", output)
        self.assertIn(
            "Configuration: Air Conditioner Outdoor Motor Data (Table 155)", output
        )
        self.assertIn("Outdoor Motor Manufacturer: 9", output)
        self.assertIn("Outdoor Fan Motor Size: 1/2 HP", output)
        self.assertIn("Outdoor Maximum Airflow: 1200 CFM", output)

    def test_configuration_response_decodes_air_handler_db_00_table_154(self):
        msg = GetConfigurationResponse(
            bytes.fromhex("00 08 f0 f0 02 07 0c 09 40 06"),
            parse_context={"source_node_type": 3},
        )
        output = msg.pretty_format()

        self.assertIn("Source Node Type: 3 (Air Handler)", output)
        self.assertIn("Configuration: Air Handler Configuration Data (Table 154)", output)
        self.assertIn("Fan Speeds: Variable/Modulating", output)
        self.assertIn("Heat Stages: Variable/Modulating", output)
        self.assertIn("HVAC Operation: Combo Operation", output)
        self.assertIn("Humidification Capable in Cool Mode: Yes", output)
        self.assertIn("Humidification Capable: Yes", output)
        self.assertIn("Dehumidification Capable: Yes", output)
        self.assertIn("Circulator/Blower Motor HP: 1 HP", output)
        self.assertIn("Circulator/Blower Motor Manufacturer: 9", output)
        self.assertIn("Circulator/Blower Maximum Airflow: 1600 CFM", output)

    def test_configuration_response_decodes_air_handler_db_00_max_airflow_little_endian(self):
        msg = GetConfigurationResponse(
            bytes.fromhex("00 08 f0 20 02 02 06 01 a2 03"),
            parse_context={"source_node_type": 3},
        )
        output = msg.pretty_format()

        self.assertIn("Configuration: Air Handler Configuration Data (Table 154)", output)
        self.assertIn("Circulator/Blower Maximum Airflow: 930 CFM", output)

    def test_configuration_response_decodes_air_handler_db_01_trim_data(self):
        msg = GetConfigurationResponse(
            bytes.fromhex("01 06 0a 04 25 64 f6 0a"),
            parse_context={"source_node_type": 3},
        )
        output = msg.pretty_format()

        self.assertIn("Record 1: db_id=0x01, length=6, value=0a:04:25:64:f6:0a", output)
        self.assertIn("Configuration: Air Handler Configuration Trim Data (Table 154)", output)
        self.assertIn("Air Handler Size: 10 kW", output)
        self.assertIn("CFM Per Ton: 4", output)
        self.assertIn("Selected Tonnage (manual): 2.5", output)
        self.assertIn("HEAT CFM: 1000 CFM", output)
        self.assertIn("Cool Speed Trim Adjustment: -10%", output)
        self.assertIn("Heat Speed Trim Adjustment: 10%", output)

    def test_configuration_response_decodes_furnace_db_00_table_153(self):
        msg = GetConfigurationResponse(
            bytes.fromhex("00 09 ff ff 56 07 64 0c 06 40 06"),
            parse_context={"source_node_type": 2},
        )
        output = msg.pretty_format()

        self.assertIn("Source Node Type: 2 (Gas Furnace)", output)
        self.assertIn("Configuration: Furnace Configuration Data (Table 153)", output)
        self.assertIn("Fan Speeds: Variable/Modulating", output)
        self.assertIn("Inducer Stages: Variable/Modulating", output)
        self.assertIn("Heat Stages: Variable/Modulating", output)
        self.assertIn("Cool Stages: Variable/Modulating", output)
        self.assertIn("Pressure Configuration: Pressure Switch", output)
        self.assertIn("Ignition Type: Silicon Carbide", output)
        self.assertIn("Fuel Type: Natural", output)
        self.assertIn("HVAC Operation: Combo Operation", output)
        self.assertIn("Humidification Capable in Cool Mode: Yes", output)
        self.assertIn("Humidification Capable: Yes", output)
        self.assertIn("Dehumidification Capable: Yes", output)
        self.assertIn("Furnace Size: 100 kBTU", output)
        self.assertIn("Circulator/Blower Motor Manufacturer: 12", output)
        self.assertIn("Circulator/Blower Motor Size: 1/2 HP", output)
        self.assertIn("Circulator/Blower Maximum Airflow: 1600 CFM", output)

    def test_configuration_response_decodes_furnace_db_01_trim_data(self):
        msg = GetConfigurationResponse(
            bytes.fromhex("01 05 04 35 5a f6 0a"),
            parse_context={"source_node_type": 2},
        )
        output = msg.pretty_format()

        self.assertIn("Record 1: db_id=0x01, length=5, value=04:35:5a:f6:0a", output)
        self.assertIn("Configuration: Furnace Configuration Trim Data (Table 153)", output)
        self.assertIn("CFM Per Ton: 4", output)
        self.assertIn("Selected Tonnage (manual): 3.5", output)
        self.assertIn("HEAT CFM: 900 CFM", output)
        self.assertIn("Cool Speed Trim Adjustment: -10%", output)
        self.assertIn("Heat Speed Trim Adjustment: 10%", output)

    def test_status_response_formats_warnings(self):
        msg = GetStatusResponse(bytes.fromhex("01 02 FF"))
        output = msg.pretty_format()

        self.assertIn("Parse Warning:", output)
        self.assertIn("Raw Payload: 01:02:ff", output)

    def test_status_response_warns_for_unknown_air_handler_db_01(self):
        msg = GetStatusResponse(
            bytes.fromhex(
                "00 14 00 00 00 00 00 0f 00 00 00 00 00 00 00 00 00 00 00 00 00 00 "
                "01 2b 00 ff ff ff ff 00 00 00 00 76 80 ff ff ff ff 00 00 00 80 00 "
                "80 00 80 00 80 00 80 00 00 00 80 00 80 00 80 00 80 00 80 05 c0 00 00"
            ),
            parse_context={"source_node_type": 3},
        )
        output = msg.pretty_format()

        self.assertIn("Status MDI Record Count: 2", output)
        self.assertIn("Record 2: db_id=0x01, length=43", output)
        self.assertIn(
            "Decode Warning: No Status MDI definition for node type 3 (Air Handler), DB ID 0x01",
            output,
        )

    def test_status_response_decodes_air_handler_db_00_table_162_fields(self):
        msg = GetStatusResponse(
            bytes.fromhex("00 14 00 00 00 00 00 0f 00 00 00 00 00 00 00 00 00 00 00 00 00 00"),
            parse_context={"source_node_type": 3},
        )
        output = msg.pretty_format()

        self.assertIn("Status: Air Handler Status Data (Table 162)", output)
        self.assertIn("Critical Fault: 0", output)
        self.assertIn("Minor Fault: 0", output)
        self.assertIn("Heat Requested Demand: 0.0%", output)
        self.assertIn("Fan Requested Mode: Manual (0)", output)
        self.assertIn("Fan Requested Rate/Slew: 15s", output)
        self.assertIn("Current Airflow: 0 CFM", output)

    def test_status_response_decodes_heat_pump_db_00_fields(self):
        msg = GetStatusResponse(
            bytes.fromhex("00 0C 00 01 02 04 06 08 0A 0C 0E 10 12 14"),
            parse_context={"source_node_type": 5},
        )
        output = msg.pretty_format()

        self.assertIn("Status: Heat Pump Status Data", output)
        self.assertIn("Critical Fault: 0", output)
        self.assertIn("Minor Fault: 1", output)
        self.assertIn("Heat Requested Demand: 1.0%", output)
        self.assertIn("Cool Requested Demand: 2.0%", output)
        self.assertIn("Fan Requested Rate/Slew: 16s", output)
        self.assertIn("Fan Requested Delay: 18s", output)
        self.assertIn("Current Dehumidification Actual Status: 10.0%", output)

    def test_sensor_response_formats_records(self):
        msg = GetSensorDataResponse(bytes.fromhex("39 02 12 34"))
        output = msg.pretty_format()

        self.assertIn("Sensor MDI Record Count: 1", output)
        self.assertIn("db_id=0x39, length=2, value=12:34", output)
        self.assertIn("Raw Payload: 39:02:12:34", output)

    def test_sensor_response_decodes_air_handler_return_air_temperature(self):
        # db_id=0, little-endian value 58:82 -> raw 0x8258:
        # valid=1, sign=0, whole=37, frac=8/16 => 37.5F
        msg = GetSensorDataResponse(
            bytes.fromhex("00 02 58 82"),
            parse_context={"source_node_type": 3},
        )
        output = msg.pretty_format()

        self.assertIn("Source Node Type: 3 (Air Handler)", output)
        self.assertIn("Sensor: Return Air Temperature Sensor", output)
        self.assertIn("Value: 37.5000 degF", output)

    def test_sensor_response_decodes_zone_ui_humidity(self):
        # db_id=1, little-endian value 28:83 -> raw 0x8328:
        # valid=1, reserved=0, whole=50, frac=8/16 => 50.5%RH
        msg = GetSensorDataResponse(
            bytes.fromhex("01 02 28 83"),
            parse_context={"source_node_type": 22},
        )
        output = msg.pretty_format()

        self.assertIn("Source Node Type: 22 (Zone User Interface)", output)
        self.assertIn("Sensor: Relative Humidity Sensor", output)
        self.assertIn("Value: 50.5000 %RH", output)

    def test_sensor_response_warns_when_node_type_map_missing(self):
        msg = GetSensorDataResponse(
            bytes.fromhex("00 02 82 58"),
            parse_context={"source_node_type": 1},
        )
        output = msg.pretty_format()

        self.assertIn("Decode Warning: No Sensor MDI map for source node type 1", output)

    def test_sensor_response_warns_on_length_mismatch(self):
        msg = GetSensorDataResponse(
            bytes.fromhex("00 01 82"),
            parse_context={"source_node_type": 3},
        )
        output = msg.pretty_format()

        self.assertIn("Decode Warning: DB ID 0x00 length mismatch for node type 3", output)

    def test_registry_parse_passes_parse_context_to_message(self):
        msg = MessageRegistry.parse(
            0x87,
            bytes.fromhex("00 02 58 82"),
            parse_context={"source_node_type": 3},
        )
        output = msg.pretty_format()

        self.assertIn("Source Node Type: 3 (Air Handler)", output)

    def test_sensor_response_decodes_heat_pump_outdoor_temperature_example(self):
        # User sample: db_id=0, bytes a1:84 (little-endian) => raw 0x84a1:
        # valid=1, sign=0, whole=74, frac=1/16 => 74.0625F
        msg = GetSensorDataResponse(
            bytes.fromhex("00 02 a1 84"),
            parse_context={"source_node_type": 5},
        )
        output = msg.pretty_format()

        self.assertIn("Source Node Type: 5 (Heat Pump)", output)
        self.assertIn("Sensor: Outdoor Temperature Sensor", output)
        self.assertIn("Value: 74.0625 degF", output)

    def test_sensor_response_shows_potential_decoding_for_air_handler_db_id_02(self):
        msg = GetSensorDataResponse(
            bytes.fromhex("02 14 14 85 61 85 00 00 00 00 00 00 00 00 de 80 00 00 00 00 00 00"),
            parse_context={"source_node_type": 3},
        )
        output = msg.pretty_format()

        self.assertIn(
            "Decode Warning: No Sensor MDI definition for node type 3 (Air Handler), DB ID 0x02",
            output,
        )
        self.assertIn("Potential Decodings (experimental):", output)
        self.assertIn("Liquid Temperature: 81.2500 degF", output)
        self.assertIn("Suction Temperature: 86.0625 degF", output)
        self.assertIn("Pressure Sensor (tentative): 222 PSI", output)

    def test_manufacturer_generic_response_decodes_daikin_subtype_03(self):
        msg = GetManufacturerGenericDataResponse(
            bytes.fromhex("09 00 03 90 09 00 00 01 00")
        )
        output = msg.pretty_format()

        self.assertIn("Manufacturer ID (LE): 0x0009", output)
        self.assertIn("Manufacturer Subtype: 0x03", output)
        self.assertIn("Air Handler Fan Motor RPM: 2448", output)
        self.assertIn("Air Handler EEV Open Rate: 0", output)
        self.assertIn("Unknown Word 3 (LE): 0x0001 (1)", output)

    def test_manufacturer_generic_response_falls_back_for_unknown_shape(self):
        msg = GetManufacturerGenericDataResponse(
            bytes.fromhex("09 00 03 90 09 00 00")
        )
        output = msg.pretty_format()

        self.assertEqual(
            output, "Manufacturer generic response payload: 09:00:03:90:09:00:00"
        )

    def test_manufacturer_generic_response_decodes_daikin_subtype_02_bytes(self):
        msg = GetManufacturerGenericDataResponse(
            bytes.fromhex(
                "09 00 02 00 df 00 ce 00 09 00 e8 03 50 20 0a 00 00 00 02 42 00 00 00 "
                "00 a2 18 85 00 b9 85 21 85 26 85 21 85 fb 80 49 85 b1 05 00 00 00 00 "
                "80 ff ff 7f 00 00 01 00 82 08 00 82"
            )
        )
        output = msg.pretty_format()

        self.assertIn("Manufacturer ID (LE): 0x0009", output)
        self.assertIn("Manufacturer Subtype: 0x02", output)
        self.assertIn("Subtype 0x02 Value Length: 55 byte(s)", output)
        self.assertIn("Byte 00: ctOutdoorFrequencyInPercent = 0x00 (0)", output)
        self.assertIn("Byte 01: Cooling rated power = 0xdf (223)", output)
        self.assertIn("Byte 03: Heating rated power = 0xce (206)", output)
        self.assertIn("Byte 05: Outdoor power = 0x09 (9)", output)
        self.assertIn("Byte 07: ctControlAlgorithmRawDemand? = 0xe8 (232)", output)
        self.assertIn("Byte 10: Unknown = 0x20 (32)", output)
        self.assertIn("Byte 11: Current compressor RPS = 0x0a (10)", output)
        self.assertIn("Byte 12: Compressor current = 0x00 (0)", output)
        self.assertIn("Byte 19: (Target?) OD fan RPM = 0x00 (0)", output)
        self.assertIn("Byte 24: (Target?) OD fan RPM = 0x00 (0)", output)
        self.assertIn("Byte 25: Unknown = 0xb9 (185)", output)
        self.assertIn("Byte 54: Unknown = 0x82 (130)", output)
        self.assertIn("Byte 23: Unknown = 0x85 (133)", output)

    def test_set_manufacturer_generic_request_decodes_daikin_subtype_03(self):
        msg = SetManufacturerGenericDataRequest(
            bytes.fromhex("09 00 03 90 09 00 00 01 00")
        )
        output = msg.pretty_format()

        self.assertIn("Manufacturer ID (LE): 0x0009", output)
        self.assertIn("Manufacturer Subtype: 0x03", output)
        self.assertIn("Air Handler Fan Motor RPM: 2448", output)
        self.assertIn("Air Handler EEV Open Rate: 0", output)
        self.assertIn("Unknown Word 3 (LE): 0x0001 (1)", output)

    def test_set_manufacturer_generic_request_decodes_daikin_subtype_02_bytes(self):
        msg = SetManufacturerGenericDataRequest(
            bytes.fromhex(
                "09 00 02 00 df 00 ce 00 09 00 e8 03 50 20 0a 00 00 00 02 42 00 00 00 "
                "00 a2 18 85 00 b9 85 21 85 26 85 21 85 fb 80 49 85 b1 05 00 00 00 00 "
                "80 ff ff 7f 00 00 01 00 82 08 00 82"
            )
        )
        output = msg.pretty_format()

        self.assertIn("Manufacturer Subtype: 0x02", output)
        self.assertIn("Subtype 0x02 Value Length: 55 byte(s)", output)
        self.assertIn("Byte 00: ctOutdoorFrequencyInPercent = 0x00 (0)", output)


class TestSetControlCommandFormatting(unittest.TestCase):
    def test_set_control_command_decodes_fan_demand_full_payload(self):
        msg = SetControlCommandRequest(bytes.fromhex("66 00 a0 00 32 c8"))
        output = msg.pretty_format()

        self.assertIn("Command Code (LE): 0x0066", output)
        self.assertIn("Command Name: Fan Demand", output)
        self.assertIn("Command Data: a0:00:32:c8", output)
        self.assertIn("Refresh Timer: 0xa0 (10.0000 min, 600.00s;", output)
        self.assertIn("Fan Mode: Manual (0)", output)
        self.assertIn("Fan Demand: 0x32 (25.0%)", output)
        self.assertIn("Fan On/Off Rate: 0xc8 (200)", output)
        self.assertIn("Raw Payload: 66:00:a0:00:32:c8", output)

    def test_set_control_command_decodes_fan_demand_without_optional_rate(self):
        msg = SetControlCommandRequest(bytes.fromhex("66 00 a0 00 32"))
        output = msg.pretty_format()

        self.assertIn("Command Name: Fan Demand", output)
        self.assertIn("Fan On/Off Rate: <not present>", output)

    def test_set_control_command_response_parses_same_as_request(self):
        msg = SetControlCommandResponse(bytes.fromhex("66 00 a0 00 32 c8"))
        output = msg.pretty_format()

        self.assertIn("Command Name: Fan Demand", output)
        self.assertIn("Refresh Timer: 0xa0 (10.0000 min, 600.00s;", output)
        self.assertIn("Fan Mode: Manual (0)", output)
        self.assertIn("Fan Demand: 0x32 (25.0%)", output)
        self.assertIn("Fan On/Off Rate: 0xc8 (200)", output)

    def test_set_control_command_decodes_damper_closure_position_demand(self):
        msg = SetControlCommandRequest(
            bytes.fromhex("60 00 a0 c8 c8 c8 c8 c8 c8 00 00")
        )
        output = msg.pretty_format()

        self.assertIn("Command Code (LE): 0x0060", output)
        self.assertIn("Command Name: Damper Closure Position Demand", output)
        self.assertIn("Command Data: a0:c8:c8:c8:c8:c8:c8:00:00", output)
        self.assertIn("Refresh Timer: 0xa0 (10.0000 min, 600.00s;", output)
        self.assertIn("Damper Closure Position Demand: 0xc8 (100.0%)", output)
        self.assertIn(
            "Damper Closure Position Demand Remaining Bytes: c8:c8:c8:c8:c8:00:00 (unknown)",
            output,
        )

    def test_set_control_command_response_decodes_damper_demand(self):
        msg = SetControlCommandResponse(
            bytes.fromhex("60 00 a0 c8 c8 c8 c8 c8 c8 00 00")
        )
        output = msg.pretty_format()

        self.assertIn("Command Name: Damper Closure Position Demand", output)
        self.assertIn("Refresh Timer: 0xa0 (10.0000 min, 600.00s;", output)
        self.assertIn("Damper Closure Position Demand: 0xc8 (100.0%)", output)

    def test_set_control_command_decodes_cool_demand(self):
        msg = SetControlCommandRequest(bytes.fromhex("65 00 a0 32"))
        output = msg.pretty_format()

        self.assertIn("Command Code (LE): 0x0065", output)
        self.assertIn("Command Name: Cool Demand", output)
        self.assertIn("Command Data: a0:32", output)
        self.assertIn("Refresh Timer: 0xa0 (10.0000 min, 600.00s;", output)
        self.assertIn("Cool Demand: 0x32 (25.0%)", output)

    def test_set_control_command_response_decodes_cool_demand(self):
        msg = SetControlCommandResponse(bytes.fromhex("65 00 a0 32"))
        output = msg.pretty_format()

        self.assertIn("Command Name: Cool Demand", output)
        self.assertIn("Refresh Timer: 0xa0 (10.0000 min, 600.00s;", output)
        self.assertIn("Cool Demand: 0x32 (25.0%)", output)

    def test_set_control_command_decodes_heat_demand(self):
        msg = SetControlCommandRequest(bytes.fromhex("64 00 a0 64"))
        output = msg.pretty_format()

        self.assertIn("Command Name: Heat Demand", output)
        self.assertIn("Refresh Timer: 0xa0 (10.0000 min, 600.00s;", output)
        self.assertIn("Heat Demand: 0x64 (50.0%)", output)

    def test_set_control_command_decodes_humidity_demands(self):
        dehum = SetControlCommandRequest(bytes.fromhex("62 00 81 0a"))
        dehum_output = dehum.pretty_format()
        humid = SetControlCommandRequest(bytes.fromhex("63 00 81 14"))
        humid_output = humid.pretty_format()

        self.assertIn("Command Name: Dehumidification Demand", dehum_output)
        self.assertIn("Dehumidification Demand: 0x0a (5.0%)", dehum_output)
        self.assertIn("Command Name: Humidification Demand", humid_output)
        self.assertIn("Humidification Demand: 0x14 (10.0%)", humid_output)

    def test_set_control_command_decodes_backup_defrost_aux_demands(self):
        backup = SetControlCommandRequest(bytes.fromhex("67 00 90 c8"))
        backup_output = backup.pretty_format()
        defrost = SetControlCommandRequest(bytes.fromhex("68 00 90 32"))
        defrost_output = defrost.pretty_format()
        aux = SetControlCommandRequest(bytes.fromhex("69 00 90 64"))
        aux_output = aux.pretty_format()

        self.assertIn("Command Name: Back-Up Heat Demand", backup_output)
        self.assertIn("Back-Up Heat Demand: 0xc8 (100.0%)", backup_output)
        self.assertIn("Command Name: Defrost Heat Demand", defrost_output)
        self.assertIn("Defrost Heat Demand: 0x32 (25.0%)", defrost_output)
        self.assertIn("Command Name: Aux / Alt Heat Demand", aux_output)
        self.assertIn("Aux / Alt Heat Demand: 0x64 (50.0%)", aux_output)

    def test_set_control_command_decodes_subsystem_busy(self):
        msg = SetControlCommandRequest(bytes.fromhex("61 00 a0 01"))
        output = msg.pretty_format()

        self.assertIn("Command Name: Subsystem Busy Status", output)
        self.assertIn("Refresh Timer: 0xa0 (10.0000 min, 600.00s;", output)
        self.assertIn("Subsystem Busy State: 0x01 (Busy)", output)


class TestDmaWriteFormatting(unittest.TestCase):
    def test_dma_write_request_formats_payload(self):
        msg = DirectMemoryAccessWriteRequest(bytes.fromhex("01 00 10 aa bb cc"))
        output = msg.pretty_format()

        self.assertIn("MDI Code: 0x01 (Configuration)", output)
        self.assertIn("MDI Packet Number: 0x00", output)
        self.assertIn("Start DB ID: 16", output)
        self.assertIn("DB Values (3 byte(s)): aa:bb:cc", output)
        self.assertIn("Raw Payload: 01:00:10:aa:bb:cc", output)

    def test_dma_write_response_formats_ack_or_echo(self):
        ack = DirectMemoryAccessWriteResponse(bytes.fromhex("ac 06")).pretty_format()
        echoed = DirectMemoryAccessWriteResponse(
            bytes.fromhex("01 00 10 aa bb cc")
        ).pretty_format()

        self.assertIn("Confirmation Code: ac:06", ack)
        self.assertIn("ACK: yes", ack)
        self.assertIn("MDI Code: 0x01 (Configuration)", echoed)


class TestSetDiagnosticsFormatting(unittest.TestCase):
    def test_set_diagnostics_request_decodes_fault_message_ascii(self):
        msg = SetDiagnosticsRequest(bytes.fromhex("03 01 02 03 45 31 32"))
        output = msg.pretty_format()

        self.assertIn("Fault Message Length: 3", output)
        self.assertIn("Fault Message: E12", output)
        self.assertIn("Raw Payload: 03:01:02:03:45:31:32", output)

    def test_set_diagnostics_request_zero_length_message_fault_cleared(self):
        msg = SetDiagnosticsRequest(bytes.fromhex("03 01 02 00"))
        output = msg.pretty_format()

        self.assertIn("Fault Message Length: 0 (fault cleared)", output)
        self.assertNotIn("Fault Message:", output)


class TestIdentificationMdiFormatting(unittest.TestCase):
    def test_get_identification_response_decodes_section_7_2_layout(self):
        payload = (
            "09 00 20 01 "
            "56 32 2E 30 00 "
            "52 30 31 00 "
            "53 4E 31 32 33 00 "
            "06 12 13 06 15 13 ff ff ff "
            "31 32 33 20 4d 61 69 6e 00 "
            "39 34 31 30 35 00 "
            "43 6c 69 6d 61 74 65 54 61 6c 6b 00 "
            "4f 6e 65 20 54 6f 75 63 68 00 "
            "44 48 36 56 53 41 32 34 31 30 00 "
            "32 2e 30 00 "
            "52 30 31 00"
        )
        msg = GetIdentificationDataResponse(bytes.fromhex(payload))
        output = msg.pretty_format()

        self.assertIn("Manufacturer ID (LE): 0x0009", output)
        self.assertIn("ClimateTalk Standard Version: 2", output)
        self.assertIn("ClimateTalk Standard Revision: 0", output)
        self.assertIn("Number of Micros: 1", output)
        self.assertIn("Micro 1: sw_version='V2.0', sw_revision='R01', serial='SN123'", output)
        self.assertIn("Date Code (mm/dd/yy): 06/12/13", output)
        self.assertIn("Verification/Test Date (mm/dd/yy): 06/15/13", output)
        self.assertIn("Installation Date (mm/dd/yy): unused (ff/ff/ff)", output)
        self.assertIn("Address: 123 Main", output)
        self.assertIn("Zip Code: 94105", output)
        self.assertIn("Manufacturer: ClimateTalk", output)
        self.assertIn("Control Name: One Touch", output)
        self.assertIn("Model: DH6VSA2410", output)
        self.assertIn("Model Version: 2.0", output)
        self.assertIn("Model Revision: R01", output)

    def test_set_identification_request_decodes_dates_and_ascii_fields(self):
        payload = (
            "06 12 13 06 15 13 ff ff ff "
            "31 32 33 20 4d 61 69 6e 00 "
            "39 34 31 30 35 00 "
            "43 6c 69 6d 61 74 65 54 61 6c 6b 00 "
            "4f 6e 65 20 54 6f 75 63 68 00 "
            "44 48 36 56 53 41 32 34 31 30 00 "
            "32 2e 30 00 "
            "52 30 31 00"
        )
        msg = SetIdentificationRequest(bytes.fromhex(payload))
        output = msg.pretty_format()

        self.assertIn("Date Code (mm/dd/yy): 06/12/13", output)
        self.assertIn("Verification/Test Date (mm/dd/yy): 06/15/13", output)
        self.assertIn("Installation Date (mm/dd/yy): unused (ff/ff/ff)", output)
        self.assertIn("Address: 123 Main", output)
        self.assertIn("Zip Code: 94105", output)
        self.assertIn("Manufacturer: ClimateTalk", output)
        self.assertIn("Control Name: One Touch", output)
        self.assertIn("Model: DH6VSA2410", output)
        self.assertIn("Model Version: 2.0", output)
        self.assertIn("Model Revision: R01", output)

    def test_get_identification_response_partial_payload_collapses_missing_field_warnings(self):
        # Real-world shorter payload that only includes header + one micro triplet.
        msg = GetIdentificationDataResponse(
            bytes.fromhex(
                "09 00 13 01 32 33 30 30 41 30 30 32 00 33 32 00 59 30 30 35 30 36 34 00"
            )
        )
        output = msg.pretty_format()

        self.assertIn("Micro 1: sw_version='2300A002', sw_revision='32', serial='Y005064'", output)
        self.assertIn("Address: missing", output)
        self.assertIn("Model Revision: missing", output)
        self.assertNotIn("Parse Warning: Identification payload ended before trailing", output)
        self.assertNotIn("Parse Warning: address: Missing ASCII field", output)


if __name__ == "__main__":
    unittest.main()
