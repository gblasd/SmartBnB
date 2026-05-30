setup:
	python -m venv .venv
	pip install -r requirements.txt

dashboard:
	streamlit run App.py

test:
	python -m pytest test.py
	