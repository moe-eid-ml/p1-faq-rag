.RECIPEPREFIX := >

.PHONY: space-push
space-push:
> @if [ -z "$$HF_TOKEN" ]; then echo "Set HF_TOKEN=<your HF write token> first"; exit 1; fi
> git -c credential.helper= push "https://HFHQ92:$$HF_TOKEN@huggingface.co/spaces/HFHQ92/wohngeld-faq-rag.git" hf-space:main --force

# ---- Dev helpers ----
K ?= 3
INCLUDE ?= wohngeld

.PHONY: run
run:
> python app.py

.PHONY: test
test:
> PYTHONPATH=. pytest -q

.PHONY: eval
eval:
> PYTHONPATH=. python cli.py eval --both -k $(K) --include $(INCLUDE)

.PHONY: lint
lint:
> ruff check .

.PHONY: lint-fix
lint-fix:
> ruff check . --fix
