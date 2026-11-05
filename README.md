# Elyra AI: Validated & Traceable Building Requirements Pipeline

A production-grade, defensive Data Engineering MVP designed for **Elyra AI**.

This project solves the fundamental architectural bottleneck in industrialized, pre-fabricated housing workflows: **converting messy, unstructured customer dialogues into strongly-typed, grounded, and verified building requirements datasets ready for downstream CAD/BIM engines.**

---

## 💡 The Core Problem Solved

In modular and pre-fabricated residential construction, customer discovery happens through natural language dialogues filled with colloquial expressions, ambiguities, missing dimensions, and mid-conversation revisions. 

Downstream architectural systems (such as parametric CAD, floor plan generators, and IFC/BIM databases) cannot work with ambiguous prose or unchecked JSON outputs from standard LLMs. They require:
1. **Mathematical certainty**: Dimensions and room quantities must obey strict architectural boundaries.
2. **Defensive conflict resolution**: Contradictions (e.g., a kitchen specified as both open-plan and enclosed) must be detected before drafting begins.
3. **Deterministic provenance**: Every dimension (e.g., master bedroom >= 18 m²) must be mathematically grounded to exact character offsets in the raw transcript to eliminate hallucinations.
4. **Normalized relational persistence**: Data must be structured into relational SQL tables for downstream queryability, accompanied by full audit logs.

This MVP demonstrates how a defensive Data Engineering pipeline transforms noisy customer text into an auditable, high-integrity data asset.

---

## 🏛️ System Architecture

```
[Raw Customer Transcript]
          │
          ▼
 [Gemini 3.8 Flash] ──── (Structured JSON Schema Enforcement)
          │
          ▼
[Canonical Extraction]
          │
          ▼
[Grounding Locator] ─── (Deterministic Character Offset Alignment & Hallucination Check)
          │
          ▼
[3-Tier Validation] ─── (Tier 1: Schema Invariants | Tier 2: Domain Bounds | Tier 3: Conflicts)
          │
          ▼
[Relational Storage] ── (PostgreSQL 16 / SQLite Fallback + Full Audit Payloads)
          │
          ▼
[Streamlit Dashboard] ─ (Live Extraction | JSON & SQL Inspector | Golden Dataset Benchmark)
```

---

## 🛡️ Adherence to Senior Data Engineering Standards

This codebase demonstrates five core engineering principles:

### 1. Harness Engineering
- **Decoupled Client Protocol**: Implements `LLMClientProtocol` with an adapter pattern. Unit tests execute deterministically against `MockLLMClient` with zero API latency and zero cost.
- **Pure Function Validators**: Validation rules are written as pure functions isolated from model extraction, allowing automated CI regression testing.

### 2. LLM Reliability
- **Protocol-Level Schema Enforcement**: Calls `gemini-3.8-flash` via the official `google-genai` SDK using `response_mime_type="application/json"` and strict Pydantic JSON schemas, eliminating parsing failures.
- **Resilient Execution**: Employs `tenacity` exponential backoff retries with jitter for rate limits (HTTP 429) and transient network disconnects.
- **Defensive Grounding**: Verbatim quotes returned by the LLM are aligned via deterministic substring search. Quotes absent from the source text are automatically flagged as `is_hallucinated = True` and penalized.

### 3. Evaluation Engineering
- **Curated Golden Dataset**: 8 realistic test cases spanning standard pre-fab houses, ambiguous requests, semantic contradictions, and conversational revisions.
- **Quantitative Metrics**: Mathematical evaluation of **Space Extraction F1-Score**, **Constraint Accuracy**, and **Grounding IoU**.
- **Automated Reporting**: Built-in benchmark harness (`src/evaluation/benchmark.py`) capable of generating automated markdown reports.

### 4. Data Quality Engineering
- **Pydantic v2 Invariants**: Enforces positive quantities, positive areas, and standardized unit enums (`m2`, `m`, `cm`).
- **Architectural Sanity Bounds**: Real-world German/European residential limits (e.g., bedrooms must be between 6 m² and 40 m²; values below 2.5 m² or above 100 m² trigger errors).
- **Semantic Conflict Detector**: Flags impossible spatial relationships (e.g., `open_plan_with` and `separated_from` on the same room) and contradictory numerical constraints.

