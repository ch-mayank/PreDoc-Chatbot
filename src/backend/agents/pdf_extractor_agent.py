"""PDF Extractor Agent for Clinical Reference Textbooks.

Deep scans authoritative medical reference textbooks (Handbook of Signs & Symptoms,
Professional Guide to Signs & Symptoms) in data/sources/raw_pdfs/ and extracts
structured clinical findings, medical causes, signs/symptoms, and red flag warnings
into data/sources/dumps/pdf_extractions/.
"""

import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

try:
    import pypdf
except ImportError:
    pypdf = None

try:
    import pdfplumber
except ImportError:
    pdfplumber = None

logger = logging.getLogger("predoc.agents.pdf_extractor")
logger.setLevel(logging.INFO)


class PDFExtractorAgent:
    """Autonomous agent that parses clinical reference textbooks and extracts structured disease profiles."""

    def __init__(self, raw_pdfs_dir: Optional[Path] = None, dumps_dir: Optional[Path] = None):
        base_dir = Path(__file__).resolve().parent.parent.parent
        if base_dir.name == "src":
            base_dir = base_dir.parent
        self.raw_pdfs_dir = raw_pdfs_dir or (base_dir / "data" / "sources" / "raw_pdfs")
        self.dumps_dir = dumps_dir or (base_dir / "data" / "sources" / "dumps" / "pdf_extractions")
        self.dumps_dir.mkdir(parents=True, exist_ok=True)
        self.last_run_stats: Dict[str, int] = {}

    def extract_clinical_conditions_from_pdf(
        self, pdf_filename: str, start_page: int = 15, max_pages: int = 250
    ) -> List[Dict]:
        """Deep scan a textbook to extract individual diseases, clinical signs, and associated findings."""
        if start_page < 0:
            raise ValueError("start_page must be zero or greater")
        if max_pages <= 0:
            raise ValueError("max_pages must be greater than zero")

        pdf_path = self.raw_pdfs_dir / pdf_filename
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF source file not found: {pdf_path}")

        if not pypdf and not pdfplumber:
            raise RuntimeError("pypdf or pdfplumber is required for PDF extraction.")

        logger.info(f"Deep scanning clinical textbook: {pdf_filename} (pages {start_page} to {start_page+max_pages})...")
        reader = None
        if pypdf:
            try:
                reader = pypdf.PdfReader(str(pdf_path))
            except Exception as exc:
                logger.warning("pypdf could not open %s; using pdfplumber: %s", pdf_filename, exc)
        plumber_pdf = None
        if pdfplumber:
            try:
                plumber_pdf = pdfplumber.open(str(pdf_path))
            except Exception as exc:
                logger.warning("Could not open %s with pdfplumber: %s", pdf_filename, exc)
        total_pages = len(reader.pages) if reader else len(plumber_pdf.pages) if plumber_pdf else 0
        end_page = min(total_pages, start_page + max_pages)

        extracted_conditions: List[Dict] = []
        current_symptom = "General Clinical Presentation"
        seen_conditions = set()
        failed_pages = 0
        fallback_pages = 0

        for page_idx in range(start_page, end_page):
            try:
                text = ""
                if reader:
                    try:
                        text = reader.pages[page_idx].extract_text() or ""
                    except Exception as exc:
                        logger.debug("pypdf page %s extraction failed: %s", page_idx + 1, exc)
                if not text.strip() and plumber_pdf and page_idx < len(plumber_pdf.pages):
                    try:
                        text = plumber_pdf.pages[page_idx].extract_text() or ""
                        fallback_pages += 1
                    except Exception as exc:
                        logger.debug("pdfplumber page %s extraction failed: %s", page_idx + 1, exc)
                if not text.strip():
                    continue

                # Identify overarching cardinal symptom header (e.g., ABDOMINAL PAIN, CHEST PAIN, DYSPNEA)
                header_match = re.search(r'\b([A-Z\s]{4,30})\s+\d+\b', text)
                if header_match:
                    hdr = header_match.group(1).strip()
                    if len(hdr) > 3 and not any(k in hdr for k in ["CONTENTS", "INDEX", "PREFACE", "CHAPTER"]):
                        current_symptom = hdr.title()

                # Extract conditions formatted as "Condition Name.\n Clinical description..."
                lines = [l.strip() for l in text.split("\n") if l.strip()]
                for i, line in enumerate(lines):
                    # Condition headers end with a period or colon, start capitalized, length < 55
                    if (line.endswith(".") or line.endswith(":")) and 3 < len(line) < 55 and line[0].isupper():
                        cname = line[:-1].strip()
                        
                        # Filter non-disease artifacts
                        if cname.lower().startswith((
                            "table", "figure", "see", "chapter", "pediatric", "geriatric",
                            "history", "physical", "medical causes", "other causes", "examination",
                            "emergency", "urgent", "caution", "alert"
                        )):
                            continue

                        # Extract subsequent clinical description paragraphs
                        if i + 1 < len(lines):
                            body_lines = []
                            for nxt in lines[i+1 : i+12]:
                                if (nxt.endswith(".") and 3 < len(nxt) < 55 and nxt[0].isupper()) or "EMERGENCY" in nxt:
                                    break
                                body_lines.append(nxt)
                            
                            clinical_text = " ".join(body_lines).strip()
                            if len(clinical_text) >= 70:
                                is_red_flag = any(rf in clinical_text.lower() for rf in [
                                    "life-threatening", "emergency", "shock", "fatal", "hypotension", "collapse"
                                ])
                                
                                condition_key = (cname.casefold(), current_symptom.casefold())
                                if condition_key in seen_conditions:
                                    continue
                                seen_conditions.add(condition_key)
                                extracted_conditions.append({
                                    "condition_name": cname,
                                    "cardinal_sign_symptom": current_symptom,
                                    "clinical_findings": clinical_text[:800],
                                    "is_red_flag": is_red_flag,
                                    "source_textbook": pdf_filename,
                                    "page_number": page_idx + 1,
                                })
            except Exception as e:
                failed_pages += 1
                logger.warning(f"Error reading page {page_idx+1} in {pdf_filename}: {e}")

        if plumber_pdf:
            plumber_pdf.close()

        self.last_run_stats = {
            "pages_scanned": max(0, end_page - start_page),
            "pages_with_fallback_text": fallback_pages,
            "pages_failed": failed_pages,
        }

        logger.info(f"Extracted {len(extracted_conditions)} authentic conditions from {pdf_filename}.")
        return extracted_conditions

    def extract_document(
        self, pdf_filename: str, start_page: int = 15, max_pages: Optional[int] = 150
    ) -> Path:
        """Extract conditions from a single textbook and save comprehensive structured JSON dump."""
        if start_page < 0:
            raise ValueError("start_page must be zero or greater")
        if max_pages is not None and max_pages <= 0:
            raise ValueError("max_pages must be greater than zero")

        conditions = self.extract_clinical_conditions_from_pdf(
            pdf_filename, start_page=start_page, max_pages=max_pages or 150
        )
        output_dump_path = self.dumps_dir / f"{Path(pdf_filename).stem}_dump.json"

        dump_data = {
            "source_file": pdf_filename,
            "total_extracted_conditions": len(conditions),
            "extraction_timestamp": datetime.now(timezone.utc).isoformat(),
            "extraction_stats": self.last_run_stats,
            "conditions": conditions,
        }

        output_dump_path.write_text(json.dumps(dump_data, indent=2, ensure_ascii=False), encoding="utf-8")
        logger.info(f"Saved textbook extraction dump: {output_dump_path} ({len(conditions)} conditions)")
        return output_dump_path

    def extract_all_sources(
        self, start_page: int = 15, max_pages_per_pdf: Optional[int] = 150
    ) -> List[Path]:
        """Deep scan all reference clinical textbooks registered in raw_pdfs/."""
        if start_page < 0:
            raise ValueError("start_page must be zero or greater")
        dumps = []
        all_master_conditions = []

        for pdf_file in self.raw_pdfs_dir.glob("*.pdf"):
            try:
                dump_path = self.extract_document(
                    pdf_file.name, start_page=start_page, max_pages=max_pages_per_pdf
                )
                dumps.append(dump_path)
                data = json.loads(dump_path.read_text(encoding="utf-8"))
                all_master_conditions.extend(data.get("conditions", []))
            except Exception as e:
                logger.error(f"Failed extracting {pdf_file.name}: {e}")

        # Save consolidated master clinical extraction catalog
        master_path = self.dumps_dir / "master_clinical_conditions_dump.json"
        master_data = {
            "total_conditions": len(all_master_conditions),
            "sources": [p.name for p in self.raw_pdfs_dir.glob("*.pdf")],
            "conditions": all_master_conditions,
        }
        master_path.write_text(json.dumps(master_data, indent=2, ensure_ascii=False), encoding="utf-8")
        logger.info(f"Master clinical conditions catalog saved: {master_path} ({len(all_master_conditions)} conditions)")
        dumps.append(master_path)
        return dumps
