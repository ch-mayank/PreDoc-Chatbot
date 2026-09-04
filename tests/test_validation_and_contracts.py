"""Unit tests for Data Contracts, Edge Case Demographic Handling, and Ambiguity Loops."""

import unittest
from backend.schemas import QueryRequest, QueryResponse, ConditionMatrixRow
from backend.agents.input_validation_agent import InputValidationAgent


class TestDataContractsAndValidation(unittest.TestCase):
    """Test suite for BA Data Contracts and Technical Validation Loops."""

    def setUp(self):
        self.validator = InputValidationAgent()

    # --- Pillar 1 & 3: Data Contracts & Edge Case Demographics ---

    def test_age_negative_gracefully_sanitized(self):
        """Negative age should be normalized to 0 (Neonate) with audit warning."""
        req = QueryRequest(question="Mild cough and congestion for 3 days", age="-5")
        self.assertEqual(req.age, "0 (Neonate)")
        self.assertTrue(any("Invalid negative age" in w for w in req.sanitization_warnings))

    def test_age_out_of_range_gracefully_sanitized(self):
        """Age > 125 should be normalized to Geriatric (65+) with audit warning."""
        req = QueryRequest(question="Mild joint stiffness for 2 weeks", age="140")
        self.assertEqual(req.age, "Geriatric (65+)")
        self.assertTrue(any("Out-of-range age" in w for w in req.sanitization_warnings))

    def test_age_bracket_recognized(self):
        """Standard age brackets (case-insensitive) should be preserved."""
        req = QueryRequest(question="Sore throat for 2 days", age="Adolescent")
        self.assertEqual(req.age, "Adolescent")

    def test_age_unrecognized_gracefully_handled(self):
        """Random string age should be normalized without raising 422/500."""
        req = QueryRequest(question="Mild headache for 1 day", age="twenty-ish")
        self.assertEqual(req.age, "Unspecified Age (Default: Adult)")
        self.assertTrue(any("Unrecognized age format" in w for w in req.sanitization_warnings))

    def test_sex_unrecognized_gracefully_handled(self):
        """Invalid biological sex should be normalized to Unspecified."""
        req = QueryRequest(question="Skin rash on forearms for 4 days", sex="martian")
        self.assertEqual(req.sex, "Unspecified (Clinical Neutral)")
        self.assertTrue(any("Unrecognized biological sex" in w for w in req.sanitization_warnings))

    def test_canonical_11col_schema_validation(self):
        """11-column condition matrix row should validate required clinical attributes."""
        row = ConditionMatrixRow(
            specialty="Cardiovascular",
            condition_name="Acute Myocardial Infarction",
            icd10_code="I21.9",
            typical_presentation="Retrosternal crushing chest pain with diaphoresis",
            urgent_warning_signs="Hemodynamic instability, sustained ventricular tachycardia",
            differential_diagnoses="Aortic dissection, pulmonary embolism, GERD",
            diagnostic_workup="12-lead ECG, serial high-sensitivity Troponin-I",
            initial_triage_tier="Level 1 Red Emergency",
            evidence_grade="Grade A",
            clinical_pearls="Time is muscle: door-to-balloon time goal < 90 minutes",
            reference_sources="ACC/AHA Guidelines, WHO ICD-10-CM"
        )
        self.assertEqual(row.icd10_code, "I21.9")
        self.assertEqual(row.initial_triage_tier, "Level 1 Red Emergency")

    # --- Pillar 1 & 3: Ambiguity Feedback Loop ("I am unsure") ---

    def test_ambiguity_triggered_on_single_vague_word(self):
        """Single-word symptom complaints must trigger 'I am unsure, please give me more info.'"""
        is_ambiguous, message = self.validator.check_ambiguity("headache")
        self.assertTrue(is_ambiguous)
        self.assertIn("I am unsure, please give me more info.", message)
        self.assertIn("Onset & Timing", message)

    def test_ambiguity_triggered_on_vague_constitutional_query(self):
        """Vague phrases like 'i feel sick' or 'my body hurts' must trigger clarification."""
        is_ambiguous, message = self.validator.check_ambiguity("my body hurts")
        self.assertTrue(is_ambiguous)
        self.assertIn("I am unsure, please give me more info.", message)

    def test_detailed_presentation_bypasses_ambiguity(self):
        """Detailed clinical presentations with onset/severity/localization must bypass ambiguity."""
        is_ambiguous, _ = self.validator.check_ambiguity(
            "Acute severe crushing retrosternal chest pain radiating to left jaw for 40 minutes"
        )
        self.assertFalse(is_ambiguous)

    def test_emergency_symptoms_bypass_ambiguity(self):
        """Acute emergency presentations bypass ambiguity directly into triage."""
        is_ambiguous, _ = self.validator.check_ambiguity("severe crushing chest pain")
        self.assertFalse(is_ambiguous)


if __name__ == "__main__":
    unittest.main()
