# 02: Deterministic Traceability & 3-Tier Validation Harness

**What to build:**
Implement deterministic character offset computation (`char_start`, `char_end`) by matching verbatim LLM extraction quotes against the raw input transcript, tagging missing quotes as `HALLUCINATED_QUOTE`. Build the 3-tier validation harness: Tier 1 (Schema & Type invariants), Tier 2 (Architectural Domain Limits such as residential room area sanity ranges), and Tier 3 (Semantic Conflict Detection such as mutual exclusivity between open-plan and enclosed spaces). The validator must return a structured `ValidationReport` with severity levels (`PASSED`, `WARNING`, `FAILED`).

**Blocked by:** 01: Core Domain Schemas, LLM Adapter & Mock Harness

**Status:** closed

- [x] Deterministic quote locator with character offset indexing and fuzzy fallback fallback/hallucination detection.
- [x] Tier 1 Schema Validator for boundary conditions and positive numbers.
- [x] Tier 2 Architectural sanity rule engine checking residential room size limits (e.g. 3m² <= bedroom area <= 300m²).
- [x] Tier 3 Conflict detector identifying opposing spatial requirements.
- [x] Unit tests in `tests/test_validators.py` covering positive pass, out-of-range warnings, contradiction flags, and hallucinated quote detection.
