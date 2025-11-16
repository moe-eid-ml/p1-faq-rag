PY := .venv/bin/python
PT := .venv/bin/pytest

.PHONY: run test eval eval-h1

run:
	$(PY) app.py

test:
	PYTHONPATH=. $(PT) -q

eval:
	$(PY) cli.py eval --both -k 3 --file data/wohngeld_eval.jsonl --include wohngeld

eval-h1:
	$(PY) cli.py eval --mode hybrid -k 1 --file data/wohngeld_eval.jsonl --include wohngeld

.PHONY: ingest eval3

ingest:
	@PDF=$$(ls -t ~/Downloads/*[Ww]ohngeld*.pdf 2>/dev/null | head -n 1); \
	if [ -z "$$PDF" ]; then echo "No Wohngeld PDF in ~/Downloads"; exit 1; fi; \
	echo "Using: $$PDF"; \
	$(PY) scripts/ingest_pdf.py "$$PDF" docs/wohngeld/wohngeld_official.txt de

eval3:
	$(PY) cli.py eval --both -k 3 --file data/wohngeld_eval.jsonl --include wohngeld

.PHONY: eval-h3
eval-h3:
	$(PY) cli.py eval --mode hybrid -k 3 --file data/wohngeld_eval.jsonl --include wohngeld

.PHONY: space-push
space-push:
        @if [ -z "$$HF_TOKEN" ]; then echo "Set HF_TOKEN=<your HF write token> first"; exit 1; fi
        git -c credential.helper= push "https://HFHQ92:$$HF_TOKEN@huggingface.co/spaces/HFHQ92/wohngeld-faq-rag.git" hf-space:main --force
