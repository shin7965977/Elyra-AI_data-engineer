# 03: Dual-Mode Relational Persistence & CLI ETL Pipeline

**What to build:**
Implement the SQLAlchemy 2.0 ORM relational layer modeling `projects`, `spaces`, `constraints`, and `validation_logs`, with complete audit trail columns (`raw_transcript` and `raw_payload`). Support PostgreSQL 16 via `docker-compose.yml` and automatic fallback to SQLite when PostgreSQL is unreachable. Implement the end-to-end batch ETL runner in `src/pipeline.py` callable via CLI (`python -m src.pipeline --input <file>`), uniting extraction, validation, grounding, and persistence.

**Blocked by:** 02: Deterministic Traceability & 3-Tier Validation Harness

**Status:** ready-for-agent

- [ ] SQLAlchemy 2.0 ORM models for `ProjectRecord`, `SpaceRecord`, `ConstraintRecord`, `ValidationLogRecord`.
- [ ] Database session manager supporting PostgreSQL with zero-config SQLite fallback.
- [ ] `docker-compose.yml` defining an isolated PostgreSQL 16 service.
- [ ] End-to-end `run_pipeline(text, client, db_session)` pipeline orchestrator.
- [ ] CLI command-line entrypoint with verbose logging and output reporting.
- [ ] Integration tests in `tests/test_pipeline.py` verifying full ingest-to-database flow.
