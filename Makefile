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


.PHONY: ask
ask:
	@if [ -z "$(Q)" ]; then echo 'Usage: make ask Q="Ihre Frage hier" [K=3 INCLUDE=wohngeld MODE=TF-IDF]'; exit 1; fi
	python ask.py -m $${MODE:-TF-IDF} -k $${K:-3} -i $${INCLUDE:-wohngeld} "$${Q}"


.PHONY: eval-hybrid
eval-hybrid:
	PYTHONPATH=. python eval_hybrid.py
