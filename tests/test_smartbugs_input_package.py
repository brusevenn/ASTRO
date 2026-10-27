import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "datasets/smartbugs-wild-actaint/subsets/actaint-usable-533-v1"
FORBIDDEN_CASE_FIELDS = {
    "label", "labels", "vulnerability", "vulnerability_type", "vulnerable_functions",
    "root_cause", "reported_function", "adjudication", "ground_truth",
}


class SmartBugsInputPackageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads((PACKAGE / "input-manifest.json").read_text(encoding="utf-8"))

    def test_manifest_is_complete_label_free_and_ordered(self):
        manifest = self.manifest
        self.assertEqual(manifest["dataset_id"], "smartbugs-wild-actaint-usable-533-v1")
        self.assertEqual(manifest["case_count"], 533)
        self.assertIs(manifest["label_free"], True)
        self.assertEqual(len(manifest["cases"]), 533)
        self.assertEqual([row["input_order"] for row in manifest["cases"]], list(range(1, 534)))
        self.assertEqual(len({row["case_id"] for row in manifest["cases"]}), 533)
        self.assertEqual(len({row["filename"] for row in manifest["cases"]}), 533)
        for row in manifest["cases"]:
            self.assertFalse(FORBIDDEN_CASE_FIELDS & set(row))

    def test_all_533_sources_match_manifest_size_and_sha256(self):
        manifest = self.manifest
        listed = {row["filename"] for row in manifest["cases"]}
        files = {path.name for path in (PACKAGE / "sources").glob("*.sol")}
        self.assertEqual(files, listed)
        for row in manifest["cases"]:
            relative = Path(row["source_path"])
            self.assertFalse(relative.is_absolute())
            source = ROOT / relative
            self.assertTrue(source.is_file(), row["case_id"])
            raw = source.read_bytes()
            self.assertEqual(len(raw), row["source_bytes"], row["case_id"])
            self.assertEqual(hashlib.sha256(raw).hexdigest(), row["source_sha256"], row["case_id"])


if __name__ == "__main__":
    unittest.main()
