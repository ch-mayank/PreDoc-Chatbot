"""Backward-compatible wrapper delegating to GenericOpenAIClient.

Maintains full backward compatibility for existing imports of ResilientAIClient
while delegating to backend.openai_client.
"""

from backend.openai_client import (
    EnterpriseRateLimiter,
    FREE_EMBEDDING_MODEL,
    FREE_MODELS,
    GenericOpenAIClient,
    MODEL_TOKEN_LIMITS,
    OpenRouterResilientClient,
    ResilientAIClient,
    get_ai_client,
    get_openai_client,
    get_openrouter_client,
)

__all__ = [
    "EnterpriseRateLimiter",
    "FREE_EMBEDDING_MODEL",
    "FREE_MODELS",
    "GenericOpenAIClient",
    "MODEL_TOKEN_LIMITS",
    "OpenRouterResilientClient",
    "ResilientAIClient",
    "get_ai_client",
    "get_openai_client",
    "get_openrouter_client",
]
