"""Input Validation Agent for Clinical Intake & Symptom Verification.

A dedicated, sub-millisecond agent that validates whether a user's input represents
a legitimate clinical presentation, symptom report, or medical inquiry before proceeding
to clinical triage decision support.
"""

import logging
from typing import Optional, Tuple

from backend.safety import is_clinical_query, check_safety_violation

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

        # 1. Deterministic safety, threat, and harm check (< 0.1ms)
        safety_violation_msg = check_safety_violation(query_clean)
        if safety_violation_msg:
            return False, safety_violation_msg

        # 2. Ultra-fast deterministic clinical intent check (< 1ms)
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

    def check_ambiguity(self, user_query: str) -> Tuple[bool, Optional[str]]:
        """Determine if a clinical query is too ambiguous or underspecified for safe triage.

        When symptoms are too vague (e.g. single-word complaints like 'headache' or 'fever'
        without duration, location, or severity), triggers the validation feedback loop:
        'I am unsure, please give me more info.'

        Returns:
            (is_ambiguous, clarification_prompt_if_ambiguous)
        """
        import re
        query_clean = user_query.strip().lower()
        words = re.findall(r"\w+", query_clean)

        # Explicit red-flag emergency keywords bypass ambiguity
        emergency_markers = {
            "crushing", "radiating", "unconscious", "seizure", "drooping", "paralysis",
            "asphyxia", "stridor", "anaphylaxis", "hemoptysis", "thunderclap"
        }
        if any(m in words for m in emergency_markers):
            return False, None

        # Temporal indicators (how long has it lasted?)
        temporal_markers = {
            "day", "days", "hour", "hours", "week", "weeks", "month", "months",
            "year", "years", "minute", "minutes", "acute", "chronic", "sudden",
            "gradual", "intermittent", "constant", "recurrent", "since", "yesterday"
        }
        # Descriptive character / severity indicators
        character_markers = {
            "sharp", "dull", "throbbing", "burning", "aching", "cramping",
            "stabbing", "mild", "moderate", "severe", "worst", "unbearable",
            "radiating", "bilateral", "unilateral", "localized", "generalized"
        }

        has_temporal = any(t in words for t in temporal_markers)
        has_character = any(c in words for c in character_markers)

        # Ambiguity Condition: Extremely brief (< 4 words) without duration or character
        if len(words) <= 3 and not (has_temporal and has_character):
            clarification = (
                "> [!NOTE]\n"
                "> **Clinical Clarification Needed**\n\n"
                "**I am unsure, please give me more info.**\n\n"
                f"Your presentation (`\"{user_query.strip()}\"`) is too brief or non-specific to formulate a reliable diagnostic differential or triage level.\n\n"
                "To help narrow down potential causes, please clarify:\n"
                "1. **Onset & Timing**: When did this symptom start, and is it constant or coming in waves?\n"
                "2. **Location & Radiation**: Where exactly is it located, and does it spread elsewhere?\n"
                "3. **Quality & Severity**: How does it feel (e.g., sharp, dull, burning, aching), and what is the pain score (1-10)?\n"
                "4. **Associated Signs**: Do you also have fever, shortness of breath, nausea, or dizziness?\n"
                "5. **Context**: What is the patient's approximate age or biological sex?"
            )
            return True, clarification

        # Vague generalized constitutional complaints (e.g., 'i feel sick', 'body hurts')
        vague_phrases = [
            r"^(i\s+)?feel(ing)?\s+(sick|bad|unwell|terrible|awful|ill|weird)$",
            r"^(my\s+)?body\s+(hurts|aches|feels\s+bad)$",
            r"^(i\s+)?have\s+pain$",
            r"^(something\s+is\s+wrong)$",
        ]
        for pat in vague_phrases:
            if re.match(pat, query_clean):
                clarification = (
                    "> [!NOTE]\n"
                    "> **Clinical Clarification Needed**\n\n"
                    "**I am unsure, please give me more info.**\n\n"
                    f"The description (`\"{user_query.strip()}\"`) does not specify an anatomical location, timeline, or severity.\n\n"
                    "Please provide more specific details:\n"
                    "- What part of the body is primarily affected?\n"
                    "- Are you experiencing localized pain, fever, fatigue, or breathing changes?\n"
                    "- Did this symptom start suddenly or gradually develop over several days?"
                )
                return True, clarification

        return False, None
