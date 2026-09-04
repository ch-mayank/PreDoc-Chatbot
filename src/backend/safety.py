"""Clinical safety and intent validation checks for PreDoc AI."""

import re
from typing import Optional

URGENT_SYMPTOMS = re.compile(
    r"(severe|crushing|tight|radiating|acute|sudden)\s+(?:retrosternal\s+)?chest\s+pain|"
    r"chest\s+pain\s+(?:radiating|spreading)|pressure in (?:the )?chest|"
    r"difficulty breathing|shortness of breath|cannot breathe|stridor|asphyxia|"
    r"face drooping|facial droop|arm weakness|speech difficulty|slurred speech|"
    r"unconscious|passed out|heavy bleeding|hemorrhage|seizure|convulsion|"
    r"loss of (?:bowel|bladder)\s+control|saddle anesthesia|cauda equina|"
    r"sudden (?:paralysis|inability to walk|inability to move)",
    re.IGNORECASE,
)

THREAT_OR_VIOLENCE_PATTERN = re.compile(
    r"\b(i\s+will\s+kill\s+u|i\s+will\s+kill\s+you|kill\s+u|kill\s+you|kill\s+yourself|"
    r"murder\s+you|murder\s+u|threat(en)?|bomb|shoot\s+you|shoot\s+u|"
    r"attack\s+you|attack\s+u|hurt\s+you|hurt\s+u|beat\s+you|die\s+bitch|"
    r"fuck\s+you|asshole|stfu)\b",
    re.IGNORECASE,
)

SELF_HARM_PATTERN = re.compile(
    r"\b(kill\s+myself|suicide|commit\s+suicide|end\s+my\s+life|want\s+to\s+die|"
    r"slit\s+my\s+wrist|hang\s+myself|overdose\s+myself)\b",
    re.IGNORECASE,
)

# Short words that require whole-word exact matching (prevents 'kill' matching 'ill', 'warm' matching 'arm')
EXACT_CLINICAL_WORDS = {
    "ill", "sick", "hurt", "pain", "ache", "sore", "rash", "weak", "burn", "itch",
    "numb", "cold", "flu", "wound", "cramp", "stiff", "lump", "mass", "faint", "ear",
    "ears", "hear", "eye", "eyes", "mouth", "tongue", "tooth", "teeth", "neck", "back",
    "spine", "arm", "leg", "foot", "feet", "hand", "finger", "toe", "skin", "heart",
    "lung", "liver", "kidney", "bladder", "bowel", "colon", "blood", "pulse", "bp",
    "sugar", "glucose", "gout", "clot", "cyst", "bile", "vein", "gut", "rib", "jaw",
    "knee", "hip", "bone", "lip", "gum", "sinus", "nose", "smell", "taste", "deaf",
    "blind", "mute", "sad", "mood", "crying", "cry", "guilt", "ptsd", "ocd", "mania",
    "grief", "stress", "sleep", "mind", "fear", "pale", "bump", "hives", "mole",
    "boil", "scab", "drain", "pus", "pee", "poop", "stool", "vomit", "phlegm",
    "shiver", "shake", "tremor", "wheeze", "cough"
}

