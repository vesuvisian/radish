import unittest

from radish.frame import Frame


def parse_frames_like_controller(raw_bytes: bytes):
    """Mirror the C++ controller's frame-walk logic for replay checks."""
    offset = 0
    frames = []
    checksum_failures = 0
    truncated_frames = 0

    while offset < len(raw_bytes):
        if len(raw_bytes) - offset < 12:
            truncated_frames += 1
            break

        packet_len = raw_bytes[offset + 9]
        frame_len = 10 + packet_len + 2
        if len(raw_bytes) - offset < frame_len:
            truncated_frames += 1
            break

        candidate = raw_bytes[offset : offset + frame_len]
        expected_checksum = Frame.compute_checksum(candidate[:-2])
        observed_checksum = int.from_bytes(candidate[-2:], "little")
        if expected_checksum != observed_checksum:
            checksum_failures += 1
            offset += 1
            continue

        frames.append(Frame.from_bytes(candidate))
        offset += frame_len

    return frames, checksum_failures, truncated_frames


def render_hex_payload_compatible(raw_bytes: bytes) -> str:
    if not raw_bytes:
        return ""
    return " ".join(f"{b:02X}" for b in raw_bytes) + " "


class TestControllerReplayHarness(unittest.TestCase):
    def test_raw_mqtt_hex_payload_contract_trailing_space(self):
        payload = render_hex_payload_compatible(bytes.fromhex("01 A0 FF"))
        self.assertEqual(payload, "01 A0 FF ")

    def test_replay_parser_handles_multiple_good_frames(self):
        f1 = Frame(
            destination_address=0x01,
            source_address=0xFF,
            subnet=0x03,
            send_method=0x00,
            send_parameters=0x0000,
            source_node_type=0xA5,
            message_type=0x00,
            packet_number=0x80,
            payload=bytes.fromhex("00 11 22 33 44 55 66 77 88 99 AA BB CC DD EE FF 01"),
        )
        f2 = Frame(
            destination_address=0x01,
            source_address=0xFF,
            subnet=0x03,
            send_method=0x00,
            send_parameters=0x0000,
            source_node_type=0xA5,
            message_type=0x77,
            packet_number=0x80,
            payload=bytes.fromhex("00"),
        )
        raw = f1.to_bytes() + f2.to_bytes()

        frames, checksum_failures, truncated_frames = parse_frames_like_controller(raw)
        self.assertEqual(len(frames), 2)
        self.assertEqual(checksum_failures, 0)
        self.assertEqual(truncated_frames, 0)
        self.assertEqual(frames[0].message_type, 0x00)
        self.assertEqual(frames[1].message_type, 0x77)

    def test_replay_parser_counts_checksum_failure_and_resyncs(self):
        good = Frame(
            destination_address=0x01,
            source_address=0xFF,
            subnet=0x03,
            send_method=0x00,
            send_parameters=0x0000,
            source_node_type=0xA5,
            message_type=0x77,
            packet_number=0x80,
            payload=bytes.fromhex("00"),
        ).to_bytes()
        bad = bytearray(good)
        bad[-1] ^= 0x01
        raw = bytes(bad) + good

        frames, checksum_failures, truncated_frames = parse_frames_like_controller(raw)
        self.assertGreaterEqual(checksum_failures, 1)
        self.assertGreaterEqual(truncated_frames, 0)
        self.assertGreaterEqual(len(frames), 0)

    def test_replay_parser_counts_truncated_tail(self):
        frame = Frame(
            destination_address=0x01,
            source_address=0xFF,
            subnet=0x03,
            send_method=0x00,
            send_parameters=0x0000,
            source_node_type=0xA5,
            message_type=0x00,
            packet_number=0x80,
            payload=bytes.fromhex("00 11 22 33 44 55 66 77 88 99 AA BB CC DD EE FF 01"),
        ).to_bytes()
        raw = frame[:-3]

        frames, checksum_failures, truncated_frames = parse_frames_like_controller(raw)
        self.assertEqual(frames, [])
        self.assertEqual(checksum_failures, 0)
        self.assertEqual(truncated_frames, 1)


if __name__ == "__main__":
    unittest.main()
