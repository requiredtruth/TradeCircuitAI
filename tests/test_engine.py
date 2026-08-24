import copy
import json
import unittest
from pathlib import Path

from tradecircuitai.core import CircuitError, parse_config
from tradecircuitai.engine import replay, verify

DATA = Path(__file__).parents[1] / "tradecircuitai" / "data"


class EngineTests(unittest.TestCase):
    def setUp(self):
        self.raw = json.loads((DATA / "demo_config.json").read_text())
        self.events = [json.loads(x) for x in (DATA / "demo_events.jsonl").read_text().splitlines() if x.strip()]

    def test_demo_has_fill_and_rejections(self):
        report = replay(parse_config(self.raw), self.events)
        outcomes = [x["outcome"] for x in report["records"]]
        self.assertEqual(outcomes, ["quote_accepted", "paper_fill", "rejected", "halted", "rejected"])
        self.assertEqual(report["records"][2]["details"]["reasons"], ["max_order_units", "max_position_units"])
        self.assertEqual(report["records"][4]["details"]["reasons"], ["manual_halt"])
        self.assertEqual(report["mode"], "paper_only")

    def test_fill_includes_adverse_slippage(self):
        report = replay(parse_config(self.raw), self.events[:2])
        self.assertEqual(report["records"][1]["details"]["fill_price"], "100.05")

    def test_is_deterministic_and_verifiable(self):
        config = parse_config(self.raw)
        one = replay(config, self.events)
        two = replay(config, copy.deepcopy(self.events))
        self.assertEqual(one, two)
        self.assertTrue(verify(config, self.events, one))
        one["final"]["cash"] = "0"
        self.assertFalse(verify(config, self.events, one))

    def test_rejects_stale_quote(self):
        events = self.events[:2]
        events[1]["timestamp"] = "2026-01-01T00:02:00Z"
        report = replay(parse_config(self.raw), events)
        self.assertIn("stale_quote", report["records"][1]["details"]["reasons"])

    def test_rejects_missing_quote(self):
        report = replay(parse_config(self.raw), [self.events[1]])
        self.assertEqual(report["records"][0]["details"]["reasons"], ["missing_quote"])

    def test_rejects_unsorted_symbols(self):
        self.raw["symbols"] = ["Z", "A"]
        with self.assertRaisesRegex(CircuitError, "sorted unique"):
            parse_config(self.raw)

    def test_rejects_time_reversal(self):
        self.events[1]["timestamp"] = self.events[0]["timestamp"]
        with self.assertRaisesRegex(CircuitError, "strictly increase"):
            replay(parse_config(self.raw), self.events[:2])

    def test_rejects_unknown_event_field(self):
        self.events[0]["exchange_key"] = "not accepted"
        with self.assertRaisesRegex(CircuitError, "unexpected"):
            replay(parse_config(self.raw), self.events[:1])
