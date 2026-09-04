"""Master Ingestion Orchestrator.

Orchestrates the autonomous multi-agent pipeline:
1. PDFExtractorAgent extracts raw textbook chapters to data/sources/dumps/pdf_extractions/
2. WebCrawlerAgent crawls authoritative guidelines to data/sources/dumps/web_extractions/
3. KnowledgePopulatorAgent transforms dumps via OpenRouter LLM into the canonical 11-column matrix
4. KnowledgeBaseAuditorAgent verifies 11-column completeness, unique probing questions, and zero empty cells.
"""

import argparse
import logging
from pathlib import Path
from typing import Dict, List, Optional

from .pdf_extractor_agent import PDFExtractorAgent
from .web_crawler_agent import WebCrawlerAgent
from .knowledge_populator_agent import KnowledgePopulatorAgent
from .auditor_agent import KnowledgeBaseAuditorAgent
from .dump_quality_agent import DumpQualityAgent

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("predoc.orchestrator")


class MasterIngestionOrchestrator:
    """Enterprise multi-agent pipeline coordinator for clinical knowledge base ingestion."""

    def __init__(self):
        base_dir = Path(__file__).resolve().parent.parent.parent
        if base_dir.name == "src":
            base_dir = base_dir.parent
        self.pdf_agent = PDFExtractorAgent()
        self.web_agent = WebCrawlerAgent()
        self.populator_agent = KnowledgePopulatorAgent()
        self.auditor_agent = KnowledgeBaseAuditorAgent()
        self.dump_quality_agent = DumpQualityAgent()

    def run_pdf_extractions(
        self, start_page: int = 15, max_pages_per_pdf: Optional[int] = 50
    ) -> List[Path]:
        """Trigger PDFExtractorAgent to deep-scan raw PDFs into dumps."""
        logger.info("--- Starting PDF Extraction Phase ---")
        dumps = self.pdf_agent.extract_all_sources(
            start_page=start_page, max_pages_per_pdf=max_pages_per_pdf
        )
        logger.info(f"PDF extraction complete. Generated {len(dumps)} dumps.")
        return dumps

    def run_web_crawls(self) -> List[Path]:
        """Trigger WebCrawlerAgent to fetch NLM clinical tables and registered guideline sources into dumps."""
        logger.info("--- Starting Web Guideline Ingestion Phase ---")
        dumps = self.web_agent.crawl_all_registered_guidelines()
        logger.info(f"Web crawling complete. Generated {len(dumps)} dumps.")
        return dumps

    def run_kb_audit(self) -> Dict:
        """Trigger KnowledgeBaseAuditorAgent to verify knowledge base files."""
        logger.info("--- Starting Knowledge Base Deep Audit ---")
        summary = self.auditor_agent.audit_entire_knowledge_base()
        logger.info(
            f"Audit Complete: {summary['total_files']} files, {summary['total_conditions']} conditions. "
            f"Compliant: {summary['compliant_files']}/{summary['total_files']}"
        )
        return summary

    def run_dump_audit(self, repair: bool = False) -> Dict:
        """Inspect raw JSON dumps and optionally repair safe defects with backups."""
        logger.info("--- Starting Raw Dump Quality Audit (repair=%s) ---", repair)
        return self.dump_quality_agent.repair() if repair else self.dump_quality_agent.inspect()

    def run_category_population(self, category_name: str, filename: str, prefix: str, candidate_conditions: List[Dict]) -> None:
        """Autonomously populate a category using dumps and LLM formatting."""
        logger.info(f"--- Starting Autonomous Population for {category_name} ({prefix}) ---")
        out_file = self.populator_agent.initialize_category_file(filename, category_name, prefix)
        
        for cond in candidate_conditions:
            cid = cond["id"]
            name = cond["name"]
            context = cond.get("context", "Clinical textbook findings from dumps")
            try:
                logger.info(f"Populating condition {cid}: {name}...")
                row = self.populator_agent.format_clinical_row(category_name, cid, name, context)
                self.populator_agent.append_condition_row(filename, row)
            except Exception as e:
                logger.error(f"Failed populating {cid}: {e}")

        logger.info(f"Finished populating {category_name}. Running quality audit...")
        report = self.auditor_agent.audit_file(out_file)
        logger.info(f"Audit for {filename}: valid={report['is_valid']}, rows={report['total_rows']}")

    def run_knowledge_base_population(self) -> Dict[str, int]:
        """Trigger KnowledgePopulatorAgent to route dumps into the 20 KB files."""
        logger.info("--- Starting Autonomous Knowledge Base Population from Dumps ---")
        counts = self.populator_agent.populate_from_extracted_dumps()
        logger.info("Population finished across 20 specialties. Running full audit...")
        self.run_kb_audit()
        return counts


def main():
    parser = argparse.ArgumentParser(description="PreDoc Master Ingestion Multi-Agent Orchestrator")
    parser.add_argument("--extract-pdfs", action="store_true", help="Extract raw clinical PDFs into dumps")
    parser.add_argument("--crawl-web", action="store_true", help="Crawl registered guidelines into dumps")
    parser.add_argument("--populate-kb", action="store_true", help="Populate knowledge base files from dumps")
    parser.add_argument("--audit", action="store_true", help="Run deep quality audit on knowledge base")
    parser.add_argument("--all", action="store_true", help="Run complete pipeline: extract, crawl, populate, audit")
    parser.add_argument("--max-pages", type=int, default=80, help="Max pages per PDF to extract")
    args = parser.parse_args()

    orchestrator = MasterIngestionOrchestrator()

    if args.all:
        orchestrator.run_pdf_extractions(max_pages_per_pdf=args.max_pages)
        orchestrator.run_web_crawls()
        orchestrator.run_knowledge_base_population()
        return

    if args.extract_pdfs:
        orchestrator.run_pdf_extractions(max_pages_per_pdf=args.max_pages)
    if args.crawl_web:
        orchestrator.run_web_crawls()
    if args.populate_kb:
        orchestrator.run_knowledge_base_population()
    if args.audit:
        orchestrator.run_kb_audit()
    if not (args.extract_pdfs or args.crawl_web or args.populate_kb or args.audit or args.all):
        parser.print_help()


if __name__ == "__main__":
    main()
