"""Enterprise Generic OpenAPI-Compliant Client.

Provides a unified, provider-agnostic interface to any OpenAPI / OpenAI-compatible endpoint:
- Configurable Primary Endpoint (e.g., NVIDIA NIM, local vLLM, Ollama, Azure, Groq, DeepSeek)
- Configurable Fallback Endpoint (e.g., secondary cloud provider, local backup)
- Cloud-native Embeddings without local model weights or disk downloads
- Standard OpenAPI models discovery (`client.models.list()`)
- Deep reasoning / thinking support (`extra_body={"chat_template_kwargs": {"enable_thinking": True}}`)
- Thread-safe global rate limiting (RPM, RPD, Token budgets)
"""

import logging
import os
import random
import threading
import time
import urllib.parse
from collections import deque
from datetime import datetime, timezone
from typing import Any, Dict, Generator, List, Optional, Tuple, Union

from dotenv import load_dotenv
import numpy as np
from openai import OpenAI, APIError, RateLimitError, NotFoundError

load_dotenv()

logger = logging.getLogger("predoc.openai_client")
logger.setLevel(logging.INFO)


def adapt_vector_dimension(vec: List[float], target_dim: int) -> List[float]:
    """Adapt vector length to target dimension with L2 unit normalization.
    
    Guarantees that vector search never crashes if failover occurs across models
    with differing embedding dimensions.
    """
    curr_len = len(vec)
    if curr_len == target_dim:
        return vec
    arr = np.array(vec, dtype=np.float32)
    if curr_len < target_dim:
        repeats = (target_dim // curr_len) + 1
        expanded = np.tile(arr, repeats)[:target_dim]
        norm = np.linalg.norm(expanded)
        if norm > 0:
            expanded = expanded / norm
        return expanded.tolist()
    else:
        truncated = arr[:target_dim]
        norm = np.linalg.norm(truncated)
        if norm > 0:
            truncated = truncated / norm
        return truncated.tolist()


# Approved Default Models for Open-Weight / OpenAPI Endpoints
FREE_MODELS = [
    "google/gemma-4-26b-a4b-it:free",
    "liquid/lfm-2.5-2.6b:free",
    "openrouter/free",
    "nvidia/nemotron-3.5-lightning:free",
]

FREE_EMBEDDING_MODEL = "liquid/lfm-2.5-embedding-350m:free"

# Known context and token budgets per model
MODEL_TOKEN_LIMITS: Dict[str, Dict[str, Any]] = {
    "nvidia/nemotron-3.5-lightning-30b-a3b": {"max_output_tokens": 16384, "context_window": 32768, "supports_thinking": True},
    "meta/llama-3.2-11b-vision-instruct": {"max_output_tokens": 4096, "context_window": 8192, "supports_thinking": False},
    "meta/llama-3.1-70b-instruct": {"max_output_tokens": 4096, "context_window": 131072, "supports_thinking": False},
    "nvidia/llama-3.1-nemotron-70b-instruct": {"max_output_tokens": 4096, "context_window": 131072, "supports_thinking": False},
    "google/gemma-4-31b-it": {"max_output_tokens": 8192, "context_window": 32768, "supports_thinking": False},
    "google/gemma-4-26b-a4b-it:free": {"max_output_tokens": 4096, "context_window": 8192, "supports_thinking": False},
    "liquid/lfm-2.5-2.6b:free": {"max_output_tokens": 2048, "context_window": 4096, "supports_thinking": False},
    "nvidia/nemotron-3.5-lightning:free": {"max_output_tokens": 4096, "context_window": 16384, "supports_thinking": True},
}

DEFAULT_TOKEN_LIMIT = {"max_output_tokens": 4096, "context_window": 8192, "supports_thinking": False}


class EnterpriseRateLimiter:
    """Thread-safe rate limiter tracking RPM, RPD, and token usage."""

    def __init__(self, rpm_limit: Optional[int] = None, rpd_limit: Optional[int] = None):
        self.rpm_limit = rpm_limit if rpm_limit is not None else int(os.getenv("GLOBAL_RATE_LIMIT_RPM", "30"))
        self.rpd_limit = rpd_limit if rpd_limit is not None else int(os.getenv("GLOBAL_RATE_LIMIT_RPD", "50000"))
        self._lock = threading.Lock()
        self._minute_timestamps: deque = deque()
        self._day_count = 0
        self._day_tokens = 0
        self._current_day = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    @property
    def minute_timestamps(self) -> list:
        with self._lock:
            return list(self._minute_timestamps)

    def _refresh_day(self):
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if today != self._current_day:
            self._current_day = today
            self._day_count = 0
            self._day_tokens = 0

    def acquire(self, estimated_tokens: int = 500) -> bool:
        """Acquire rate-limit clearance, smoothly throttling if approaching limits."""
        with self._lock:
            self._refresh_day()
            now = time.time()

            # Clean timestamps older than 60 seconds
            while self._minute_timestamps and now - self._minute_timestamps[0] > 60:
                self._minute_timestamps.popleft()

            # Check RPD limit
            if self._day_count >= self.rpd_limit:
                raise RuntimeError(f"Global daily rate limit reached ({self.rpd_limit} req/day).")

            # Check RPM limit and smooth out
            if len(self._minute_timestamps) >= self.rpm_limit:
                sleep_needed = 60.0 - (now - self._minute_timestamps[0]) + 0.1
                if sleep_needed > 0:
                    logger.info(f"Rate limiter: Smoothing request rate. Sleeping {sleep_needed:.2f}s...")
                    time.sleep(sleep_needed)
                    now = time.time()
                    while self._minute_timestamps and now - self._minute_timestamps[0] > 60:
                        self._minute_timestamps.popleft()

            self._minute_timestamps.append(time.time())
            self._day_count += 1
            self._day_tokens += estimated_tokens
            return True

    def record_usage(self, actual_tokens: int):
        """Record actual tokens consumed from API response."""
        with self._lock:
            self._refresh_day()
            self._day_tokens += actual_tokens

    def get_status(self) -> Dict[str, Any]:
        """Return current rate limiter telemetry."""
        with self._lock:
            self._refresh_day()
            now = time.time()
            active_minute = [t for t in self._minute_timestamps if now - t <= 60]
            return {
                "requests_this_minute": len(active_minute),
                "rpm_limit": self.rpm_limit,
                "requests_today": self._day_count,
                "rpd_limit": self.rpd_limit,
                "tokens_consumed_today": self._day_tokens,
                "current_day_utc": self._current_day,
            }


_global_rate_limiter: Optional[EnterpriseRateLimiter] = None


def get_rate_limiter() -> EnterpriseRateLimiter:
    """Return single global rate limiter singleton for the entire system."""
    global _global_rate_limiter
    if _global_rate_limiter is None:
        _global_rate_limiter = EnterpriseRateLimiter()
    return _global_rate_limiter


class GenericOpenAIClient:
    """Generic OpenAPI / OpenAI-compliant client with dual-endpoint routing and failover."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        primary_base_url: Optional[str] = None,
        primary_api_key: Optional[str] = None,
        primary_embedding_model: Optional[str] = None,
        primary_embedding_dim: Optional[int] = None,
        fallback_base_url: Optional[str] = None,
        fallback_api_key: Optional[str] = None,
        fallback_embedding_model: Optional[str] = None,
        fallback_embedding_dim: Optional[int] = None,
        fallback_model: Optional[str] = None,
        api_keys: Optional[List[str]] = None,
        models: Optional[List[str]] = None,
        base_timeout: float = 4.0,
        max_retries: int = 1,
        **legacy_kwargs,
    ):
        from backend.config import get_secret

        # 1. Primary Endpoint Resolution (Any OpenAPI-compatible endpoint)
        p_base = (
            base_url
            or primary_base_url
            or os.getenv("PRIMARY_API_BASE")
            or os.getenv("OPENAI_BASE_URL")
            or "https://integrate.api.nvidia.com/v1"
        ).rstrip("/")

        p_key = (
            api_key
            or primary_api_key
            or get_secret("primary_api_key", "PRIMARY_API_KEY", default="")
            or get_secret("nvidia_api_key", "NVIDIA_API_KEY", default="")
            or get_secret("openai_api_key", "OPENAI_API_KEY", default="")
            or get_secret("openrouter_key", "OPENROUTER_API_KEY", default="")
        ).strip()

        # 2. Fallback Endpoint Resolution (Any OpenAPI-compatible fallback endpoint)
        f_base = (
            fallback_base_url
            or os.getenv("FALLBACK_API_BASE")
            or "https://openrouter.ai/api/v1"
        ).rstrip("/")

        f_key = (
            fallback_api_key
            or get_secret("fallback_api_key", "FALLBACK_API_KEY", default="")
            or get_secret("openrouter_key_fallback", "OPENROUTER_API_KEY_FALLBACK", default="")
            or (get_secret("openrouter_key", "OPENROUTER_API_KEY", default="") if p_key != get_secret("openrouter_key", "OPENROUTER_API_KEY", default="") else "")
        ).strip()

        # Legacy api_keys support for unit test compatibility
        if api_keys:
            if len(api_keys) > 0 and api_keys[0]:
                p_key = api_keys[0].strip()
            if len(api_keys) > 1 and api_keys[1]:
                f_key = api_keys[1].strip()
            self.api_keys = [k for k in api_keys if k]
        else:
            self.api_keys = [k for k in [p_key, f_key] if k]

        self.primary_base_url = p_base
        self.primary_key = p_key
        self.primary_embedding_model = (
            primary_embedding_model
            or os.getenv("PRIMARY_EMBEDDING_MODEL", "nvidia/nemotron-3-embed-1b")
        )
        self.primary_embedding_dim = int(
            primary_embedding_dim
            or os.getenv("PRIMARY_EMBEDDING_DIM", "2048")
        )

        self.fallback_base_url = f_base
        self.fallback_key = f_key
        self.fallback_embedding_model = (
            fallback_embedding_model
            or os.getenv("FALLBACK_EMBEDDING_MODEL", "liquid/lfm-2.5-embedding-350m:free")
        )
        self.fallback_embedding_dim = int(
            fallback_embedding_dim
            or os.getenv("FALLBACK_EMBEDDING_DIM", "1024")
        )
        self.fallback_model = (
            fallback_model
            or os.getenv("FALLBACK_LLM_MODEL", "google/gemma-4-26b-a4b-it:free")
        )

        self.base_timeout = 8.0
        self.max_retries = max_retries
        self.models = models or FREE_MODELS

        # Initialize Primary standard OpenAI client (max_retries=0 so failover is fast)
        p_headers = {}
        if "openrouter" in self.primary_base_url:
            p_headers = {"HTTP-Referer": "https://predoc.ai", "X-Title": "PreDoc Clinical Assistant"}

        self.primary_client = OpenAI(
            base_url=self.primary_base_url,
            api_key=self.primary_key or "sk-dummy",
            timeout=self.base_timeout,
            max_retries=0,
            default_headers=p_headers if p_headers else None,
        )

        # Initialize Fallback standard OpenAI client if key is configured
        self.fallback_client: Optional[OpenAI] = None
        if self.fallback_key and (self.fallback_base_url != self.primary_base_url or self.fallback_key != self.primary_key):
            f_headers = {}
            if "openrouter" in self.fallback_base_url:
                f_headers = {"HTTP-Referer": "https://predoc.ai", "X-Title": "PreDoc Clinical Assistant"}
            self.fallback_client = OpenAI(
                base_url=self.fallback_base_url,
                api_key=self.fallback_key,
                timeout=self.base_timeout,
                max_retries=self.max_retries,
                default_headers=f_headers if f_headers else None,
            )

        # Single Global Rate Limiter
        self.rate_limiter = get_rate_limiter()
        self._cached_models: Dict[str, Any] = {}
        self._models_cache_timestamp: float = 0.0

    @property
    def nvidia_key(self) -> str:
        """Backward compatibility alias for primary API key."""
        return self.primary_key

    @property
    def openrouter_key(self) -> str:
        """Backward compatibility alias for fallback API key."""
        return self.fallback_key

    @property
    def primary_provider(self) -> str:
        """Derive provider name cleanly from endpoint URL hostname."""
        try:
            domain = urllib.parse.urlparse(self.primary_base_url).netloc
            if "nvidia" in domain:
                return "nvidia"
            if "openrouter" in domain:
                return "openrouter"
            return domain.split(":")[0] or "primary"
        except Exception:
            return "primary"

    @property
    def fallback_provider(self) -> str:
        """Derive fallback provider name cleanly from endpoint URL hostname."""
        try:
            domain = urllib.parse.urlparse(self.fallback_base_url).netloc
            if "nvidia" in domain:
                return "nvidia"
            if "openrouter" in domain:
                return "openrouter"
            return domain.split(":")[0] or "fallback"
        except Exception:
            return "fallback"

    def get_token_limit_for_model(self, model: str) -> Dict[str, Any]:
        """Return token limit specification for a model."""
        return MODEL_TOKEN_LIMITS.get(model, DEFAULT_TOKEN_LIMIT)

    def list_models(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """Fetch models list adhering to the OpenAI OpenAPI Specification (GET /models)."""
        now = time.time()
        if not force_refresh and self._cached_models and (now - self._models_cache_timestamp < 3600):
            return self._cached_models.get("models", [])

        models_list = []
        # 1. Query primary endpoint via standard OpenAI client
        try:
            resp = self.primary_client.models.list()
            for m in resp.data:
                mid = getattr(m, "id", None)
                if mid:
                    spec = self.get_token_limit_for_model(mid)
                    models_list.append({
                        "id": mid,
                        "object": "model",
                        "created": getattr(m, "created", int(now)),
                        "owned_by": getattr(m, "owned_by", self.primary_provider),
                        "provider": self.primary_provider,
                        "max_output_tokens": spec["max_output_tokens"],
                        "context_window": spec["context_window"],
                        "supports_thinking": spec["supports_thinking"],
                    })
        except Exception as exc:
            logger.warning(f"Error listing models from primary endpoint {self.primary_base_url}: {exc}")

        # 2. Query fallback endpoint if configured
        if self.fallback_client:
            try:
                resp_fb = self.fallback_client.models.list()
                for m in resp_fb.data:
                    mid = getattr(m, "id", None)
                    if mid:
                        spec = self.get_token_limit_for_model(mid)
                        models_list.append({
                            "id": mid,
                            "object": "model",
                            "created": getattr(m, "created", int(now)),
                            "owned_by": getattr(m, "owned_by", self.fallback_provider),
                            "provider": self.fallback_provider,
                            "is_free": mid.endswith(":free"),
                            "max_output_tokens": spec["max_output_tokens"],
                            "context_window": spec["context_window"],
                            "supports_thinking": spec["supports_thinking"],
                        })
            except Exception as exc:
                logger.warning(f"Error listing models from fallback endpoint {self.fallback_base_url}: {exc}")

        self._cached_models = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "count": len(models_list),
            "models": models_list,
        }
        self._models_cache_timestamp = now
        return models_list

    def fetch_available_models(self, force_refresh: bool = False) -> Dict[str, Any]:
        """Adapter method for backwards compatibility with previous client interface."""
        models = self.list_models(force_refresh=force_refresh)
        primary_m = [m for m in models if m.get("provider") == self.primary_provider]
        fallback_m = [m for m in models if m.get("provider") == self.fallback_provider]
        return {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "primary_provider": self.primary_provider,
            "fallback_provider": self.fallback_provider,
            "total_models": len(models),
            "primary_models_count": len(primary_m),
            "fallback_models_count": len(fallback_m),
            "all_models": models,
            "primary_models": primary_m,
            "fallback_models": fallback_m,
        }

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.2,
        max_tokens: Optional[int] = None,
        preferred_model: Optional[str] = None,
        model: Optional[str] = None,
        enable_thinking: Optional[bool] = None,
        extra_body: Optional[Dict[str, Any]] = None,
        stream: bool = False,
        **kwargs,
    ) -> Union[Dict[str, Any], Generator[str, None, None]]:
        """Standard OpenAI Chat Completion with rate limiting, thinking reasoning, and endpoint failover."""
        # Enforce single rate limiter
        self.rate_limiter.acquire(estimated_tokens=max_tokens or 500)

        target_model = model or preferred_model or (
            "meta/llama-3.2-11b-vision-instruct" if "nvidia" in self.primary_base_url
            else "meta/llama-3.3-70b-instruct"
        )
        spec = self.get_token_limit_for_model(target_model)
        effective_max_tokens = max_tokens or spec["max_output_tokens"]

        should_think = (
            enable_thinking if enable_thinking is not None
            else spec["supports_thinking"]
        )

        request_extra_body = dict(extra_body or {})
        if should_think and "chat_template_kwargs" not in request_extra_body:
            request_extra_body["chat_template_kwargs"] = {"enable_thinking": True}

        # 1. Attempt via Primary OpenAPI Endpoint
        try:
            call_kwargs: Dict[str, Any] = {
                "model": target_model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": effective_max_tokens,
                "stream": stream,
            }
            if request_extra_body:
                call_kwargs["extra_body"] = request_extra_body

            if stream:
                return self._stream_generator(self.primary_client, call_kwargs)

            comp = self.primary_client.chat.completions.create(**call_kwargs)
            choice = comp.choices[0]
            msg = choice.message
            content = msg.content or ""
            reasoning = getattr(msg, "reasoning_content", None) or getattr(msg, "reasoning", None) or ""

            usage = getattr(comp, "usage", None)
            total_tokens = getattr(usage, "total_tokens", 0) if usage else 0
            self.rate_limiter.record_usage(total_tokens)

            return {
                "status": "success",
                "provider": self.primary_provider,
                "model_used": target_model,
                "content": content.strip(),
                "reasoning": reasoning.strip(),
                "raw": comp.model_dump() if hasattr(comp, "model_dump") else str(comp),
            }

        except Exception as exc:
            logger.warning(
                f"Primary endpoint ({self.primary_base_url}) error on {target_model}: {exc}. "
                "Evaluating fallback endpoint..."
            )

        # 2. Attempt via Fallback OpenAPI Endpoint (if configured)
        if not self.fallback_client:
            raise RuntimeError(f"Primary endpoint failed on {target_model} and no fallback endpoint is configured.")

        candidate_fb_models = [m for m in [
            "google/gemma-4-26b-a4b-it:free",
            "liquid/lfm-2.5-2.6b:free",
            self.fallback_model if self.fallback_model and "free" in self.fallback_model else None,
            "meta-llama/llama-3.3-70b-instruct",
            "meta/llama-3.3-70b-instruct",
            "meta-llama/llama-3.1-8b-instruct",
            self.fallback_model if not "vision" in (self.fallback_model or "") else None,
        ] if m]
        seen_models = set()
        fallback_models_queue = []
        for m in candidate_fb_models:
            if m not in seen_models:
                seen_models.add(m)
                fallback_models_queue.append(m)

        for fb_model in fallback_models_queue:
            try:
                fb_comp = self.fallback_client.chat.completions.create(
                    model=fb_model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=min(effective_max_tokens, 4096),
                )
                choice = fb_comp.choices[0]
                content = choice.message.content or getattr(choice.message, "reasoning", "") or ""
                return {
                    "status": "success",
                    "provider": self.fallback_provider,
                    "model_used": fb_model,
                    "content": content.strip(),
                    "reasoning": "",
                    "raw": fb_comp.model_dump() if hasattr(fb_comp, "model_dump") else str(fb_comp),
                }
            except RateLimitError:
                logger.warning(f"Fallback endpoint 429 on {fb_model}, advancing fallback queue...")
                continue
            except Exception as fb_exc:
                logger.warning(f"Fallback endpoint error on {fb_model}: {fb_exc}")
                continue

        raise RuntimeError(f"All configured OpenAPI endpoints failed for request.")

    def create_embedding(
        self,
        input_texts: Union[str, List[str]],
        model: Optional[str] = None,
        target_dim: Optional[int] = None,
    ) -> List[List[float]]:
        """Generate cloud API embeddings without downloading local model weights.

        Features:
        - 0 MB local footprint (pure cloud API execution).
        - Automatically aligns vector dimensions to target_dim if failover occurs.
        - Enforces global rate limits before dispatching network calls.
        """
        target_model = model or self.primary_embedding_model
        expected_dim = target_dim or self.primary_embedding_dim
        inputs = [input_texts] if isinstance(input_texts, str) else input_texts

        # Enforce rate limiter
        self.rate_limiter.acquire(estimated_tokens=max(10, len(inputs) * 20))

        # 1. Primary Embedding Endpoint
        try:
            resp = self.primary_client.embeddings.create(input=inputs, model=target_model)
            raw_embeddings = [d.embedding for d in resp.data]
            if expected_dim:
                return [adapt_vector_dimension(e, expected_dim) for e in raw_embeddings]
            return raw_embeddings
        except Exception as exc:
            logger.warning(f"Primary embedding failed on {target_model}: {exc}. Evaluating fallback embedding...")

        # 2. Fallback Embedding Endpoint
        if self.fallback_client and self.fallback_embedding_model:
            try:
                resp_fb = self.fallback_client.embeddings.create(input=inputs, model=self.fallback_embedding_model)
                raw_embeddings = [d.embedding for d in resp_fb.data]
                if expected_dim:
                    return [adapt_vector_dimension(e, expected_dim) for e in raw_embeddings]
                return raw_embeddings
            except Exception as fb_exc:
                logger.error(f"Fallback embedding failed on {self.fallback_embedding_model}: {fb_exc}")

        raise RuntimeError("All configured cloud embedding endpoints failed.")

    def _stream_generator(self, client: OpenAI, kwargs: Dict[str, Any]) -> Generator[str, None, None]:
        """Stream chunks following the OpenAI streaming specification."""
        completion = client.chat.completions.create(**kwargs)
        for chunk in completion:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            delta_content = getattr(delta, "content", None)
            if delta_content:
                yield delta_content


_generic_client_instance = None


def get_openai_client() -> GenericOpenAIClient:
    """Singleton accessor for GenericOpenAIClient."""
    global _generic_client_instance
    if _generic_client_instance is None:
        _generic_client_instance = GenericOpenAIClient()
    return _generic_client_instance


# Aliases for backward compatibility
ResilientAIClient = GenericOpenAIClient
OpenRouterResilientClient = GenericOpenAIClient
get_ai_client = get_openai_client
get_openrouter_client = get_openai_client
