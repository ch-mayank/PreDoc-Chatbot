"""Specialty Classifier Agent.

Classifies incoming clinical text, symptoms, or source medical guidelines into one of the 20
approved medical specialties following data/governance/classification_rules.md.
"""

from typing import List, Dict, Any, Optional

ALLOWED_CATEGORIES = [
    "Cardiovascular",
    "Dermatological",
    "Endocrine & Metabolic",
    "Gastrointestinal",
    "Hematology & Immunology",
    "Infectious & Parasitic",
    "Mental & Behavioral",
    "Musculoskeletal",
    "Neurological",
    "Obstetrics & Gynecology",
    "Oncological (Cancers)",
    "Ophthalmology & ENT",
    "Pediatrics & Neonatology",
    "Renal & Urological",
    "Respiratory",
    "Toxicology & Environmental",
    "Geriatrics & Age-Related",
    "Critical Care & Anesthesia",
    "Clinical Genetics & Rare Diseases",
    "Pain & Palliative Care",
]


class SpecialtyClassifierAgent:
    """Agent that classifies clinical conditions into 20 medical specialties."""

    def __init__(self, model: Optional[str] = None):
        self.categories = ALLOWED_CATEGORIES
        from backend.config import AGENT_CLASSIFIER_MODEL
        self.model = model or AGENT_CLASSIFIER_MODEL

    def classify_text(self, text: str) -> str:
        """Rule-based and semantic classification of clinical text into a specialty."""
        t_lower = text.lower()

        # Keyword mapping vectors
        mappings = {
            "Cardiovascular": ["heart", "cardio", "stemi", "angina", "aortic", "pericarditis", "arrhythmia", "edema", "hypertension", "infarction", "chest pain", "chest pressure", "palpitation", "syncope", "cardiac"],
            "Dermatological": ["skin", "rash", "eczema", "psoriasis", "lesion", "dermatitis", "melanoma", "pruritus", "erythema", "macule"],
            "Endocrine & Metabolic": ["thyroid", "diabetes", "adrenal", "pituitary", "glucose", "insulin", "ketoacidosis", "cushing", "hashimoto"],
            "Gastrointestinal": ["stomach", "bowel", "colon", "liver", "pancreas", "hepatitis", "gallbladder", "appendicitis", "gerd", "ulcer", "abdominal"],
            "Hematology & Immunology": ["anemia", "leukemia", "platelet", "hemophilia", "thrombosis", "lymphoma", "neutropenia", "spleen", "marrow"],
            "Infectious & Parasitic": ["fever", "virus", "bacterial", "infection", "sepsis", "malaria", "tuberculosis", "fungal", "parasite"],
            "Mental & Behavioral": ["depression", "anxiety", "schizophrenia", "bipolar", "psychosis", "ptsd", "panic", "dementia", "delirium"],
            "Musculoskeletal": ["joint", "bone", "arthritis", "fracture", "osteoporosis", "tendon", "muscle", "lupus", "rheumatoid", "spine"],
            "Neurological": ["brain", "seizure", "stroke", "migraine", "nerve", "neuropathy", "paralysis", "epilepsy", "sclerosis", "coma", "headache"],
            "Obstetrics & Gynecology": ["ovary", "uterus", "pregnancy", "cervical", "menstruation", "vaginal", "fetal", "ectopic", "preeclampsia"],
            "Oncological (Cancers)": ["cancer", "tumor", "carcinoma", "sarcoma", "metastasis", "oncology", "malignant", "neoplasm", "chemotherapy"],
            "Ophthalmology & ENT": ["eye", "ear", "nose", "throat", "vision", "glaucoma", "tinnitus", "sinusitis", "otitis", "retinal"],
            "Pediatrics & Neonatology": ["child", "pediatric", "infant", "neonatal", "congenital", "croup", "bronchiolitis", "newborn"],
            "Renal & Urological": ["kidney", "renal", "bladder", "prostate", "nephritis", "dialysis", "urinary", "calculus", "creatinine"],
            "Respiratory": ["lung", "asthma", "pneumonia", "copd", "bronchitis", "pleural", "cough", "dyspnea", "wheezing", "hypoxia", "breath"],
            "Toxicology & Environmental": ["poison", "overdose", "toxicity", "venom", "bite", "exposure", "radiation", "heat stroke", "cyanide"],
            "Geriatrics & Age-Related": ["elderly", "geriatric", "frailty", "sarcopenia", "falls", "bedsores", "cognitive decline"],
            "Critical Care & Anesthesia": ["shock", "ards", "icic", "cico", "resuscitation", "intubation", "ventilator", "malignant hyperthermia"],
            "Clinical Genetics & Rare Diseases": ["genetic", "gene", "mutation", "syndrome", "marfan", "ehlers-danlos", "porphyria", "wilson"],
            "Pain & Palliative Care": ["chronic pain", "intractable pain", "palliative", "neuralgia", "crps", "allodynia", "hyperalgesia", "hospice", "end of life", "analgesia"]
        }

        scores = {cat: 0 for cat in self.categories}
        for cat, keywords in mappings.items():
            for kw in keywords:
                if kw in t_lower:
                    scores[cat] += 1

        best_cat = max(scores, key=scores.get)
        return best_cat if scores[best_cat] > 0 else "Cardiovascular"
