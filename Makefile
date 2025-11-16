.RECIPEPREFIX := >

.PHONY: space-push
space-push:
> @if [ -z "$$HF_TOKEN" ]; then echo "Set HF_TOKEN=<your HF write token> first"; exit 1; fi
> git -c credential.helper= push "https://HFHQ92:$$HF_TOKEN@huggingface.co/spaces/HFHQ92/wohngeld-faq-rag.git" hf-space:main --force
