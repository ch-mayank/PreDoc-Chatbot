"""Clinical safety and intent validation checks for PreDoc AI."""

import re
from typing import Optional

URGENT_SYMPTOMS = re.compile(
    r"severe chest pain|pressure in (the )?chest|difficulty breathing|"
    r"cannot breathe|face drooping|arm weakness|speech difficulty|"
    r"unconscious|passed out|heavy bleeding|seizure",
    re.IGNORECASE,
)

CLINICAL_STEMS = {
    "pain", "ache", "sore", "fever", "cough", "rash", "weak", "dizz", "swell", "bleeding", "bleed",
    "vomit", "nausea", "fatigue", "tired", "breath", "dyspnea", "chest", "head", "abdom", "stomach",
    "throat", "burn", "itch", "wound", "injury", "cramp", "stiff", "seizure", "palpitat", "numb",
    "tingl", "chill", "diarrhea", "constipat", "lesion", "lump", "mass", "discharge", "vision",
    "blur", "cold", "flu", "infect", "pressure", "spasm", "trauma", "bruise", "joint", "muscle",
    "swollen", "edema", "syncope", "faint", "erythem", "wheez", "hemopt", "jaundice", "yellow",
    "cardia", "pulmon", "renal", "uro", "neuro", "derm", "gastro", "endo", "hema", "pediatr",
    "geriatr", "syndrome", "disease", "disorder", "diagnos", "symptom", "sign", "triage", "ill",
    "sick", "hurt", "ear", "eye", "mouth", "tongue", "tooth", "teeth", "neck", "back", "spine",
    "arm", "leg", "foot", "feet", "hand", "finger", "toe", "skin", "heart", "lung", "liver",
    "kidney", "bladder", "bowel", "colon", "blood", "pulse", "bp", "temperature", "sugar", "glucose"
}

NON_CLINICAL_PATTERNS = [
    r"^(hi|hello|hey|greetings|howdy|good\s+morning|good\s+afternoon|good\s+evening)\b",
    r"\bwho\s+(are|r)\s+(you|u)\b",
    r"\bwhat\s+(is|are)\s+you(r)?\b",
    r"\bwhat\s+can\s+you\s+do\b",
    r"\bhow\s+are\s+you\b",
    r"\btell\s+me\s+a\s+joke\b",
    r"\bwhat(\')?s\s+up\b",
    r"^(test|testing|asdf|qwerty|ping|pong)$",
]


def emergency_message(question: str) -> Optional[str]:
    """Return an urgent-care warning when red-flag symptoms are mentioned."""
    if URGENT_SYMPTOMS.search(question):
        return (
            "**Emergency warning:** These symptoms may need immediate medical "
            "attention. Call your local emergency number or go to the nearest "
            "emergency department now. Do not rely on this chatbot for urgent care.\n\n"
        )
    return None


def is_clinical_query(text: str) -> bool:
    """Validate whether input describes clinical signs, symptoms, anatomy, or diagnostic inquiries."""
    clean = text.strip().lower()
    if not clean:
        return False

    # Check for direct conversational chatter
    for pat in NON_CLINICAL_PATTERNS:
        if re.search(pat, clean):
            words = re.findall(r"\w+", clean)
            if not any(any(w.startswith(s) or s in w for s in CLINICAL_STEMS) for w in words):
                return False

    # Check if query contains any clinical, anatomical, or symptom stems
    words = re.findall(r"\w+", clean)
    return any(any(w.startswith(s) or s in w for s in CLINICAL_STEMS) for w in words)
