"""Application settings and model configuration.

Provider-agnostic OpenAPI specification architecture:
- Primary OpenAPI Endpoint (configurable URL, API key, LLM model, and Cloud Embedding)
- Fallback OpenAPI Endpoint (configurable URL, API key, fallback model, and Cloud Embedding)
- Resilient Cloud API Embeddings (0 MB local footprint, automatic dimension alignment)
- Per-Agent specialized model allocation
"""

import logging
import os
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv
from llama_index.core import Settings
from llama_index.core.embeddings import BaseEmbedding
from llama_index.llms.openai_like import OpenAILike
from pydantic import Field
import yaml

logger = logging.getLogger("predoc.config")
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
if BASE_DIR.name == "src":
    BASE_DIR = BASE_DIR.parent
PERSIST_DIR = BASE_DIR / "storage"
DATA_DIR = BASE_DIR / "data"


def get_secret(secret_name: str, env_name: str, default: Optional[str] = None) -> str:
    """Read secrets from Docker secrets, host work-secrets, .env, or default."""
    candidate_paths = [
        Path(f"/run/secrets/{secret_name}"),
        Path(f"/mnt/data/work/work-secrets/{secret_name}"),
        Path(f"/mnt/data/work/work-secrets/{secret_name}.txt"),
        Path(f"Z:/data/work/work-secrets/{secret_name}"),
        Path(f"Z:/data/work/work-secrets/{secret_name}.txt"),
    ]
    custom_secrets_dir = os.getenv("SECRETS_DIR")
    if custom_secrets_dir:
        candidate_paths.insert(0, Path(custom_secrets_dir) / secret_name)
        candidate_paths.insert(1, Path(custom_secrets_dir) / f"{secret_name}.txt")

    for p in candidate_paths:
        if p.exists():
            try:
                val = p.read_text(encoding="utf-8").strip()
                if val:
                    return val
            except OSError:
                pass

    value = os.getenv(env_name)
    if value:
        return value.strip()
    if default is not None:
        return default
    raise ValueError(f"Missing required configuration secret: {env_name}")


# Role-Based Access Control (RBAC) Credentials
# 1. Administrator Role (Full access to /dashboard, /api/metrics, /api/system/status, and consultations)
ADMIN_USER = get_secret("admin_user", "ADMIN_USER", default="").strip()
ADMIN_PASS = get_secret("admin_pass", "ADMIN_PASS", default="").strip()
ADMIN_API_KEY = get_secret("admin_api_key", "ADMIN_API_KEY", default=os.getenv("ADMIN_API_KEY", "")).strip()

# 2. Clinician / Standard User Role (Access to / Consultation UI and /api/chat consultations)
USER_USER = (
    get_secret("user_user", "USER_USER", default="")
    or get_secret("user_username", "USER_USERNAME", default="")
).strip()
USER_PASS = (
    get_secret("user_pass", "USER_PASS", default="")
    or get_secret("user_password", "USER_PASSWORD", default="")
).strip()
USER_API_KEY = (
    get_secret("clinical_api_key", "CLINICAL_API_KEY", default="")
    or get_secret("user_api_key", "USER_API_KEY", default="")
    or get_secret("demo_api_key", "DEMO_API_KEY", default="")
    or os.getenv("CLINICAL_API_KEY", "")
).strip()
DEMO_API_KEY = USER_API_KEY  # Backward-compatible alias

# 3. Grace-period rotated key support (Best practice: dual key rotation with transition window)
PREVIOUS_ADMIN_API_KEY = (
    get_secret("previous_admin_api_key", "PREVIOUS_ADMIN_API_KEY", default="")
).strip()
PREVIOUS_USER_API_KEY = (
    get_secret("previous_clinical_api_key", "PREVIOUS_CLINICAL_API_KEY", default="")
).strip()

# Audit log active keys on startup to standard logger (only shown in logs, never in source)
logger.info("==================================================")
logger.info("[SECURITY AUDIT] PreDoc Beta Security Initialized")
logger.info("[SECURITY AUDIT] Active Admin API Key: %s", ADMIN_API_KEY)
if PREVIOUS_ADMIN_API_KEY:
    logger.info("[SECURITY AUDIT] Previous Admin API Key (Grace Period): %s", PREVIOUS_ADMIN_API_KEY)
