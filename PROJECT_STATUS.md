# Project Status

## Milestone 4 - Review checkpoint

Status: complete and verified; Milestone 4 commit follows.

Last Updated: 2026-11-14 22:42:49 IST (Asia/Kolkata)

### Completed

- Added LangChain provider switching through `.env` for OpenAI, Gemini and Anthropic Claude, with provider-specific model settings and no API calls during construction.
- Added evidence-grounded Q&A over the existing BM25 retriever; the LLM receives only retrieved chunks, exact stored excerpts and PDF page metadata.
- Added prompt requirements for preserving financial years, figures, units and standalone/consolidated scope.
- Added exact excerpt and PDF-page citation validation against stored retrieval evidence.
- Citation validation now rejects empty page lists and checks numeric, year, unit and scope claims against the cited chunk text.
- Unsupported-question detection now rejects queries with multiple unmatched substantive terms before invoking the LLM.
- Added deterministic rejection for unsupported, unresolved, ambiguous or invalidly cited answers using exactly `Information not found in the provided document`.
- Added mocked regression tests for empty pages, hallucinated figures paired with valid excerpts, unmatched substantive terms, unsupported and ambiguous questions, all three provider branches and unknown-provider rejection.

### Files created or modified

- `app/llm.py`
- `app/qa.py`
- `app/config.py`
- `tests/test_qa.py`
- `PROJECT_STATUS.md`

### Verified test results

- `.venv\\Scripts\\python.exe -m pytest -q`: **40 passed, 6 warnings** in 12.08 seconds.
- No paid API calls were made.
- Frontend integration was not started.
- Milestone 4 is complete and committed after review.

Project: Provider-Agnostic Annual Report Knowledge Engine  
Current milestone: Milestone 4 - Review checkpoint
Last Updated: 2026-11-14 22:42:49 IST (Asia/Kolkata)

## Completed

- Milestone 0 — repository baseline inspected; no implementation files are present yet.
- Added this status tracker to the project root.

## Files created or modified

- `PROJECT_STATUS.md` — created.

## Test results

- No tests run; no application or test files are present in the repository.

## Unresolved issues

- The provided shared ChatGPT brief could not be retrieved because browser access was unavailable and the text fetch returned a cache miss. Requirements and architecture therefore remain unverified.

## Technical decisions

- Do not infer or change the project architecture until the agreed brief is available.
- Keep this file concise and update it only with verified implementation and test results.

## Milestone 0 verification follow-up

### Verified findings

- Direct workspace verification of `.venv\Scripts\python.exe --version` failed with `Access is denied`.
- Direct workspace verification of `.venv\Scripts\python.exe -m pip --version` failed with the same error.
- The existing `.venv\pyvenv.cfg` still targets the inaccessible WindowsApps Python 3.13 installation.
- PyCharm project configuration still points to the project `.venv`; therefore PyCharm is configured for the same currently failing interpreter and compatibility cannot be claimed.
- No packages were installed in this follow-up because the project interpreter is not executable.
- `Centum_Annual_Report.pdf` was checked in the project root and was not found. It has not been processed.

### Test results

- `.venv\Scripts\python.exe --version`: failed, exit code 103.
- `.venv\Scripts\python.exe -m pip --version`: failed, exit code 103.
- PyCharm SDK configuration inspection: passed, but it references the failing `.venv`.
- PDF presence check: failed; `Centum_Annual_Report.pdf` is absent from the project root.

### Unresolved issues

- The manual VS Code report that `.venv` is working conflicts with independent execution from the Project 2 workspace. The checked `.venv` remains broken and was not recreated or deleted.
- Required dependencies, imports, `pip check`, and `requirements.txt` remain pending until the existing `.venv` executes successfully.
- The earlier inaccessible-interpreter issue is not marked resolved because direct verification still reproduces it.
- The prior shared-URL issue is superseded by direct requirements supplied in ChatGPT; no URL retrieval is required.

## Milestone 0 audit findings

### Verified

