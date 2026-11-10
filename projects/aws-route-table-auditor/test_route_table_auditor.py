import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from route_table_auditor import analyse, main


FIXTURE_PATH = Path(__file__).with_name("sample-route-tables.json")


def sample():
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


class RouteTableAuditorTests(unittest.TestCase):
    def test_sample_summary_and_findings(self):
        report = analyse(sample())
        self.assertEqual(report["summary"]["route_table_count"], 3)
        self.assertEqual(report["summary"]["route_count"], 6)
        self.assertEqual(report["summary"]["default_route_count"], 2)
        self.assertEqual(report["summary"]["blackhole_route_count"], 1)
        self.assertEqual(report["summary"]["severity_counts"]["high"], 1)
        self.assertEqual(report["summary"]["severity_counts"]["info"], 1)
        self.assertEqual(
            {finding["code"] for finding in report["findings"]},
            {"blackhole-route", "unassociated-route-table"},
        )

    def test_ipv6_default_route_is_recognised(self):
        document = {"RouteTables": [{
            "RouteTableId": "rtb-v6", "VpcId": "vpc-v6",
            "Routes": [{"DestinationIpv6CidrBlock": "::/0",
                        "EgressOnlyInternetGatewayId": "eigw-example",
                        "State": "active"}],
            "Associations": []
        }]}
        report = analyse(document)
        self.assertEqual(report["summary"]["default_route_count"], 1)
        self.assertEqual(report["route_tables"][0]["default_routes"][0]["destination"], "::/0")

    def test_prefix_list_destination_is_supported(self):
        document = {"RouteTables": [{
            "RouteTableId": "rtb-prefix", "VpcId": "vpc-prefix",
            "Routes": [{"DestinationPrefixListId": "pl-example",
                        "VpcEndpointId": "vpce-example", "State": "active"}],
            "Associations": [{"Main": True, "AssociationState": {"State": "associated"}}]
        }]}
        report = analyse(document)
        self.assertEqual(report["route_tables"][0]["route_count"], 1)
        self.assertEqual(report["findings"], [])

    def test_duplicate_canonical_cidr_is_critical(self):
        document = {"RouteTables": [{
            "RouteTableId": "rtb-dup", "VpcId": "vpc-dup",
            "Routes": [
                {"DestinationCidrBlock": "192.0.2.1/24", "GatewayId": "local", "State": "active"},
                {"DestinationCidrBlock": "192.0.2.0/24", "GatewayId": "local", "State": "active"}
            ],
            "Associations": []
        }]}
        report = analyse(document)
        self.assertIn("duplicate-route-destination", {f["code"] for f in report["findings"]})

    def test_subnet_associated_to_two_route_tables_is_critical(self):
        document = {"RouteTables": []}
        for table_id in ("rtb-a", "rtb-b"):
            document["RouteTables"].append({
                "RouteTableId": table_id, "VpcId": "vpc-a", "Routes": [],
                "Associations": [{
                    "SubnetId": "subnet-shared",
                    "AssociationState": {"State": "associated"}
                }]
            })
        report = analyse(document)
        self.assertIn(
            "subnet-associated-with-multiple-route-tables",
            {f["code"] for f in report["findings"]},
        )

    def test_multiple_active_main_route_tables_are_critical(self):
        document = {"RouteTables": []}
        for table_id in ("rtb-a", "rtb-b"):
            document["RouteTables"].append({
                "RouteTableId": table_id, "VpcId": "vpc-a", "Routes": [],
                "Associations": [{
                    "Main": True, "AssociationState": {"State": "associated"}
                }]
            })
        report = analyse(document)
        self.assertIn("multiple-main-route-tables", {f["code"] for f in report["findings"]})

    def test_invalid_route_destination_is_reported(self):
        document = {"RouteTables": [{
            "RouteTableId": "rtb-invalid", "VpcId": "vpc-invalid",
            "Routes": [{"DestinationCidrBlock": "not-a-cidr", "GatewayId": "local",
                        "State": "active"}],
            "Associations": []
        }]}
        report = analyse(document)
        self.assertIn("invalid-route-destination", {f["code"] for f in report["findings"]})

    def test_non_active_subnet_association_is_reported(self):
        document = {"RouteTables": [{
            "RouteTableId": "rtb-pending", "VpcId": "vpc-pending", "Routes": [],
            "Associations": [{
                "SubnetId": "subnet-pending",
                "AssociationState": {"State": "associating"}
            }]
        }]}
        report = analyse(document)
        self.assertIn("subnet-association-not-active", {f["code"] for f in report["findings"]})

    def test_non_object_and_missing_route_tables_are_rejected(self):
        with self.assertRaises(ValueError):
            analyse([])
        with self.assertRaises(ValueError):
            analyse({})

    def test_bad_route_table_shape_is_rejected(self):
        with self.assertRaises(ValueError):
            analyse({"RouteTables": [{"VpcId": "vpc-missing-id"}]})

    def test_cli_stdout_is_valid_json(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = main([str(FIXTURE_PATH)])
        self.assertEqual(result, 0)
        parsed = json.loads(output.getvalue())
        self.assertEqual(parsed["summary"]["route_table_count"], 3)

    def test_cli_refuses_existing_output_without_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "report.json"
            target.write_text("keep me", encoding="utf-8")
            errors = io.StringIO()
            with contextlib.redirect_stderr(errors):
                result = main([str(FIXTURE_PATH), "--output", str(target)])
            self.assertEqual(result, 2)
            self.assertEqual(target.read_text(encoding="utf-8"), "keep me")

    def test_cli_overwrite_requires_explicit_flag(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "report.json"
            target.write_text("old", encoding="utf-8")
            result = main([str(FIXTURE_PATH), "--output", str(target), "--overwrite"])
            self.assertEqual(result, 0)
            self.assertEqual(json.loads(target.read_text(encoding="utf-8"))["summary"]["route_table_count"], 3)

    def test_cli_refuses_to_replace_input(self):
        with contextlib.redirect_stderr(io.StringIO()):
            result = main([str(FIXTURE_PATH), "--output", str(FIXTURE_PATH), "--overwrite"])
        self.assertEqual(result, 2)


if __name__ == "__main__":
    unittest.main()
