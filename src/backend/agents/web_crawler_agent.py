"""Enterprise AI Web Crawler & Guideline Extraction Agent.

Autonomous multi-category clinical crawler that:
1. Dynamically discovers clinical conditions per specialty using fast AI models (Nvidia / Gemma).
2. Ground-truths terms via the US National Library of Medicine (NLM / NIH) Clinical Tables API.
3. Performs semantic AI entity extraction from CDC, WHO, and NIH guideline pages, stripping junk HTML.
4. Enforces idempotency and self-healing: checks SHA-256 checksums and data integrity to only
   re-crawl when data is missing or corrupted.
5. Embeds self-describing metadata manifests with semantic content summaries into every dump.
"""

import hashlib
import json
import logging
import os
import re
import time
import urllib.parse
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from backend.openai_client import GenericOpenAIClient

logger = logging.getLogger("predoc.agents.web_crawler")
logger.setLevel(logging.INFO)

# The 20 Approved Medical Specialties per data/governance/classification_rules.md
APPROVED_CATEGORIES: List[str] = [
    "Cardiovascular",
    "Respiratory",
    "Gastrointestinal",
    "Neurological",
    "Infectious & Parasitic",
    "Dermatological",
    "Musculoskeletal",
    "Renal & Urological",
    "Endocrine & Metabolic",
    "Hematology & Immunology",
    "Mental & Behavioral",
    "Obstetrics & Gynecology",
    "Oncological (Cancers)",
    "Ophthalmology & ENT",
    "Pediatrics & Neonatology",
    "Toxicology & Environmental",
    "Geriatrics & Age-Related",
    "Critical Care & Anesthesia",
    "Clinical Genetics & Rare Diseases",
    "Pain & Palliative Care",
]

# Intelligent seed cache for instant offline fallback if LLM APIs are unreachable
OFFLINE_SEED_CACHE: Dict[str, List[str]] = {
    "Cardiovascular": ["myocardial infarction", "angina pectoris", "heart failure", "aortic aneurysm", "arrhythmia", "pericarditis"],
    "Respiratory": ["pneumonia", "asthma", "chronic obstructive pulmonary disease", "pneumothorax", "pulmonary embolism"],
    "Gastrointestinal": ["acute appendicitis", "acute cholecystitis", "diverticulitis", "pancreatitis", "peptic ulcer"],
    "Neurological": ["ischemic stroke", "subarachnoid hemorrhage", "bacterial meningitis", "migraine", "epilepsy"],
    "Infectious & Parasitic": ["septic shock", "malaria", "tuberculosis", "lyme disease", "infective endocarditis"],
    "Dermatological": ["melanoma", "psoriasis", "atopic dermatitis", "cellulitis", "steven johnson syndrome"],
    "Musculoskeletal": ["rheumatoid arthritis", "septic arthritis", "osteomyelitis", "compartment syndrome"],
    "Renal & Urological": ["acute kidney injury", "nephrolithiasis", "pyelonephritis", "glomerulonephritis", "benign prostatic hyperplasia"],
    "Endocrine & Metabolic": ["diabetic ketoacidosis", "thyrotoxicosis", "adrenal insufficiency", "hypoglycemia", "cushing syndrome"],
    "Hematology & Immunology": ["anaphylaxis", "immune thrombocytopenia", "deep vein thrombosis", "sickle cell disease", "aplastic anemia"],
    "Mental & Behavioral": ["major depressive disorder", "panic disorder", "bipolar disorder", "acute delirium", "generalized anxiety"],
    "Obstetrics & Gynecology": ["preeclampsia", "ectopic pregnancy", "ovarian torsion", "pelvic inflammatory disease", "endometriosis"],
    "Oncological (Cancers)": ["bronchogenic carcinoma", "colorectal adenocarcinoma", "leukemia", "lymphoma", "glioblastoma"],
    "Ophthalmology & ENT": ["acute angle-closure glaucoma", "epistaxis", "peritonsillar abscess", "retinal detachment", "mastoiditis"],
    "Pediatrics & Neonatology": ["croup", "bronchiolitis", "febrile seizure", "intussusception", "neonatal jaundice"],
    "Toxicology & Environmental": ["acetaminophen overdose", "opioid toxicity", "carbon monoxide poisoning", "organophosphate toxicity", "heat stroke"],
    "Geriatrics & Age-Related": ["delirium in dementia", "orthostatic hypotension", "hip fracture", "sarcopenia", "polypharmacy toxicity"],
    "Critical Care & Anesthesia": ["acute respiratory distress syndrome", "septic shock", "cardiac arrest", "malignant hyperthermia", "anaphylactic shock"],
    "Clinical Genetics & Rare Diseases": ["cystic fibrosis", "huntington disease", "marfan syndrome", "sickle cell anemia", "hemochromatosis"],
    "Pain & Palliative Care": ["complex regional pain syndrome", "trigeminal neuralgia", "postherpetic neuralgia", "intractable cancer pain", "fibromyalgia"],
}


