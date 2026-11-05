# Specification: Elyra AI Validated & Traceable Data Pipeline

## Problem Statement
In industrialized architecture and pre-fabricated housing workflows, early-stage client communications consist of unstructured natural language transcripts filled with colloquial phrasing, ambiguities, missing dimensions, mid-conversation corrections, and contradictory requirements. Downstream architectural CAD and BIM engines strictly require deterministic, strongly-typed, and validated structural requirements (project taxonomy, spatial topology, quantitative constraints). Directly querying an LLM to generate unstructured or unchecked JSON results in schema drift, ungrounded hallucinations, physically impossible room dimensions, and unflagged layout contradictions.

## Solution
Build a defensive, production-grade **Validated & Traceable Data Pipeline** and **Interactive Review Application**. The system ingests natural language customer requirements, uses Gemini 3.8 Flash to extract structured building requirements into a strongly-typed Pydantic Canonical Schema, and performs deterministic character-offset grounding back to original transcript coordinates. It executes a 3-tier validation harness (Schema validation, Architectural Domain sanity checks, and Semantic Contradiction detection) before persisting normalized records into a dual-mode SQL persistence layer (PostgreSQL 16 with automatic SQLite fallback) along with complete raw audit trails. An interactive Streamlit dashboard enables real-time extraction, side-by-side JSON/SQL inspection, human-in-the-loop review/approval, and benchmark comparison against an 8-case Golden Dataset with quantitative accuracy metrics.

## User Stories
1. As an Elyra Hiring Manager, I want to provide my Gemini API Key in the UI sidebar, so that I can independently test the pipeline with my own credentials.
2. As a Sales Representative, I want to paste raw customer conversation transcripts into the interface, so that I do not need to manually parse building requirements.
3. As a Data Engineer, I want the LLM to output data strictly adhering to a Pydantic Canonical Schema, so that data types, units, and nested relationships are guaranteed at runtime.
4. As a System Auditor, I want each extracted constraint to contain exact character start and end indices pointing to the raw text, so that I can mathematically prove the information was not hallucinated.
5. As a Data Quality Engineer, I want the system to flag negative, zero, or architecturally absurd room dimensions (e.g., bedrooms < 3m² or > 300m²), so that invalid geometry cannot reach the CAD engine.
6. As a BIM Engineer, I want the system to detect semantic contradictions (such as a kitchen marked as both open-plan and fully enclosed), so that conflicting spatial layouts are caught before drafting.
7. As a Downstream Database Consumer, I want extracted projects, spaces, and constraints normalized into clean SQL relational tables, so that downstream systems can query them using standard SQL.
8. As a Compliance Officer, I want the database to store the raw transcript and raw LLM JSON payload alongside the normalized records, so that historical extractions are 100% reproducible and auditable.
9. As a Human Reviewer, I want to see a live validation badge (PASSED / WARNING / FAILED) and warning messages in the UI, so that I know immediately if a submission requires human intervention.
10. As a Technical Reviewer, I want to view the structured Canonical JSON and the resulting SQL database records side-by-side in the UI, so that I can verify the end-to-end data transformation pipeline.
11. As a Reviewer, I want to click an "Approve" button or edit flagged values in the UI, so that low-confidence data can be corrected before downstream consumption.
12. As an MLOps Engineer, I want an automated benchmark harness running against an 8-case Golden Dataset, so that model performance can be measured systematically.
13. As a Benchmark Evaluator, I want to view a side-by-side diff between Ground Truth and LLM Extractions in the UI, so that I can visibly inspect extraction errors and deviations.
14. As an Engineer running in CI/CD, I want a Mock LLM Adapter, so that unit and integration tests run deterministically in milliseconds without consuming live API tokens.
15. As a DevOps Engineer, I want a single docker-compose.yml to spin up PostgreSQL, with an automatic SQLite fallback, so that running the application requires zero database setup friction.

## Implementation Decisions
- **LLM Client Protocol & Adapter**: Abstract protocol `LLMClientProtocol` implemented by `GoogleGenAIClient` (Gemini 3.8 Flash with structured JSON output schema) and `MockLLMClient` for deterministic offline testing.
- **Canonical Schema Hierarchy**:
  - `ProjectMetadata`: building type, estimated stories/floors, total floor area target.
  - `SpaceRequirement`: room type (`bedroom`, `bathroom`, `kitchen`, etc.), quantity, topological relationship (`open_plan_with`, `adjacent_to`).
  - `Constraint`: target space, attribute (`area`, `length`, `width`), operator (`>=`, `<=`, `==`), value, and standardized unit (`m2`, `m`, `cm`).
  - `FieldProvenance`: verbatim quote, exact character offset start (`char_start`), and end (`char_end`).
- **Deterministic Grounding Verification**: Standalone pure function locator verifying quote existence inside the transcript. If the quote is missing, it is tagged as `HALLUCINATED_QUOTE`.
- **Three-Tier Validation Harness**:
  1. *Schema Invariants*: Pydantic v2 strict models, positive numbers, enum constraints.
  2. *Domain Limits*: Sanity range checks on residential rooms.
  3. *Conflict Detection*: Cross-space contradiction detection (e.g., mutually exclusive open-plan vs enclosed tags).
- **Relational Storage & Audit Trail**:
  - Normalized tables: `projects` -> `spaces` -> `constraints`, plus `validation_logs`.
  - Audit trail: `raw_transcript` (TEXT) and `raw_payload` (JSONB/JSON) stored directly in `projects`.
- **Dual-Mode Persistence Layer**: SQLAlchemy 2.0 ORM connecting to PostgreSQL 16 by default or falling back to local `sqlite:///elyra.db`.
- **Streamlit Dual-Tab Architecture**:
  - Sidebar: API key input, DB status, preloaded samples.
  - Tab 1: Text input -> Extraction -> Validation Status -> JSON View + SQL Relational View -> Human Approval.
  - Tab 2: 8 Golden Dataset test cases, Ground Truth vs LLM side-by-side comparison, quantitative evaluation metrics (Space Precision/Recall, Constraint Match, Grounding IoU).

## Testing Decisions
- Seam 1: Pipeline Seam (`run_pipeline(text, client, db_session) -> PipelineResult`).
- Seam 2: Grounding & Validation Seam (`validate_requirements(extracted, raw_text) -> ValidationReport`).
- Seam 3: Benchmark Evaluation Seam (`evaluate_dataset(golden_cases, client) -> BenchmarkMetrics`).
- 100% of automated tests execute offline using `MockLLMClient` fixtures.

## Out of Scope
- PDF / OCR processing (slated for Future Work).
- Architectural code compliance RAG / pgvector retrieval.
- CAD / BIM geometry generation (IFC exports).
- Authentication / Multi-tenant RBAC.
