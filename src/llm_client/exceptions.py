"""Custom exceptions for the invariant module."""

from __future__ import annotations


class InferenceError(RuntimeError):
    """Base class for domain-specific runtime errors."""


class LLMUnavailableError(InferenceError):
    """Raised when the LLM backend cannot serve a request."""


class PromptNotFoundError(InferenceError):
    """Raised when an expected prompt template cannot be loaded."""