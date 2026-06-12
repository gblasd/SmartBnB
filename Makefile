setup:
	python -m venv .venv
	pip install -r requirements.txt

dashboard:
	streamlit run App.py

test:
	python -m pytest test.py
	
listings_loader:
	cd src && python3 -m ingestion.listings_loader

calendar_loader:
	cd src && python3 -m ingestion.calendar_loader

reviews_loader:
	cd src && python3 -m ingestion.reviews_loader

listings_indexing:
	cd src && python3 -m ingestion.listings_indexing
