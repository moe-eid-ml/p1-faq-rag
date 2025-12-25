# ---- Dev helpers ----
K ?= 3
INCLUDE ?= wohngeld

.PHONY: run test smoke eval lint lint-fix ci prepush space-push

run:
	python app.py

test:
	PYTHONPATH=. pytest -q

smoke:
	PYTHONPATH=. pytest -q -k "abstain_on_nonsense_query or source_pointer_present_on_normal_answer"

eval:
	PYTHONPATH=. python cli.py eval --both -k $(K) --include $(INCLUDE)

lint:
	ruff check .

lint-fix:
	ruff check . --fix

ci: lint test

prepush: ci
	@if [ -n "$$(git status --porcelain)" ]; then \
		echo "Working tree not clean. Commit or restore before pushing."; \
		git status -sb; \
		exit 1; \
	fi
	@if [ "$$(git rev-parse --abbrev-ref HEAD)" != "main" ]; then \
		echo "Not on main. Switch to main before pushing."; \
		exit 1; \
	fi
	@echo "Prepush OK ✅"

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
