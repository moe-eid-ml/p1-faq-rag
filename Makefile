# ---- Dev helpers ----
K ?= 3
INCLUDE ?= wohngeld

.PHONY: run test eval lint lint-fix space-push

run:
	python app.py

test:
	PYTHONPATH=. pytest -q

eval:
	PYTHONPATH=. python cli.py eval --both -k $(K) --include $(INCLUDE)

lint:
	ruff check .

lint-fix:
	ruff check . --fix

space-push:
	@if [ -z "$$HF_TOKEN" ]; then echo "Set HF_TOKEN=<your HF write token> first"; exit 1; fi
	git -c credential.helper= push "https://HFHQ92:$$HF_TOKEN@huggingface.co/spaces/HFHQ92/wohngeld-faq-rag.git" hf-space:main --force
