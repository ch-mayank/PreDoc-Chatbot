"""Input Validation Agent for Clinical Intake & Symptom Verification.

A dedicated, low-latency AI agent that validates whether a user's input represents
a legitimate clinical presentation, symptom report, or medical inquiry before proceeding
to clinical triage decision support.
"""

import json
import logging
import re
from typing import Dict, Optional, Tuple

from backend.openai_client import get_openai_client
from backend.safety import is_clinical_query

logger = logging.getLogger("predoc.agents.input_validation")
logger.setLevel(logging.INFO)


class InputValidationAgent:
    """Dedicated fast autonomous agent that verifies and validates user clinical inputs."""

    def __init__(self, model: Optional[str] = None):
        from backend.config import AGENT_VALIDATION_MODEL
        self.model = model or AGENT_VALIDATION_MODEL
        self.client = get_openai_client()

    def validate_clinical_input(self, user_query: str) -> Tuple[bool, Optional[str]]:
        """Rapidly determine if user query is a valid clinical presentation.

        Returns:
            (is_valid_clinical, guidance_message_if_invalid)
        """
        query_clean = user_query.strip()
        if not query_clean:
            return False, "Please enter a clinical query or describe your presenting symptoms."

        # 1. Ultra-fast deterministic heuristic check (< 1ms)
        # If clearly non-clinical chatter or greeting, reject immediately without latency
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

        # 2. Fast AI validation for nuanced / ambiguous inputs
        prompt = (
            "You are a clinical intake validation agent for an emergency and outpatient triage system.\n"
            "Evaluate if the following user input describes an actual medical symptom, health complaint, or clinical inquiry.\n\n"
            f'User Input: "{query_clean}"\n\n'
            "Respond strictly in JSON format with exactly two keys:\n"
            '{"is_clinical": true/false, "reason": "brief explanation"}'
        )

        try:
            # Call fast LLM with low token count
            messages = [
                {"role": "system", "content": "You are a clinical intake validation agent for PreDoc AI."},
                {"role": "user", "content": prompt}
            ]
            res = self.client.chat_completion(
                messages=messages,
                preferred_model=self.model,
                temperature=0.0,
                max_tokens=60,
            )
            response = res.get("content", "")
            # Parse response
            match = re.search(r"\{.*\}", response, re.DOTALL)
            if match:
                data = json.loads(match.group(0))
                is_clinical = data.get("is_clinical", True)
                if not is_clinical:
                    return False, (
                        "> [!IMPORTANT]\n"
                        "> **Non-Clinical Query Detected**: PreDoc AI is an enterprise clinical decision support and triage system.\n\n"
                        f"The query entered (`\"{query_clean}\"`) was evaluated as non-clinical by our clinical intake agent ({data.get('reason', 'general inquiry')}).\n\n"
                        "**Please enter a clinical query describing presenting symptoms, duration, and location to proceed.**"
                    )
        except Exception as e:
            logger.warning(f"Fast AI validation failed: {e}. Falling back to deterministic safety rule.")

        # Default to True if it passed the heuristic check
        return True, None
