import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path

from tradecircuitai.cli import main

DATA = Path(__file__).parents[1] / "tradecircuitai" / "data"


class CliTests(unittest.TestCase):
    def test_replay_and_verify(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = str(Path(tmp) / "report.json")
            args = [str(DATA/"demo_config.json"), str(DATA/"demo_events.jsonl")]
            self.assertEqual(main(["replay", *args, "--output", report]), 0)
            output = StringIO()
            with redirect_stdout(output): self.assertEqual(main(["verify", *args, report]), 0)
            self.assertIn("verified", output.getvalue())

    def test_tampering_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = Path(tmp) / "report.json"
            args = [str(DATA/"demo_config.json"), str(DATA/"demo_events.jsonl")]
            main(["replay", *args, "--output", str(report)])
            raw = json.loads(report.read_text()); raw["audit_head"] = "0" * 64; report.write_text(json.dumps(raw))
            errors = StringIO()
            with redirect_stderr(errors): self.assertEqual(main(["verify", *args, str(report)]), 2)
            self.assertIn("does not match", errors.getvalue())
