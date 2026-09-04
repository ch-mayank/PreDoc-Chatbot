"""Unit tests for PreDoc Autonomous Clinical Agents Suite."""

import sys
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from backend.agents.classifier_agent import SpecialtyClassifierAgent
from backend.agents.probing_agent import ClinicalProbingAgent
from backend.agents.auditor_agent import KnowledgeBaseAuditorAgent
from backend.agents.pdf_extractor_agent import PDFExtractorAgent
from backend.agents.web_crawler_agent import WebCrawlerAgent
from backend.agents.orchestrator import MasterIngestionOrchestrator


class TestClinicalAgents(unittest.TestCase):
    """Test suite for autonomous clinical agents."""

    def setUp(self):
        self.root_dir = Path(__file__).resolve().parent.parent

    def test_classifier_agent_initialization(self):
        agent = SpecialtyClassifierAgent()
        self.assertEqual(len(agent.categories), 20)
        self.assertIn("Cardiovascular", agent.categories)
        self.assertIn("Dermatological", agent.categories)
        # Test classification
        res = agent.classify_text("Patient reports severe crushing chest pain radiating to left arm")
        self.assertEqual(res, "Cardiovascular")

    def test_probing_agent_generation(self):
        agent = ClinicalProbingAgent()
        questions = agent.generate_questions(
            disease="ST-Elevation Myocardial Infarction (STEMI)",
            primary="Severe crushing retrosternal chest pain, diaphoresis",
            secondary="Indigestion-like discomfort",
        )
        self.assertIsInstance(questions, str)
        self.assertIn("Does your chest discomfort feel like", questions)
        self.assertTrue(questions.endswith('"') or questions.endswith("?"))

    def test_auditor_agent_compliance(self):
        import tempfile
        auditor = KnowledgeBaseAuditorAgent()
        sample_valid = (
            "| ID | Disease / Condition | ICD-10-CM | Triage Priority Tier | Target Demographics (Age & Sex) | Primary Presentation | Secondary / Atypical Presentation | Risk Factors & Triggers | Red Flag / Escalation Markers | Clarifying Probing Questions | Key Differentials |\n"
            "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n"
            '| **TST-001** | Test Condition | A00.0 | Level 1 (Red) | Adults (18-65 yrs); Equal (1:1) | Severe acute hallmark clinical presentation | Mild secondary variant | High risk factors | Sudden collapse | 1) "Tailored question one?" 2) "Tailored question two?" | Differential One, Two |\n'
        )
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as tf:
            tf.write(sample_valid)
            temp_path = Path(tf.name)

        try:
            report = auditor.audit_file(temp_path)
            self.assertTrue(report["is_valid"])
            self.assertEqual(report["total_rows"], 1)
            self.assertEqual(len(report["column_errors"]), 0)
        finally:
            if temp_path.exists():
                temp_path.unlink()

    def test_pdf_extractor_agent_init(self):
        pdf_agent = PDFExtractorAgent()
        self.assertTrue(pdf_agent.raw_pdfs_dir.exists())
        self.assertTrue(pdf_agent.dumps_dir.exists())

    def test_web_crawler_agent_catalog(self):
        crawler = WebCrawlerAgent()
        sources = crawler.load_catalog()
        self.assertGreaterEqual(len(sources), 20)
        source_ids = [s.get("id") for s in sources]
        self.assertIn("SRC-001", source_ids)

    def test_orchestrator_initialization(self):
        orchestrator = MasterIngestionOrchestrator()
        self.assertIsNotNone(orchestrator.pdf_agent)
        self.assertIsNotNone(orchestrator.web_agent)
        self.assertIsNotNone(orchestrator.populator_agent)
        self.assertIsNotNone(orchestrator.auditor_agent)

    def test_input_validation_agent(self):
        from backend.agents.input_validation_agent import InputValidationAgent
        validator = InputValidationAgent()
        
        # Non-clinical query rejection
        is_valid, msg = validator.validate_clinical_input("hi who are u")
        self.assertFalse(is_valid)
        self.assertIn("Non-Clinical Query Detected", msg)

        # Genuine clinical query acceptance
        is_valid_clin, _ = validator.validate_clinical_input("Severe crushing retrosternal chest pain radiating to left arm")
        self.assertTrue(is_valid_clin)


if __name__ == "__main__":
    unittest.main()
