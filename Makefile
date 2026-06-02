setup:
	python -m venv .venv
	pip install -r requirements.txt

dashboard:
	streamlit run App.py

test:
	python -m pytest test.py
	
run_etl:
	cd src && python3 -m ingestion.listings_loader