FORMAT_DIR = src tests

release_from-develop:
	gh pr create --base main --head develop --title "Release v$(version)"
	gh pr merge --auto
	gh release create $(version) --target main --latest --generate-notes --title "$(version)"

build:
	rm -rf dist
	uv build

update-version:
	@echo "Updating version to $(version)"
	@sed -i.bak 's/^version = ".*"/version = "$(version)"/' pyproject.toml && rm pyproject.toml.bak
	@sed -i.bak 's/__version__ = ".*"/__version__ = "$(version)"/' src/wikidot/__init__.py && rm src/wikidot/__init__.py.bak
	@echo "Version updated in pyproject.toml and src/wikidot/__init__.py"

release:
	echo "Releasing version $(version)"
	make update-version version=$(version)
	make format
	make lint-fix
	git add .
	git commit -m 'release: $(version)' --allow-empty
	git push origin develop
	make release_from-develop version=$(version)

commit:
	make format
	git add .
	git commit -m '$(message)'

format:
	uv sync --extra format
	uv run ruff format $(FORMAT_DIR)

format-check:
	uv sync --extra format
	uv run ruff format --check $(FORMAT_DIR)

lint:
	uv sync --extra lint
	uv run ruff check $(FORMAT_DIR)
	uv run mypy $(FORMAT_DIR) --install-types --non-interactive

lint-fix:
	uv sync --extra lint
	uv run ruff check $(FORMAT_DIR) --fix

# テスト関連のコマンド（デフォルトはユニットテストのみ）
test:
	uv sync --extra test
	uv run pytest tests/unit/ -v

test-cov:
	uv sync --extra test
	uv run pytest tests/unit/ -v --cov=src/wikidot --cov-report=term-missing --cov-report=html --cov-fail-under=80

test-unit:
	uv sync --extra test
	uv run pytest tests/unit/ -v

test-unit-cov:
	uv sync --extra test
	uv run pytest tests/unit/ -v --cov=src/wikidot --cov-report=term-missing --cov-report=html --cov-fail-under=80

test-integration:
	uv sync --extra test
	uv run pytest tests/integration/ -v

test-integration-cov:
	uv sync --extra test
	uv run pytest tests/integration/ -v --cov=src/wikidot --cov-report=term-missing --cov-report=html --cov-fail-under=50

.PHONY: build release release_from-develop update-version format format-check commit lint lint-fix test test-cov test-unit test-unit-cov test-integration test-integration-cov
