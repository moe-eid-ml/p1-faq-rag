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
