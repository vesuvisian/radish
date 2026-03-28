import unittest

from radish.messages.base import parse_db_id_datagram
from radish.messages.ct_cim import GetConfigurationResponse, GetStatusResponse


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
        self.assertIn("db_id=0x00, length=1, value=7f", output)
        self.assertIn("Raw Payload: 00:01:7f", output)

    def test_status_response_formats_warnings(self):
        msg = GetStatusResponse(bytes.fromhex("01 02 FF"))
        output = msg.pretty_format()

        self.assertIn("Status MDI Record Count: 0", output)
        self.assertIn("Parse Warning:", output)
        self.assertIn("Raw Payload: 01:02:ff", output)


if __name__ == "__main__":
    unittest.main()
