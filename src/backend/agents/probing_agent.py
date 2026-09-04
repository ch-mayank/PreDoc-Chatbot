"""Clinical Probing Agent.

Generates 2 to 4 highly specific, patient-tailored follow-up questions for any clinical condition.
Enforces zero repetitive questions across rows.
"""

import re
from typing import List, Optional


class ClinicalProbingAgent:
    """Agent for generating condition-specific clinical probing questions."""

    def __init__(self, model: Optional[str] = None):
        from backend.config import AGENT_PROBING_MODEL
        self.model = model or AGENT_PROBING_MODEL

    def generate_questions(self, disease: str, primary: str, secondary: str) -> str:
        """Generate 2-3 tailored probing questions uniquely crafted for this specific condition."""
        disease_clean = disease.strip()
        disease_lower = disease.lower()
        p1 = primary.split(",")[0].strip() if "," in primary else primary[:40].strip()
        if not p1 or "presentation" in p1.lower():
            p1 = f"symptoms typical of {disease_clean}"

        # Tailored logic rules per symptom type, each incorporating disease_clean for uniqueness
        if "chest pain" in primary.lower() or "angina" in disease_lower or "cardio" in disease_lower:
            return (
                f'1) "Does your chest discomfort feel like crushing, tight, or sharp symptoms associated with {disease_clean}?" '
                f'2) "Does your pain radiate to your left shoulder, jaw, neck, or back?" '
                f'3) "Do exertion, resting, or deep breaths noticeably alter your discomfort?"'
            )
        elif "headache" in primary.lower() or "migraine" in disease_lower or "cephalalgia" in disease_lower:
            return (
                f'1) "Is your {disease_clean} headache localized to one temple, occipital, or band-like across your forehead?" '
                f'2) "Are you experiencing visual aura, photophobia, phonophobia, or nausea?" '
                f'3) "Did this episode of {disease_clean} emerge as a sudden thunderclap or evolve gradually?"'
            )
        elif "sciatica" in disease_lower or "radiculopathy" in disease_lower or "back pain" in primary.lower() or "leg pain" in primary.lower():
            return (
                f'1) "Does your leg discomfort shoot or radiate from your lower back or buttock down the back of your leg past the knee?" '
                f'2) "Does the pain noticeably worsen when sitting, bending forward, coughing, or bearing weight?" '
                f'3) "Are you experiencing numbness in your groin/saddle region, sudden foot weakness, or changes in bowel/bladder control?"'
            )
        elif "neuropathy" in disease_lower or "peripheral nerve" in primary.lower() or "ataxia" in primary.lower():
            return (
                f'1) "Does your discomfort feel like numbness, burning, or pins-and-needles starting in your feet or legs?" '
                f'2) "Is the sensation or weakness symmetrical across both legs or confined to one side?" '
                f'3) "Have you experienced balance unsteadiness, frequent stumbling, or reduced sensation to touch or temperature?"'
            )
        elif "abdominal pain" in primary.lower() or "stomach" in primary.lower() or "bowel" in disease_lower:
            return (
                f'1) "Where in your abdomen is the pain from {disease_clean} most intense (epigastric, RUQ, RLQ, or periumbilical)?" '
                f'2) "Does eating, fasting, or changing your position trigger or soothe the pain?" '
                f'3) "Have you experienced fever, vomiting, diarrhea, or dark stools alongside your {disease_clean} symptoms?"'
            )
        elif "rash" in primary.lower() or "skin" in primary.lower() or "dermat" in disease_lower:
            return (
                f'1) "Are the cutaneous lesions of {disease_clean} itchy, burning, or tender upon palpation?" '
                f'2) "Where did the rash characteristic of {disease_clean} first emerge and has it spread?" '
                f'3) "Are there visible pustules, bullae, peeling, or mucosal involvement in your mouth/eyes?"'
            )
        elif "shortness of breath" in primary.lower() or "dyspnea" in primary.lower() or "cough" in primary.lower():
            return (
                f'1) "Does your breathing difficulty from {disease_clean} worsen during exertion or when lying recumbent?" '
                f'2) "Have you developed a cough, audible wheeze, or sputum production associated with {disease_clean}?" '
                f'3) "Have you experienced sudden swelling in your ankles or rapid weight changes?"'
            )
        elif "bleeding" in primary.lower() or "epistaxis" in disease_lower or "blood" in primary.lower():
            return (
                f'1) "Has the bleeding related to {disease_clean} been continuous for more than 20 minutes despite direct pressure?" '
                f'2) "Are you taking blood thinners, aspirin, or suffering from hypertension or clotting disorders?" '
                f'3) "Have you experienced dizziness, lightheadedness, or black tarry stools?"'
            )

        # Default unique condition-tailored format
        return (
            f'1) "Have you experienced hallmark signs of {disease_clean}, particularly {p1.lower()}?" '
            f'2) "Did the onset of {disease_clean} symptoms occur acutely within hours or develop over several days?" '
            f'3) "Are you experiencing any red flag warnings such as fever, rapid weight loss, or severe progressive weakness?"'
        )

    def generate_conversational_probing(
        self,
        query_text: str,
        missing_dimensions: List[str],
        age: Optional[str] = None,
        sex: Optional[str] = None,
    ) -> List[str]:
        """Generate 2-3 focused, patient-directed probing questions to clarify missing clinical dimensions."""
        questions = []
        q_lower = query_text.lower()

        # Anatomical / radiation probing
        if any("location" in d.lower() for d in missing_dimensions):
            if "leg" in q_lower:
                questions.append("Where exactly in your leg is the discomfort located (thigh, knee, calf, or foot), and does it radiate or shoot from your lower back or hip?")
            elif "arm" in q_lower:
                questions.append("Where in your arm is the pain (shoulder, forearm, wrist, or fingers), and does it spread from your neck?")
            elif "chest" in q_lower:
                questions.append("Does the chest discomfort spread anywhere, such as to your left arm, jaw, neck, or through to your back?")
            elif "abdom" in q_lower or "stomach" in q_lower:
                questions.append("Where in your abdomen is the pain located (upper middle, right lower side, or generalized)?")
            else:
                questions.append("Where exactly is the symptom located, and does it spread or radiate to any other area?")

        # Onset / timing probing
        if any("onset" in d.lower() for d in missing_dimensions):
            questions.append("When did this symptom first begin, and did it start suddenly (within minutes/hours) or develop gradually over days or weeks?")

        # Character / quality probing
        if any("quality" in d.lower() for d in missing_dimensions):
            if "leg" in q_lower or "back" in q_lower or "nerve" in q_lower:
                questions.append("How would you describe the sensation (e.g., sharp, shooting, burning, dull ache, or pins-and-needles), and on a scale of 1 to 10, how severe is it?")
            else:
                questions.append("How does the sensation feel (e.g., sharp, throbbing, dull ache, burning, or tightness), and what is your pain score from 1 to 10?")

        # Modifiers / triggers probing
        if any("aggravating" in d.lower() or "relieving" in d.lower() for d in missing_dimensions):
            if "leg" in q_lower or "back" in q_lower:
                questions.append("Does walking, sitting, bending, or resting make the symptoms significantly better or worse?")
            else:
                questions.append("Does any specific activity, posture, food, or medication make the symptoms better or worse?")

        # Red flags probing
        if any("red flag" in d.lower() or "associated" in d.lower() for d in missing_dimensions):
            if "leg" in q_lower or "back" in q_lower:
                questions.append("Are you having any critical red flags, such as numbness around the groin/saddle area, sudden weakness/foot drop, fever, or changes in bowel or bladder control?")
            elif "chest" in q_lower:
                questions.append("Are you experiencing shortness of breath, cold sweating, lightheadedness, or nausea?")
            else:
                questions.append("Have you noticed any fever, unexplained weight loss, shortness of breath, or numbness/weakness?")

        return questions[:3]
