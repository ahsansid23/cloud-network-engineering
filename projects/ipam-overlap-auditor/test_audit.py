import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from audit import audit_rows, load_inventory

ROOT = Path(__file__).parent


def row(name, site, vrf, cidr):
    return {"network_name": name, "site": site, "vrf": vrf, "cidr": cidr}


class IpamAuditTests(unittest.TestCase):
    def test_disjoint_networks_pass(self):
        self.assertEqual(audit_rows([
            row("a", "dc1", "default", "10.0.0.0/24"),
            row("b", "dc1", "default", "10.0.1.0/24"),
        ]), [])

    def test_containment_is_reported(self):
        findings = audit_rows([
            row("summary", "dc1", "default", "10.0.0.0/16"),
            row("subnet", "dc1", "default", "10.0.2.0/24"),
        ])
        self.assertEqual([item["code"] for item in findings], ["CONTAINED_NETWORK"])

    def test_identical_network_is_duplicate(self):
        findings = audit_rows([
            row("a", "dc1", "default", "192.0.2.0/24"),
            row("b", "dc1", "default", "192.0.2.0/24"),
        ])
        self.assertEqual(findings[0]["code"], "DUPLICATE_NETWORK")

    def test_different_sites_or_vrfs_are_separate_scopes(self):
        self.assertEqual(audit_rows([
            row("a", "dc1", "default", "10.0.0.0/24"),
            row("b", "dc1", "guest", "10.0.0.0/24"),
            row("c", "dc2", "default", "10.0.0.0/24"),
        ]), [])

    def test_ipv4_and_ipv6_are_not_cross_compared(self):
        self.assertEqual(audit_rows([
            row("v4", "dc1", "default", "10.0.0.0/24"),
            row("v6", "dc1", "default", "2001:db8::/64"),
        ]), [])

    def test_invalid_cidr_is_reported(self):
        findings = audit_rows([row("bad", "dc1", "default", "10.0.0.5/24")])
        self.assertEqual(findings[0]["code"], "INVALID_CIDR")

    def test_missing_required_value_is_reported(self):
        findings = audit_rows([{
            "network_name": "no-scope", "site": "dc1", "vrf": "", "cidr": "10.0.0.0/24"
        }])
        self.assertEqual(findings[0]["code"], "MISSING_FIELD")

    def test_csv_header_is_validated(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.csv"
            path.write_text("name,cidr" + chr(10) + "a,10.0.0.0/24" + chr(10), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "missing required columns"):
                load_inventory(path)

    def test_sample_cli_reports_findings(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "audit.py"), str(ROOT / "inventory.csv"), "--format", "json"],
            capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 1)
        self.assertIn('"finding_count": 2', result.stdout)


if __name__ == "__main__":
    unittest.main()
