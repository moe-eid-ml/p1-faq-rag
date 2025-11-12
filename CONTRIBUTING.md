# Contributing

## Setup
python -m venv .venv && source .venv/bin/activate
pip install -e . && pre-commit install || true

## Commands (Codex CLI)
codex validate   # Arabic-only Q/A + banned terms
codex slugs      # enforce slug__YYYY-MM-DD.txt
codex embed      # build build/index.json
codex sync       # validate → slugs → embed

## Dev
pytest -q || echo "No tests found"
python app.py

## Adding a FAQ
Create docs/faq/ar/<slug>__YYYY-MM-DD.txt with:
ID:, CAT:, TAGS:, then Q: and A:
Run codex sync and commit.

## Security
No secrets in git. Use .env (ignored).