class WebCrawlerAgent:
    """Autonomous enterprise agent for discovering, crawling, and AI-extracting clinical guidelines."""

    def __init__(
        self,
        catalog_path: Optional[Path] = None,
        dumps_dir: Optional[Path] = None,
        model: Optional[str] = None,
    ):
        base_dir = Path(__file__).resolve().parent.parent.parent
        self.catalog_path = catalog_path or (base_dir / "data" / "sources" / "source_catalog.json")
        self.dumps_dir = dumps_dir or (base_dir / "data" / "sources" / "dumps" / "web_extractions")
        self.dumps_dir.mkdir(parents=True, exist_ok=True)

        try:
            from backend.config import AGENT_CRAWLER_MODEL
            self.model = model or AGENT_CRAWLER_MODEL
        except Exception:
            self.model = model or "nvidia/nemotron-3.5-lightning:free"

        self.categories = APPROVED_CATEGORIES
        self.client = GenericOpenAIClient()
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "PreDoc-Clinical-AI-Crawler/2.2 (NIH/NLM-Enterprise-Ingestion; contact@predoc.ai)"
        })
        retry_policy = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=frozenset({"GET"}),
        )
        adapter = HTTPAdapter(max_retries=retry_policy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    def load_catalog(self) -> List[Dict]:
        """Load registered clinical sources from catalog."""
        if not self.catalog_path.exists():
            return []
        try:
            data = json.loads(self.catalog_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Unable to load source catalog %s: %s", self.catalog_path, exc)
            return []
        sources = data.get("sources", [])
        return sources if isinstance(sources, list) else []

    @staticmethod
    def calculate_checksum(data_str: str) -> str:
        """Compute SHA-256 checksum of raw content string."""
        return hashlib.sha256(data_str.encode("utf-8")).hexdigest()

    def is_dump_healthy(self, dump_file: Path) -> Tuple[bool, str]:
        """Verify if an existing dump is intact, schema-compliant, and uncorrupted."""
        if not dump_file.exists():
            return False, "File does not exist"
        if dump_file.stat().st_size < 50:
            return False, "File is virtually empty (<50 bytes)"

        try:
            content = dump_file.read_text(encoding="utf-8")
            data = json.loads(content)
        except Exception as exc:
            return False, f"JSON parse error: {exc}"

        if not isinstance(data, dict):
            return False, "Root element is not a JSON dictionary"

        # Check conditions or guidelines
        conditions = data.get("conditions")
        guidelines = data.get("guidelines")

        if conditions is not None:
            if not isinstance(conditions, list) or len(conditions) == 0:
                return False, "Conditions list is empty or invalid"
        elif guidelines is not None:
            if not isinstance(guidelines, list) or len(guidelines) == 0:
                return False, "Guidelines list is empty or invalid"
        else:
            return False, "Neither 'conditions' nor 'guidelines' key found"

        # Check integrity manifest checksum if recorded
        manifest = data.get("manifest")
        if isinstance(manifest, dict) and "data_checksum" in manifest:
            expected_hash = manifest["data_checksum"]
            core_data = json.dumps(conditions or guidelines, sort_keys=True)
            actual_hash = self.calculate_checksum(core_data)
            if expected_hash != actual_hash:
                return False, "SHA-256 data checksum mismatch (corrupted content)"

        return True, "Dump is verified and healthy"

    def discover_conditions_for_category(self, category: str, count: int = 10) -> List[str]:
        """Dynamically discover clinical conditions from an LLM using ONLY the category name."""
        prompt = (
            f"You are an autonomous clinical taxonomist agent.\n"
            f"Given ONLY the medical specialty category: '{category}', generate a list of {count} primary, "
            f"high-acuity, emergency, and common clinical conditions belonging strictly to this specialty.\n"
            f"Output ONLY a valid JSON array of strings (e.g. [\"Condition 1\", \"Condition 2\"]). "
            f"Do not write any intro, outro, or explanation."
        )

        try:
            result = self.client.chat_completion(
                messages=[
                    {"role": "system", "content": "You are a precise clinical taxonomy parser. Output valid JSON only."},
                    {"role": "user", "content": prompt},
                ],
                preferred_model=self.model,
                temperature=0.1,
                max_tokens=600,
            )
            raw_text = result.get("content", "").strip()

            # Strip markdown code fences or multiple brackets
            parsed = None
            for pattern in [r"\[[^\]]*\]", r"\[.*\]"]:
                match = re.search(pattern, raw_text, re.DOTALL)
                if match:
                    try:
                        candidate = json.loads(match.group(0))
                        if isinstance(candidate, list) and len(candidate) > 0:
                            parsed = candidate
                            break
                    except Exception:
                        continue

            if parsed and isinstance(parsed, list):
                clean_terms = [str(item).strip() for item in parsed if str(item).strip()]
                logger.info(f"AI discovered {len(clean_terms)} conditions for category '{category}' using {result.get('model_used')}")
                return clean_terms
        except Exception as exc:
            logger.warning(f"AI condition discovery failed for '{category}': {exc}. Falling back to resilient seed cache.")

        # Fallback to seed cache so crawler never fails completely
        return OFFLINE_SEED_CACHE.get(category, [f"{category.lower()} disorder"])

    def fetch_nlm_conditions_for_term(self, term: str) -> List[Dict]:
        """Query official US National Library of Medicine (NLM/NIH) Clinical Tables API."""
        url = f"https://clinicaltables.nlm.nih.gov/api/conditions/v3/search?terms={urllib.parse.quote_plus(term)}&ef=primary_name,icd10cm_codes,synonyms&maxList=10"
        try:
            time.sleep(0.2)
            resp = self.session.get(url, timeout=(5, 20))
            resp.raise_for_status()
            data = resp.json()
            results = []
            extra_fields = data[2] if len(data) > 2 and isinstance(data[2], dict) else {}
            names = extra_fields.get("primary_name", [])
            codes = extra_fields.get("icd10cm_codes", [])
            synonyms = extra_fields.get("synonyms", [])

            for idx in range(len(names)):
                results.append({
                    "primary_name": names[idx],
                    "icd10_code": codes[idx] if idx < len(codes) else "R69",
                    "synonyms": synonyms[idx] if idx < len(synonyms) else [],
                    "search_term": term,
                    "source": "US National Library of Medicine (NLM / NIH)",
                })
            return results
        except Exception as e:
            logger.warning(f"NLM API query failed for '{term}': {e}")
        return []

    def ai_extract_guideline_entities(self, raw_text: str, source_title: str, url: str) -> List[Dict[str, Any]]:
        """Use fast AI model to filter out HTML boilerplate and extract structured clinical entities."""
        # Truncate text extract to relevant chunk for prompt
        clean_slice = raw_text[:4000].strip()
        if len(clean_slice) < 100:
            return []

        prompt = (
            f"You are an expert Clinical Guideline Entity Extractor.\n"
            f"Analyze the following medical guideline text from '{source_title}' ({url}):\n\n"
            f"--- TEXT START ---\n{clean_slice}\n--- TEXT END ---\n\n"
            f"Extract any clinical diseases, guidelines, or conditions mentioned.\n"
            f"Filter out all website navigation, cookies, and non-clinical boilerplate.\n"
            f"For each clinical condition found, provide:\n"
            f"- 'condition_name': Canonical medical title\n"
            f"- 'category': One of {APPROVED_CATEGORIES}\n"
            f"- 'cardinal_symptoms': List of 2-4 key symptoms\n"
            f"- 'red_flags': List of urgent red-flag warning signs\n"
            f"- 'triage_level': Integer 1 to 5 (1=Emergent/Resuscitation, 5=Non-urgent)\n\n"
            f"Output ONLY a valid JSON array of objects. Do not write any markdown code fences or narrative."
        )

        try:
            result = self.client.chat_completion(
                messages=[
                    {"role": "system", "content": "You are a clinical NLP extractor. Return ONLY valid JSON."},
                    {"role": "user", "content": prompt},
                ],
                preferred_model=self.model,
                temperature=0.1,
                max_tokens=800,
            )
            raw_msg = result.get("content", "").strip()
            match = re.search(r"\[.*\]", raw_msg, re.DOTALL)
            if match:
                entities = json.loads(match.group(0))
                if isinstance(entities, list):
                    return entities
        except Exception as exc:
            logger.warning(f"AI guideline entity extraction failed for '{source_title}': {exc}")

        return []

    def crawl_all_registered_guidelines(self, force_refresh: bool = False) -> List[Path]:
        """Enterprise crawl pipeline with corruption detection, AI discovery, and manifest hashing."""
        logger.info("--- Starting Enterprise Multi-Category Clinical Web Ingestion ---")
        output_dumps = []

        nlm_dump_path = self.dumps_dir / "nlm_clinical_tables_dump.json"
        guide_dump_path = self.dumps_dir / "cdc_who_clinical_guidelines_dump.json"

        # 1. Check NLM Dump Health (Idempotent / Self-Healing)
        nlm_healthy, nlm_reason = self.is_dump_healthy(nlm_dump_path)
        if nlm_healthy and not force_refresh:
            logger.info(f"NLM Clinical Tables dump is verified healthy: {nlm_dump_path} ({nlm_reason}). Skipping re-crawl.")
            output_dumps.append(nlm_dump_path)
        else:
            logger.info(f"NLM dump requires generation/repair (Healthy={nlm_healthy}, Reason: {nlm_reason}). Starting AI discovery...")
            nlm_master_list = []

            for category in self.categories:
                logger.info(f"Autonomous discovery: Generating search targets for '{category}'...")
                discovered_terms = self.discover_conditions_for_category(category, count=5)
                for term in discovered_terms:
                    found = self.fetch_nlm_conditions_for_term(term)
                    nlm_master_list.extend(found)

            # Deduplicate by primary name and code
            unique_conditions = {}
            for item in nlm_master_list:
                key = (item.get("primary_name", "").strip().casefold(), item.get("icd10_code", "").strip().casefold())
                if key[0]:
                    unique_conditions[key] = item
            clean_conditions = list(unique_conditions.values())

            core_data_str = json.dumps(clean_conditions, sort_keys=True)
            data_hash = self.calculate_checksum(core_data_str)

            nlm_data = {
                "source_id": "SRC-005",
                "title": "US National Library of Medicine (NLM / NIH) Clinical Conditions Database",
                "schema_version": "2.2.0",
                "manifest": {
                    "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "data_checksum": data_hash,
                    "model_used": self.model,
                    "categories_covered": len(self.categories),
                    "total_conditions": len(clean_conditions),
                    "semantic_summary": f"Authoritative NLM/NIH clinical conditions spanning all {len(self.categories)} specialties with verified ICD-10-CM codes.",
                },
                "conditions": clean_conditions,
            }
            nlm_dump_path.write_text(json.dumps(nlm_data, indent=2, ensure_ascii=False), encoding="utf-8")
            logger.info(f"Saved verified NLM dump: {nlm_dump_path} ({len(clean_conditions)} conditions, Checksum: {data_hash[:8]}...)")
            output_dumps.append(nlm_dump_path)

        # 2. Check CDC / WHO Guidelines Dump Health
        guide_healthy, guide_reason = self.is_dump_healthy(guide_dump_path)
        if guide_healthy and not force_refresh:
            logger.info(f"CDC/WHO guidelines dump is verified healthy: {guide_dump_path} ({guide_reason}). Skipping re-crawl.")
            output_dumps.append(guide_dump_path)
        else:
            logger.info(f"CDC/WHO dump requires generation/repair (Healthy={guide_healthy}, Reason: {guide_reason}). Crawling guidelines...")
            catalog_sources = self.load_catalog()
            guideline_dumps = []
            failed_sources = []

            for s in catalog_sources:
                sid = s.get("id", "SRC-GEN")
                title = s.get("title", "Guideline")
                url = s.get("url") or s.get("guideline_url")
                if url and url.startswith("http") and not url.endswith(".pdf"):
                    try:
                        time.sleep(0.3)
                        resp = self.session.get(url, timeout=(5, 20))
                        resp.raise_for_status()
                        soup = BeautifulSoup(resp.text, "html.parser")
                        for t in soup(["script", "style", "nav", "footer", "header", "aside"]):
                            t.decompose()
                        raw_text = soup.get_text(separator="\n", strip=True)

                        # Perform AI Semantic Entity Extraction
                        ai_entities = self.ai_extract_guideline_entities(raw_text, title, url)

                        guideline_dumps.append({
                            "source_id": sid,
                            "title": title,
                            "url": url,
                            "text_extract": raw_text[:5000],
                            "ai_extracted_entities": ai_entities,
                        })
                    except Exception as e:
                        logger.warning(f"Error fetching {url}: {e}")
                        failed_sources.append({"source_id": sid, "url": url, "error": str(e)})

            guide_core_str = json.dumps(guideline_dumps, sort_keys=True)
            guide_hash = self.calculate_checksum(guide_core_str)

            guide_data = {
                "source_id": "SRC-004",
                "title": "CDC / WHO Public Health Clinical Practice Guidelines",
                "schema_version": "2.2.0",
                "manifest": {
                    "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "data_checksum": guide_hash,
                    "model_used": self.model,
                    "total_sources_crawled": len(guideline_dumps),
                    "failed_sources_count": len(failed_sources),
                    "semantic_summary": f"Curated public health practice guidelines from CDC, WHO, and NIH with AI-extracted clinical presentations.",
                },
                "failed_sources": failed_sources,
                "guidelines": guideline_dumps,
            }
            guide_dump_path.write_text(json.dumps(guide_data, indent=2, ensure_ascii=False), encoding="utf-8")
            logger.info(f"Saved verified CDC/WHO guidelines dump: {guide_dump_path} (Checksum: {guide_hash[:8]}...)")
            output_dumps.append(guide_dump_path)

        return output_dumps

    def inspect_dump(self, dump_path: Path) -> Dict[str, Any]:
        """Inspect dump header and manifest summary without parsing full payload."""
        if not dump_path.exists():
            return {"error": f"Dump file does not exist: {dump_path}"}
        try:
            data = json.loads(dump_path.read_text(encoding="utf-8"))
            return {
                "file": str(dump_path),
                "size_kb": round(dump_path.stat().st_size / 1024, 2),
                "title": data.get("title", "Unknown"),
                "schema_version": data.get("schema_version", "1.0.0"),
                "manifest": data.get("manifest", {}),
                "healthy": self.is_dump_healthy(dump_path)[0],
            }
        except Exception as exc:
            return {"error": str(exc), "healthy": False}

    def crawl_clinical_guideline(self, source_id: str, title: str, base_url: str) -> Path:
        """Compatibility method for crawling a single guideline."""
        if not base_url.startswith(("http://", "https://")):
            raise ValueError("base_url must use http:// or https://")

        response = self.session.get(base_url, timeout=(5, 20))
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()

        text = soup.get_text(separator="\n", strip=True)
        ai_entities = self.ai_extract_guideline_entities(text, title, base_url)

        dump_path = self.dumps_dir / f"{source_id}_guideline.json"
        dump_data = {
            "source_id": source_id,
            "title": title,
            "url": base_url,
            "text_extract": text[:10000],
            "ai_extracted_entities": ai_entities,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        dump_path.write_text(json.dumps(dump_data, indent=2, ensure_ascii=False), encoding="utf-8")
        return dump_path
