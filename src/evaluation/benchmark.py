"""Quantitative evaluation benchmark harness for measuring extraction accuracy."""

import glob
import json
import os
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from src.models.canonical import BuildingRequirementsExtraction, SpaceType
from src.extractors.protocol import LLMClientProtocol
from src.validators.grounding import ground_extraction


class CaseEvaluationMetric(BaseModel):
    case_id: str
    category: str
    title: str
    space_precision: float
    space_recall: float
    space_f1: float
    constraint_accuracy: float
    grounding_score: float
    passed_validation: bool


class BenchmarkSummary(BaseModel):
    total_cases: int
    mean_space_f1: float
    mean_constraint_accuracy: float
    mean_grounding_score: float
    case_metrics: List[CaseEvaluationMetric] = Field(default_factory=list)


def load_golden_dataset(dataset_dir: str = "data/golden_dataset") -> List[Dict]:
    """Load all golden dataset JSON files from the specified directory."""
    cases = []
    pattern = os.path.join(dataset_dir, "*.json")
    files = sorted(glob.glob(pattern))

    for filepath in files:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            cases.append(data)

    return cases


def evaluate_extraction(case: Dict, extraction: BuildingRequirementsExtraction) -> CaseEvaluationMetric:
    """Evaluate an extraction against the ground truth of a specific test case."""
    gt_data = case["ground_truth"]
    gt_spaces = gt_data.get("spaces", [])
    gt_constraints = gt_data.get("constraints", [])

    # 1. Space Matching (Precision / Recall / F1)
    gt_space_types = {}
    for sp in gt_spaces:
        st = sp["space_type"]
        gt_space_types[st] = gt_space_types.get(st, 0) + sp.get("quantity", 1)

    pred_space_types = {}
    for sp in extraction.spaces:
        st = sp.space_type.value
        pred_space_types[st] = pred_space_types.get(st, 0) + sp.quantity

    true_positives = 0
    for st, count in pred_space_types.items():
        if st in gt_space_types:
            true_positives += min(count, gt_space_types[st])

    pred_total = sum(pred_space_types.values())
    gt_total = sum(gt_space_types.values())

    precision = (true_positives / pred_total) if pred_total > 0 else (1.0 if gt_total == 0 else 0.0)
    recall = (true_positives / gt_total) if gt_total > 0 else (1.0 if pred_total == 0 else 0.0)
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

    # 2. Constraint Matching
    if not gt_constraints and not extraction.constraints:
        constraint_acc = 1.0
    elif not gt_constraints or not extraction.constraints:
        constraint_acc = 0.0
    else:
        matched_c = 0
        for gc in gt_constraints:
            g_attr = gc.get("attribute")
            g_val = gc.get("value")
            # Look for matching prediction
            for ec in extraction.constraints:
                if ec.attribute.value == g_attr and abs(ec.value - g_val) < 0.1:
                    matched_c += 1
                    break
        constraint_acc = matched_c / max(len(gt_constraints), len(extraction.constraints))

    # 3. Grounding Score
    total_prov = 0
    valid_prov = 0
    for sp in extraction.spaces:
        if sp.provenance:
            total_prov += 1
            if not sp.provenance.is_hallucinated and sp.provenance.char_start is not None:
                valid_prov += 1
    for c in extraction.constraints:
        if c.provenance:
            total_prov += 1
            if not c.provenance.is_hallucinated and c.provenance.char_start is not None:
                valid_prov += 1

    grounding_score = (valid_prov / total_prov) if total_prov > 0 else 1.0

    return CaseEvaluationMetric(
        case_id=case["case_id"],
        category=case["category"],
        title=case["title"],
        space_precision=round(precision, 3),
        space_recall=round(recall, 3),
        space_f1=round(f1, 3),
        constraint_accuracy=round(constraint_acc, 3),
        grounding_score=round(grounding_score, 3),
        passed_validation=True,
    )


def run_full_benchmark(cases: List[Dict], client: LLMClientProtocol) -> BenchmarkSummary:
    """Run extraction benchmark across all test cases and summarize metrics."""
    metrics_list = []

    for case in cases:
        transcript = case["transcript"]
        raw_extraction = client.extract(transcript)
        grounded = ground_extraction(raw_extraction, transcript)
        metric = evaluate_extraction(case, grounded)
        metrics_list.append(metric)

    n = len(metrics_list)
    mean_f1 = sum(m.space_f1 for m in metrics_list) / n if n > 0 else 0.0
    mean_c = sum(m.constraint_accuracy for m in metrics_list) / n if n > 0 else 0.0
    mean_g = sum(m.grounding_score for m in metrics_list) / n if n > 0 else 0.0

    return BenchmarkSummary(
        total_cases=n,
        mean_space_f1=round(mean_f1, 3),
        mean_constraint_accuracy=round(mean_c, 3),
        mean_grounding_score=round(mean_g, 3),
        case_metrics=metrics_list,
    )


def generate_markdown_report(summary: BenchmarkSummary) -> str:
    """Generate a clean GitHub-flavored markdown report table."""
    lines = [
        "# Elyra AI Extraction Benchmark Report",
        "",
        f"**Total Evaluated Cases:** {summary.total_cases}",
        f"- **Mean Space Extraction F1:** {summary.mean_space_f1:.1%}",
        f"- **Mean Constraint Accuracy:** {summary.mean_constraint_accuracy:.1%}",
        f"- **Mean Grounding Accuracy:** {summary.mean_grounding_score:.1%}",
        "",
        "| Case ID | Category | Space F1 | Constraint Acc | Grounding |",
        "| :--- | :--- | :---: | :---: | :---: |",
    ]

    for m in summary.case_metrics:
        lines.append(
            f"| `{m.case_id}` | {m.category} | {m.space_f1:.1%} | {m.constraint_accuracy:.1%} | {m.grounding_score:.1%} |"
        )

    return "\n".join(lines)