- PyCharm project configuration points to `.venv` as its Python SDK (`.idea/misc.xml` and project module configuration).
- `.venv\pyvenv.cfg` targets Python 3.13.14 under `C:\Users\HP\AppData\Local\Microsoft\WindowsApps\...`.
- `.venv\Scripts\python.exe` and `.venv\Scripts\pip.exe` do not execute: both fail because the configured Windows Store Python target returns `Access is denied`.
- Project terminal commands execute successfully in PowerShell, but commands using the project's `.venv` fail as above.
- A separate system Python 3.15.0 and pip 26.2.1 are available at `C:\Python315`, but they are not the configured project interpreter.
- The project workspace is readable and writable by Codex; a temporary write/read probe succeeded and was removed.
- No application modules or business logic were created.

### Test results

- `\.venv\Scripts\python.exe --version`: failed; inaccessible configured base interpreter.
- `\.venv\Scripts\python.exe -m pip --version`: failed; same interpreter access error.
- `\.venv\Scripts\pip.exe --version`: failed; exit code 103.
- `C:\Python315\python.exe --version`: passed; Python 3.15.0.
- `C:\Python315\python.exe -m pip --version`: passed; pip 26.2.1.
- Workspace write/read probe: passed; temporary probe removed afterward.
- PyMuPDF, FastAPI, openai, google-genai and anthropic were not installed or imported; no package installation was attempted. Compatibility cannot be validated in the broken project environment.

### Unresolved issues

- The configured `.venv` must be repaired or recreated before dependency compatibility or application tests can be run. No environment change was attempted.
- PyCharm may not be able to run Python code using the configured SDK until the `.venv` interpreter target is fixed.
- No dependency lockfile or requirements file is present, so intended package versions are not yet defined.

## Milestone 0 / Milestone 1 transition

- User-reported manual repair set `.venv\pyvenv.cfg` to Python 3.13.17 from `C:\Users\HP\AppData\Local\Programs\Python\Python313`.
- Independent Codex execution still receives `Access is denied` when invoking `.venv\Scripts\python.exe`; Python, pip, package installation, imports, `pip check`, and runtime tests could not be executed here.
- PyCharm configuration continues to reference the project `.venv`; the SDK path is structurally correct, but runtime compatibility could not be independently confirmed.
- The earlier WindowsApps target is no longer present in the current `pyvenv.cfg`, but the environment is not marked fully verified because execution remains blocked.

## Current milestone: Milestone 1 - Foundation and PDF inspection

### Completed

- Created the minimal FastAPI foundation: `/` HTML homepage and `/health` JSON endpoint.
- Added environment-backed settings for provider and model configuration without credentials or API calls.
- Added static HTML/CSS/JavaScript placeholders and pytest health/homepage tests.
- Added explicitly pinned dependency manifest covering PyMuPDF, FastAPI, Uvicorn, provider SDKs, LangChain integrations, BM25, dotenv, Jinja2, httpx and pytest.

### Files created or modified

- `app/__init__.py`
- `app/main.py`
- `app/config.py`
- `templates/index.html`
- `static/style.css`
- `static/app.js`
- `.env.example`
- `.gitignore`
- `requirements.txt`
- `tests/test_health.py`
- `PROJECT_STATUS.md`

### Verification results

- `.venv\Scripts\python.exe --version`: blocked by `Access is denied` in this execution environment.
- `.venv\Scripts\python.exe -m pip --version`: blocked by the same restriction.
- Dependency installation: not executed; no successful installation is claimed.
- Package imports, LangChain provider imports, FastAPI startup, `/health`, `/`, and `pip check`: not executed because the project interpreter could not be launched.
- `Centum_Annual_Report.pdf`: not found in the project workspace; no PDF inspection was performed.

### Technical decisions

- Keep PDF extraction, chunking, retrieval and citation verification outside LangChain; LangChain is reserved for later LLM integration and prompt handling.
- Do not create provider adapters, make paid API calls, implement RAG, or process a PDF in this milestone.
- Preserve the user-specified Python 3.13.17 environment and do not recreate `.venv` from Codex.

### Unresolved issues / next milestone

- Resolve the execution-context restriction or run the provided dependency and test commands manually from the project workspace.
- After successful environment execution, install from `requirements.txt`, run imports and `pip check`, then inspect `Centum_Annual_Report.pdf` with PyMuPDF only.

## Milestone 1 PDF inspection update

### Verified by Codex

- PDF located at `documents/Centum_Annual_Report.pdf`.
- File exists and is approximately 12.0 MB.
- No PDF processing or application extraction code was added.

### Not yet verified

- Page count, text extractability, financial-statement locations, table structures, multi-page tables, merged cells, units, and printed-page-number differences remain uninspected.

