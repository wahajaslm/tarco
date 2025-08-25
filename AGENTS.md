# Trade Compliance API – Contributor Guide

## Project Overview
- Returns universal, deterministic JSON for import/export compliance.
- All numeric and legal facts originate from the PostgreSQL database populated via ETL of TARIC, VAT and related XLSX/ZIP sources.
- HS classification uses a retrieve → rerank → calibrate pipeline with Qdrant and optional ML models.
- Uncertain classifications must respond with `needs_clarification` data.

## Key Components
- **FastAPI** service with structured logging.
- **PostgreSQL** (with pgvector) as canonical store; **Qdrant** for vector search.
- **Ollama** local LLM for explanations and slot extraction.
- **Redis** for caching and rate limiting.
- **Docker Compose** orchestrates services; scripts/bootstrap.py builds database and vector indexes.

## Development Workflow
1. Place raw data files under `data/raw/` or use `scripts/bootstrap.py --create-sample` to seed test data.
2. Start dependencies via `docker-compose up -d postgres redis ollama qdrant`.
3. Run `python scripts/bootstrap.py` to ingest data and create embeddings.
4. Launch API with `docker-compose up api` and verify at `http://localhost:8000/healthz`.

## Code & Testing Guidelines
- Target Python 3.11+.
- Follow PEP8; use `ruff` for linting.
- Run unit tests with `pytest`; main workflow check: `pytest tests/test_workflow.py::test_cotton_hoodie_workflow -v`.
- Maintain deterministic behavior: all numbers from the database, vector search via Qdrant, no placeholder logic.
- Add tests for new features and ensure existing tests pass before committing.

## Documentation & Support
- See [README.md](README.md) for full architecture and deployment instructions.
- Operational procedures in [RUNBOOK.md](RUNBOOK.md).
- API docs served at `/docs` when the service is running.

## Contribution Steps
1. Fork and branch from `main`.
2. Implement changes and update/extend tests.
3. Run `ruff check` and `pytest` locally.
4. Commit with clear messages and open a Pull Request.

