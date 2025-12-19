.PHONY: help install dev server db-up db-down db-migrate db-create-migration db-reset db-test db-stats db-clear test clean lint format batch batch-llm batch-multi dashboard

# Default target
.DEFAULT_GOAL := help

# Colors for output
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[0;33m
RED := \033[0;31m
NC := \033[0m # No Color

# Project paths
PROJECT_DIR := $(shell pwd)
export PYTHONPATH := $(PROJECT_DIR):$(PYTHONPATH)

help: ## Show this help message
	@echo "$(BLUE)Monopoly Game Arena - Makefile Commands$(NC)"
	@echo ""
	@echo "$(GREEN)Usage:$(NC) make [target]"
	@echo ""
	@echo "$(YELLOW)Available targets:$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-20s$(NC) %s\n", $$1, $$2}'
	@echo ""

# ============================================================================
# Installation & Setup
# ============================================================================

install: ## Install dependencies using uv
	@echo "$(BLUE)📦 Installing dependencies...$(NC)"
	uv sync
	@echo "$(GREEN)✅ Dependencies installed$(NC)"

dev: install ## Install dev dependencies and setup pre-commit
	@echo "$(BLUE)🛠️  Setting up development environment...$(NC)"
	uv sync --all-extras
	@echo "$(GREEN)✅ Development environment ready$(NC)"

# ============================================================================
# Server
# ============================================================================

server: ## Start FastAPI server with auto-reload
	@echo "$(BLUE)🚀 Starting server...$(NC)"
	@echo "$(YELLOW)📁 PYTHONPATH: $(PYTHONPATH)$(NC)"
	uv run uvicorn server.app:app --host 0.0.0.0 --port 8000 --reload

server-prod: ## Start server in production mode (no reload)
	@echo "$(BLUE)🚀 Starting server (production)...$(NC)"
	uv run uvicorn server.app:app --host 0.0.0.0 --port 8000

# ============================================================================
# Dashboard
# ============================================================================

dashboard: ## Start analytics dashboard (http://localhost:8050)
	@echo "$(BLUE)📊 Starting Dashboard...$(NC)"
	@echo "$(YELLOW)📁 PYTHONPATH: $(PYTHONPATH)$(NC)"
	uv run python -m dashboard.app

dashboard-dev: ## Start dashboard in development mode with debug
	@echo "$(BLUE)📊 Starting Dashboard (dev mode)...$(NC)"
	uv run python dashboard/app.py

# ============================================================================
# Database
# ============================================================================

db-up: ## Start PostgreSQL database (Docker)
	@echo "$(BLUE)🐘 Starting PostgreSQL...$(NC)"
	docker-compose up -d postgres
	@echo "$(GREEN)✅ PostgreSQL started$(NC)"
	@echo "$(YELLOW)Connection: postgresql://monopoly_user:monopoly_pass@localhost:5432/monopoly_arena$(NC)"

db-down: ## Stop PostgreSQL database
	@echo "$(BLUE)🛑 Stopping PostgreSQL...$(NC)"
	docker-compose down
	@echo "$(GREEN)✅ PostgreSQL stopped$(NC)"

db-logs: ## Show PostgreSQL logs
	docker-compose logs -f postgres

db-psql: ## Connect to PostgreSQL CLI
	docker exec -it monopoly_postgres psql -U monopoly_user -d monopoly_arena

db-migrate: ## Apply database migrations (alembic upgrade head)
	@echo "$(BLUE)🔄 Applying migrations...$(NC)"
	uv run alembic upgrade head
	@echo "$(GREEN)✅ Migrations applied$(NC)"

db-create-migration: ## Create new migration (usage: make db-create-migration MSG="your message")
	@if [ -z "$(MSG)" ]; then \
		echo "$(RED)❌ Error: MSG is required$(NC)"; \
		echo "$(YELLOW)Usage: make db-create-migration MSG=\"your message\"$(NC)"; \
		exit 1; \
	fi
	@echo "$(BLUE)📝 Creating migration: $(MSG)$(NC)"
	uv run alembic revision --autogenerate -m "$(MSG)"
	@echo "$(GREEN)✅ Migration created$(NC)"

db-downgrade: ## Rollback last migration
	@echo "$(BLUE)⏪ Rolling back migration...$(NC)"
	uv run alembic downgrade -1
	@echo "$(GREEN)✅ Migration rolled back$(NC)"

db-current: ## Show current migration version
	@echo "$(BLUE)📊 Current migration version:$(NC)"
	uv run alembic current

db-history: ## Show migration history
	@echo "$(BLUE)📜 Migration history:$(NC)"
	uv run alembic history --verbose

db-init: ## Initialize database (create tables)
	@echo "$(BLUE)🔧 Initializing database...$(NC)"
	uv run python scripts/db_manager.py init
	@echo "$(GREEN)✅ Database initialized$(NC)"

db-reset: ## Reset database (DESTRUCTIVE - drops all tables!)
	@echo "$(RED)⚠️  WARNING: This will DELETE ALL DATA!$(NC)"
	@read -p "Are you sure? Type 'yes' to continue: " confirm; \
	if [ "$$confirm" = "yes" ]; then \
		uv run python scripts/db_manager.py reset; \
		echo "$(GREEN)✅ Database reset$(NC)"; \
	else \
		echo "$(YELLOW)❌ Aborted$(NC)"; \
	fi

db-test: ## Test database connection
	@echo "$(BLUE)🔍 Testing database connection...$(NC)"
	uv run python scripts/db_manager.py test

db-stats: ## Show database statistics
	@echo "$(BLUE)📊 Database statistics:$(NC)"
	uv run python scripts/db_manager.py stats

db-clear: ## Clear all data from tables (keeps structure)
	@echo "$(BLUE)🗑️  Clearing all data from tables...$(NC)"
	uv run python scripts/db_manager.py clear --force
	@echo "$(GREEN)✅ All tables cleared$(NC)"

db-backup: ## Backup database to file
	@echo "$(BLUE)💾 Backing up database...$(NC)"
	@mkdir -p backups
	docker exec monopoly_postgres pg_dump -U monopoly_user monopoly_arena > backups/backup_$(shell date +%Y%m%d_%H%M%S).sql
	@echo "$(GREEN)✅ Backup created in backups/$(NC)"

db-restore: ## Restore database from latest backup
	@LATEST=$$(ls -t backups/*.sql 2>/dev/null | head -1); \
	if [ -z "$$LATEST" ]; then \
		echo "$(RED)❌ No backups found$(NC)"; \
		exit 1; \
	fi; \
	echo "$(BLUE)📥 Restoring from: $$LATEST$(NC)"; \
	docker exec -i monopoly_postgres psql -U monopoly_user -d monopoly_arena < $$LATEST; \
	echo "$(GREEN)✅ Database restored$(NC)"

# ============================================================================
# Testing
# ============================================================================

test: ## Run all tests with pytest
	@echo "$(BLUE)🧪 Running tests...$(NC)"
	uv run pytest -v

test-db: ## Run database integration test
	@echo "$(BLUE)🧪 Testing database integration...$(NC)"
	uv run python test_database.py

test-cov: ## Run tests with coverage report
	@echo "$(BLUE)🧪 Running tests with coverage...$(NC)"
	uv run pytest --cov=. --cov-report=html --cov-report=term

# ============================================================================
# Code Quality
# ============================================================================

lint: ## Run linting (ruff check)
	@echo "$(BLUE)🔍 Running linter...$(NC)"
	uv run ruff check .

lint-fix: ## Fix linting issues automatically
	@echo "$(BLUE)🔧 Fixing linting issues...$(NC)"
	uv run ruff check --fix .

format: ## Format code with ruff
	@echo "$(BLUE)✨ Formatting code...$(NC)"
	uv run ruff format .

format-check: ## Check code formatting without making changes
	@echo "$(BLUE)🔍 Checking code formatting...$(NC)"
	uv run ruff format --check .

type-check: ## Run type checking with mypy
	@echo "$(BLUE)🔍 Running type checker...$(NC)"
	uv run mypy .

# ============================================================================
# Game Commands
# ============================================================================

play: ## Run CLI game simulation
	@echo "$(BLUE)🎲 Starting Monopoly game...$(NC)"
	uv run python play_monopoly.py

play-seed: ## Run game with specific seed (usage: make play-seed SEED=42)
	@if [ -z "$(SEED)" ]; then \
		echo "$(RED)❌ Error: SEED is required$(NC)"; \
		echo "$(YELLOW)Usage: make play-seed SEED=42$(NC)"; \
		exit 1; \
	fi
	@echo "$(BLUE)🎲 Starting game with seed $(SEED)...$(NC)"
	uv run python play_monopoly.py --seed $(SEED)

batch: ## Run batch games (usage: make batch GAMES=10 AGENT=greedy)
	@echo "$(BLUE)🎲 Running batch games...$(NC)"
	uv run python scripts/batch_games.py \
		--games $(or $(GAMES),5) \
		--players $(or $(PLAYERS),4) \
		--agent $(or $(AGENT),greedy) \
		--max-turns $(or $(TURNS),100)

batch-llm: ## Run batch LLM games (usage: make batch-llm GAMES=5 STRATEGY=balanced)
	@echo "$(BLUE)🤖 Running batch LLM games...$(NC)"
	uv run python scripts/batch_games.py \
		--games $(or $(GAMES),5) \
		--players $(or $(PLAYERS),4) \
		--agent llm \
		--llm-strategy $(or $(STRATEGY),balanced) \
		--max-turns $(or $(TURNS),100)

batch-multi: ## Run batch games with rotating LLM strategies
	@echo "$(BLUE)🔄 Running batch games with rotating strategies...$(NC)"
	uv run python scripts/batch_games.py \
		--games $(or $(GAMES),9) \
		--players $(or $(PLAYERS),4) \
		--agent llm \
		--multi-strategy \
		--max-turns $(or $(TURNS),100)

# ============================================================================
# Cleanup
# ============================================================================

clean: ## Clean up generated files
	@echo "$(BLUE)🧹 Cleaning up...$(NC)"
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name ".coverage" -delete 2>/dev/null || true
	@echo "$(GREEN)✅ Cleanup complete$(NC)"

clean-all: clean ## Clean everything including venv and database
	@echo "$(RED)⚠️  Cleaning everything (including venv and database)...$(NC)"
	rm -rf .venv
	docker-compose down -v
	@echo "$(GREEN)✅ Full cleanup complete$(NC)"

# ============================================================================
# Development Workflow
# ============================================================================

setup: install db-up db-migrate db-test ## Complete setup (install + db + migrate + test)
	@echo ""
	@echo "$(GREEN)✅ Setup complete!$(NC)"
	@echo ""
	@echo "$(YELLOW)Next steps:$(NC)"
	@echo "  1. Run server: $(GREEN)make server$(NC)"
	@echo "  2. Open browser: $(BLUE)http://localhost:8000$(NC)"
	@echo ""

start: db-up server ## Start database and server together

stop: db-down ## Stop all services

restart: stop start ## Restart all services

status: ## Show status of all services
	@echo "$(BLUE)📊 Services Status:$(NC)"
	@echo ""
	@echo "$(YELLOW)Docker:$(NC)"
	@docker-compose ps 2>/dev/null || echo "  Not running"
	@echo ""
	@echo "$(YELLOW)Database Migration:$(NC)"
	@uv run alembic current 2>/dev/null || echo "  Not initialized"
	@echo ""

# ============================================================================
# Documentation
# ============================================================================

docs-serve: ## Serve documentation (if using mkdocs)
	@echo "$(BLUE)📚 Serving documentation...$(NC)"
	@echo "$(YELLOW)Documentation available in markdown files:$(NC)"
	@echo "  - README.md"
	@echo "  - DATABASE_SETUP.md"
	@echo "  - QUICK_START.md"
	@echo "  - RUN_INSTRUCTIONS.md"

# ============================================================================
# Utility Commands
# ============================================================================

shell: ## Open Python shell with project context
	@echo "$(BLUE)🐍 Opening Python shell...$(NC)"
	uv run python

env: ## Show environment variables
	@echo "$(BLUE)🔧 Environment:$(NC)"
	@echo "PYTHONPATH: $(PYTHONPATH)"
	@echo "Project Dir: $(PROJECT_DIR)"

check: lint format-check type-check test ## Run all checks (lint, format, type, test)
	@echo ""
	@echo "$(GREEN)✅ All checks passed!$(NC)"
	@echo ""

check-imports: ## Quick check if Python imports work
	@echo "$(BLUE)🔍 Checking imports...$(NC)"
	@uv run python -c "from server.database import Game, Player, GameEvent; print('✅ Database models OK')"
	@uv run python -c "from server.app import app; print('✅ FastAPI app OK')"
	@echo "$(GREEN)✅ All imports working!$(NC)"

# ============================================================================
# Docker Management
# ============================================================================

docker-build: ## Build Docker images
	@echo "$(BLUE)🐳 Building Docker images...$(NC)"
	docker-compose build

docker-logs: ## Show all Docker logs
	docker-compose logs -f

docker-clean: ## Clean Docker resources
	@echo "$(BLUE)🧹 Cleaning Docker resources...$(NC)"
	docker-compose down -v --remove-orphans
	@echo "$(GREEN)✅ Docker cleanup complete$(NC)"

# ============================================================================
# Quick Commands (Aliases)
# ============================================================================

s: server ## Alias for 'server'
r: server ## Alias for 'server' (run)
t: test ## Alias for 'test'
c: clean ## Alias for 'clean'
l: lint ## Alias for 'lint'
f: format ## Alias for 'format'
