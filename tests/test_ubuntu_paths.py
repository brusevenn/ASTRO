from pathlib import Path
import unittest


REPO = Path(__file__).resolve().parents[1]


class UbuntuPathTests(unittest.TestCase):
    def test_contractlint_uses_repository_relative_import_root(self):
        source = (REPO / "astro" / "analysis" / "contractlint.py").read_text(encoding="utf-8")
        self.assertNotIn("/root/astro_submit/astro", source)
        self.assertIn("ASTRO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))", source)

    def test_sim_uses_repository_relative_import_root(self):
        source = (REPO / "astro" / "find_candidate" / "sim.py").read_text(encoding="utf-8")
        self.assertNotIn("/root/astro_submit/astro", source)
        self.assertIn("ASTRO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))", source)

    def test_dataset_compile_helper_uses_current_python_and_local_entrypoint(self):
        source = (REPO / "astro" / "lib" / "call_contractlint.py").read_text(encoding="utf-8")
        self.assertNotIn("/root/research/acinfer/acinfer/acinfer/analysis/contractlint.py", source)
        self.assertIn('cmd = [sys.executable, os.path.join(astro_root, "analysis", "contractlint.py")]', source)


if __name__ == "__main__":
    unittest.main()
