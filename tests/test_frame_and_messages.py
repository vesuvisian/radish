import unittest

from radish.frame import Frame, parse_frames
from radish.messages import MessageRegistry


class TestFrameParsing(unittest.TestCase):
    def test_frame_round_trip_and_checksum_valid(self):
        frame = Frame(
            destination_address=0x01,
            source_address=0xFF,
            subnet=0x03,
            send_method=0x00,
            send_parameters=0x0000,
            source_node_type=0x01,
            message_type=0x81,
            packet_number=0x00,
            payload=bytes.fromhex("00 01 7F"),
        )

        parsed = Frame.from_bytes(frame.to_bytes())
        self.assertTrue(parsed.checksum_valid)
        self.assertEqual(parsed.message_type, 0x81)
        self.assertEqual(parsed.payload, bytes.fromhex("00 01 7F"))

    def test_frame_checksum_mismatch_raises(self):
        frame = Frame(
            destination_address=0x01,
            source_address=0xFF,
            message_type=0x75,
            payload=b"",
        ).to_bytes()
        bad = frame[:-1] + bytes([frame[-1] ^ 0x01])

        with self.assertRaisesRegex(ValueError, "Checksum mismatch"):
            Frame.from_bytes(bad, validate_checksum=True)

    def test_frame_trailing_bytes_are_ignored_for_backwards_compat(self):
        frame = Frame(
            destination_address=0x01,
            source_address=0xFF,
            message_type=0x75,
            payload=b"",
        ).to_bytes()

        parsed = Frame.from_bytes(frame + b"\x00")
        self.assertEqual(parsed.message_type, 0x75)

    def test_parse_multiple_frames_from_stream(self):
        frame_1 = Frame(
            destination_address=0x01,
            source_address=0xFF,
            message_type=0x75,
            payload=b"",
        ).to_bytes()
        frame_2 = Frame(
            destination_address=0x01,
            source_address=0x02,
            message_type=0x81,
            payload=bytes.fromhex("00 01 7F"),
        ).to_bytes()

        frames, warnings = parse_frames(frame_1 + frame_2)
        self.assertEqual(warnings, [])
        self.assertEqual(len(frames), 2)
        self.assertEqual(frames[0].message_type, 0x75)
        self.assertEqual(frames[1].message_type, 0x81)

    def test_parse_frames_recovers_after_invalid_data(self):
        valid = Frame(
            destination_address=0x01,
            source_address=0x02,
            message_type=0x75,
            payload=b"",
        ).to_bytes()
        corrupted = b"\xAA" + valid[:-1] + bytes([valid[-1] ^ 0x01]) + valid

        frames, warnings = parse_frames(corrupted, validate_checksum=True)
        self.assertEqual(len(frames), 1)
        self.assertEqual(frames[0].message_type, 0x75)
        self.assertTrue(any("Invalid frame" in warning for warning in warnings))

    def test_known_daikin_frame_checksum_validates(self):
        # Captured on a live Daikin CT-485 bus.
        raw = bytes.fromhex(
            "02 ff 02 00 00 00 a5 00 80 11 "
            "00 00 00 09 19 02 0a 40 04 03 04 3c 0c ef f7 ce 84 "
            "cb 51"
        )
        frame = Frame.from_bytes(raw, validate_checksum=True)
        self.assertTrue(frame.checksum_valid)
        self.assertEqual(frame.checksum.to_bytes(2, "little"), bytes.fromhex("cb 51"))

    def test_dataflow_ack_payload_is_decoded_as_r2r(self):
        # Real capture where Message Type is 0x82 but dataflow payload is clearly R2R ACK.
        raw = bytes.fromhex(
            "ff 01 03 02 03 00 01 82 80 11 "
            "06 00 00 09 35 36 66 30 61 01 ec 29 7a ce d9 7f ba "
            "39 17"
        )
        frame = Frame.from_bytes(raw, validate_checksum=True)
        rendered = str(frame)
        self.assertIn("Message Type: 0x82 (Get Status Response)", rendered)
        self.assertIn("Dataflow Note: R2R ACK/request-style payload overlay detected", rendered)
        self.assertIn("R2R Code: ACK", rendered)
        self.assertIn("inferred sender subordinate", rendered)

    def test_true_r2r_keeps_coordinator_subordinate_labels(self):
        # True Message Type 0x00 packet should retain classic coordinator/subordinate labels.
        raw = bytes.fromhex(
            "01 ff 03 00 00 00 a5 00 80 11 "
            "00 00 00 09 19 02 0a 40 04 03 04 3c 0c ef f7 ce 84 "
            "cd 4f"
        )
        frame = Frame.from_bytes(raw, validate_checksum=True)
        rendered = str(frame)
        self.assertIn("Message Type: 0x00 (Request to Receive (R2R))", rendered)
        self.assertIn("Coordinator MAC address: 00:00:09:19:02:0a:40:04", rendered)


class TestAdditionalMessageTypes(unittest.TestCase):
    def test_unknown_message_type_uses_base_message(self):
        msg = MessageRegistry.parse(0x21, bytes.fromhex("34 12 DE AD BE EF"))
        self.assertEqual(msg.name, "Message")
        self.assertEqual(msg.data, bytes.fromhex("34 12 DE AD BE EF"))


if __name__ == "__main__":
    unittest.main()
