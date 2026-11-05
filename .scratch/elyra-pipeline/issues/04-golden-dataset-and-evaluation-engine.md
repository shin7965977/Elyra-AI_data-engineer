# 04: Golden Dataset (8 Cases) & Quantitative Evaluation Engine

**What to build:**
Curate an 8-case Golden Dataset spanning 4 realistic pre-fab residential housing scenarios: 2 standard happy paths, 2 ambiguous/missing details, 2 contradictory/out-of-bounds, and 2 multi-turn/revision dialogs. Build a quantitative evaluation engine that benchmarks extraction output against Ground Truth, computing Space Precision/Recall/F1, Constraint Exact Match, and Provenance Grounding IoU. Provide an executable benchmark script generating a clean Markdown summary report.

**Blocked by:** 01: Core Domain Schemas, LLM Adapter & Mock Harness, 02: Deterministic Traceability & 3-Tier Validation Harness

**Status:** ready-for-agent

- [ ] 8 structured JSON files in `data/golden_dataset/` with raw transcripts and ground truth canonical objects.
- [ ] Evaluation runner in `src/evaluation/benchmark.py` calculating Space F1, Constraint Accuracy, and Grounding Match.
- [ ] Pytest test suite in `tests/test_benchmark.py` ensuring metrics are computed accurately.
- [ ] Formatted Markdown benchmark report generation summarizing field-level accuracy.
