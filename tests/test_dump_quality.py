"""Regression tests for raw ingestion dump quality control."""

import json
import sys
import tempfile
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from backend.agents.dump_quality_agent import DumpQualityAgent


class TestDumpQualityAgent(unittest.TestCase):
    def test_inspect_and_repair_duplicate_conditions(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            dump_path = root / "pdf_extractions" / "conditions.json"
            dump_path.parent.mkdir()
            dump_path.write_text(
                json.dumps(
                    {
                        "total_conditions": 3,
                        "conditions": [
                            {"condition_name": "Asthma", "clinical_findings": "A"},
                            {"condition_name": "Asthma", "clinical_findings": "Duplicate"},
                            "not-a-condition",
                        ],
                    }
                ),
                encoding="utf-8",
            )

            agent = DumpQualityAgent(root)
            report = agent.inspect()
            self.assertEqual(report["total_files"], 1)
            self.assertEqual(report["valid_files"], 1)
            self.assertEqual(report["files"][0]["removed_candidates"], 2)

            repaired = agent.repair()
            self.assertEqual(repaired["repaired_files"], 1)
            self.assertTrue(dump_path.with_suffix(".json.bak").exists())
            result = json.loads(dump_path.read_text(encoding="utf-8"))
            self.assertEqual(len(result["conditions"]), 1)
            self.assertEqual(result["total_conditions"], 1)
            self.assertIn("quality_checked_at", result)

    def test_inspect_reports_invalid_json_without_changing_it(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            dump_path = root / "broken.json"
            original = "{ broken"
            dump_path.write_text(original, encoding="utf-8")

            report = DumpQualityAgent(root).inspect()
            self.assertEqual(report["broken_files"], 1)
            self.assertFalse(report["files"][0]["valid"])
            self.assertEqual(dump_path.read_text(encoding="utf-8"), original)


if __name__ == "__main__":
    unittest.main()
