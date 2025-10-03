.PHONY: help install install-dev test lint format clean build docker-build docker-run

help:  ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install:  ## Install package
	pip install -e .

install-dev:  ## Install package with dev dependencies
	pip install -e ".[dev,test]"

test:  ## Run tests
	pytest --cov=regexvault --cov-report=term-missing --cov-report=html

test-verbose:  ## Run tests with verbose output
	pytest -v --cov=regexvault --cov-report=term-missing

lint:  ## Run linters
	ruff check src/ tests/
	black --check src/ tests/
	mypy src/

format:  ## Format code
	black src/ tests/
	ruff check --fix src/ tests/

validate-patterns:  ## Validate pattern files
	@python -c "from regexvault import load_registry; load_registry(validate_examples=True); print('✓ All patterns valid')"

clean:  ## Clean build artifacts
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf .pytest_cache
	rm -rf .coverage
	rm -rf htmlcov/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

build:  ## Build package
	python -m build

docker-build:  ## Build Docker image
	docker build -t regex-vault:latest -f docker/Dockerfile .

docker-run:  ## Run Docker container
	docker run -p 8080:8080 -p 9090:9090 regex-vault:latest

docker-compose-up:  ## Start with docker-compose
	docker-compose -f docker/docker-compose.yml up -d

docker-compose-down:  ## Stop docker-compose
	docker-compose -f docker/docker-compose.yml down

serve:  ## Start development server
	regex-vault serve --config config.yml --reload

serve-prod:  ## Start production server
	regex-vault serve --config config.yml
