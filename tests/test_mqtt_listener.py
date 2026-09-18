import unittest
from unittest.mock import MagicMock

from radish.frame import Frame
from radish.messages.ct_485 import RequestToReceive

import mqtt_listener


class TestMqttListenerHardening(unittest.TestCase):
    def test_empty_r2r_payload_is_caught_by_listener(self):
        # Empty R2R still raises in the parser; mqtt_listener must survive it.
        frame = Frame(
            destination_address=0x01,
            source_address=0xFF,
            message_type=0x00,
            payload=b"",
        )

        with self.assertRaises(IndexError):
            RequestToReceive(b"").pretty_format_standard()

        outputs, warnings, _ = mqtt_listener.render_raw_frames(frame.to_bytes())
        self.assertEqual(len(outputs), 1)
        self.assertIn("render failed: IndexError", outputs[0])
        self.assertTrue(any("Failed to fully render frame" in w for w in warnings))

    def test_render_raw_frames_survives_corrupt_autonet_shutdown_frame(self):
        # Short garbage payload: parser may raise or partially decode; listener must continue.
        frame = Frame(
            destination_address=0x01,
            source_address=0x03,
            subnet=0x00,
            send_method=0x00,
            send_parameters=0x0100,
            source_node_type=0xF6,
            message_type=0x00,
            packet_number=0x3F,
            payload=b"\x01\x05\x00",
            checksum=0x0000,
        )

        outputs, warnings, _ = mqtt_listener.render_raw_frames(frame.to_bytes())
        self.assertEqual(len(outputs), 1)
        # 3-byte payload still formats via slices; ensure we got some output either way.
        self.assertTrue(outputs[0])

    def test_render_raw_frames_keeps_going_when_pretty_format_raises(self):
        good = Frame(
            destination_address=0x01,
            source_address=0xFF,
            message_type=0x75,
            payload=b"",
        ).to_bytes()
        # Empty Token Offer payload trips node_id_filter = data[0].
        bad = Frame(
            destination_address=0x00,
            source_address=0xFF,
            message_type=0x77,
            payload=b"",
        ).to_bytes()

        outputs, warnings, _ = mqtt_listener.render_raw_frames(good + bad)
        self.assertEqual(len(outputs), 2)
        self.assertTrue(any("render failed" in block for block in outputs))
        self.assertTrue(any("Failed to fully render frame" in w for w in warnings))

    def test_on_message_does_not_raise_on_decode_failure(self):
        userdata = {
            "exclude_dataflow": False,
            "message_types": None,
            "dedupe_repeated": False,
            "last_dedupe_key": None,
        }
        msg = MagicMock()
        msg.topic = "radish/rs485/raw"
        msg.payload = b"abc"  # odd number of hex digits -> ValueError

        mqtt_listener.on_message(MagicMock(), userdata, msg)


if __name__ == "__main__":
    unittest.main()
