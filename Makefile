build:
	python -m build

release:
	python -m twine upload dist/*

PHONY: build release