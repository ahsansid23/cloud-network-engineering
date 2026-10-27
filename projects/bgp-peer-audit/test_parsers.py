import unittest
from pathlib import Path

from parsers.junos import parse as parse_junos
from parsers.cisco_ios import parse as parse_cisco

ROOT = Path(__file__).parent


class VendorParserTests(unittest.TestCase):
    def test_junos_multiple_peers_and_prefixes(self):
        text = (ROOT / "fixtures/junos-neighbors.txt").read_text(encoding="utf-8")
        data = parse_junos(text, "edge-r1")
        peers = data["devices"][0]["peers"]
        self.assertEqual(len(peers), 2)
        self.assertEqual(peers[0], {"address": "192.0.2.2", "remote_as": 65020,
                                    "state": "Established", "prefixes_received": 120})
        self.assertEqual(peers[1]["state"], "Active")

    def test_cisco_multiple_peers_and_prefixes(self):
        text = (ROOT / "fixtures/cisco-ios-neighbors.txt").read_text(encoding="utf-8")
        peers = parse_cisco(text, "edge-r1")["devices"][0]["peers"]
        self.assertEqual(peers[0]["prefixes_received"], 120)
        self.assertEqual(peers[1]["state"], "Active")
        self.assertEqual(peers[1]["remote_as"], 65030)

    def test_junos_unsupported_input_fails_clearly(self):
        with self.assertRaisesRegex(ValueError, "No supported Junos"):
            parse_junos("not neighbor output", "edge-r1")

    def test_cisco_missing_state_fails_clearly(self):
        with self.assertRaisesRegex(ValueError, "Could not find BGP state"):
            parse_cisco("BGP neighbor is 192.0.2.2, remote AS 65020\n", "edge-r1")


if __name__ == "__main__":
    unittest.main()