# Medical prefixes/stems (>= 4 chars) where prefix matching (w.startswith(p)) is safe
CLINICAL_PREFIXES = {
    "fever", "cough", "vomit", "nausea", "fatigue", "tired", "breath", "dyspnea",
    "chest", "headach", "abdom", "stomach", "throat", "injury", "seizur", "palpitat",
    "tingl", "chill", "diarrh", "constipat", "lesion", "discharg", "vision", "infect",
    "pressur", "spasm", "trauma", "bruis", "joint", "muscle", "swoll", "edema",
    "syncope", "erythem", "wheez", "hemopt", "jaundic", "cardia", "pulmon", "renal",
    "urolo", "neuro", "dermat", "gastro", "endocr", "hemat", "pediatr", "geriatr",
    "syndrom", "diseas", "disorder", "diagnos", "symptom", "triage", "hyper", "hypo",
    "anemi", "arrhythm", "tachy", "brady", "hyperten", "hypoten", "inflamm", "allerg",
    "fractur", "sprain", "hemorrh", "bleed", "dizz",
    # Sensory & ENT (Auditory, Hearing, Ophthalmic)
    "hearing", "auditor", "tinnitus", "earach", "vertigo", "otit", "cerumen", "tympan",
    "nasal", "rhinit", "sinusit", "pharyng", "laryng", "tonsil", "hoarse", "epistax",
    "visual", "strabism", "cataract", "glaucom", "retin", "conjunctiv", "cornea",
    # Mental, Behavioral, Affective & Cognitive
    "depress", "anhedon", "enjoyment", "pleasur", "anxiet", "anxious", "panic",
    "insomnia", "sleepless", "nightmare", "bipolar", "psychiatr", "psycholog",
    "hallucinat", "delusion", "schizo", "suicid", "manic", "euphor", "phobi",
    "obsess", "compuls", "hopeless", "worthless", "appetit", "paranoi", "dementi",
    "deliri", "amnesi", "neurotic", "agitat", "restless", "dysthymi", "cognitive",
    "concentrat",
    # Systemic, Somatic & Neuromuscular
    "swollen", "swelling", "exhaust", "letharg", "urina", "urinat", "gastric", "paralys"
}

# Backward compatibility alias for tests
CLINICAL_STEMS = EXACT_CLINICAL_WORDS | CLINICAL_PREFIXES

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


def check_safety_violation(text: str) -> Optional[str]:
    """Deterministically intercept threats, violent language, or self-harm in < 0.1ms."""
    clean = text.strip()
    if not clean:
        return None

    if SELF_HARM_PATTERN.search(clean):
        return (
            "> [!CAUTION]\n"
            "> **Immediate Crisis Support & Safety Assistance**\n\n"
            "If you or someone you know is experiencing thoughts of self-harm or suicide, please connect with emergency support immediately:\n"
            "- **In the US / Canada**: Call or text **988** for the Suicide & Crisis Lifeline (free, confidential, 24/7).\n"
            "- **In the UK**: Call **111** or reach Samaritans at **116 123**.\n"
            "- **In India**: Call **112** (Emergency) or **9152987821** (KIRAN Mental Health Helpline).\n"
            "- **Worldwide**: Contact your nearest emergency department or local emergency services immediately.\n\n"
            "PreDoc AI is an informational clinical decision support tool and cannot provide crisis or mental health emergency interventions."
        )

    if THREAT_OR_VIOLENCE_PATTERN.search(clean):
        return (
            "> [!WARNING]\n"
            "> **Safety Policy Notice: Threatening or Violent Language Prohibited**\n\n"
            "PreDoc AI is a professional clinical decision support and medical triage reference system. "
            "Threats of violence, abusive language, and non-clinical hostile inputs are strictly prohibited.\n\n"
            "To receive medical triage and diagnostic guidance, please describe authentic clinical symptoms, for example:\n"
            "- *\"Substernal chest tightness with diaphoresis for 45 minutes\"*\n"
            "- *\"High fever, productive cough, and chills for 3 days\"*\n"
            "- *\"Sudden onset unilateral facial weakness and slurred speech\"*"
        )

    return None


def is_clinical_query(text: str) -> bool:
    """Validate whether input describes clinical signs, symptoms, anatomy, or diagnostic inquiries."""
    clean = text.strip().lower()
    if not clean:
        return False

    # Immediate rejection if safety violation detected
    if check_safety_violation(clean):
        return False

    words = re.findall(r"\w+", clean)
    if not words:
        return False

    # Check for direct conversational chatter
    for pat in NON_CLINICAL_PATTERNS:
        if re.search(pat, clean):
            # Only consider clinical if it also contains valid clinical terms
            has_clinical = any(
                w in EXACT_CLINICAL_WORDS or any(w.startswith(p) for p in CLINICAL_PREFIXES)
                for w in words
            )
            if not has_clinical:
                return False

    # Strict token-level matching: exact for short words, prefix for long medical stems
    return any(
        w in EXACT_CLINICAL_WORDS or any(w.startswith(p) for p in CLINICAL_PREFIXES)
        for w in words
    )
