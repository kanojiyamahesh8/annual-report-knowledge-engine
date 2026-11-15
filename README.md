# Annual Report Q&A

Evidence-grounded Q&A over the supplied Centum Electronics annual report. The application extracts financial tables with PyMuPDF, retrieves evidence with BM25, and uses a configurable LangChain chat provider to answer with exact excerpts and PDF page citations.

## Requirements

- Python 3.13 recommended
- One configured LLM provider credential
- The supplied annual-report PDF at `documents/Centum_Annual_Report.pdf`

The checked-in evidence artifact covers the complete 335-page report and 245 extracted financial tables.

## Setup

From the project root in PowerShell:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env` and configure one provider. Never commit `.env` or API keys.

## Provider configuration

OpenAI:

```env
LLM_PROVIDER=openai
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4o-mini
```

Gemini:

```env
LLM_PROVIDER=gemini
GOOGLE_API_KEY=your_google_api_key
GEMINI_MODEL=gemini-2.0-flash
```

Anthropic:

```env
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=your_anthropic_api_key
ANTHROPIC_MODEL=claude-3-5-sonnet-latest
```

Groq:

```env
LLM_PROVIDER=groq
GROQ_API_KEY=your_groq_api_key
GROQ_MODEL=llama-3.3-70b-versatile
```

The provider factory and Q&A service are provider-neutral. The selected model must be available to the configured account. API billing and access are provider-specific.

Optional settings:

```env
EVIDENCE_PATH=data/full_evidence.json
LLM_TIMEOUT_SECONDS=30
LLM_MAX_RETRIES=2
LOG_LEVEL=INFO
```

## Run locally

```powershell
.\.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000` in a browser.

Useful endpoints:

```text
GET  /health
GET  /ready
POST /api/ask
```

Example request:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/ask `
  -Method Post `
  -ContentType 'application/json' `
  -Body '{"question":"What were standalone total assets in 2026?"}'
```

## Provider smoke tests

The smoke-test script makes one minimal live request using the configured credentials. It reports only provider, model, latency, error type, and HTTP status; it does not print keys, prompts, or response content.

```powershell
python scripts\provider_smoke_test.py --provider groq
python scripts\provider_smoke_test.py --provider openai
python scripts\provider_smoke_test.py --provider gemini
python scripts\provider_smoke_test.py --provider anthropic
```

To test every configured provider:

```powershell
python scripts\provider_smoke_test.py --provider all
```

Live smoke tests require valid credentials, model access, and provider billing/credits. Use one provider at a time to control API usage.

## Verification

Run the complete test suite:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Latest verified result: **66 passed, 6 warnings**. The test suite covers extraction, table continuity, BM25 retrieval, deterministic row/column selection, exact cell-page provenance, citation validation, unsupported questions, API contracts, provider switching, request IDs, retries, and resilience behavior.

The latest live provider verification passed for Groq. Gemini and Anthropic live checks require credentials; provider switching for all supported adapters is covered by mocked tests.

## Evidence and answer guarantees

- Only retrieved evidence is supplied to the LLM.
- Financial tables remain atomic chunks and multi-page tables preserve row-level PDF page provenance.
- Answers must preserve financial year, figures, units, and standalone/consolidated scope.
- Supporting excerpts must match stored evidence exactly.
- Invalid, unsupported, ambiguous, or unresolved questions return exactly `Information not found in the provided document`.
- Provider failures are returned safely while structured logs include request IDs and safe provider error type/status diagnostics.
