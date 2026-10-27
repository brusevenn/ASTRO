import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch


REPO = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO / "astro" / "lib" / "compile_config.py"


def load_compile_config():
    spec = importlib.util.spec_from_file_location("astro_compile_config", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class CompileConfigFallbackTests(unittest.TestCase):
    def test_defaults_to_non_xblock_when_project_extension_is_missing(self):
        module = load_compile_config()
        self.assertFalse(module.get_xblock())

    def test_xblock_operations_fail_actionably_without_project_extension(self):
        module = load_compile_config()
        message = "XBlock mode requires the project-specific crytic_compile.localize extension"

        with self.assertRaisesRegex(RuntimeError, message):
            module.use_xblock()
        with self.assertRaisesRegex(RuntimeError, message):
            module.set_xblock_json({"synthetic": True})

    def test_delegates_to_project_extension_when_available(self):
        external_config = types.SimpleNamespace(
            get_xblock=lambda: True,
            use_xblock=lambda: "enabled",
            set_xblock_json=lambda value: ("stored", value),
        )
        localize = types.ModuleType("crytic_compile.localize")
        localize.__path__ = []
        localize.config = external_config

        with patch.dict(sys.modules, {"crytic_compile.localize": localize}):
            module = load_compile_config()

        self.assertTrue(module.get_xblock())
        self.assertEqual(module.use_xblock(), "enabled")
        self.assertEqual(module.set_xblock_json({"synthetic": True}), ("stored", {"synthetic": True}))


if __name__ == "__main__":
    unittest.main()
