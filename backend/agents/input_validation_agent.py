"""Input Validation Agent for Clinical Intake & Symptom Verification.

A dedicated, sub-millisecond agent that validates whether a user's input represents
a legitimate clinical presentation, symptom report, or medical inquiry before proceeding
to clinical triage decision support.
"""

import logging
from typing import Optional, Tuple

from backend.safety import is_clinical_query

logger = logging.getLogger("predoc.agents.input_validation")
logger.setLevel(logging.INFO)


class InputValidationAgent:
    """Dedicated fast autonomous agent that verifies and validates user clinical inputs."""

    def __init__(self, model: Optional[str] = None):
        pass

    def validate_clinical_input(self, user_query: str) -> Tuple[bool, Optional[str]]:
        """Rapidly determine if user query is a valid clinical presentation (< 1ms).

        Returns:
            (is_valid_clinical, guidance_message_if_invalid)
        """
        query_clean = user_query.strip()
        if not query_clean:
            return False, "Please enter a clinical query or describe your presenting symptoms."

        # Ultra-fast deterministic heuristic check (< 1ms)
        if not is_clinical_query(query_clean):
            return False, (
                "> [!IMPORTANT]\n"
                "> **Non-Clinical Query Detected**: PreDoc AI is an enterprise clinical decision support and triage system.\n\n"
                f"The query entered (`\"{query_clean}\"`) does not describe identifiable clinical symptoms, medical signs, or health complaints.\n\n"
                "**Please enter a clinical query to receive diagnostic triage guidance, for example:**\n"
                "- *\"Acute crushing retrosternal chest pain radiating to left jaw for 40 minutes\"*\n"
                "- *\"Sharp right lower quadrant abdominal pain with rebound tenderness and low-grade fever\"*\n"
                "- *\"Sudden onset unilateral facial droop and right arm weakness\"*\n"
                "- *\"Persistent productive cough, exertional shortness of breath, and chills for 4 days\"*\n\n"
                "You can also select **Patient Age**, **Biological Sex**, and **Target Specialties** above to contextualize risk stratification."
            )

        return True, None
