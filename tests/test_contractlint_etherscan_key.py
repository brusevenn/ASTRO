import sys
import unittest
from pathlib import Path
from unittest.mock import patch


REPO = Path(__file__).resolve().parents[1]
ASTRO_ROOT = REPO / "astro"
for import_root in (ASTRO_ROOT, ASTRO_ROOT / "analysis"):
    if str(import_root) not in sys.path:
        sys.path.insert(0, str(import_root))

from analysis import contractlint


class EtherscanApiKeySelectionTests(unittest.TestCase):
    def test_empty_key_list_returns_none_without_random_selection(self):
        with patch.object(contractlint, "ETH_KEY", []), patch.object(
            contractlint.random, "randint", side_effect=AssertionError("random selection should be skipped")
        ):
            self.assertIsNone(contractlint._select_etherscan_api_key())

    def test_configured_keys_keep_random_selection(self):
        with patch.object(contractlint, "ETH_KEY", ["dummy-a", "dummy-b"]), patch.object(
            contractlint.random, "randint", return_value=3
        ) as randint:
            self.assertEqual(contractlint._select_etherscan_api_key(), "dummy-b")
            randint.assert_called_once_with(1, 1000)


if __name__ == "__main__":
    unittest.main()