### Blocker

- PyMuPDF inspection could not run: `.venv\Scripts\python.exe` remains inaccessible with `Access is denied`, and the available system Python 3.15 has no `fitz` module. No alternative PDF parser was used.

### Next recommended action

- From a working Project 2 terminal, run the PyMuPDF-only inspection using `documents/Centum_Annual_Report.pdf`, then record the actual output here before implementing extraction.

## Milestone 1 environment clarification

- Verified manually by the user in the PyCharm terminal: the configured Python 3.13.17 executable, `.venv\Scripts\python.exe`, and pip execute successfully.
- Not verified by Codex: the same `.venv` remains inaccessible from Codex's restricted execution context with `Access is denied`.
- Consequently, Codex has not claimed PyMuPDF inspection results; page count, text extraction, financial statement locations, table layouts, multi-page behavior, and printed-page mapping remain pending.

## Milestone 1 PDF inspection results

### Verified by Codex using PyMuPDF

- Input: `documents/Centum_Annual_Report.pdf`.
- Page count: 335.
- Text extraction: all 335 pages contain non-empty extractable text; no OCR was used.
- Standalone financial statements: PDF pages 131-135. Balance Sheet is page 131; Profit and Loss is page 132; Cash Flow spans pages 133-134; Changes in Equity is page 135.
- Standalone notes begin at PDF page 136 and continue through the later standalone section.
- Consolidated financial statements: PDF pages 227-232. Balance Sheet is page 227; Profit and Loss is page 228; Cash Flows span pages 229-230; Changes in Equity spans pages 231-232.
- Consolidated notes begin at PDF page 233.
- Core standalone tables extracted with `find_tables()` preserved row labels and year columns: page 131 produced 55 rows x 4 columns; page 132 33 x 4; page 133 50 x 3; page 134 produced 10 x 3 and 10 x 4 tables; page 135 included an 8-column equity table.
- Units and comparative years are present in table headers. The rupee symbol is not preserved cleanly in some extracted text and appears as an encoding artifact, so original source excerpts must be retained.
- Complex note tables require explicit handling: examples include 9-column ageing tables split across pages 161-162 and 173-174, a promoter/shareholding table split across pages 165-166, and a wide 23-column PPE table on page 155 with grouped headers.
- `find_tables()` can preserve useful table structure but does not by itself stitch multi-page tables or fully reconstruct merged/grouped headers.
- Printed-page mapping differs from zero-based/PDF page indexing. In the financial section, PDF page 120 carries printed page 143, PDF page 131 carries printed page 154, and PDF page 132 carries printed page 155, indicating a +23 offset there. The cover and early front matter do not use the same simple mapping.

### Tests executed and results

- Elevated `.venv\Scripts\python.exe --version`: passed; Python 3.13.17.
- Elevated `.venv\Scripts\python.exe -m pip --version`: passed; pip 26.2.2.
- PyMuPDF page/text scan: passed; 335/335 pages have text.
- PyMuPDF section-location scan: passed; standalone and consolidated statement ranges identified above.
- PyMuPDF targeted `find_tables()` scans: passed on representative statement and notes pages; results recorded above.
- Temporary inspection script was removed after use; no extraction pipeline was created.

### Technical decisions

- Use zero-based PDF page index plus extracted printed-page label as separate citation metadata; never assume a global offset.
- Preserve raw page text and raw table excerpts because currency glyph encoding and merged headers may not survive normalization.
- Implement multi-page table stitching and grouped-header reconstruction explicitly in Milestone 2; do not delegate PDF parsing to LangChain.

### Unresolved issues / next recommended milestone

- The exact table stitching rules for all notes and consolidated tables remain to be implemented and validated against representative figures.
- Proceed to Milestone 2: PyMuPDF extraction models for paragraphs, headings, tables, source pages, units, raw excerpts and multi-page table continuity.

## Milestone 2 implementation update

### Completed

- Added `app/extraction.py` with explicit PyMuPDF extraction models for pages, table fragments, financial tables and extracted documents.
- Preserved PDF page numbers, detected printed-page labels, raw page text, raw table excerpts, table headers, rows, units and source-page lists.
- Added conservative multi-page stitching: consecutive fragments merge only when their extracted headers repeat; unrelated or nonconsecutive tables remain separate.
- Added tests for repeated-header financial table continuation and non-merge behavior.

