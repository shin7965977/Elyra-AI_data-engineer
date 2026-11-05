# 03: Dual-Mode Relational Persistence & CLI ETL Pipeline

**What to build:**
Implement the SQLAlchemy 2.0 ORM relational layer modeling `projects`, `spaces`, `constraints`, and `validation_logs`, with complete audit trail columns (`raw_transcript` and `raw_payload`). Support PostgreSQL 16 via `docker-compose.yml` and automatic fallback to SQLite when PostgreSQL is unreachable. Implement the end-to-end batch ETL runner in `src/pipeline.py` callable via CLI (`python -m src.pipeline --input <file>`), uniting extraction, validation, grounding, and persistence.

**Blocked by:** 02: Deterministic Traceability & 3-Tier Validation Harness

**Status:** closed

- [x] SQLAlchemy 2.0 ORM models for `ProjectRecord`, `SpaceRecord`, `ConstraintRecord`, `ValidationLogRecord`.
- [x] Database session manager supporting PostgreSQL with zero-config SQLite fallback.
- [x] `docker-compose.yml` defining an isolated PostgreSQL 16 service.
- [x] End-to-end `run_pipeline(text, client, db_session)` pipeline orchestrator.
- [x] CLI command-line entrypoint with verbose logging and output reporting.
- [x] Integration tests in `tests/test_pipeline.py` verifying full ingest-to-database flow.
