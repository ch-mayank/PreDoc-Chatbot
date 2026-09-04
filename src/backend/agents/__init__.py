"""PreDoc Clinical Agents Package.

Provides specialized autonomous agents for:
- Clinical specialty classification (SpecialtyClassifierAgent)
- Active condition-specific clinical probing (ClinicalProbingAgent)
- PDF textbook deep scanning and text dumping (PDFExtractorAgent)
- Web guideline crawling and extraction (WebCrawlerAgent)
- LLM-powered canonical 11-column matrix population (KnowledgePopulatorAgent)
- Schema and deduplication auditing (KnowledgeBaseAuditorAgent)
- Raw JSON dump quality checks and safe repair (DumpQualityAgent)
- End-to-end multi-agent pipeline orchestration (MasterIngestionOrchestrator)
"""

from .classifier_agent import SpecialtyClassifierAgent
from .probing_agent import ClinicalProbingAgent
from .pdf_extractor_agent import PDFExtractorAgent
from .web_crawler_agent import WebCrawlerAgent
from .knowledge_populator_agent import KnowledgePopulatorAgent
from .auditor_agent import KnowledgeBaseAuditorAgent
from .dump_quality_agent import DumpQualityAgent
from .orchestrator import MasterIngestionOrchestrator

__all__ = [
    "SpecialtyClassifierAgent",
    "ClinicalProbingAgent",
    "PDFExtractorAgent",
    "WebCrawlerAgent",
    "KnowledgePopulatorAgent",
    "KnowledgeBaseAuditorAgent",
    "DumpQualityAgent",
    "MasterIngestionOrchestrator",
]
