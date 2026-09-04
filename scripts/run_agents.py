"""CLI launcher for PreDoc Autonomous Ingestion & Validation Agents.

Usage:
  python scripts/run_agents.py --extract-pdfs --max-pages 100
  python scripts/run_agents.py --crawl-web
  python scripts/run_agents.py --validate-input "severe chest pain"
  python scripts/run_agents.py --audit
    python scripts/run_agents.py --audit-dumps [--repair-dumps]
  python scripts/run_agents.py --all
"""

import argparse
import json
import sys
from pathlib import Path

# Add project root and src/ to sys.path
root_dir = Path(__file__).resolve().parent.parent
src_dir = root_dir / "src"
for p in [str(src_dir), str(root_dir)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from backend.agents.orchestrator import MasterIngestionOrchestrator


def main():
    parser = argparse.ArgumentParser(description="PreDoc Autonomous Multi-Agent Pipeline CLI")
    parser.add_argument("--extract-pdfs", action="store_true", help="Extract raw textbook chapters to dumps")
    parser.add_argument("--crawl-web", action="store_true", help="Crawl registered clinical guidelines to dumps")
    parser.add_argument("--populate-kb", action="store_true", help="Populate knowledge base files from dumps")
    parser.add_argument("--audit", action="store_true", help="Audit knowledge base schema & data quality")
    parser.add_argument("--audit-dumps", action="store_true", help="Inspect raw JSON extraction dumps")
    parser.add_argument("--repair-dumps", action="store_true", help="Repair safe dump defects and create .bak files")
    parser.add_argument("--validate-input", type=str, help="Test InputValidationAgent with a custom clinical or non-clinical query")
    parser.add_argument("--all", action="store_true", help="Run full pipeline: extract, crawl, populate, and audit")
    parser.add_argument("--start-page", type=int, default=15, help="First zero-based PDF page to scan (default: 15)")
    parser.add_argument("--max-pages", type=int, default=80, help="Max pages per PDF to extract in batch (default: 80)")

    args = parser.parse_args()

    if args.validate_input:
        from backend.agents.input_validation_agent import InputValidationAgent
        agent = InputValidationAgent()
        is_valid, msg = agent.validate_clinical_input(args.validate_input)
        print("\n=== PreDoc InputValidationAgent Test ===")
        print(f"Query: {args.validate_input!r}")
        print(f"Validation Status: {'VALID CLINICAL PRESENTATION' if is_valid else 'REJECTED (NON-CLINICAL)'}")
        if msg:
            print(f"\nFeedback Provided to User:\n{msg}")
        return

    if (args.audit_dumps or args.repair_dumps) and not (
        args.extract_pdfs or args.crawl_web or args.populate_kb or args.audit or args.all
    ):
        from backend.agents.dump_quality_agent import DumpQualityAgent

        print("\n>>> Running DumpQualityAgent...")
        dump_report = DumpQualityAgent().repair() if args.repair_dumps else DumpQualityAgent().inspect()
        print(json.dumps(dump_report, indent=2))
        return

    orchestrator = MasterIngestionOrchestrator()

    if args.all:
        print("\n=== Running Complete Multi-Agent Ingestion Pipeline ===")
        orchestrator.run_pdf_extractions(start_page=args.start_page, max_pages_per_pdf=args.max_pages)
        orchestrator.run_web_crawls()
        orchestrator.run_knowledge_base_population()
        orchestrator.run_kb_audit()
        print("\n=== Multi-Agent Pipeline Completed Successfully ===")
        return

    if args.extract_pdfs:
        print("\n>>> Running PDFExtractorAgent...")
        orchestrator.run_pdf_extractions(start_page=args.start_page, max_pages_per_pdf=args.max_pages)

    if args.crawl_web:
        print("\n>>> Running WebCrawlerAgent...")
        orchestrator.run_web_crawls()

    if args.populate_kb:
        print("\n>>> Running KnowledgePopulatorAgent (Routing dumps into KB)...")
        orchestrator.run_knowledge_base_population()

    if args.audit:
        print("\n>>> Running KnowledgeBaseAuditorAgent...")
        orchestrator.run_kb_audit()

    if args.audit_dumps or args.repair_dumps:
        print("\n>>> Running DumpQualityAgent...")
        dump_report = orchestrator.run_dump_audit(repair=args.repair_dumps)
        print(json.dumps(dump_report, indent=2))

    if not (args.extract_pdfs or args.crawl_web or args.populate_kb or args.audit or args.audit_dumps or args.repair_dumps or args.all or args.validate_input):
        parser.print_help()


if __name__ == "__main__":
    main()
