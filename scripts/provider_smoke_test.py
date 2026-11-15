"""Live smoke test for the configured LangChain provider adapters.

This intentionally makes one small API request per selected provider. It is
opt-in and should be run only when API usage is acceptable.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
import sys
from time import perf_counter
from typing import Any

# Allow direct execution as `python scripts/provider_smoke_test.py`.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.config import Settings
from app.llm import create_llm


PROVIDERS = ("openai", "gemini", "anthropic", "groq")


@dataclass(frozen=True)
class SmokeResult:
    provider: str
    model: str
    ok: bool
    latency_ms: float
    error_type: str | None = None
    status_code: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            key: value
            for key, value in {
                "provider": self.provider,
                "model": self.model,
                "ok": self.ok,
                "latency_ms": self.latency_ms,
                "error_type": self.error_type,
                "status_code": self.status_code,
            }.items()
            if value is not None
        }


def _model_name(config: Settings, provider: str) -> str:
    return {
        "openai": config.openai_model,
        "gemini": config.gemini_model,
        "anthropic": config.anthropic_model,
        "groq": config.groq_model,
    }[provider]


def _status_code(exc: BaseException) -> int | None:
    current: BaseException | None = exc
    seen: set[int] = set()
    deepest = exc
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        deepest = current
        current = current.__cause__ or current.__context__
    status = getattr(deepest, "status_code", None)
    if status is None:
        status = getattr(getattr(deepest, "response", None), "status_code", None)
    return status if isinstance(status, int) else None


def smoke_provider(provider: str, prompt: str) -> SmokeResult:
    config = Settings(llm_provider=provider)
    started = perf_counter()
    try:
        model = create_llm(config)
        response = model.invoke(prompt)
        content = getattr(response, "content", response)
        if isinstance(content, list):
            content = "".join(
                part.get("text", "") if isinstance(part, dict) else str(part)
                for part in content
            )
        if not str(content).strip():
            raise RuntimeError("Provider returned empty content")
        return SmokeResult(
            provider=provider,
            model=_model_name(config, provider),
            ok=True,
            latency_ms=round((perf_counter() - started) * 1000, 2),
        )
    except Exception as exc:
        return SmokeResult(
            provider=provider,
            model=_model_name(config, provider),
            ok=False,
            latency_ms=round((perf_counter() - started) * 1000, 2),
            error_type=type(exc).__name__,
            status_code=_status_code(exc),
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--provider",
        choices=["all", *PROVIDERS],
        default="all",
        help="Provider to test; defaults to all four providers.",
    )
    parser.add_argument(
        "--prompt",
        default="Reply with exactly OK.",
        help="Minimal prompt used for the smoke request.",
    )
    args = parser.parse_args()
    providers = PROVIDERS if args.provider == "all" else (args.provider,)
    results = [smoke_provider(provider, args.prompt) for provider in providers]
    for result in results:
        print(json.dumps(result.to_dict(), ensure_ascii=False))
    return 0 if all(result.ok for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
