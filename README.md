# PreDoc-Chatbot: Enterprise Clinical AI Assistant

PreDoc-Chatbot is a production-grade Clinical AI Triage and Symptom Matching Assistant powered by an autonomous multi-agent ingestion pipeline, FastAPI, and hybrid retrieval.

---

## 1. Prerequisites & Environment

> [!IMPORTANT]
> **Python Version Constraint**: This project strictly requires **Python 3.12** (`>=3.12, <3.13`). Older or newer Python versions are not supported.

- **Python Runtime**: `3.12`
- **Docker Base Image**: `python:3.12-slim`
- **Package Manager**: `pip` / `setuptools` (configured via `pyproject.toml`)

---

## 2. Enterprise Project Architecture

```
PreDoc-Chatbot/
├── SOUL.md                                 # [Clinical AI Constitution & Behavioral Boundaries]
├── AGENTS.md                               # [Autonomous Agent Architecture & Developer Guide]
├── pyproject.toml                          # [Packaging, Ruff, Black & Pytest Configuration - Python 3.12]
├── requirements.txt                        # [Production Python Dependencies]
├── .env.example                            # [Environment Variables Template]
├── .gitignore                              # [Enterprise Exclusion Rules]
├── Dockerfile                              # [Container Definition - python:3.12-slim]
├── docker-compose.yml                      # [Container Orchestration]
├── README.md                               # [This Documentation]
│
├── .agents/                                # [Agent Customizations Root]
│   └── rules/
│       └── clinical_integrity.md           # [Workspace AI Behavioral Rules]
│
├── data/                                   # [Data Tier: 3-Tier Medallion Pattern]
│   ├── governance/                         # [Layer 1: Governance, Schemas & Audit Trail]
│   │   ├── template.md                     # Canonical 11-column matrix extraction contract (SSOT)
│   │   ├── template.yaml                   # Machine-readable schema for automated validation
│   │   ├── classification_rules.md         # 20-specialty taxonomy, tie-breakers & probing rules
│   │   └── version_log.md                  # Master audit trail & regulatory provenance log
│   │
│   ├── sources/                            # [Layer 2: Raw / Unstructured Sources]
│   │   ├── raw_pdfs/                       # Isolated clinical reference textbooks (PDFs)
│   │   │   ├── Handbook_of_Signs_and_Symptoms.pdf
│   │   │   └── professional-guide-to-signs-and-symptoms-6th-edition.pdf
│   │   ├── dumps/                          # [Agent Working Space for Raw Structured Dumps]
│   │   │   ├── pdf_extractions/            # Extracted chapters & sections from PDF textbooks
│   │   │   └── web_extractions/            # Crawled clinical guidelines from WHO, CDC, PubMed
│   │   └── source_catalog.json             # 25 registered clinical guidelines & textbook sources
│   │
│   └── knowledge_base/                     # [Layer 3: Curated Clinical Knowledge Base]
│                                           # (Destination directory populated by autonomous agents)
│
├── backend/                                # [Application Tier: FastAPI & Clinical Logic]
│   ├── __init__.py                         # Root package initializer
│   ├── main.py                             # Server entry point & API endpoints (Zero auto-vectorization)
│   ├── config.py                           # Pydantic settings & path resolution
│   ├── agent.py                            # Clinical ReAct triage agent
│   ├── rag.py                              # Hybrid Vector + BM25 retrieval engine
│   ├── safety.py                           # Rule-based emergency keyword detector
│   ├── schemas.py                          # Pydantic V2 request/response schemas
│   ├── security.py                         # Authentication and rate limiting
│   └── agents/                             # [Autonomous Clinical Agents Suite]
│       ├── __init__.py                     # Package exports
│       ├── pdf_extractor_agent.py          # Deep scans reference PDFs into structured dumps
│       ├── web_crawler_agent.py            # Crawls registered clinical guidelines into dumps
│       ├── knowledge_populator_agent.py    # Transforms dumps via LLM into 11-column matrix
│       ├── auditor_agent.py                # Schema validation & quality control auditor
│       ├── orchestrator.py                 # Master pipeline coordinator
│       ├── classifier_agent.py             # 20-specialty symptom routing agent
│       └── probing_agent.py                # Condition-specific follow-up question generator
│
├── frontend/                               # [Presentation Tier: Modern Glassmorphic Web App]
│   └── index.html                          # Responsive UI with age/sex inputs & specialty pills
│
├── scripts/                                # [Production Maintenance & CLI Tools]
│   └── run_agents.py                       # Unified CLI runner for autonomous agents
│
├── storage/                                # [Vector Storage Cache]
└── tests/                                  # [Unit Test Suite - 11/11 Passing]
    ├── test_evaluations.py                 # Safety, evaluation questions, metadata tests
    └── test_agents.py                      # Full agent suite tests
```

---

## 3. Autonomous Ingestion Agent System

Populating `data/knowledge_base/` is **strictly performed by the autonomous agents** reading from verified raw clinical sources.

```bash
# 1. Deep-scan clinical reference textbooks into structured dumps:
python scripts/run_agents.py --extract-pdfs --max-pages 30

# 2. Crawl registered guidelines from WHO/CDC/PubMed into dumps:
python scripts/run_agents.py --crawl-web

# 3. Inspect raw JSON dumps for malformed records and duplicates:
python scripts/run_agents.py --audit-dumps

# 4. Repair safe dump defects; malformed JSON is reported and left untouched:
python scripts/run_agents.py --repair-dumps

# 5. Deep-audit the knowledge base schema and data quality:
python scripts/run_agents.py --audit

# 6. Run the full multi-agent pipeline:
python scripts/run_agents.py --all
```

---

## 4. Running the Tests

```bash
python -m unittest discover tests
```
All 11 unit tests across routing, safety, and the agent suite pass on Python 3.12.