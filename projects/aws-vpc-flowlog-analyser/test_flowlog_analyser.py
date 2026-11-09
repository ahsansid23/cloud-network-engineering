import io
import json
import tempfile
import unittest
from pathlib import Path
from contextlib import redirect_stderr, redirect_stdout

from flowlog_analyser import FlowLogParseError, analyse_lines, main, parse_record


SAMPLE = "2 123456789012 eni-0123456789abcdef0 203.0.113.8 10.0.0.8 49152 443 6 4 400 1790000000 1790000060 ACCEPT OK"


class ParseRecordTests(unittest.TestCase):
    def test_parses_ipv4_tcp_record(self):
        record = parse_record(SAMPLE, 1)
        self.assertEqual(record["srcaddr"], "203.0.113.8")
        self.assertEqual(record["protocol"], "tcp")
        self.assertEqual(record["dstport"], 443)
        self.assertEqual(record["bytes"], 400)

    def test_parses_ipv6_and_missing_ports(self):
        line = "2 123456789012 eni-0123456789abcdef0 2001:db8::1 2001:db8::2 - - 58 1 64 1790000000 1790000001 ACCEPT OK"
        record = parse_record(line, 7)
        self.assertEqual(record["srcaddr"], "2001:db8::1")
        self.assertIsNone(record["dstport"])
        self.assertEqual(record["protocol"], "icmpv6")

    def test_skips_nodata_and_skipdata_without_parsing_payload(self):
        line = "2 - - - - - - - - - - - - SKIPDATA"
        self.assertEqual(parse_record(line, 3), {"status": "SKIPDATA"})

    def test_rejects_wrong_field_count(self):
        with self.assertRaisesRegex(FlowLogParseError, "expected 14 fields"):
            parse_record("2 123456789012", 9)

    def test_rejects_custom_or_newer_version(self):
        line = SAMPLE.replace("2 ", "3 ", 1)
        with self.assertRaisesRegex(FlowLogParseError, "only default version 2"):
            parse_record(line, 1)

    def test_rejects_invalid_ip(self):
        line = SAMPLE.replace("203.0.113.8", "not-an-ip")
        with self.assertRaisesRegex(FlowLogParseError, "srcaddr"):
            parse_record(line, 4)

    def test_rejects_port_out_of_range(self):
        line = SAMPLE.replace("49152 443", "49152 70000")
        with self.assertRaisesRegex(FlowLogParseError, "dstport"):
            parse_record(line, 2)

    def test_rejects_end_before_start(self):
        line = SAMPLE.replace("1790000000 1790000060", "1790000060 1790000000")
        with self.assertRaisesRegex(FlowLogParseError, "end must be >= start"):
            parse_record(line, 5)


class AnalysisTests(unittest.TestCase):
    def test_aggregates_actions_sources_ports_and_statuses(self):
        lines = [
            SAMPLE,
            SAMPLE.replace("203.0.113.8", "203.0.113.8").replace("400 179", "600 179"),
            SAMPLE.replace("203.0.113.8", "198.51.100.4").replace("ACCEPT OK", "REJECT OK"),
            "2 - - - - - - - - - - - - SKIPDATA",
        ]
        report = analyse_lines(lines, top_n=2)
        self.assertEqual(report["records_seen"], 4)
        self.assertEqual(report["data_records"], 3)
        self.assertEqual(report["action_counts"], {"ACCEPT": 2, "REJECT": 1})
        self.assertEqual(report["status_counts"], {"OK": 3, "SKIPDATA": 1})
        self.assertEqual(report["top_sources"][0]["address"], "203.0.113.8")
        self.assertEqual(report["top_destination_ports"][0]["port"], 443)
        self.assertEqual(len(report["rejected_flow_examples"]), 1)

    def test_reports_line_number_for_bad_record(self):
        with self.assertRaisesRegex(FlowLogParseError, "line 2"):
            analyse_lines([SAMPLE, "not a flow log"])

    def test_requires_positive_top_n(self):
        with self.assertRaisesRegex(ValueError, "at least 1"):
            analyse_lines([SAMPLE], top_n=0)


class CliTests(unittest.TestCase):
    def test_cli_prints_json(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "flows.txt"
            source.write_text(SAMPLE + "\n", encoding="utf-8")
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                code = main([str(source)])
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(stdout.getvalue())["data_records"], 1)

    def test_cli_refuses_to_overwrite_without_flag(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "flows.txt"
            output = Path(directory) / "report.json"
            source.write_text(SAMPLE + "\n", encoding="utf-8")
            output.write_text("keep me", encoding="utf-8")
            stderr = io.StringIO()
            with redirect_stderr(stderr):
                code = main([str(source), "--output", str(output)])
            self.assertEqual(code, 2)
            self.assertEqual(output.read_text(encoding="utf-8"), "keep me")

    def test_cli_rejects_input_as_output(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "flows.txt"
            source.write_text(SAMPLE + "\n", encoding="utf-8")
            stderr = io.StringIO()
            with redirect_stderr(stderr):
                code = main([str(source), "--output", str(source), "--overwrite"])
            self.assertEqual(code, 2)
            self.assertIn("same as the input", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
