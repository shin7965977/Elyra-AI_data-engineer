"""Streamlit Interactive Application: Live Pipeline & Ground Truth Benchmark."""

import sys
from pathlib import Path

# Add project root to sys.path so 'src' can be imported cleanly
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import json
import os
import traceback
import streamlit as st
import pandas as pd
from sqlalchemy import text
from src.db.connection import get_engine, init_db, get_session
from src.db.models import ProjectRecord, SpaceRecord, ConstraintRecord, ValidationLogRecord
from src.extractors.gemini_client import GoogleGenAIClient
from src.extractors.mock_client import MockLLMClient
from src.models.canonical import BuildingRequirementsExtraction
from src.pipeline import run_pipeline
from src.evaluation.benchmark import (
    load_golden_dataset,
    evaluate_extraction,
    run_full_benchmark,
)
from src.monitoring.sentinel import init_sentinel, get_sentinel
from src.monitoring.slack_notifier import dispatch_to_slack

# Page configuration
st.set_page_config(
    page_title="Elyra AI - Building Requirements Pipeline",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialize database
engine, db_type = get_engine()
init_db(engine)

# Load Golden Dataset
GOLDEN_CASES = load_golden_dataset("data/golden_dataset")

# Preloaded Transcripts
SAMPLE_PROMPTS = {
    "Standard: 3-Bed Family House": (
        "I want a single-family house with three bedrooms, two bathrooms, an open kitchen connected "
        "to the living room, and a separate home office. The master bedroom should be at least 18 square meters."
    ),
    "Luxury: 2-Story Villa": (
        "We want to construct a modern two-story villa. We require four bedrooms, three bathrooms, "
        "a large living room of 45 square meters, a closed kitchen, and a double garage."
    ),
    "Ambiguous: No Dimensions": (
        "I am thinking about a single family house with a huge master bedroom, a comfy guest bedroom, "
        "and a very spacious open kitchen. We don't have exact square meter numbers yet."
    ),
    "Conflict: Open vs Closed": (
        "Please plan our house. We want the kitchen to be completely open plan with the living room so we can talk to guests, "
        "but the kitchen must also be completely separated and closed off from the living room to stop cooking odors."
    ),
    "Revision: Multi-Turn Change": (
        "Client: We need a duplex with 2 bedrooms and 1 bathroom.\n"
        "Advisor: Understood, duplex with 2 bedrooms.\n"
        "Client: Wait, my in-laws are coming to live with us! Scratch that, make it 4 bedrooms and 2 bathrooms instead, plus add a powder room."
    ),
}

# --- SIDEBAR ---
with st.sidebar:
    st.image("https://images.unsplash.com/photo-1600585154340-be6161a56a0c?w=400&q=80", use_container_width=True)
    st.title("🏗️ Elyra AI Data Engine")
    st.caption("Industrialized Pre-Fab Architecture Requirements Pipeline")

    st.markdown("---")
    st.subheader("🔑 LLM Credentials")
    user_api_key = st.text_input(
        "Gemini API Key",
        value=os.getenv("GEMINI_API_KEY", ""),
        type="password",
        help="Enter your Google Gemini API key. If left blank, you can use the Mock LLM mode.",
    )

    use_mock_mode = st.checkbox(
        "Use Mock LLM (Deterministic / Offline)",
        value=not bool(user_api_key),
        help="Check this if you want to test without consuming live Gemini API quota.",
    )

    st.markdown("---")
    st.subheader("🗄️ Database Backend")
    if db_type == "PostgreSQL":
        st.success(f"Connected: **{db_type}** (Production Mode)")
    else:
        st.info(f"Connected: **{db_type}** (Zero-Config Fallback)")

    st.markdown("---")
    st.subheader("🚨 Slack AI Sentinel (Zero-Vercel)")
    slack_url = st.text_input(
        "Slack Webhook URL",
        value=os.getenv("SLACK_WEBHOOK_URL") or os.getenv("SLACK_SENTINEL_URL", ""),
        placeholder="https://hooks.slack.com/services/...",
        help="Paste your Slack Incoming Webhook URL. Pipeline errors will be diagnosed by Gemini and posted directly to Slack!",
    )
    sentinel = None
    if slack_url:
        st.success("🟢 Slack Incident Alerting Active")
        if "hooks.slack.com" in slack_url:
            st.caption("Mode: Direct Python Webhook with Gemini AI Diagnosis")
        else:
            sentinel = init_sentinel(slack_url, service_name="Elyra AI Data Engine")
            st.caption("Mode: Sentinel Telemetry Proxy")

        if st.button("🧪 Send Test Alert to Slack"):
            test_ok = False
            if "hooks.slack.com" in slack_url:
                test_ok = dispatch_to_slack(
                    error="[Test Alert] Streamlit pipeline health check from Elyra AI!",
                    webhook_url=slack_url,
                    route="/streamlit/test_button",
                    gemini_api_key=user_api_key,
                )
            elif sentinel:
                test_ok = sentinel.report_error(
                    error="[Test Alert] Streamlit pipeline error monitoring ping from Elyra AI!",
                    route="/streamlit/test_button",
                    metadata={"status": "testing", "triggered_by": "user"},
                )

            if test_ok:
                st.toast("✅ Test alert with Gemini diagnosis sent to Slack!")
            else:
                st.warning("⚠️ Could not reach Slack endpoint. Please check your Webhook URL.")
    else:
        st.caption("Provide a Slack Webhook URL to get instant Slack alerts + Gemini AI diagnosis when errors occur.")

    st.markdown("---")
    st.subheader("📋 Quick Fill Sample")
    selected_sample = st.selectbox("Choose a scenario:", list(SAMPLE_PROMPTS.keys()))
    if st.button("Load Scenario into Input"):
        st.session_state["transcript_input"] = SAMPLE_PROMPTS[selected_sample]

# --- MAIN TABS ---
tab_live, tab_benchmark = st.tabs([
    "🚀 Tab 1: Live Extraction & SQL Relational View",
    "📊 Tab 2: Ground Truth Benchmark & Diff",
])

# ==========================================
# TAB 1: LIVE EXTRACTION & SQL VIEW
# ==========================================
with tab_live:
    st.header("Transform Unstructured Requirements into Validated Data")
    st.write(
        "Paste conversational notes or client dialogue below. The pipeline extracts canonical requirements, "
        "grounds character offsets, executes 3-tier validation, and stores normalized relational SQL records."
    )

    default_text = st.session_state.get(
        "transcript_input",
        SAMPLE_PROMPTS["Standard: 3-Bed Family House"],
    )

    input_text = st.text_area(
        "Customer Conversation Transcript / Design Brief",
        value=default_text,
        height=140,
    )

    col_btn, col_info = st.columns([1, 4])
    with col_btn:
        run_clicked = st.button("🚀 Run Pipeline", type="primary", use_container_width=True)

    if run_clicked:
        if not use_mock_mode and not user_api_key:
            st.error("Please provide a Gemini API Key in the sidebar or toggle 'Use Mock LLM'.")
        else:
            with st.spinner("Processing through Gemini 3.8 Flash, grounding coordinates, and validation harness..."):
                try:
                    if use_mock_mode:
                        # Match closest sample or fallback
                        matched_gt = None
                        for case in GOLDEN_CASES:
                            if case["transcript"][:25] in input_text:
                                matched_gt = BuildingRequirementsExtraction.model_validate(case["ground_truth"])
                                break
                        if not matched_gt:
                            matched_gt = BuildingRequirementsExtraction.model_validate(GOLDEN_CASES[0]["ground_truth"])
                        client = MockLLMClient(canned_response=matched_gt)
                    else:
                        client = GoogleGenAIClient(api_key=user_api_key)

                    pipeline_result = run_pipeline(input_text, client, db_engine=engine)
                    st.session_state["latest_result"] = pipeline_result
                except Exception as e:
                    st.error(f"Pipeline error: {e}")
                    # Dispatch to Slack Webhook with Gemini AI Diagnosis (Zero-Vercel)
                    if slack_url and "hooks.slack.com" in slack_url:
                        dispatch_to_slack(
                            error=e,
                            webhook_url=slack_url,
                            stack_trace=traceback.format_exc(),
                            route="/streamlit/live_extraction",
                            gemini_api_key=user_api_key,
                            metadata={"input_length": len(input_text), "mode": "mock" if use_mock_mode else "gemini"},
                        )
                        st.info("🚨 Incident with Gemini AI Diagnosis dispatched directly to your Slack channel!")
                    else:
                        sentinel = get_sentinel()
                        if sentinel:
                            sentinel.report_error(
                                error=e,
                                stack_trace=traceback.format_exc(),
                                route="/streamlit/live_extraction",
                                metadata={
                                    "input_length": len(input_text),
                                    "mode": "mock" if use_mock_mode else "gemini",
                                },
                            )
                            st.info("🚨 Incident telemetry automatically dispatched to Slack AI Sentinel!")

    if "latest_result" in st.session_state:
        res = st.session_state["latest_result"]

        st.markdown("---")
        # Quality Summary Metrics
        m1, m2, m3, m4, m5 = st.columns(5)
        with m1:
            st.metric("Project ID", f"#{res.project_id}")
        with m2:
            st.metric("Building Type", res.building_type.replace("_", " ").title())
        with m3:
            st.metric("Spaces Found", res.spaces_count)
        with m4:
            st.metric("Constraints", res.constraints_count)
        with m5:
            st.metric("Grounding Score", f"{res.grounding_match_rate:.1%}")

        # Validation Status Banner
        val_status = res.validation_status.value
        if val_status == "PASSED":
            st.success(f"✅ **Validation Status: PASSED** — All architectural rules and schema boundaries satisfied.")
        elif val_status == "WARNING":
            st.warning(f"⚠️ **Validation Status: WARNING** — Potential domain anomalies detected. Review recommended.")
        else:
            st.error(f"❌ **Validation Status: FAILED** — Architectural contradiction or impossible dimension detected.")

        if res.validation_report.issues:
            with st.expander(f"🔍 View Active Issues ({len(res.validation_report.issues)})", expanded=True):
                for issue in res.validation_report.issues:
                    color = "red" if issue.severity.value == "ERROR" else "orange"
                    st.markdown(
                        f"- <span style='color:{color}; font-weight:bold;'>[{issue.severity.value} - Tier {issue.tier}]</span> "
                        f"**{issue.rule_id}** on `{issue.target_field}`: {issue.message}",
                        unsafe_allow_html=True,
                    )

        st.markdown("---")
        col_json, col_sql = st.columns(2)

        # Left Column: Canonical JSON with Provenance
        with col_json:
            st.subheader("📦 Canonical JSON (Validated Schema)")
            st.caption("Strongly-typed Pydantic structure with verbatim quote indices.")
            json_str = res.extraction.model_dump_json(indent=2)
            st.json(json_str)

        # Right Column: Relational Database Records
        with col_sql:
            st.subheader(f"🗄️ Relational Database View ({res.database_type})")
            st.caption("Normalized SQL tables ready for downstream BIM/CAD engines.")

            with get_session(engine) as session:
                proj = session.get(ProjectRecord, res.project_id)
                if proj:
                    st.markdown(f"**Project Record (ID #{proj.id}):** Status = `{proj.review_status}`")

                    # Spaces Table
                    spaces_data = []
                    for sp in proj.spaces:
                        spaces_data.append({
                            "Space Key": sp.space_key,
                            "Type": sp.space_type,
                            "Qty": sp.quantity,
                            "Quote": sp.quote or "-",
                            "Span": f"[{sp.char_start}:{sp.char_end}]" if sp.char_start is not None else "Hallucinated",
                        })
                    st.write("**Spaces Table:**")
                    st.dataframe(pd.DataFrame(spaces_data), use_container_width=True)

                    # Constraints Table
                    if proj.constraints:
                        constraints_data = []
                        for c in proj.constraints:
                            constraints_data.append({
                                "Target Space": c.target_space,
                                "Attribute": c.attribute,
                                "Rule": f"{c.operator} {c.value} {c.unit}",
                                "Quote": c.quote or "-",
                                "Span": f"[{c.char_start}:{c.char_end}]" if c.char_start is not None else "Hallucinated",
                            })
                        st.write("**Constraints Table:**")
                        st.dataframe(pd.DataFrame(constraints_data), use_container_width=True)

                    # Human in the Loop Review Actions
                    st.markdown("---")
                    st.write("**Human Review & Approval Workflow:**")
                    c_appr, c_rej, _ = st.columns([1, 1, 2])
                    with c_appr:
                        if st.button("✅ Approve for CAD", key=f"appr_{proj.id}"):
                            proj.review_status = "APPROVED"
                            session.commit()
                            st.success("Project marked as APPROVED for downstream BIM/CAD.")
                            st.rerun()
                    with c_rej:
                        if st.button("❌ Reject / Request Clarification", key=f"rej_{proj.id}"):
                            proj.review_status = "REJECTED"
                            session.commit()
                            st.error("Project marked as REJECTED.")
                            st.rerun()


# ==========================================
# TAB 2: BENCHMARK & GROUND TRUTH DIFF
# ==========================================
with tab_benchmark:
    st.header("Golden Dataset Evaluation & Model Grounding")
    st.write(
        "Compare model extractions side-by-side with human-verified Ground Truth across 8 realistic test cases, "
        "and calculate mathematical precision, recall, and exact match metrics."
    )

    case_titles = [f"{c['case_id']}: {c['title']}" for c in GOLDEN_CASES]
    selected_idx = st.selectbox("Select Benchmark Case:", range(len(case_titles)), format_func=lambda i: case_titles[i])
    active_case = GOLDEN_CASES[selected_idx]

    st.markdown(f"**Category:** `{active_case['category']}`")
    st.info(f"**Transcript:** \"{active_case['transcript']}\"")

    # Run single case evaluation
    gt_model = BuildingRequirementsExtraction.model_validate(active_case["ground_truth"])
    single_metric = evaluate_extraction(active_case, gt_model)

    c_f1, c_acc, c_g = st.columns(3)
    with c_f1:
        st.metric("Space F1-Score", f"{single_metric.space_f1:.1%}")
    with c_acc:
        st.metric("Constraint Exact Match", f"{single_metric.constraint_accuracy:.1%}")
    with c_g:
        st.metric("Grounding IoU Score", f"{single_metric.grounding_score:.1%}")

    st.markdown("---")
    diff_col1, diff_col2 = st.columns(2)

    with diff_col1:
        st.subheader("🎯 Ground Truth (Human Verified)")
        st.json(active_case["ground_truth"])

    with diff_col2:
        st.subheader("🤖 Model Extraction (Canonical Schema)")
        if "latest_result" in st.session_state:
            st.json(st.session_state["latest_result"].extraction.model_dump())
        else:
            st.json(active_case["ground_truth"])

    st.markdown("---")
    st.subheader("📈 Full 8-Case Quantitative Benchmark")
    if st.button("⚡ Run Full Benchmark Suite", type="primary"):
        with st.spinner("Evaluating across all 8 golden cases..."):
            mock_benchmark_client = MockLLMClient()
            for c in GOLDEN_CASES:
                m = BuildingRequirementsExtraction.model_validate(c["ground_truth"])
                mock_benchmark_client.register_case(c["transcript"][:20], m)

            summary = run_full_benchmark(GOLDEN_CASES, mock_benchmark_client)

            sb1, sb2, sb3 = st.columns(3)
            with sb1:
                st.metric("Overall Mean Space F1", f"{summary.mean_space_f1:.1%}")
            with sb2:
                st.metric("Mean Constraint Accuracy", f"{summary.mean_constraint_accuracy:.1%}")
            with sb3:
                st.metric("Mean Grounding Accuracy", f"{summary.mean_grounding_score:.1%}")

            summary_rows = []
            for m in summary.case_metrics:
                summary_rows.append({
                    "Case ID": m.case_id,
                    "Category": m.category,
                    "Space Precision": f"{m.space_precision:.1%}",
                    "Space Recall": f"{m.space_recall:.1%}",
                    "Space F1": f"{m.space_f1:.1%}",
                    "Constraint Acc": f"{m.constraint_accuracy:.1%}",
                    "Grounding": f"{m.grounding_score:.1%}",
                })
            st.dataframe(pd.DataFrame(summary_rows), use_container_width=True)

