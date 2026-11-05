# 01: Core Domain Schemas, LLM Adapter & Mock Harness

**What to build:**
Create the strongly-typed Pydantic v2 Canonical Schemas (`ProjectMetadata`, `SpaceRequirement`, `Constraint`, `FieldProvenance`, and `BuildingRequirementsExtraction`) representing structured architectural requirements. Implement the abstract `LLMClientProtocol`, the production `GoogleGenAIClient` targeting `gemini-3.8-flash` with native JSON Schema output mode, and the deterministic `MockLLMClient` for offline testing. Provide unit tests validating schema parsing and adapter execution.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] Pydantic v2 domain models for Project, Space, Constraint, and Provenance with strict type enforcement.
- [ ] Abstract `LLMClientProtocol` defining the standard extraction interface.
- [ ] `GoogleGenAIClient` utilizing `google-genai` SDK with `gemini-3.8-flash` and structured JSON schema enforcement.
- [ ] `MockLLMClient` allowing injection of canned responses for zero-cost, deterministic testing.
- [ ] Unit tests in `tests/test_schemas.py` and `tests/test_extractors.py` passing with 100% green status.
