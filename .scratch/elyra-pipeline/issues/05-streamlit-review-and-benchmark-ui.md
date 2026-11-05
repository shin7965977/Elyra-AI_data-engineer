# 05: Streamlit Dual-Tab Review & Benchmark Dashboard

**What to build:**
Build an interactive Streamlit application (`src/ui/app.py`). Include a sidebar for custom Gemini API Key input and DB connection status. Implement Tab 1 (Live Pipeline) allowing text input, triggering the pipeline, displaying real-time validation badges (PASSED/WARNING/FAILED), and showing the Canonical JSON alongside live SQL table queries with an Approve button. Implement Tab 2 (Benchmark & Comparison) displaying an interactive side-by-side diff between Ground Truth and LLM Extractions across the 8 Golden Dataset cases, with metric summary cards and one-click full benchmark execution. Author a comprehensive `README.md` highlighting how this MVP solves Elyra AI's core data engineering challenges.

**Blocked by:** 03: Dual-Mode Persistence & CLI ETL Pipeline, 04: Golden Dataset (8 Cases) & Quantitative Evaluation Engine

**Status:** ready-for-agent

- [ ] Streamlit sidebar with API key input, DB toggle/indicator, and sample transcript selector.
- [ ] Tab 1 with Live Extraction, Validation Badges, side-by-side Canonical JSON and SQL Database Inspector, and Human Approval action.
- [ ] Tab 2 with Golden Dataset selector, Side-by-Side Ground Truth vs LLM diff, and full benchmark metrics display.
- [ ] Root `README.md` documenting architecture, Elyra problem-solution alignment, and reproduction instructions.
- [ ] End-to-end smoke test verifying application components import and initialize cleanly.