### 5. Production Observability & Auditability
- **Real-Time Slack Incident Telemetry**: Integrated with [Slack AI Sentinel](https://github.com/shin7965977/slack-ai-sentinel) (`src/monitoring/sentinel.py`) to automatically dispatch stack traces, error fingerprints, and contextual metadata to your Slack channel on pipeline crashes or API outages.
- **Structured Logging**: `loguru` outputs contextual logs tracking latency, character counts, and validation results.
- **Full Relational Audit Trail**: The `projects` table stores the raw unparsed customer text (`raw_transcript`) alongside the raw model response (`raw_payload`) to guarantee full reproducibility.
- **Human-in-the-Loop Review**: Projects flagged with warnings or errors require human approval before being marked as `APPROVED` for downstream BIM/CAD systems.

---

## 🛠️ Tooling & Tech Stack

| Category | Technology | Purpose |
| :--- | :--- | :--- |
| **Language & Runtime** | Python 3.11 | Core execution environment |
| **LLM & Inference** | `google-genai`, Gemini 3.8 Flash | Structured requirements extraction |
| **Resilience** | `tenacity` | Exponential backoff retry engine |
| **Data Modeling** | `pydantic >= 2.6` | Canonical schema and type validation |
| **Persistence** | `SQLAlchemy 2.0`, `psycopg2-binary` | Relational ORM mapping |
| **Database** | PostgreSQL 16 (Docker) / SQLite | Production database with zero-setup fallback |
| **Interactive UI** | `streamlit` | Review dashboard, live extraction, and benchmark |
| **Testing** | `pytest` | Unit, integration, and benchmark test suite |
| **Logging** | `loguru` | Structured pipeline observability |

---

## 🚀 Quickstart Guide

### 1. Prerequisites
- Python 3.11+
- Docker & Docker Compose (optional, for PostgreSQL)

### 2. Setup Environment
```bash
# Clone and enter workspace
git clone <repo-url>
cd Elyra-AI_data-engineer

# Create virtual environment
python -m venv .venv
# On Windows:
.\.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. (Optional) Start PostgreSQL
```bash
docker-compose up -d
```
*Note: If Docker is not running, the application will automatically fall back to local SQLite (`elyra.db`).*

### 4. Run Automated Test Suite
```bash
pytest tests/ -v
```
All unit tests, integration tests, and benchmark verifications run completely offline using mock fixtures.

### 5. Launch Interactive Streamlit App
```bash
streamlit run src/ui/app.py
```
Open `http://localhost:8501` in your browser:
- Enter your Gemini API key in the sidebar (or check "Use Mock LLM" for offline exploration).
- In **Tab 1**, test live extraction, inspect Canonical JSON, and review normalized SQL database tables.
- In **Tab 2**, inspect Ground Truth diffs and run the full 8-case quantitative evaluation benchmark.

### 6. Run via CLI
```bash
python -m src.pipeline --input "I want a single-family house with 3 bedrooms and an open kitchen."
```

---

## 🔮 Future Work & Production Roadmap

This MVP was intentionally scoped to deliver a high-integrity, zero-dependency Core Data Pipeline (Phase 1 & Phase 2). The following extensions represent the natural roadmap for enterprise integration at Elyra AI:

1. **Langfuse LLMOps & Production Tracing**:
   - Integrate [Langfuse](https://langfuse.com/) SDK to provide deep distributed tracing across every pipeline run.
   - Monitor live token consumption, per-request latency percentiles ($p_{50}, p_{95}$), estimated cost per extraction, and prompt drift over time.
   - Stream model confidence scores and automated evaluation metrics directly into Langfuse dashboards.

2. **Unstructured PDF & Architectural Spec Ingestion**:
   - Add a document processing worker (e.g., via `pdfplumber` or Docling) to ingest raw PDF floor plan specifications, client questionnaires, and RFP documents.

3. **Building Code Compliance RAG (German DIN / EnEV Standards)**:
   - Connect PostgreSQL with `pgvector` to query local German building regulations (e.g., minimum ceiling heights, fire separation laws, energy efficiency insulation standards) to validate extracted constraints against official codes.

4. **Downstream IFC / BIM File Generation**:
   - Convert normalized relational spaces and constraints directly into Industry Foundation Classes (IFC) schema or parametric CAD inputs for automated drafting.


