import unittest


def is_dataflow_packet(packet_number: int) -> bool:
    return (packet_number & 0x80) != 0


def subordinate_handles_frame(
    *,
    destination_address: int,
    subnet: int,
    message_type: int,
    packet_number: int,
    identity_address: int,
    identity_subnet: int,
) -> bool:
    if destination_address != identity_address or subnet != identity_subnet:
        return False
    if is_dataflow_packet(packet_number):
        return False
    if message_type == 0x00:  # R2R
        return False
    return 0x01 <= message_type <= 0xDA


class TestSubordinateServiceRoutingContract(unittest.TestCase):
    def test_routes_start_of_application_range(self):
        self.assertTrue(
            subordinate_handles_frame(
                destination_address=0x12,
                subnet=0x03,
                message_type=0x01,
                packet_number=0x00,
                identity_address=0x12,
                identity_subnet=0x03,
            )
        )

    def test_routes_end_of_application_range(self):
        self.assertTrue(
            subordinate_handles_frame(
                destination_address=0x12,
                subnet=0x03,
                message_type=0xDA,
                packet_number=0x00,
                identity_address=0x12,
                identity_subnet=0x03,
            )
        )

    def test_does_not_route_out_of_application_range(self):
        self.assertFalse(
            subordinate_handles_frame(
                destination_address=0x12,
                subnet=0x03,
                message_type=0xDB,
                packet_number=0x00,
                identity_address=0x12,
                identity_subnet=0x03,
            )
        )

    def test_does_not_route_r2r(self):
        self.assertFalse(
            subordinate_handles_frame(
                destination_address=0x12,
                subnet=0x03,
                message_type=0x00,
                packet_number=0x00,
                identity_address=0x12,
                identity_subnet=0x03,
            )
        )

    def test_does_not_route_dataflow(self):
        self.assertFalse(
            subordinate_handles_frame(
                destination_address=0x12,
                subnet=0x03,
                message_type=0x02,
                packet_number=0x80,
                identity_address=0x12,
                identity_subnet=0x03,
            )
        )

    def test_does_not_route_non_local_destination(self):
        self.assertFalse(
            subordinate_handles_frame(
                destination_address=0x13,
                subnet=0x03,
                message_type=0x02,
                packet_number=0x00,
                identity_address=0x12,
                identity_subnet=0x03,
            )
        )


if __name__ == "__main__":
    unittest.main()