logger.info("[SECURITY AUDIT] Active Clinical API Key: %s", USER_API_KEY)
if PREVIOUS_USER_API_KEY:
    logger.info("[SECURITY AUDIT] Previous Clinical API Key (Grace Period): %s", PREVIOUS_USER_API_KEY)
logger.info("==================================================")

# 1. Primary OpenAPI Spec Endpoint Configuration
PRIMARY_API_BASE = (
    os.getenv("PRIMARY_API_BASE")
    or os.getenv("OPENAI_BASE_URL")
    or "https://integrate.api.nvidia.com/v1"
).rstrip("/")

PRIMARY_API_KEY = (
    get_secret("primary_api_key", "PRIMARY_API_KEY", default="")
    or get_secret("nvidia_api_key", "NVIDIA_API_KEY", default="")
    or get_secret("openai_api_key", "OPENAI_API_KEY", default="")
    or get_secret("openrouter_key", "OPENROUTER_API_KEY", default="")
).strip()

PRIMARY_LLM_MODEL = os.getenv(
    "PRIMARY_LLM_MODEL",
    os.getenv("DEFAULT_LLM_MODEL", "meta/llama-3.2-11b-vision-instruct"),
)
PRIMARY_EMBEDDING_MODEL = os.getenv("PRIMARY_EMBEDDING_MODEL", "nvidia/nemotron-3-embed-1b")
PRIMARY_EMBEDDING_DIM = int(os.getenv("PRIMARY_EMBEDDING_DIM", "2048"))

# 2. Secondary / Fallback OpenAPI Spec Endpoint Configuration
FALLBACK_API_BASE = (
    os.getenv("SECONDARY_API_BASE")
    or os.getenv("FALLBACK_API_BASE")
    or "https://openrouter.ai/api/v1"
).rstrip("/")

FALLBACK_API_KEY = (
    get_secret("secondary_api_key", "SECONDARY_API_KEY", default="")
    or get_secret("fallback_api_key", "FALLBACK_API_KEY", default="")
    or get_secret("openrouter_key_fallback", "OPENROUTER_API_KEY_FALLBACK", default="")
    or (get_secret("openrouter_key", "OPENROUTER_API_KEY", default="") if PRIMARY_API_KEY != get_secret("openrouter_key", "OPENROUTER_API_KEY", default="") else "")
).strip()

FALLBACK_LLM_MODEL = os.getenv("SECONDARY_LLM_MODEL", os.getenv("FALLBACK_LLM_MODEL", "meta/llama-3.3-70b-instruct"))
FALLBACK_EMBEDDING_MODEL = os.getenv("SECONDARY_EMBEDDING_MODEL", os.getenv("FALLBACK_EMBEDDING_MODEL", "liquid/lfm-2.5-embedding-350m:free"))
FALLBACK_EMBEDDING_DIM = int(os.getenv("SECONDARY_EMBEDDING_DIM", os.getenv("FALLBACK_EMBEDDING_DIM", "1024")))

# Legacy aliases for backwards compatibility
OPENROUTER_API_KEY = FALLBACK_API_KEY or PRIMARY_API_KEY
NVIDIA_API_KEY = PRIMARY_API_KEY
DEFAULT_LLM_MODEL = PRIMARY_LLM_MODEL
AGENT_EMBEDDING_MODEL = PRIMARY_EMBEDDING_MODEL
AI_PROVIDER = "primary"

# Single Global Rate Limiter Settings
GLOBAL_RATE_LIMIT_RPM = int(os.getenv("GLOBAL_RATE_LIMIT_RPM", "30"))
GLOBAL_RATE_LIMIT_RPD = int(os.getenv("GLOBAL_RATE_LIMIT_RPD", "50000"))

# Clinical Intake & Probing Confidence Thresholds
CLINICAL_SPECIFICITY_THRESHOLD = float(os.getenv("CLINICAL_SPECIFICITY_THRESHOLD", "0.70"))
PROBING_MAX_TURNS = int(os.getenv("PROBING_MAX_TURNS", "3"))

# Chunking Configuration
Settings.chunk_size = 256
Settings.chunk_overlap = 20

# Optimal Specialized Model Allocation Per Agent
FAST_MODEL = os.getenv("AGENT_FAST_MODEL", "meta/llama-3.2-11b-vision-instruct")
REASONING_MODEL = os.getenv("AGENT_REASONING_MODEL", PRIMARY_LLM_MODEL)

