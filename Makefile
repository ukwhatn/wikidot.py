FORMAT_DIR = "wikidot"

release_from-develop:
	gh pr create --base main --head develop --title "Release v$(version)"
	gh pr merge --auto
	gh release create $(version) --target main --latest --generate-notes --title "$(version)"

build:
	rm -rf dist
	pip install -e .[build]
	python -m build

release:
	echo "Releasing version $(version)"
	git add .
	git commit -m 'release: $(version)' --allow-empty
	git push origin develop
	make release_from-develop version=$(version)

format:
	pip install -e .[format]
	python -m isort $(FORMAT_DIR)
	python -m black $(FORMAT_DIR)

commit:
	make format
	git add .
	git commit -m '$(message)'

lint:
	pip install -e .[lint]
	python -m flake8 $(FORMAT_DIR)
	python -m mypy $(FORMAT_DIR) --install-types --non-interactive

test:
	pip install -e .[test]

PHONY: build release release_from-develop format commit test