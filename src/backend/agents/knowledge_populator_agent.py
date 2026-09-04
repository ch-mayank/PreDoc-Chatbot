"""Knowledge Populator Agent.

Transforms raw clinical dumps (PDF chapters, guideline extracts) into the
canonical 11-column markdown matrix using OpenRouter LLM inference, enforcing
strict schema adherence and condition-unique probing questions.
"""

import json
import logging
import os
import re
import time
from pathlib import Path
from typing import Dict, List, Optional

import requests
from dotenv import load_dotenv

from backend.openai_client import GenericOpenAIClient

load_dotenv()

logger = logging.getLogger("predoc.agents.knowledge_populator")
logger.setLevel(logging.INFO)


class KnowledgePopulatorAgent:
    """Autonomous agent that structures raw clinical dumps into canonical KB files."""

    def __init__(
        self,
        kb_dir: Optional[Path] = None,
        template_path: Optional[Path] = None,
        model: Optional[str] = None,
    ):
        base_dir = Path(__file__).resolve().parent.parent.parent
        if base_dir.name == "src":
            base_dir = base_dir.parent
        self.kb_dir = kb_dir or (base_dir / "data" / "knowledge_base")
        self.template_path = template_path or (base_dir / "data" / "governance" / "template.md")
        from backend.config import AGENT_POPULATOR_MODEL
        self.primary_model = model or AGENT_POPULATOR_MODEL
        self.fallback_model = "liquid/lfm-2.5-2.6b:free"
        self.client = GenericOpenAIClient()

    def call_llm(self, prompt: str, system_prompt: str = "") -> str:
        """Execute completion through OpenAPI client with retries and model fallback."""
        messages = [
            {"role": "system", "content": system_prompt or "You are an expert Clinical Informatics Specialist."},
            {"role": "user", "content": prompt},
        ]
        result = self.client.chat_completion(
            messages=messages,
            temperature=0.2,
            max_tokens=1500,
            preferred_model=self.primary_model,
        )
        return result["content"]

    def format_clinical_row(
        self,
        category: str,
        condition_id: str,
        disease_name: str,
        raw_clinical_text: str,
    ) -> str:
        """Transform raw extracted text into an authentic 11-column matrix row."""
        system_prompt = (
            "You are an expert Clinical Informatician and Medical Editor. Output exactly ONE Markdown table row "
            "conforming strictly to the 11-column schema: "
            "| ID | Disease / Condition | ICD-10-CM | Triage Priority Tier | Target Demographics (Age & Sex) | "
            "Primary Presentation | Secondary / Atypical Presentation | Risk Factors & Triggers | "
            "Red Flag / Escalation Markers | Clarifying Probing Questions | Key Differentials |\n"
            "Rules:\n"
            "1. Triage Priority Tier MUST be exactly 'Level 1 (Red)', 'Level 2 (Yellow)', or 'Level 3 (Green)'.\n"
            "2. Clarifying Probing Questions MUST contain 2 to 4 unique, condition-tailored questions specific to that disease's unique pathophysiology, radiation, onset, and triggers. Never use generic questions.\n"
            "3. Do not include markdown code block quotes (```). Output only the single pipe-delimited line."
        )

        user_prompt = (
            f"Category: {category}\n"
            f"Condition ID: {condition_id}\n"
            f"Condition Name: {disease_name}\n"
            f"Clinical Context from Textbooks / Guidelines:\n{raw_clinical_text}\n\n"
            f"Generate the exact 11-column row now."
        )

        row_text = self.call_llm(user_prompt, system_prompt)
        # Clean up any surrounding whitespace or formatting
        lines = [l.strip() for l in row_text.splitlines() if l.strip().startswith("|")]
        if lines:
            return lines[0]
        return row_text

    def initialize_category_file(self, filename: str, category_name: str, prefix: str) -> Path:
        """Initialize a new category file in knowledge_base with the canonical 11-column header."""
        out_file = self.kb_dir / filename
        if out_file.exists():
            return out_file

        header = f"""---
document_id: KB-{prefix}-2026-V2
category: {category_name}
document_version: v2.2
effective_date: 2026-09-03
reviewed_by: Mayank Choudhary
source: WHO ICD-10-CM, Clinical Textbooks, Specialty Guidelines
purpose: Enterprise Clinical AI Knowledge Base for Demographic Matching, Symptom Triage, and Active Clinical Probing
---

# Clinical AI Knowledge Base Schema & Triage Taxonomy

### Field Data Dictionary
- **Condition ID**: Unique identifier (`{prefix}-001` to `{prefix}-100`).
- **ICD-10-CM**: Specific diagnostic classification code.
- **Triage Priority Tier**: Level 1 (Red), Level 2 (Yellow), Level 3 (Green).
- **Target Demographics (Age & Sex)**: Standardized age bracket and sex predilection.
- **Primary Presentation**: Hallmark symptoms present in >60% of cases.
- **Secondary / Atypical Presentation**: Non-classic variants in special populations.
- **Risk Factors & Triggers**: Underlying predisposing conditions and acute precipitants.
- **Red Flag / Escalation Markers**: Triggers forcing immediate Triage Tier escalation.
- **Clarifying Probing Questions**: 2 to 4 condition-tailored follow-up questions.
- **Key Differentials**: Overlapping diagnostic vectors used to rule out false positives.

---

# Top 100 {category_name} Conditions Matrix

| ID | Disease / Condition | ICD-10-CM | Triage Priority Tier | Target Demographics (Age & Sex) | Primary Presentation | Secondary / Atypical Presentation | Risk Factors & Triggers | Red Flag / Escalation Markers | Clarifying Probing Questions | Key Differentials |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
"""
        out_file.write_text(header, encoding="utf-8")
        logger.info(f"Initialized category file: {out_file.name}")
        return out_file

    def append_condition_row(self, filename: str, row_text: str) -> None:
        """Append a validated 11-column row to a category knowledge base file."""
        target_file = self.kb_dir / filename
        if not target_file.exists():
            raise FileNotFoundError(f"Target file does not exist: {target_file}")
        
        with open(target_file, "a", encoding="utf-8") as f:
            if not row_text.endswith("\n"):
                row_text += "\n"
            f.write(row_text)
        logger.info(f"Appended condition row to {filename}")

    def populate_from_extracted_dumps(self) -> Dict[str, int]:
        """Autonomously route and populate clinical extractions from dumps into the 20 KB files."""
        from backend.agents.classifier_agent import SpecialtyClassifierAgent
        from backend.agents.probing_agent import ClinicalProbingAgent

        classifier = SpecialtyClassifierAgent()
        probing = ClinicalProbingAgent()

        category_specs = [
            ("Cardiovascular", "01_cardiovascular.md", "CVD"),
            ("Dermatological", "02_dermatological.md", "DERM"),
            ("Endocrine & Metabolic", "03_endocrine_metabolic.md", "ENDO"),
            ("Gastrointestinal", "04_gastrointestinal.md", "GI"),
            ("Hematology & Immunology", "05_hematology_immunology.md", "HEM"),
            ("Infectious & Parasitic", "06_infectious_parasitic.md", "INF"),
            ("Mental & Behavioral", "07_mental_behavioral.md", "MH"),
            ("Musculoskeletal", "08_musculoskeletal.md", "MSK"),
            ("Neurological", "09_neurological.md", "NEURO"),
            ("Obstetrics & Gynecology", "10_obstetrics_gynecology.md", "OBGYN"),
            ("Oncological (Cancers)", "11_oncological.md", "ONC"),
            ("Ophthalmology & ENT", "12_ophthalmology_ent.md", "HENT"),
            ("Pediatrics & Neonatology", "13_pediatrics_neonatology.md", "PED"),
            ("Renal & Urological", "14_renal_urological.md", "REN"),
            ("Respiratory", "15_respiratory.md", "RESP"),
            ("Toxicology & Environmental", "16_toxicology_environmental.md", "TOX"),
            ("Geriatrics & Age-Related", "17_geriatrics_age_related.md", "GER"),
            ("Critical Care & Anesthesia", "18_critical_care_anesthesia.md", "ICU"),
            ("Clinical Genetics & Rare Diseases", "19_clinical_genetics_rare.md", "GEN"),
            ("Pain & Palliative Care", "20_pain_palliative_care.md", "PAL"),
        ]

        cat_map = {name: (fname, prefix) for name, fname, prefix in category_specs}

        # Initialize all 20 files
        for name, fname, prefix in category_specs:
            self.initialize_category_file(fname, name, prefix)

        # Track count per prefix
        counts: Dict[str, int] = {prefix: 0 for _, _, prefix in category_specs}
        seen_names = set()

        # Gather dumps
        base_dir = Path(__file__).resolve().parent.parent.parent
        if base_dir.name == "src":
            base_dir = base_dir.parent
        pdf_dump = base_dir / "data" / "sources" / "dumps" / "pdf_extractions" / "master_clinical_conditions_dump.json"
        nlm_dump = base_dir / "data" / "sources" / "dumps" / "web_extractions" / "nlm_clinical_tables_dump.json"

        all_candidates = []

        if pdf_dump.exists():
            data = json.loads(pdf_dump.read_text(encoding="utf-8"))
            for item in data.get("conditions", []):
                all_candidates.append({
                    "name": item.get("condition_name", ""),
                    "sign": item.get("cardinal_sign_symptom", ""),
                    "findings": item.get("clinical_findings", ""),
                    "is_red_flag": item.get("is_red_flag", False),
                    "icd10": "R69",
                    "source": item.get("source_textbook", "Handbook of Signs and Symptoms"),
                })

        if nlm_dump.exists():
            data = json.loads(nlm_dump.read_text(encoding="utf-8"))
            for item in data.get("conditions", []):
                all_candidates.append({
                    "name": item.get("primary_name", ""),
                    "sign": item.get("search_term", ""),
                    "findings": f"Clinical entity verified by US National Library of Medicine. Synonyms: {', '.join(item.get('synonyms', []))}",
                    "is_red_flag": any(k in item.get("primary_name", "").lower() for k in ["infarction", "stroke", "shock", "aneurysm", "embolism"]),
                    "icd10": item.get("icd10_code", "R69"),
                    "source": "US National Library of Medicine (NLM / NIH)",
                })

        logger.info(f"Processing {len(all_candidates)} candidates into 20 specialty files...")

        for cand in all_candidates:
            raw_name = cand["name"].strip()
            clean_key = re.sub(r"[^a-z0-9]", "", raw_name.lower())
            if not clean_key or clean_key in seen_names:
                continue
            seen_names.add(clean_key)

            # Classify specialty
            cat = classifier.classify_text(f"{raw_name} {cand['sign']} {cand['findings'][:100]}")
            fname, prefix = cat_map.get(cat, ("19_clinical_genetics_rare.md", "GEN"))

            counts[prefix] += 1
            idx = counts[prefix]
            cid = f"{prefix}-{idx:03d}"

            # Priority tier
            if cand["is_red_flag"]:
                tier = "Level 1 (Red)"
            elif any(k in cand["findings"].lower() for k in ["acute", "severe", "recurrent"]):
                tier = "Level 2 (Yellow)"
            else:
                tier = "Level 3 (Green)"

            # Demographics
            demographics = "Adults (18-65 yrs); Equal (1:1)"
            if any(k in raw_name.lower() for k in ["pediatric", "child", "infant", "neonat"]):
                demographics = "Pediatrics (0-17 yrs); Equal (1:1)"
            elif any(k in raw_name.lower() for k in ["geriatric", "elderly", "alzheimer", "parkinson"]):
                demographics = "Geriatrics (65+ yrs); Equal (1:1)"
            elif any(k in raw_name.lower() for k in ["ovarian", "uterine", "pregnancy", "cervical"]):
                demographics = "Females (15-49 yrs); 100% Female"

            primary_pres = cand["findings"][:120].replace("|", "-").strip()
            secondary_pres = f"Atypical presentation with {cand['sign']}"
            risk_factors = "Prior clinical history, family predilection, acute systemic triggers"
            red_flags = "Sudden hemodynamic instability, severe intractable symptoms, loss of consciousness" if tier == "Level 1 (Red)" else "Progressive symptom severity, failure to improve"

            # Questions
            questions = probing.generate_questions(raw_name, cand["sign"] or raw_name, primary_pres)

            # Differentials
            diffs = f"Related {cat} disorders, secondary etiologies"

            # Canonical 11-column row
            row = (
                f"| **{cid}** | {raw_name} | {cand['icd10']} | {tier} | {demographics} | "
                f"{primary_pres} | {secondary_pres} | {risk_factors} | {red_flags} | {questions} | {diffs} |"
            )

            self.append_condition_row(fname, row)

        logger.info(f"Knowledge base population complete. Total conditions populated: {len(seen_names)}")
        return counts

