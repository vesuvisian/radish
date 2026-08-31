import unittest

from radish.messages.ct_cim import GetUserMenuResponse
from radish.messages.user_menu import decode_user_menu_payload


class TestUserMenuDecoder(unittest.TestCase):
    def test_decode_user_menu_payload(self):
        menu_data = (
            b"\xb6SYS SETUP1\xb7"
            b"\xc2\xe1BOOST MD\xe0OFF\xe8ON\xc3"
            b"\xc2\xe1BOOST TEMP\xe0Always ON\xe870\xe075F\xc3"
        )
        decoded = decode_user_menu_payload(menu_data)

        self.assertEqual(decoded["title"], "SYS SETUP1")
        self.assertEqual(len(decoded["items"]), 2)
        self.assertEqual(decoded["items"][0]["label"], "BOOST MD")
        self.assertEqual(decoded["items"][0]["options"], ["OFF", "ON"])
        self.assertEqual(decoded["items"][0]["selected_option"], "ON")
        self.assertEqual(decoded["items"][1]["label"], "BOOST TEMP")
        self.assertEqual(decoded["items"][1]["selected_option"], "70")
        self.assertEqual(decoded["warnings"], [])

    def test_get_user_menu_response_formats_decoded_items(self):
        payload = (
            b"\x01\x04\x00\x00\x00\xf0"
            b"\xb6SYS SETUP1\xb7"
            b"\xc2\xe1BOOST MD\xe0OFF\xe8ON\xc3"
        )
        msg = GetUserMenuResponse(payload)
        output = msg.pretty_format()

        self.assertIn("Menu Title: SYS SETUP1", output)
        self.assertIn("Menu Item Count: 1", output)
        self.assertIn("Item 1: BOOST MD", output)
        self.assertIn("Options: OFF, ON", output)
        self.assertIn("Selected: ON", output)

    def test_get_user_menu_response_omits_selected_when_none(self):
        payload = (
            b"\x01\x03\x00\x00\x00\xf0"
            b"\xb6STATUS\xb7"
            b"\xc2\xe2TS\xe0 1457 hr\xc3"
        )
        msg = GetUserMenuResponse(payload)
        output = msg.pretty_format()

        self.assertIn("Item 1: TS", output)
        self.assertIn("Options: 1457 hr", output)
        self.assertNotIn("Selected:", output)

    def test_decode_diag_fault_items_with_e2_label_token(self):
        menu_data = bytes.fromhex(
            "b6 44 49 41 47 b7 "
            "c2 e2 46 41 55 4c 54 20 23 31 e0 45 37 37 c3 "
            "c2 e2 46 41 55 4c 54 20 23 32 e0 45 37 37 c3 "
            "c2 e2 46 41 55 4c 54 20 23 33 e0 45 45 35 c3 "
            "c2 e1 43 4c 45 41 52 e8 4e 4f e0 59 45 53 c3"
        )
        decoded = decode_user_menu_payload(menu_data)

        self.assertEqual(decoded["title"], "DIAG")
        self.assertEqual(len(decoded["items"]), 4)
        self.assertEqual(decoded["items"][0]["label"], "FAULT #1")
        self.assertEqual(decoded["items"][0]["options"], ["E77"])
        self.assertEqual(decoded["items"][2]["label"], "FAULT #3")
        self.assertEqual(decoded["items"][2]["options"], ["EE5"])
        self.assertEqual(decoded["items"][3]["label"], "CLEAR")
        self.assertEqual(decoded["items"][3]["selected_option"], "NO")
        self.assertEqual(decoded["warnings"], [])

    def test_decode_directory_variant_titles(self):
        menu_data = bytes.fromhex(
            "a0 a6 "
            "b6 43 4f 4e 46 49 47 b7 "
            "b6 44 49 41 47 b7 "
            "b6 53 54 41 54 55 53 b7 "
            "b6 53 59 53 20 53 45 54 55 50 31 b7"
        )
        decoded = decode_user_menu_payload(menu_data)
        self.assertEqual(decoded["title"], None)
        self.assertEqual(decoded["items"], [])
        self.assertEqual(
            decoded["directory_entries"],
            ["CONFIG", "DIAG", "STATUS", "SYS SETUP1"],
        )

    def test_get_user_menu_response_formats_directory_variant(self):
        payload = bytes.fromhex(
            "01 00 00 00 00 f0 "
            "a0 a6 "
            "b6 43 4f 4e 46 49 47 b7 "
            "b6 44 49 41 47 b7 "
            "b6 53 54 41 54 55 53 b7"
        )
        msg = GetUserMenuResponse(payload)
        output = msg.pretty_format()
        self.assertIn("Menu Item Count: 0", output)
        self.assertIn("Menu Directory Count: 3", output)
        self.assertIn("Directory Entry 1: CONFIG", output)
        self.assertIn("Directory Entry 2: DIAG", output)
        self.assertIn("Directory Entry 3: STATUS", output)

    def test_ignores_empty_noise_item_and_extra_c3_delimiters(self):
        menu_data = bytes.fromhex(
            "b6 53 45 54 55 50 b7 "
            "c2 e1 41 43 43 e0 48 55 4d e8 4e 4f 4e 45 c3 "
            "c3 "
            "c2 e1 20 e0 20 e8 20 e0 20 c3 "
            "c2 e1 48 54 20 4b 49 54 e8 4e 4f 4e 45 e0 33 c3"
        )
        decoded = decode_user_menu_payload(menu_data)
        self.assertEqual(decoded["title"], "SETUP")
        self.assertEqual(len(decoded["items"]), 2)
        self.assertEqual(decoded["items"][0]["label"], "ACC")
        self.assertEqual(decoded["items"][1]["label"], "HT KIT")
        self.assertEqual(decoded["warnings"], [])

    def test_accepts_implicit_item_termination_before_next_item(self):
        # First item has no c3 before next c2.
        menu_data = bytes.fromhex(
            "b6 44 49 41 47 b7 "
            "c2 e2 46 41 55 4c 54 31 e0 45 37 37 "
            "c2 e2 46 41 55 4c 54 32 e0 45 45 35 c3"
        )
        decoded = decode_user_menu_payload(menu_data)
        self.assertEqual(len(decoded["items"]), 2)
        self.assertEqual(decoded["items"][0]["label"], "FAULT1")
        self.assertEqual(decoded["items"][0]["options"], ["E77"])
        self.assertEqual(decoded["items"][1]["label"], "FAULT2")
        self.assertEqual(decoded["items"][1]["options"], ["EE5"])
        self.assertEqual(decoded["warnings"], [])


if __name__ == "__main__":
    unittest.main()
