import subprocess
import sys
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]


class ContractlintCliTests(unittest.TestCase):
    def test_help_starts_without_project_xblock_extension(self):
        result = subprocess.run(
            [sys.executable, str(REPO / "astro" / "analysis" / "contractlint.py"), "--help"],
            cwd=str(REPO),
            capture_output=True,
            text=True,
            timeout=120,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("usage:", result.stdout.lower())
        self.assertIn("--solc-args", result.stdout)


if __name__ == "__main__":
    unittest.main()
