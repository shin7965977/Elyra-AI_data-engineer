"""Tests for benchmark evaluation engine and golden dataset."""

import os
from src.evaluation.benchmark import (
    load_golden_dataset,
    evaluate_extraction,
    run_full_benchmark,
    generate_markdown_report,
)
from src.extractors.mock_client import MockLLMClient
from src.models.canonical import BuildingRequirementsExtraction


def test_load_golden_dataset():
    cases = load_golden_dataset("data/golden_dataset")
    assert len(cases) == 8
    categories = {c["category"] for c in cases}
    assert "standard_happy_path" in categories
    assert "ambiguous_missing_details" in categories
    assert "contradiction_and_edge_cases" in categories
    assert "multiturn_revisions" in categories


def test_evaluate_extraction_perfect_match():
    cases = load_golden_dataset("data/golden_dataset")
    case = cases[0]

    # Convert ground truth into extraction model
    gt_model = BuildingRequirementsExtraction.model_validate(case["ground_truth"])
    metric = evaluate_extraction(case, gt_model)

    assert metric.case_id == case["case_id"]
    assert metric.space_f1 == 1.0
    assert metric.constraint_accuracy == 1.0


def test_run_full_benchmark_with_mock_client():
    cases = load_golden_dataset("data/golden_dataset")
    client = MockLLMClient()

    # Pre-register case responses with exact ground truths
    for c in cases:
        gt_model = BuildingRequirementsExtraction.model_validate(c["ground_truth"])
        client.register_case(c["transcript"][:20], gt_model)

    summary = run_full_benchmark(cases, client)
    assert summary.total_cases == 8
    assert summary.mean_space_f1 > 0.9
    assert summary.mean_constraint_accuracy > 0.9

    report = generate_markdown_report(summary)
    assert "Elyra AI Extraction Benchmark Report" in report
    assert "**Total Evaluated Cases:** 8" in report
