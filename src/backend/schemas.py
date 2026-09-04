"""Pydantic schemas and clinical data contracts for PreDoc AI.

Defines strict JSON schemas for:
- Patient Consultation Request (with edge-case sanitization for age & sex)
- Clinical Triage Response (with differential diagnoses, ICD-10 codes, and probing questions)
- 11-Column Knowledge Base Condition Schema
- Operational Telemetry & System Status
"""

import re
from typing import Dict, List, Optional, Union
from pydantic import BaseModel, Field, field_validator, model_validator


VALID_SEX_OPTIONS = {"Male", "Female", "Other", "Intersex", "Unspecified"}
VALID_AGE_BRACKETS = {
    "Neonate",      # 0 - 28 days
    "Infant",       # 1 - 12 months
    "Child",        # 1 - 11 years
    "Adolescent",   # 12 - 18 years
    "Adult",        # 19 - 64 years
    "Geriatric"     # 65+ years
}


class ClinicalProbingQuestion(BaseModel):
    """Structured high-yield diagnostic question to clarify patient presentation."""
    question_id: str = Field(..., description="Unique question identifier")
    question_text: str = Field(..., description="Targeted diagnostic follow-up question")
    clinical_rationale: str = Field(..., description="Why this question differentiates potential pathologies")


class TriageDifferential(BaseModel):
    """Differential diagnosis candidate matching patient presentation."""
    condition_name: str = Field(..., description="Canonical disease or syndrome name")
    icd10_code: str = Field(..., description="ICD-10-CM diagnostic classification code")
    triage_level: str = Field(..., description="Level 1 Red Emergency, Level 2 Yellow Urgent, or Level 3 Green Routine")
    confidence_rationale: str = Field(..., description="Clinical reasoning explaining presentation match")
    red_flag_warnings: List[str] = Field(default_factory=list, description="Immediate dangerous warning signs")


class QueryRequest(BaseModel):
    """The patient symptom consultation request payload."""

    question: Optional[str] = Field(None, description="Clinical query / patient symptom text")
    message: Optional[str] = Field(None, description="Alternative field for symptom message")
    categories: Optional[List[str]] = Field(default_factory=list, description="Target medical specialties")
    age: Optional[Union[str, int]] = Field(None, description="Patient age (0-125) or clinical bracket")
    sex: Optional[str] = Field(None, description="Patient biological sex (Male, Female, Other, Unspecified)")
    history: Optional[List[Dict[str, str]]] = Field(default_factory=list, description="Multi-turn conversation history [{'role': 'user'|'assistant', 'content': '...'}]")
    turn_count: Optional[int] = Field(1, description="Current intake round turn count")
    force_evaluation: bool = Field(False, description="Bypass probing threshold and force immediate clinical evaluation")
    sanitization_warnings: List[str] = Field(default_factory=list, description="Audit warnings from edge-case normalization")

    @model_validator(mode="before")
    def unify_query(cls, data: dict):
        if isinstance(data, dict):
            q = data.get("question") or data.get("message")
            if not q or len(str(q).strip()) < 2:
                raise ValueError("A valid 'question' or 'message' string must be provided.")
            data["question"] = str(q).strip()
        return data

    @model_validator(mode="after")
    def validate_demographics_gracefully(self):
        """Handle demographic edge cases gracefully without raising 422 or 500 exceptions."""
        warnings: List[str] = []

        # 1. Edge-Case Validation for Age
        if self.age is not None:
            raw_age = str(self.age).strip()
            # Check for numeric age
            if re.match(r"^-?\d+$", raw_age):
                age_val = int(raw_age)
                if age_val < 0:
                    warnings.append(f"Invalid negative age '{raw_age}' corrected to 0 (Neonate).")
                    self.age = "0 (Neonate)"
                elif age_val > 125:
                    warnings.append(f"Out-of-range age '{raw_age}' (>125) normalized to 'Geriatric (65+)'.")
                    self.age = "Geriatric (65+)"
                else:
                    self.age = str(age_val)
            else:
                # Check for standard brackets (case-insensitive)
                matched_bracket = next(
                    (b for b in VALID_AGE_BRACKETS if b.lower() == raw_age.lower()),
                    None
                )
                if matched_bracket:
                    self.age = matched_bracket
                else:
                    warnings.append(
                        f"Unrecognized age format '{raw_age}'. Gracefully normalized to 'Unspecified Age (Default: Adult)'."
                    )
                    self.age = "Unspecified Age (Default: Adult)"

        # 2. Edge-Case Validation for Biological Sex
        if self.sex is not None:
            raw_sex = str(self.sex).strip()
            matched_sex = next(
                (s for s in VALID_SEX_OPTIONS if s.lower() == raw_sex.lower()),
                None
            )
            if matched_sex:
                self.sex = matched_sex
            else:
                warnings.append(
                    f"Unrecognized biological sex '{raw_sex}'. Normalized to 'Unspecified (Clinical Neutral)'."
                )
                self.sex = "Unspecified (Clinical Neutral)"

        self.sanitization_warnings = warnings
        return self


class QueryResponse(BaseModel):
    """The structured triage response returned to clinicians or patients."""

    status: str = "success"
    authenticated_user: str = "clinical_guest"
    answer: str
    response: Optional[str] = None
    triage_level: Optional[str] = Field(None, description="Overall triage tier (Level 1 Red, Level 2 Yellow, Level 3 Green)")
    differentials: List[TriageDifferential] = Field(default_factory=list, description="Candidate differential diagnoses")
    probing_questions: List[ClinicalProbingQuestion] = Field(default_factory=list, description="Follow-up diagnostic questions")
    specificity_score: Optional[float] = Field(None, description="Clinical specificity confidence score between 0.0 and 1.0")
    specificity_threshold: Optional[float] = Field(None, description="Configured clinical specificity threshold")
    is_clarification_needed: bool = Field(False, description="True if specificity is below threshold and active probing is ongoing")
    turn_count: int = Field(1, description="Turn count of consultation")
    missing_dimensions: List[str] = Field(default_factory=list, description="Clinical dimensions still missing from presentation")
    audit_notes: List[str] = Field(default_factory=list, description="Validation and sanitization audit trail")

    @model_validator(mode="after")
    def sync_response(self):
        if not self.response:
            self.response = self.answer
        return self


class ConditionMatrixRow(BaseModel):
    """Canonical 11-column clinical knowledge base schema."""
    specialty: str = Field(..., description="Col 1: Primary medical specialty taxonomy")
    condition_name: str = Field(..., description="Col 2: Condition / Disease / Syndrome name")
    icd10_code: str = Field(..., description="Col 3: ICD-10-CM classification code")
    typical_presentation: str = Field(..., description="Col 4: Hallmark clinical presentation")
    urgent_warning_signs: str = Field(..., description="Col 5: Red flags requiring immediate escalation")
    differential_diagnoses: str = Field(..., description="Col 6: Key differential considerations")
    diagnostic_workup: str = Field(..., description="Col 7: Recommended diagnostic tests/labs")
    initial_triage_tier: str = Field(..., description="Col 8: Level 1 Red, Level 2 Yellow, or Level 3 Green")
    evidence_grade: str = Field(..., description="Col 9: Evidence tier (Grade A/B/C)")
    clinical_pearls: str = Field(..., description="Col 10: High-yield diagnostic pearls & probing questions")
    reference_sources: str = Field(..., description="Col 11: Authoritative citations (WHO/CDC/NLM/Textbooks)")

