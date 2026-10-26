import importlib.util
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


class FakeArray:
    def __init__(self, values):
        self.values = values
        self.matrix = None

    def reshape(self, rows, columns):
        self.matrix = [self.values[i * columns:(i + 1) * columns] for i in range(rows)]
        return self

    def tolist(self):
        return self.matrix


class FakeNumpy:
    @staticmethod
    def array(values):
        return FakeArray(values)


class FakeProcess:
    def __init__(self, command, **kwargs):
        self.command = command

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def communicate(self):
        Path(self.command[-1], "return.txt").write_text("2;2;1,0,0,1", encoding="utf-8")
        return b"", b""


class HungarianPortabilityTests(unittest.TestCase):
    def test_uses_environment_interpreter_and_repository_relative_helper(self):
        repo = Path(__file__).resolve().parents[1]
        module_path = repo / "astro" / "wfg" / "call_hungarian.py"
        spec = importlib.util.spec_from_file_location("astro_call_hungarian", module_path)
        module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {"numpy": FakeNumpy}):
            spec.loader.exec_module(module)

        helper = (repo / "astro" / "wfg" / "python2" / "hungarian1.py").resolve()
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict(os.environ, {"ASTRO_PYTHON2": "python2-test"}):
                with patch.object(module.subprocess, "Popen", side_effect=FakeProcess) as popen:
                    result = module.call_hungarian([[1, 0], [0, 1]], temp_dir)

        command = popen.call_args.args[0]
        self.assertEqual(command[0], "python2-test")
        self.assertEqual(Path(command[1]).resolve(), helper)
        self.assertEqual(result, [[1, 0], [0, 1]])


if __name__ == "__main__":
    unittest.main()
