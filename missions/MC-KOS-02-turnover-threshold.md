# MC-KOS-02: Turnover Threshold

## Objective
TODO: Define the turnover threshold criteria and related rules.

## Inputs
- TODO: Source documents or datasets

## Steps
1. TODO: Specify the exact workflow.

## Acceptance Criteria
- TODO: Define the expected output and checks.

# MC-KOS-02: Turnover Threshold Checker (Mindestumsatz / Jahresumsatz)

## Goal
Add a deterministic checker that finds explicit turnover threshold requirements (e.g., **Mindestumsatz**, **Jahresumsatz**) and compares them against a minimal company profile. The checker must only output **RED** when the KO condition is *provably* triggered, otherwise default to **YELLOW/ABSTAIN/neutral**.

## Non-goals (explicitly out of scope)
- No PDF parsing/OCR work in this PR (assume page text already exists as a string).
- No portal integrations.
- No new dependencies.
- No UI / Gradio changes.
- No refactors outside the files listed below.

## Inputs
### Page context
- `page_text: Optional[str]`
- `doc_id: str` (filename)
- `page_number: int` (1-indexed)

### Company profile (v0)
A dict with only:
- `annual_turnover_eur: int | float` (single-year turnover, EUR)

If the company profile is missing or lacks `annual_turnover_eur`, the checker must not output Green; it should output **YELLOW** when a requirement exists.

## Files to touch
- `kosniper/checkers/turnover_threshold.py` (NEW)
- `kosniper/checkers/__init__.py` (wire export/registry)
- `kosniper/pipeline.py` (wire into checker runner only if needed; do not change existing aggregation precedence)
- `tests/test_kosniper_turnover_threshold_checker.py` (NEW)
- `data/kosniper/goldset_v0/labels/v0.jsonl` (OPTIONAL: add 1 adversarial label line if the schema supports it without breaking existing tests)

## Behavioral contract
### 1) When to emit findings
- If `page_text` is `None` or empty/whitespace after normalization:
  - Emit **exactly one** finding with `overall = "abstain"` and reason code `no_text`.
- If `page_text` is present but **no turnover requirement is detected**:
  - Emit **zero** findings (neutral).

### 2) Detecting a turnover requirement
A turnover requirement is only considered “present” if:
- a turnover keyword is present near the value (within a small window), e.g. within ~120 chars:
  - `mindestumsatz`, `jahresumsatz`, `mindestjahresumsatz`, `umsatz`
- and a currency marker is present near the numeric value:
  - `€`, `eur`, `euro`

Important: avoid false matches against unrelated monetary figures (e.g., contract value). If the number is not near a turnover keyword, treat as **no requirement**.

### 3) Parsing rules (deterministic + explainable)
Implement a small parser that can extract **one** unambiguous EUR threshold value:
- German thousands separators: `1.000.000` → `1000000`
- German decimals: `1,5` → `1.5`
- Multipliers:
  - `Mio.` / `Million(en)` → × 1,000,000
  - `Tsd.` / `T` (only when clearly meaning thousands in context) → × 1,000
- Currency required. If missing: **YELLOW** with reason `missing_currency`.

If there are **0** valid values or **>1** valid values on the page: **YELLOW** with reason `ambiguous_threshold_count`.

### 4) Ambiguity triggers (force YELLOW)
If any of the following patterns exist in the neighborhood of the detected threshold, treat as ambiguous:
- ranges: `zwischen X und Y`, `von X bis Y`
- averages / multi-year: `durchschnitt`, `letzten 3 geschäftsjahre`, `drei geschäftsjahre`, `im mittel`
- scope qualifiers: `gesamtumsatz` vs `umsatz im relevanten geschäftsbereich`, `je los`, `pro los`, `für los`, `in summe`
- explicit multiple criteria (e.g., two different turnover lines)

Emit **one** YELLOW finding with reason `ambiguous_requirement`.

### 5) Comparison logic
Given a single unambiguous threshold `threshold_eur`:
- If company profile missing or missing `annual_turnover_eur`:
  - Emit **YELLOW** with reason `missing_company_turnover`.
- Else compare:
  - If `annual_turnover_eur < threshold_eur`: emit **RED** with reason `below_threshold`.
  - If `annual_turnover_eur >= threshold_eur`: emit **zero** findings (neutral).

### 6) Evidence requirements
Any emitted finding (RED/YELLOW/ABSTAIN) must include evidence:
- `doc_id`
- `page_number`
- `snippet` containing the turnover keyword and the value (or for `no_text`, a short snippet like `"(no text)"`).

Do NOT emit `start_offset/end_offset` unless they are computed against the exact original (non-normalized) text. For v0, leave offsets as `None`.

## Acceptance criteria
1) Clear requirement + company below ⇒ **one RED finding** with evidence snippet containing the extracted value.
2) Clear requirement + company meets ⇒ **zero findings**.
3) Requirement exists but ambiguous (multi-year/average/range/scope/multiple thresholds) ⇒ **one YELLOW finding** with a reason code.
4) Requirement exists but company profile missing/field missing ⇒ **one YELLOW finding** with reason `missing_company_turnover`.
5) Empty/None/whitespace text ⇒ **one ABSTAIN finding** with reason `no_text`.
6) Adversarial test: hyphenation/newline split (e.g., `Mindest-\numsatz`) still triggers detection.
7) `DISABLE_SEMANTIC=1 pytest -q` passes.

## Tests (minimum set)
Add unit tests covering:
- `"Der Mindestumsatz muss mindestens 500.000 EUR betragen."` with company 400k ⇒ RED
- same with company 600k ⇒ zero findings
- `"Durchschnittlicher Jahresumsatz der letzten 3 Jahre: mind. 500.000 EUR"` ⇒ YELLOW ambiguous_requirement
- multi-threshold page (gesamtumsatz + relevanter bereich) ⇒ YELLOW ambiguous_threshold_count or ambiguous_requirement
- `"Mindestumsatz: 500.000"` (no currency) ⇒ YELLOW missing_currency
- `"Mindest-\numsatz: 1,5 Mio. EUR"` parsing ⇒ threshold 1,500,000; compare correctly
- empty string / None ⇒ ABSTAIN no_text

## Commands
- `DISABLE_SEMANTIC=1 pytest -q`

## PR hygiene
- Anything useful but not required by the acceptance criteria goes to `docs/parking-lot.md` and does not go in the diff.
- Keep parsing deterministic and local; prefer YELLOW over clever guesses.

## Walkthrough (fill in PR)
- pipeline/data flow change:
- new invariant/test:
- new failure mode covered: