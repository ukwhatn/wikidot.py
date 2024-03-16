build:
	python -m build

release:
	python -m twine upload dist/*
	rm -rf dist

PHONY: build release