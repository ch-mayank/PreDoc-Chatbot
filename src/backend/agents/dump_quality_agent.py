"""Quality control and repair for structured ingestion dumps."""

import json
import logging
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("predoc.agents.dump_quality")


class DumpQualityAgent:
    """Find malformed or low-quality JSON dumps and repair only safe defects."""

    def __init__(self, dumps_root: Optional[Path] = None):
        base_dir = Path(__file__).resolve().parent.parent.parent
        if base_dir.name == "src":
            base_dir = base_dir.parent
        self.dumps_root = dumps_root or (base_dir / "data" / "sources" / "dumps")

    def _load_json(self, path: Path) -> Any:
        return json.loads(path.read_text(encoding="utf-8"))

    @staticmethod
    def _condition_key(item: Dict[str, Any]) -> str:
        name = item.get("condition_name") or item.get("primary_name") or ""
        code = item.get("icd10_code") or ""
        return f"{name.strip().casefold()}|{code.strip().casefold()}"

    def _normalize_dump(self, path: Path, data: Any) -> tuple[Any, int]:
        """Return normalized data and number of removed invalid/duplicate records."""
        if not isinstance(data, dict):
            raise ValueError("root must be a JSON object")

        removed = 0
        for collection_name in ("conditions", "guidelines"):
            collection = data.get(collection_name)
            if collection is None:
                continue
            if not isinstance(collection, list):
                raise ValueError(f"{collection_name} must be a JSON array")

            clean_items: List[Dict[str, Any]] = []
            seen = set()
            for item in collection:
                if not isinstance(item, dict):
                    removed += 1
                    continue
                if collection_name == "conditions":
                    key = self._condition_key(item)
                    if not key or key == "|":
                        removed += 1
                        continue
                    if key in seen:
                        removed += 1
                        continue
                    seen.add(key)
                clean_items.append(item)
            data[collection_name] = clean_items
            data["total_conditions" if collection_name == "conditions" else "total_sources_crawled"] = len(clean_items)

        data["quality_checked_at"] = datetime.now(timezone.utc).isoformat()
        return data, removed

    def inspect(self) -> Dict[str, Any]:
        """Inspect every JSON dump without changing files."""
        report: Dict[str, Any] = {"total_files": 0, "valid_files": 0, "broken_files": 0, "files": []}
        if not self.dumps_root.exists():
            return report

        for path in sorted(self.dumps_root.rglob("*.json")):
            entry: Dict[str, Any] = {"path": str(path), "valid": True, "removed_candidates": 0}
            report["total_files"] += 1
            try:
                data = self._load_json(path)
                _, removed = self._normalize_dump(path, data)
                entry["removed_candidates"] = removed
                report["valid_files"] += 1
            except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
                entry["valid"] = False
                entry["error"] = str(exc)
                report["broken_files"] += 1
            report["files"].append(entry)
        return report

    def repair(self) -> Dict[str, Any]:
        """Repair safe JSON defects and retain an adjacent backup before writing."""
        report = self.inspect()
        repaired = 0
        skipped = []
        for entry in report["files"]:
            path = Path(entry["path"])
            try:
                data = self._load_json(path)
                normalized, removed = self._normalize_dump(path, data)
                if removed:
                    backup_path = path.with_suffix(path.suffix + ".bak")
                    shutil.copy2(path, backup_path)
                    path.write_text(json.dumps(normalized, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
                    repaired += 1
                    entry["backup"] = str(backup_path)
                    entry["removed"] = removed
            except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
                skipped.append({"path": str(path), "error": str(exc)})
        report["repaired_files"] = repaired
        report["skipped_files"] = skipped
        return report