### Files created or modified

- `app/extraction.py` - created.
- `tests/test_extraction.py` - created.
- `PROJECT_STATUS.md` - modified.

### Tests executed and results

- Elevated `.venv\Scripts\python.exe -m pytest -q`: passed, 4 tests passed, 6 deprecation warnings.
- Tests cover the existing homepage/health endpoints and the new multi-page table stitching behavior.
- A full-document `extract_document()` smoke run was attempted against the 335-page PDF but did not return a completed summary within the execution window; it is not marked as passed.

### Technical decisions

- Keep extraction models independent of FastAPI and LangChain so they can be tested as pure document-processing code.
- Retain raw excerpts alongside normalized rows to support later citation verification and audit review.
- Use repeated-header matching plus consecutive PDF pages as the initial safe stitching rule; do not guess across missing or ambiguous headers.

### Known issues / next recommended action

- `extract_document()` currently scans every page with `find_tables()`, which is slow on the full report and needs performance profiling before broad batch use.
- Units and merged/grouped headers need representative validation against the actual standalone and consolidated tables.
- Next: add extraction validation tests against selected report pages and JSON serialization for processed evidence; do not begin retrieval yet.

## Milestone 2 validation and JSON evidence

### Completed

- Added optional selected-page extraction to avoid requiring a full-report table scan for targeted validation.
- Added deterministic JSON serialization for extracted pages and financial tables, including source pages, headers, rows, units and raw excerpts.
- Generated `data/selected_evidence.json` from 17 real report pages: standalone statements (131-135), known multi-page standalone tables (161-162, 165-166, 173-174), and consolidated statements (227-232).
- Selected-page extraction produced 23 tables and stitched multi-page tables on `[133, 134]`, `[161, 162]`, `[165, 166]`, `[173, 174]`, and `[229, 230]`.

### Files created or modified

- `app/extraction.py` - modified for selected pages and JSON serialization.
- `tests/test_extraction.py` - modified with serialization coverage.
- `data/selected_evidence.json` - generated real-document evidence artifact.
- `PROJECT_STATUS.md` - modified.

### Tests executed and results

- Elevated `.venv\Scripts\python.exe -m pytest -q`: passed, 5 tests passed, 6 deprecation warnings.
- Selected-page PyMuPDF extraction: passed; 17 pages selected, full document count retained as 335, 23 tables extracted.
- Multi-page stitching validation: passed for the five page pairs listed above.
- JSON reload validation: passed; artifact is valid JSON with 17 pages and 23 tables, 146,860 bytes.

### Known issues / next recommended action

- The generated artifact is a selected-page validation output, not yet the complete processed report JSON.
- Table units and merged/grouped headers still require figure-level validation before retrieval is implemented.
- Next: complete extraction validation for representative financial figures, then proceed to structure-aware chunking and BM25 retrieval.

## Git checkpoint

- Repository initialized locally; no remote configured and nothing will be pushed.
- Checkpoint commit message: `checkpoint: add PyMuPDF extraction and JSON evidence`.
- Files planned for this checkpoint: application foundation, extraction models, tests, requirements, configuration examples, selected JSON evidence, and this status file.
- `.venv`, `.env`, caches, IDE metadata, the generated structure listing, logs and the source PDF are excluded by `.gitignore`.
- Credential review: no API keys or credential values are present in the files planned for staging; `.env` remains ignored.

## Milestone 2 representative financial-figure validation

### Completed

- Added direct PDF-versus-structured-extraction regression tests for standalone and consolidated statements.
- Standalone values matched the PDF tables exactly:
  - PDF page 131, `Total assets (1+2)`: `11,059.12`, `11,204.97`.
  - PDF page 132, `Revenue from operations`: `9,730.56`, `7,760.93`.
  - PDF page 133, `Cash and cash equivalents at the end of the year`: `364.97`, `486.76`.
- Consolidated values matched the PDF tables exactly:
  - PDF page 227, `Total assets (1+2+3)`: `13,027.12`, `12,394.46`.
  - PDF page 228, `Revenue from operations`: `9,527.49`, `7,402.59`.
  - PDF page 229, `Cash and cash equivalents at the end of the year`: `622.38`, `654.56`.

### Files created or modified

- `tests/test_financial_validation.py` - created.
- `PROJECT_STATUS.md` - modified.

### Tests executed and results

