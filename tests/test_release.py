import pathlib
import unittest

ROOT = pathlib.Path(__file__).parents[1]


class ReleaseTests(unittest.TestCase):
    def test_required_files(self):
        for path in ["README.md", "SUPPORT.md", "LICENSE", "CHANGELOG.md", "PROJECT_SPEC.md", "install.sh", "run.sh"]:
            self.assertTrue((ROOT/path).is_file(), path)

    def test_addresses_are_exact(self):
        content = (ROOT/"SUPPORT.md").read_text()
        expected = {"bc1qh474jpyw4malh0fmg2uy7n05ggtjvnjtcwhdne", "0x8fcC9C0d1FFCE17b1dEC91B299E56d66BC126Ba8", "D6qp2awRAHVo2VgincTAW5frhnJ9MBZcz4"}
        self.assertEqual({x.split("`",2)[1] for x in content.splitlines() if x.startswith("- ")}, expected)

    def test_no_network_or_broker_module(self):
        sources = "\n".join(p.read_text() for p in (ROOT/"tradecircuitai").rglob("*.py"))
        for forbidden in ["requests", "urllib", "websocket", "ccxt", "alpaca", "binance", "private_key"]:
            self.assertNotIn(forbidden, sources.lower())
