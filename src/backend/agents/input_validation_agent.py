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
        from backend.config import AGENT_VALIDATION_MODEL
        self.model = model or AGENT_VALIDATION_MODEL

    def _build_non_clinical_message(self, query_clean: str) -> str:
        """Standardized guidance message when input does not describe clinical complaints."""
        return (
            "> [!IMPORTANT]\n"
            "> **Non-Clinical Query Detected**: PreDoc AI is an enterprise clinical decision support and triage system.\n\n"
            f"The query entered (`\"{query_clean}\"`) does not describe identifiable clinical symptoms, medical signs, or health complaints.\n\n"
            "**Please enter a clinical query to receive diagnostic triage guidance, for example:**\n"
            "- *\"Acute crushing retrosternal chest pain radiating to left jaw for 40 minutes\"*\n"
            "- *\"Sharp right lower quadrant abdominal pain with rebound tenderness and low-grade fever\"*\n"
            "- *\"Sudden onset unilateral facial droop and right arm weakness\"*\n"
            "- *\"Persistent productive cough, exertional shortness of breath, and chills for 4 days\"*\n"
            "- *\"Sudden unilateral hearing loss with tinnitus and feeling of ear fullness for 2 days\"*\n"
            "- *\"Persistent depressed mood and lack of enjoyment in all activities for 3 weeks\"*\n\n"
            "You can also select **Patient Age**, **Biological Sex**, and **Target Specialties** above to contextualize risk stratification."
        )

    def _fast_llm_crosscheck(self, query: str) -> bool:
        """Sub-second AI validation crosscheck for subtle, conversational, or rare clinical complaints.
        
        Acts as an intelligent safety net when deterministic regex and dictionary checks miss 
        colloquial patient expressions (e.g. 'hearing issue', 'i don't feels enjoyment in anything', 
        'things look foggy', 'brain fog', 'cant sleep at night').
        """
        try:
            from backend.openai_client import get_openai_client
            client = get_openai_client()
            prompt = (
                "You are an ultra-fast clinical intake validator for a triage system.\n"
                "Determine if the user's statement describes a clinical symptom, health issue, sensory impairment, "
                "bodily sensation, mental/behavioral health concern, or medical question.\n\n"
                f'User statement: "{query}"\n\n'
                "Reply with ONLY one word: CLINICAL or NON_CLINICAL."
            )
            response = client.chat_completion(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                max_tokens=10,
            )
            if isinstance(response, dict):
                content = (response.get("content") or "").strip().upper()
            else:
                content = (getattr(response.choices[0].message, "content", "") or "").strip().upper()
            return "CLINICAL" in content and "NON_CLINICAL" not in content
        except Exception as e:
            logger.warning(f"Fast LLM validation crosscheck failed: {e}")
            return False

    def validate_clinical_input(self, user_query: str) -> Tuple[bool, Optional[str]]:
        """Rapidly determine if user query is a valid clinical presentation (< 1ms).

        Returns:
            (is_valid_clinical, guidance_message_if_invalid)
        """
        import re
        from backend.safety import NON_CLINICAL_PATTERNS
        query_clean = user_query.strip()
        if not query_clean:
            return False, "Please enter a clinical query or describe your presenting symptoms."

        # 1. Deterministic safety, threat, and harm check (< 0.1ms)
        safety_violation_msg = check_safety_violation(query_clean)
        if safety_violation_msg:
            return False, safety_violation_msg

        # 2. Ultra-fast deterministic clinical intent check (< 0.1ms)
        if is_clinical_query(query_clean):
            return True, None

        # 3. Deterministic conversational chatter filter (< 0.1ms)
        for pat in NON_CLINICAL_PATTERNS:
            if re.search(pat, query_clean.lower()):
                return False, self._build_non_clinical_message(query_clean)

        # 4. Fast Agent Crosscheck (< 300ms fallback for colloquial, psychiatric, or sensory complaints)
        if self._fast_llm_crosscheck(query_clean):
            logger.info(f"Fast validation agent verified clinical intent for: '{query_clean}'")
            return True, None

        return False, self._build_non_clinical_message(query_clean)

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

    def evaluate_clinical_specificity(
        self,
        query_text: str,
        history: Optional[list] = None,
        age: Optional[str] = None,
        sex: Optional[str] = None
    ) -> Tuple[float, dict, list]:
        """Evaluate clinical presentation completeness across 5 diagnostic dimensions.

        Dimensions evaluated (SOCRATES / OPQRST framework):
        1. Location & Radiation (Specific anatomical site vs generic body region)
        2. Onset & Timing (Duration, acute vs gradual, chronicity)
        3. Character & Quality (Sensory description, pain scale, severity)
        4. Functional Modifiers & Aggravating/Relieving Factors (Movement, triggers, rest)
        5. Red Flags & Associated Systemic Signs (Fever, bowel/bladder, neurological deficits)

        Returns:
            (specificity_score [0.0 - 1.0], dimension_flags_dict, missing_dimensions_list)
        """
        import re

        # Combine current query with historical user turns to assess cumulative context
        full_text = query_text.lower()
        if history:
            for item in history:
                if isinstance(item, dict) and item.get("role") == "user":
                    full_text += " " + str(item.get("content", "")).lower()

        tokens = set(re.findall(r"\w+", full_text))

        # 1. Location & Radiation (Anatomical, Sensory, or Affective Domain)
        specific_sites = {
            "calf", "thigh", "knee", "shin", "foot", "feet", "toes", "ankle", "groin",
            "buttock", "gluteal", "lumbar", "sciatic", "forearm", "wrist", "hand", "fingers",
            "elbow", "shoulder", "sternum", "retrosternal", "epigastric", "ruq", "rlq",
            "flank", "temple", "occipital", "frontal", "cervical", "spine", "sacrum",
            "left", "right", "bilateral", "unilateral", "radiating", "radiates", "shooting",
            # Sensory & ENT
            "ear", "ears", "hearing", "auditory", "eardrum", "tinnitus", "canal", "eye",
            "eyes", "vision", "throat", "pharynx", "larynx", "tonsil", "sinus", "nasal", "nose",
            # Mental & Affective Domain
            "mood", "mental", "affective", "psychological", "emotion", "emotional"
        }
        generic_sites = {"leg", "arm", "body", "head", "stomach", "chest", "back", "skin", "joint", "face", "mouth", "mind", "sleep"}

        has_specific_loc = bool(tokens & specific_sites) or bool(re.search(r"\b(down|into|to|across)\s+the\b", full_text))
        has_generic_loc = bool(tokens & generic_sites) or has_specific_loc

        # 2. Onset & Timing
        # Disregard demographic age expressions (e.g., '30-45 years', '40 yo', '50 years old')
        clean_text_timing = re.sub(r"\b\d+\s*(?:-\s*\d+)?\s*(?:years|yrs|yo|y/o)(?:\s*old)?\b", "", full_text)
        clean_tokens_timing = set(re.findall(r"\w+", clean_text_timing))

        timing_markers = {
            "day", "days", "hour", "hours", "week", "weeks", "month", "months",
            "minute", "minutes", "acute", "chronic", "sudden",
            "gradual", "intermittent", "constant", "recurrent", "since", "yesterday",
            "morning", "night", "started", "onset", "abrupt", "insidious", "woke"
        }
        has_onset_timing = (
            bool(clean_tokens_timing & timing_markers)
            or bool(re.search(r"\b\d+\s*(?:d|w|m|h|hrs|days|weeks|months)\b", clean_text_timing))
            or bool(re.search(r"\bfor\s+\d+\s+years?\b", clean_text_timing))
        )

        # 3. Character & Quality
        character_markers = {
            "sharp", "dull", "throbbing", "burning", "aching", "cramping", "stabbing",
            "shooting", "electric", "tingling", "numbness", "numb", "pins", "needles",
            "tightness", "tight", "pressure", "crushing", "mild", "moderate", "severe",
            "worst", "unbearable", "spasm", "stiff", "stiffness", "heavy", "heaviness",
            "tearing", "pounding", "splitting",
            # Sensory & Auditory
            "muffled", "ringing", "buzzing", "roaring", "deaf", "blind", "blurry", "cloudy", "loss", "reduced",
            # Mental & Behavioral
            "depressed", "depression", "sad", "hopeless", "worthless", "anhedonia", "enjoyment",
            "pleasure", "anxious", "anxiety", "panic", "racing", "manic", "mania", "guilt", "agitated", "restless"
        }
        has_character = bool(tokens & character_markers) or bool(re.search(r"\b\d+\s*/\s*10\b", full_text))

        # 4. Functional Modifiers & Triggers
        modifier_markers = {
            "walking", "sitting", "standing", "bending", "lifting", "rest", "resting",
            "movement", "coughing", "sneezing", "exercise", "exertion", "eating",
            "food", "better", "worse", "aggravated", "relieved", "triggers", "trigger",
            "limp", "limping", "weight", "bearing", "lying", "recumbent", "climbing",
            "motion", "touch", "palpation", "breathing", "inhalation",
            # Sensory & Environmental Triggers
            "noise", "noisy", "sound", "loud", "music", "water", "swimming", "flight", "airplane", "headphone",
            # Mental & Social Modifiers
            "stress", "work", "social", "people", "alone", "conflict", "sleep", "morning", "night"
        }
        has_modifiers = bool(tokens & modifier_markers)

        # 5. Red Flags & Associated Signs (Positive or Denied)
        redflag_markers = {
            "fever", "chills", "sweat", "sweating", "weight", "nausea", "vomiting",
            "diarrhea", "bowel", "bladder", "incontinence", "saddle", "trauma", "fall",
            "injury", "swelling", "edema", "redness", "erythema", "warmth", "dyspnea",
            "breath", "dizziness", "syncope", "fainting", "paralysis", "weakness",
            "droop", "confusion", "loss", "denies", "denied",
            # ENT / Otologic
            "vertigo", "drainage", "discharge", "otorrhea", "fullness", "otalgia",
            # Psychiatric
            "suicid", "suicide", "hallucination", "delusion", "hopelessness"
        }
        has_redflags = bool(tokens & redflag_markers)

        # Dimension weights
        score = 0.0
        if has_specific_loc:
            score += 0.25
        elif has_generic_loc:
            score += 0.10

        if has_onset_timing:
            score += 0.20
        if has_character:
            score += 0.20
        if has_modifiers:
            score += 0.20
        if has_redflags:
            score += 0.15

        dimensions = {
            "anatomical_site": has_specific_loc or has_generic_loc,
            "specific_localization": has_specific_loc,
            "onset_timing": has_onset_timing,
            "character_quality": has_character,
            "functional_modifiers": has_modifiers,
            "systemic_redflags": has_redflags,
        }

        missing = []
        if not has_specific_loc:
            missing.append("Specific anatomical location & radiation path (e.g., thigh, calf, radiating from back)")
        if not has_onset_timing:
            missing.append("Onset duration & timing (how many days/weeks, sudden vs. gradual)")
        if not has_character:
            missing.append("Symptom quality & severity (sharp, burning, shooting, dull, or pain score /10)")
        if not has_modifiers:
            missing.append("Aggravating or relieving factors (worse when walking, sitting, bending, or at rest)")
        if not has_redflags:
            missing.append("Associated signs & red flags (fever, numbness, weakness, or bowel/bladder changes)")

        score = round(min(1.0, score), 2)
        return score, dimensions, missing

