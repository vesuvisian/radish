import unittest
from dataclasses import dataclass


def derive_ct_mac_from_wifi(sta_mac: bytes) -> bytes:
    if len(sta_mac) != 6:
        raise ValueError("STA MAC must be 6 bytes")
    return bytes([0x00, 0x00, 0x09, sta_mac[1], sta_mac[2], sta_mac[3], sta_mac[4], sta_mac[5]])


@dataclass
class SimAutoNet:
    node_type: int = 39
    state: str = "UNADDRESSED"
    slot_due_ms: int = 0
    keepalive_timeout_ms: int = 120_000
    last_addr_conf_ms: int = 0

    def on_node_discovery(self, now_ms: int, slot_delay_ms: int, filter_value: int) -> bool:
        if self.state != "UNADDRESSED":
            return False
        if filter_value not in (0x00, self.node_type):
            return False
        self.state = "AWAITING_SLOT_DELAY_FOR_DISCOVERY_RESPONSE"
        self.slot_due_ms = now_ms + slot_delay_ms
        return True

    def on_bus_activity(self):
        if self.state == "AWAITING_SLOT_DELAY_FOR_DISCOVERY_RESPONSE":
            self.state = "UNADDRESSED"

    def on_tick(self, now_ms: int) -> bool:
        if self.state == "AWAITING_SLOT_DELAY_FOR_DISCOVERY_RESPONSE" and now_ms >= self.slot_due_ms:
            self.state = "AWAITING_SET_ADDRESS"
            return True
        if (
            self.state == "ADDRESSED_ACTIVE"
            and self.last_addr_conf_ms > 0
            and (now_ms - self.last_addr_conf_ms) >= self.keepalive_timeout_ms
        ):
            self.state = "UNADDRESSED"
            return False
        return False

    def on_set_address(self, addr: int, subnet: int, write_enabled: bool, mac_match: bool, session_match: bool) -> bool:
        if not write_enabled or not mac_match or not session_match:
            return False
        if addr == 0 and subnet == 0:
            self.state = "UNADDRESSED"
            return True
        self.state = "ADDRESSED_ACTIVE"
        return True

    def on_address_confirmation(self, now_ms: int, node_list_byte: int) -> bool:
        self.last_addr_conf_ms = now_ms
        if self.state == "ADDRESSED_ACTIVE" and node_list_byte != self.node_type:
            self.state = "UNADDRESSED"
            return False
        return True


class TestAutoNetClientContract(unittest.TestCase):
    def test_mac_derivation_has_required_prefix_and_length(self):
        mac = derive_ct_mac_from_wifi(bytes.fromhex("A4 CF 12 34 56 78"))
        self.assertEqual(len(mac), 8)
        self.assertEqual(mac[:3], bytes.fromhex("00 00 09"))
        self.assertEqual(mac.hex(":"), "00:00:09:cf:12:34:56:78")

    def test_node_discovery_slot_delay_and_emit(self):
        sim = SimAutoNet()
        started = sim.on_node_discovery(now_ms=1000, slot_delay_ms=250, filter_value=39)
        self.assertTrue(started)
        self.assertEqual(sim.state, "AWAITING_SLOT_DELAY_FOR_DISCOVERY_RESPONSE")
        emitted = sim.on_tick(now_ms=1249)
        self.assertFalse(emitted)
        emitted = sim.on_tick(now_ms=1250)
        self.assertTrue(emitted)
        self.assertEqual(sim.state, "AWAITING_SET_ADDRESS")

    def test_discovery_response_aborted_if_bus_activity_seen(self):
        sim = SimAutoNet()
        sim.on_node_discovery(now_ms=1000, slot_delay_ms=250, filter_value=0)
        sim.on_bus_activity()
        emitted = sim.on_tick(now_ms=1300)
        self.assertFalse(emitted)
        self.assertEqual(sim.state, "UNADDRESSED")

    def test_set_address_accepts_and_transitions(self):
        sim = SimAutoNet(state="AWAITING_SET_ADDRESS")
        accepted = sim.on_set_address(addr=0x12, subnet=0x03, write_enabled=True, mac_match=True, session_match=True)
        self.assertTrue(accepted)
        self.assertEqual(sim.state, "ADDRESSED_ACTIVE")

    def test_set_address_00_relinquishes(self):
        sim = SimAutoNet(state="AWAITING_SET_ADDRESS")
        accepted = sim.on_set_address(addr=0x00, subnet=0x00, write_enabled=True, mac_match=True, session_match=True)
        self.assertTrue(accepted)
        self.assertEqual(sim.state, "UNADDRESSED")

    def test_keepalive_timeout_relinquishes(self):
        sim = SimAutoNet(state="ADDRESSED_ACTIVE", keepalive_timeout_ms=120_000, last_addr_conf_ms=10_000)
        sim.on_tick(now_ms=130_000)
        self.assertEqual(sim.state, "UNADDRESSED")

    def test_address_confirmation_mismatch_relinquishes(self):
        sim = SimAutoNet(state="ADDRESSED_ACTIVE", node_type=39)
        valid = sim.on_address_confirmation(now_ms=5000, node_list_byte=5)
        self.assertFalse(valid)
        self.assertEqual(sim.state, "UNADDRESSED")


if __name__ == "__main__":
    unittest.main()
