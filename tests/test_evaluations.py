"""Small offline checks for routing and safety behavior.

These tests do not call the paid model or require the vector index. They give
us a quick safety net while the retrieval and prompts continue to evolve.
"""

import json
import os
import sys
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

os.environ.setdefault("OPENROUTER_API_KEY", "test-key")
os.environ.setdefault("ADMIN_USER", "admin")
os.environ.setdefault("ADMIN_PASS", "password")
os.environ.setdefault("DEMO_API_KEY", "demo-key")

from backend.agent import ALLOWED_CATEGORIES
from backend.config import get_file_metadata
from backend.safety import emergency_message


class EvaluationConfigurationTests(unittest.TestCase):
    def test_evaluation_questions_are_present(self):
        questions_path = Path(__file__).parents[1] / "evaluation_questions.json"
        questions = json.loads(questions_path.read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(questions), 5)
        self.assertTrue(all("question" in item for item in questions))

    def test_known_categories_are_allowlisted(self):
        self.assertIn("Cardiovascular", ALLOWED_CATEGORIES)
        self.assertIn("Respiratory", ALLOWED_CATEGORIES)


class SafetyBehaviorTests(unittest.TestCase):
    def test_emergency_symptoms_return_warning(self):
        warning = emergency_message("I have severe chest pain and cannot breathe")
        self.assertIsNotNone(warning)
        self.assertIn("emergency", warning.lower())

    def test_normal_question_does_not_return_emergency_warning(self):
        self.assertIsNone(emergency_message("What are common eczema symptoms?"))

    def test_document_metadata_contains_version_and_source(self):
        metadata = get_file_metadata("cardiovascular.md")
        self.assertEqual(metadata["document"], "cardiovascular.md")
        self.assertIn("Cardiovascular", metadata["category"])
        self.assertEqual(metadata["version"], "v2.2")
        self.assertEqual(metadata["effective_date"], "2026-09-03")
        self.assertEqual(metadata["reviewed_by"], "Mayank Choudhary")
        self.assertIn("WHO", metadata["source"])


if __name__ == "__main__":
    unittest.main()
