.PHONY: init

init:
	pip install -r requirements.txt 
	pre-commit install && pre-commit autoupdate