setup.py:
	poetry2setup > setup.py

requirements:
	poetry export > requirements.txt
	poetry export --dev > requirements-dev.txt

format:
	isort . && black .


.PHONY: setup.py requirements format