- Elevated `.venv\Scripts\python.exe -m pytest -q`: passed, 7 tests passed, 6 deprecation warnings in 6.09 seconds.
- Direct PyMuPDF table rows and structured extraction rows matched for all six representative figures above.

### Known issues / next recommended action

- Validation currently covers selected statement figures; notes, grouped headers, units and the full report still need broader representative checks.
- Next: begin Milestone 3 structure-aware chunking and BM25 retrieval using the verified JSON evidence model; keep tables intact and retain evidence IDs/pages.

## Milestone 2 complex-note validation and completion review

### Verified complex cases

- PPE grouped-header table on PDF page 155: PyMuPDF preserved the raw grouped header text and 23 extracted columns, including `Gross block` and `As at April 01, 2024`; the page unit text includes `in million`. The raw excerpt retains values such as `1,337.25`.
- Trade-receivables ageing table on PDF pages 161-162: stitched source pages and preserved the 9-column header, year/value relationship, and `2,971.87` total for the representative row.
- Promoter/shareholding table on PDF pages 165-166: stitched source pages and preserved the beginning/change/end share values for Apparao V Mallavarapu (`58,97,549`, `(6,66,000)`, `52,31,549`).
- Payables ageing table on PDF pages 173-174: stitched source pages and preserved the `Total` row ending in `2,549.37`.
- Grouped-header evidence is retained raw, but the current structured model does not yet normalize grouped PPE columns into semantic subcolumns; this remains a known limitation.

### Tests executed and results

- Complete pytest suite: passed, 10 tests passed, 6 deprecation warnings in 7.79 seconds.
- Added `tests/test_complex_note_tables.py` regression coverage for grouped headers, units, year-to-value relationships and multi-page continuity.
- Full-report `extract_document()` performance check: did not return a completed summary within the available execution window for the 335-page scan. The all-page `find_tables()` path remains a performance issue requiring profiling/optimization before full-report processing can be considered complete.

### Git checkpoint verification

- Local checkpoint is committed: `371c917 checkpoint: add PyMuPDF extraction and JSON evidence`.
- Verified commit object: `371c9178ad704415621eef9075be2b33a8f40619`.
- No remote push was performed.
- Current post-checkpoint changes are limited to `PROJECT_STATUS.md`, `tests/test_financial_validation.py`, and `tests/test_complex_note_tables.py`; they are not committed yet.

### Milestone 2 status

- Milestone 2 is not complete yet. Representative complex-table validation and regression tests pass, but full-report extraction performance and semantic normalization of grouped headers remain unresolved. Do not begin Milestone 3 until those issues are addressed or explicitly accepted.

## Milestone 2 issue-resolution attempt

### Implemented

- Added a low-cost page candidate filter before calling PyMuPDF `find_tables()`. The optimized scan reduced table-detection candidates from all 335 pages to 152 pages while retaining statement/note table keywords and financial-year/unit signals.
- Added grouped-header normalization for obvious two-row headers. Parent and child labels are combined into semantic column names such as `Outstanding for following periods from due date of payment / Less than 6 months`; raw excerpts remain unchanged.
- Regenerated `data/selected_evidence.json` so the artifact reflects normalized headers.
- Added regression assertions for normalized ageing-table headers and unit/raw-excerpt retention.

### Verification

- Selected real-page extraction: passed; normalized headers verified for tables spanning 161-162, 165-166 and 173-174.
- Complete pytest suite: passed, 10 tests passed, 6 deprecation warnings in 18.26 seconds.
- Full-report performance check after optimization: still did not return a completed 335-page extraction summary within the available execution window. A 20-page candidate sample took 7.67 seconds with default/lines table detection, so the full scan is expected to remain slow.

### Remaining issues / milestone decision

- The candidate filter and grouped-header normalization improve the implementation, but full-report extraction performance remains unresolved and the dense PPE table on page 155 still exposes a wide raw layout rather than fully semantic subcolumns.
- Historical checkpoint: Milestone 2 was incomplete at that point because full-report performance and PPE grouped-column semantics were still unresolved; those issues are addressed in the final resolution below.

## Milestone 2 final issue resolution

### Completed

