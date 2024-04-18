release_from-develop:
	gh pr create --base main --head develop --title "Release v$(version)"
	gh pr merge --auto
	gh release create $(version) --target main --latest --generate-notes --title "$(version)"

make post-release:
	rm -rf dist

build:
	rm -rf dist
	pip install -e .[dev]
	python -m build

release:
	echo "Releasing version $(version)"
	git add .
	git commit -m 'release: $(version)' --allow-empty
	git push origin develop
	make release_from-develop version=$(version)

PHONY: build release release_from-develop post-release