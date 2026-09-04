"""Knowledge Base Auditor Agent.

Performs deep clinical quality control, schema compliance audits,
and deduplication checks across the knowledge base markdown files.
"""

import logging
import re
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger("predoc.agents.auditor")
logger.setLevel(logging.INFO)


class KnowledgeBaseAuditorAgent:
    """Autonomous agent that verifies schema compliance and data uniqueness."""

    EXPECTED_COLUMNS = 11
    VALID_TIERS = {"Level 1 (Red)", "Level 2 (Yellow)", "Level 3 (Green)"}

    def __init__(self, kb_dir: Optional[Path] = None, model: Optional[str] = None):
        base_dir = Path(__file__).resolve().parent.parent.parent
        if base_dir.name == "src":
            base_dir = base_dir.parent
        self.kb_dir = kb_dir or (base_dir / "data" / "knowledge_base")
        from backend.config import AGENT_AUDITOR_MODEL
        self.model = model or AGENT_AUDITOR_MODEL

    def audit_file(self, file_path: Path) -> Dict:
        """Audit a single markdown file for 11-column completeness and data quality."""
        results = {
            "filename": file_path.name,
            "total_rows": 0,
            "column_errors": [],
            "empty_cell_errors": [],
            "tier_errors": [],
            "probing_question_duplicates": [],
            "is_valid": True,
        }

        if not file_path.exists():
            results["is_valid"] = False
            results["error"] = "File does not exist"
            return results

        lines = file_path.read_text(encoding="utf-8").splitlines()
        seen_probing_questions = set()

        for idx, line in enumerate(lines):
            line = line.strip()
            if not line.startswith("|") or line.startswith("| :---") or "Disease / Condition" in line:
                continue

            parts = [p.strip() for p in line.split("|")[1:-1]]
            results["total_rows"] += 1

            # 1. Column count check
            if len(parts) != self.EXPECTED_COLUMNS:
                results["column_errors"].append(
                    f"Line {idx+1}: Expected {self.EXPECTED_COLUMNS} cols, got {len(parts)}"
                )
                results["is_valid"] = False
                continue

            cid, disease, icd, tier, demo, primary, secondary, risk, red_flags, probing, diff = parts

            # 2. Empty cell check
            for col_idx, val in enumerate(parts):
                if not val or val == "-" or "placeholder" in val.lower():
                    results["empty_cell_errors"].append(
                        f"Row {cid} Col {col_idx+1} is empty or placeholder."
                    )
                    results["is_valid"] = False

            # 3. Triage Priority Tier check
            clean_tier = tier.strip()
            if clean_tier not in self.VALID_TIERS:
                results["tier_errors"].append(f"Row {cid} invalid tier: '{clean_tier}'")
                results["is_valid"] = False

            # 4. Probing Question Duplication check
            clean_probing = probing.strip().lower()
            if clean_probing in seen_probing_questions:
                results["probing_question_duplicates"].append(
                    f"Row {cid} has duplicate probing questions: '{clean_probing[:60]}...'"
                )
                results["is_valid"] = False
            else:
                seen_probing_questions.add(clean_probing)

        return results

    def audit_entire_knowledge_base(self) -> Dict:
        """Run deep audit across all files in data/knowledge_base/."""
        summary = {
            "total_files": 0,
            "total_conditions": 0,
            "compliant_files": 0,
            "non_compliant_files": 0,
            "file_reports": [],
        }

        for md_file in sorted(self.kb_dir.glob("*.md")):
            report = self.audit_file(md_file)
            summary["total_files"] += 1
            summary["total_conditions"] += report["total_rows"]
            if report["is_valid"]:
                summary["compliant_files"] += 1
            else:
                summary["non_compliant_files"] += 1
            summary["file_reports"].append(report)

        return summary