AGENT_TRIAGE_MODEL = os.getenv("AGENT_TRIAGE_MODEL", REASONING_MODEL)
AGENT_VALIDATION_MODEL = os.getenv("AGENT_VALIDATION_MODEL", FAST_MODEL)
AGENT_CLASSIFIER_MODEL = os.getenv("AGENT_CLASSIFIER_MODEL", FAST_MODEL)
AGENT_PROBING_MODEL = os.getenv("AGENT_PROBING_MODEL", REASONING_MODEL)
AGENT_POPULATOR_MODEL = os.getenv("AGENT_POPULATOR_MODEL", REASONING_MODEL)
AGENT_AUDITOR_MODEL = os.getenv("AGENT_AUDITOR_MODEL", FAST_MODEL)
AGENT_CRAWLER_MODEL = os.getenv("AGENT_CRAWLER_MODEL", REASONING_MODEL)


# Resilient Pure-Cloud Embedding Implementation (0 MB Local Footprint)
class ResilientCloudEmbedding(BaseEmbedding):
    """Zero-download cloud API embedding adhering to OpenAPI specifications.

    - 0 MB local footprint (no local PyTorch/HuggingFace downloads).
    - Routes requests to GenericOpenAIClient with failover capability.
    - Automatically projects/adapts vectors to target_dim if fallback models differ in dimensions.
    """
    target_dim: int = Field(default=2048, description="Target vector dimension")

    def __init__(self, target_dim: Optional[int] = None, **kwargs):
        dim = target_dim or PRIMARY_EMBEDDING_DIM
        super().__init__(target_dim=dim, **kwargs)

    def _get_query_embedding(self, query: str) -> List[float]:
        from backend.openai_client import get_openai_client
        client = get_openai_client()
        embeddings = client.create_embedding(query, target_dim=self.target_dim)
        return embeddings[0]

    def _get_text_embedding(self, text: str) -> List[float]:
        from backend.openai_client import get_openai_client
        client = get_openai_client()
        embeddings = client.create_embedding(text, target_dim=self.target_dim)
        return embeddings[0]

    def _get_text_embeddings(self, texts: List[str]) -> List[List[float]]:
        from backend.openai_client import get_openai_client
        client = get_openai_client()
        return client.create_embedding(texts, target_dim=self.target_dim)

    async def _aget_query_embedding(self, query: str) -> List[float]:
        return self._get_query_embedding(query)

    async def _aget_text_embedding(self, text: str) -> List[float]:
        return self._get_text_embedding(text)


# Configure LlamaIndex Core Services
Settings.llm = OpenAILike(
    api_key=PRIMARY_API_KEY or "sk-dummy",
    api_base=PRIMARY_API_BASE,
    model=DEFAULT_LLM_MODEL,
    is_chat_model=True,
)

Settings.embed_model = ResilientCloudEmbedding(target_dim=PRIMARY_EMBEDDING_DIM)


def get_file_metadata(filename: str) -> dict:
    """Read identity and version information from a document's frontmatter."""
    document_path = Path(filename)
    if not document_path.exists():
        kb_path = DATA_DIR / "knowledge_base" / document_path.name
        if kb_path.exists():
            document_path = kb_path
        else:
            document_path = DATA_DIR / document_path.name

    if not document_path.exists():
        return {
            "document": filename,
            "category": Path(filename).stem.replace("_", " ").title(),
            "version": "v2.2",
            "effective_date": "2026-09-03",
            "reviewed_by": "Mayank Choudhary",
            "source": "WHO / CDC Clinical Reference Data",
        }

    frontmatter = {}
    content = document_path.read_text(encoding="utf-8")
    if content.startswith("---\n"):
        _, metadata_text, _ = content.split("---", 2)
        frontmatter = yaml.safe_load(metadata_text) or {}

    return {
        "document": document_path.name,
        "category": str(frontmatter.get("category", document_path.stem)),
        "version": str(frontmatter.get("document_version", "v2.2")),
        "effective_date": str(frontmatter.get("effective_date", "2026-09-03")),
        "reviewed_by": str(frontmatter.get("reviewed_by", "Mayank Choudhary")),
        "source": str(
            frontmatter.get("source", "WHO / CDC Clinical Reference Data")
        ),
    }
