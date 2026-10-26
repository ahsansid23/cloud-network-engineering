import unittest
from report import audit_snapshot


def snapshot(peer):
    return {"devices": [{"name": "edge-r1", "peers": [peer]}]}


class AuditSnapshotTests(unittest.TestCase):
    def test_healthy_peer_passes(self):
        rows = audit_snapshot(snapshot({
            "address": "192.0.2.2", "remote_as": 65020, "state": "Established",
            "prefixes_received": 120, "min_prefixes": 100, "max_prefixes": 150,
        }))
        self.assertEqual(rows[0]["status"], "PASS")

    def test_non_established_peer_fails(self):
        rows = audit_snapshot(snapshot({
            "address": "192.0.2.2", "remote_as": 65020, "state": "Idle",
        }))
        self.assertEqual(rows[0]["status"], "FAIL")
        self.assertIn("expected Established", rows[0]["findings"])

    def test_prefix_below_minimum_fails(self):
        rows = audit_snapshot(snapshot({
            "address": "192.0.2.2", "remote_as": 65020, "state": "Established",
            "prefixes_received": 20, "min_prefixes": 50,
        }))
        self.assertEqual(rows[0]["status"], "FAIL")

    def test_missing_prefix_count_warns(self):
        rows = audit_snapshot(snapshot({
            "address": "192.0.2.2", "remote_as": 65020, "state": "Established",
            "min_prefixes": 50,
        }))
        self.assertEqual(rows[0]["status"], "WARN")

    def test_invalid_thresholds_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "cannot exceed"):
            audit_snapshot(snapshot({
                "address": "192.0.2.2", "remote_as": 65020, "state": "Established",
                "min_prefixes": 100, "max_prefixes": 50,
            }))

    def test_duplicate_peer_address_is_rejected(self):
        payload = snapshot({"address": "192.0.2.2", "remote_as": 65020,
                            "state": "Established"})
        payload["devices"][0]["peers"].append({
            "address": "192.0.2.2", "remote_as": 65030, "state": "Established"})
        with self.assertRaisesRegex(ValueError, "duplicate peer address"):
            audit_snapshot(payload)


if __name__ == "__main__":
    unittest.main()
