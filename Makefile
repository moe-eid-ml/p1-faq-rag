VENV=.venv

init:
	/opt/homebrew/bin/python3.12 -m venv $(VENV) || true
	$(VENV)/bin/pip install -r requirements.txt

convert: init
	. $(VENV)/bin/activate; python convert_pdf.py

run: init convert
	. $(VENV)/bin/activate; python app.py

run-share: init convert
	. $(VENV)/bin/activate; python -c "import app; app.demo.launch(share=True)"