- Optimized full-report extraction with a candidate-page filter and isolated PyMuPDF worker processes that process page batches using one PDF handle per worker.
- Full-report extraction now completes successfully: 335 pages, 245 extracted tables, 41 stitched multi-page tables, and 12 semantic PPE columns.
- Final measured runtime: 25.00 seconds in the Project 2 Python 3.13.17 environment.
- Added semantic PPE grouped-column metadata for page 155 while retaining the original 23-column raw table evidence. The normalized columns are Particulars, Freehold land, Leasehold improvements, Building, Plant and equipments, Electrical installations, Computers, Office equipments, Furniture and fixtures, Vehicles, Leasehold land, and Total.
- Added regression coverage for PPE semantic groups, normalized ageing headers, units/raw excerpts, multi-page continuity, and representative financial values.
- Regenerated `data/selected_evidence.json` with PPE semantic metadata: 18 selected pages, 24 tables, 165,912 bytes.

### Files created or modified

- `app/extraction.py` - modified for candidate filtering, process-batched scans, grouped-header normalization and PPE semantic metadata.
- `tests/test_complex_note_tables.py` - modified with PPE semantic-column assertions.
- `data/selected_evidence.json` - regenerated.
- `PROJECT_STATUS.md` - modified.

### Tests and benchmarks

- Complete pytest suite: passed, 10 tests passed, 6 deprecation warnings in 10.58 seconds.
- Full-report extraction: passed, completed in 25.00 seconds with exit code 0.
- PPE page-155 semantic-header verification: passed; 12 normalized columns and three grouped sections retained.

### Milestone decision

- Milestone 2 is complete. Milestone 3 has not started and remains the next recommended milestone: structure-aware chunking and BM25 retrieval using the verified evidence model.

## GitHub publication

- Local Milestone 2 changes are prepared for commit and publication.
- GitHub repository creation and push are pending authentication/tool availability; no remote is configured yet.
- The source PDF, `.env`, `.venv`, caches and IDE metadata remain excluded by `.gitignore`.

## GitHub publication

- Public repository: https://github.com/kanojiyamahesh8/annual-report-knowledge-engine
- Remote: `origin` set to the repository URL above.
- Local Milestone 2 HEAD before this status update: `2711b12e158093a1bcd545b2eebcd896031bf99f`.
- Initial publication push: succeeded; `origin/master` matched local `master` at that commit.
- Publication status: source, tests, requirements and documentation pushed successfully; source PDF, secrets, `.venv`, caches and IDE files were excluded.
- This status update is the final publication record and will be committed and pushed as a follow-up commit.

## Milestone 3 initial implementation

### Completed

- Added `app/retrieval.py` with explicit evidence chunking and BM25 retrieval using `rank-bm25`.
- Page text is chunked by paragraph boundaries with a configurable character limit and retains PDF source pages and raw excerpts.
- Financial tables are emitted as atomic `financial_table` chunks and are never split; table IDs, source pages, headers, semantic headers, units and raw excerpts are retained.
- Added `load_evidence()` and `BM25Retriever.from_evidence()` for the verified local JSON evidence format.
- Added transparent tokenization and ranked results containing chunk IDs, source pages, source table IDs and scores.
- No LLM provider integration, provider factory, API calls, vector database or LangChain retrieval logic was added.

### Files created or modified

- `app/retrieval.py` - created.
- `tests/test_retrieval.py` - created.
- `PROJECT_STATUS.md` - modified.

### Tests executed and results

- Complete pytest suite: passed, 13 tests passed, 6 deprecation warnings in 12.74 seconds.
- BM25 smoke test over `data/selected_evidence.json`: passed; returned ranked page and financial-table evidence with source pages for the `total assets 2026` query.
- Tests cover atomic tables, source-page retention, BM25 ranking, and empty-query behavior.

### Technical decisions

- Keep BM25 and chunking explicit Python code; LangChain remains reserved for later LLM integration and prompt handling.
- Preserve table atomicity even when a table exceeds the normal page-text chunk size.
- Return evidence metadata with every retrieval result so later answer generation can cite stored pages and excerpts.

### Known issues / next recommended action

- Retrieval ranking is now functional over local evidence, but question-specific relevance evaluation over a broader set of actual annual-report questions remains to be added.
- Citation validation, fallback responses and provider integration are intentionally deferred.
- Continue Milestone 3 with retrieval evaluation tests before beginning Milestone 4 provider integration.

## Milestone 3 real-report retrieval evaluation

### Completed

