build:
	pip install -e .[dev]
	python -m build

release:
	make build
	python -m twine upload dist/*
	rm -rf dist

PHONY: build release