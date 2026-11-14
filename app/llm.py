"""Provider-agnostic LangChain LLM construction and prompt utilities."""

from __future__ import annotations

from typing import Any

from langchain_core.prompts import ChatPromptTemplate

from app.config import Settings, settings


SUPPORTED_PROVIDERS = {"openai", "gemini", "anthropic"}


class LLMConfigurationError(ValueError):
    """Provider configuration is invalid or incomplete."""


def validate_llm_settings(config: Settings) -> None:
    provider = config.llm_provider.casefold().strip()
    if provider not in SUPPORTED_PROVIDERS:
        raise LLMConfigurationError(
            f"Unsupported LLM_PROVIDER: {config.llm_provider!r}. Expected openai, gemini or anthropic."
        )
    api_key = {
        "openai": config.openai_api_key,
        "gemini": config.google_api_key,
        "anthropic": config.anthropic_api_key,
    }[provider]
    if not api_key.strip():
        raise LLMConfigurationError(f"Missing API key for provider: {provider}")
    if config.llm_timeout_seconds <= 0:
        raise LLMConfigurationError("LLM_TIMEOUT_SECONDS must be positive")
    if config.llm_max_retries < 0:
        raise LLMConfigurationError("LLM_MAX_RETRIES must be non-negative")


def create_llm(config: Settings | None = None) -> Any:
    """Create a LangChain chat model without making a request."""
    config = config or settings
    validate_llm_settings(config)
    provider = config.llm_provider.casefold().strip()
    if provider == "openai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(api_key=config.openai_api_key, model=config.openai_model, timeout=config.llm_timeout_seconds, max_retries=config.llm_max_retries)
    if provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(google_api_key=config.google_api_key, model=config.gemini_model, timeout=config.llm_timeout_seconds, max_retries=config.llm_max_retries)
    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(api_key=config.anthropic_api_key, model=config.anthropic_model, timeout=config.llm_timeout_seconds, max_retries=config.llm_max_retries)
    raise LLMConfigurationError(f"Unsupported LLM_PROVIDER: {config.llm_provider!r}. Expected openai, gemini or anthropic.")


def qa_prompt() -> ChatPromptTemplate:
    return ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """You answer questions only from the supplied annual-report evidence.
Do not use outside knowledge or infer missing values. Preserve the financial year,
standalone/consolidated scope, units, signs and exact figures. Return JSON only with
this shape: {{"answer": "...", "excerpts": [{{"text": "exact supporting excerpt", "pages": [131]}}]}}.
Every factual statement must be supported by an exact excerpt copied from evidence.
Use PDF page numbers from the evidence. If evidence is insufficient or the question
is ambiguous, return exactly {{"answer": "Information not found in the provided document", "excerpts": []}}.""",
            ),
            (
                "human",
                "Question:\n{question}\n\nRetrieved evidence (use only this):\n{evidence}",
            ),
        ]
    )