- Added `tests/test_retrieval_evaluation.py` with five questions based on verified annual-report figures and table layouts.
- Evaluation now asserts the expected table ID, PDF source pages, chunk ID and exact supporting excerpt for each result.
- Added page-heading context to financial-table BM25 text so standalone and consolidated statements are disambiguated without changing raw excerpts or table atomicity.

### Evaluation cases and verified evidence

- Standalone total assets: `table-0001`, PDF page 131, excerpt includes `11,059.12` and `11,204.97`.
- Standalone revenue from operations: `table-0002`, PDF page 132, excerpt includes `9,730.56` and `7,760.93`.
- Consolidated revenue from operations: `table-0019`, PDF page 228, exact table excerpt verified.
- Consolidated ending cash and cash equivalents: `table-0020`, PDF pages 229-230, exact supporting excerpt verified.
- Apparao Mallavarapu promoter shares: `table-0012`, PDF pages 165-166, excerpt includes `52,31,549`.

### Tests executed and results

- Real-report retrieval evaluation: passed, 5 tests passed.
- Complete pytest suite: passed, 18 tests passed, 6 deprecation warnings in 11.31 seconds.

### Next recommended action

- Continue Milestone 3 with broader retrieval questions and ranking-quality checks. Citation validation, fallback handling and LLM provider integration remain deferred; Milestone 4 has not started.

## Milestone 3 broader retrieval evaluation

### Completed

- Expanded `tests/test_retrieval_evaluation.py` with eight additional real-report questions covering current assets, operating and investing cash flows, ending cash, receivables ageing, payables ageing, PPE net block and consolidated total assets.
- Added ranking-quality checks requiring expected financial-table evidence in the top five results.
- Added scope-specific ranking checks: standalone total current assets ranks `table-0001` first, and consolidated total assets ranks `table-0018` first.
- Verified evidence pages and excerpts for all broader cases, including multi-page tables on 161-162, 173-174 and 229-230.

### Tests executed and results

- Retrieval evaluation suite: passed, 14 tests passed.
- Complete pytest suite: passed, 27 tests passed, 6 deprecation warnings in 9.10 seconds.

### Known issues / next recommended action

- BM25 evaluation now covers 13 real annual-report questions plus scope-ranking checks, but broader benchmark generation and negative/ambiguous query evaluation remain future Milestone 3 work.
- Citation validation, mandatory fallback behavior and LLM provider integration remain deferred. Milestone 4 has not started.

## Milestone 3 negative, ambiguous and citation-readiness evaluation

### Completed

- Added unsupported-question evaluation for a lunar-mining query; retrieval returns no exact unsupported phrase or excerpt, so no false evidence match is accepted by the test.
- Added ambiguous-question evaluation for `What was revenue?`; retrieval exposes both standalone (`table-0002`, page 132) and consolidated (`table-0019`, page 228) evidence scopes rather than treating the question as uniquely resolved.
- Added citation-readiness checks confirming a selected table result carries a stable chunk ID, table ID, PDF source pages, and a non-empty raw excerpt containing the verified figure.

### Tests executed and results

- Retrieval evaluation suite: passed, 17 tests passed.
- Complete pytest suite: passed, 30 tests passed, 6 deprecation warnings in 8.44 seconds.

### Known issues / next recommended action

- Negative and ambiguous behavior is evaluated at retrieval level only. The mandatory fallback response and answer-level citation validation remain intentionally unimplemented until the Q&A service milestone.
- Milestone 4 provider integration has not started. Continue Milestone 3 only if additional retrieval benchmark coverage is needed; otherwise stop at the milestone boundary for review.

## Milestone 3 Git checkpoint

- Milestone 3 is complete for the current scope: structure-aware chunking, atomic financial-table evidence, BM25 retrieval, real-report evaluations, negative/ambiguous query checks, and citation-ready metadata are implemented and tested.
- Complete test suite verified by Codex: 30 passed, 6 deprecation warnings.
- Files reviewed for this checkpoint include `app/retrieval.py`, `tests/test_retrieval.py`, and `tests/test_retrieval_evaluation.py`.
- GitHub remote remains `https://github.com/kanojiyamahesh8/annual-report-knowledge-engine.git` on the current `master` branch.
- `.env`, `.venv`, caches, IDE files, source PDF, generated structure data and temporary `tempMile.txt` remain excluded.
- Milestone 4 provider integration has not started.
