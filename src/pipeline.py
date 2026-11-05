"""End-to-end Data Pipeline orchestrator: Ingest -> Extract -> Ground -> Validate -> Persist."""

import argparse
import json
import sys
from typing import Optional
from loguru import logger
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.models.canonical import BuildingRequirementsExtraction
from src.extractors.protocol import LLMClientProtocol
from src.extractors.gemini_client import GoogleGenAIClient
from src.validators.grounding import ground_extraction
from src.validators.rules import ThreeTierValidator, ValidationReport, ValidationStatus
from src.db.connection import get_engine, init_db, get_session
from src.db.models import ProjectRecord, SpaceRecord, ConstraintRecord, ValidationLogRecord


class PipelineResult(BaseModel):
    project_id: int
    project_name: str
    building_type: str
    validation_status: ValidationStatus
    spaces_count: int
    constraints_count: int
    grounding_match_rate: float
    issues_count: int
    database_type: str
    extraction: BuildingRequirementsExtraction
    validation_report: ValidationReport


def run_pipeline(
    raw_transcript: str,
    llm_client: LLMClientProtocol,
    db_engine=None,
    project_name: Optional[str] = None,
) -> PipelineResult:
    """Execute end-to-end requirements ingestion, extraction, grounding, validation, and storage.

    Args:
        raw_transcript: Raw text requirements.
        llm_client: Implementation of LLMClientProtocol (Gemini or Mock).
        db_engine: Optional SQLAlchemy engine. If None, initialized via get_engine().
        project_name: Optional override for the project name.

    Returns:
        PipelineResult with execution summary and stored entities.
    """
    logger.info("Step 1: Ingesting raw transcript (length: {} chars)...", len(raw_transcript))

    # 1. Extraction via LLM
    logger.info("Step 2: Calling LLM extraction engine...")
    extraction = llm_client.extract(raw_transcript)

    # 2. Grounding against original text
    logger.info("Step 3: Performing deterministic character-offset grounding...")
    extraction = ground_extraction(extraction, raw_transcript)

    # 3. Validation via 3-Tier Rule Engine
    logger.info("Step 4: Running 3-Tier validation harness...")
    validator = ThreeTierValidator()
    val_report = validator.validate(extraction, raw_transcript)

    logger.info(
        "Validation completed. Status: {}, Grounding match: {:.1%}, Issues: {}",
        val_report.status.value,
        val_report.grounding_match_rate,
        len(val_report.issues),
    )

    # 4. Database Persistence
    logger.info("Step 5: Persisting to relational storage...")
    engine = db_engine
    db_type = "Custom"
    if engine is None:
        engine, db_type = get_engine()

    init_db(engine)

    with get_session(engine) as session:
        proj_name = project_name or extraction.project.project_name or "PreFab Project"
        project_record = ProjectRecord(
            project_name=proj_name,
            building_type=extraction.project.building_type.value,
            target_stories=extraction.project.target_stories,
            total_area_target_m2=extraction.project.total_area_target_m2,
            raw_transcript=raw_transcript,
            raw_payload=extraction.model_dump_json(indent=2),
            validation_status=val_report.status.value,
            review_status="PENDING_REVIEW" if val_report.status != ValidationStatus.PASSED else "APPROVED",
        )
        session.add(project_record)
        session.flush()  # Obtain project_record.id

        # Insert spaces
        for sp in extraction.spaces:
            space_rec = SpaceRecord(
                project_id=project_record.id,
                space_key=sp.space_id,
                space_type=sp.space_type.value,
                quantity=sp.quantity,
                relationships_json=json.dumps([r.model_dump() for r in sp.relationships]),
                notes=sp.notes,
                quote=sp.provenance.quote if sp.provenance else None,
                char_start=sp.provenance.char_start if sp.provenance else None,
                char_end=sp.provenance.char_end if sp.provenance else None,
                is_hallucinated=sp.provenance.is_hallucinated if sp.provenance else False,
            )
            session.add(space_rec)

        # Insert constraints
        for c in extraction.constraints:
            c_rec = ConstraintRecord(
                project_id=project_record.id,
                constraint_key=c.constraint_id,
                target_space=c.target_space,
                attribute=c.attribute.value,
                operator=c.operator.value,
                value=c.value,
                unit=c.unit.value,
                quote=c.provenance.quote if c.provenance else None,
                char_start=c.provenance.char_start if c.provenance else None,
                char_end=c.provenance.char_end if c.provenance else None,
                is_hallucinated=c.provenance.is_hallucinated if c.provenance else False,
            )
            session.add(c_rec)

        # Insert validation logs
        for issue in val_report.issues:
            log_rec = ValidationLogRecord(
                project_id=project_record.id,
                rule_id=issue.rule_id,
                tier=issue.tier,
                severity=issue.severity.value,
                target_field=issue.target_field,
                message=issue.message,
            )
            session.add(log_rec)

        session.commit()
        project_id = project_record.id

    logger.success(f"Pipeline finished! Project ID #{project_id} stored in {db_type}.")

    return PipelineResult(
        project_id=project_id,
        project_name=proj_name,
        building_type=extraction.project.building_type.value,
        validation_status=val_report.status,
        spaces_count=len(extraction.spaces),
        constraints_count=len(extraction.constraints),
        grounding_match_rate=val_report.grounding_match_rate,
        issues_count=len(val_report.issues),
        database_type=db_type,
        extraction=extraction,
        validation_report=val_report,
    )


def main():
    parser = argparse.ArgumentParser(description="Elyra AI Requirements Extraction ETL Pipeline")
    parser.add_argument("--input", "-i", type=str, help="Path to raw transcript text file or direct string")
    parser.add_argument("--name", "-n", type=str, default="CLI Run Project", help="Optional project name")
    parser.add_argument("--api-key", type=str, default=None, help="Gemini API Key override")
    args = parser.parse_args()

    if not args.input:
        sample_text = (
            "I want a single-family house with three bedrooms, two bathrooms, an open kitchen connected "
            "to the living room, and a separate home office. The master bedroom should be at least 18 square meters."
        )
        print("No --input provided. Using default sample transcript:")
        print(f"'{sample_text}'\n")
        raw_text = sample_text
    else:
        try:
            with open(args.input, "r", encoding="utf-8") as f:
                raw_text = f.read()
        except FileNotFoundError:
            raw_text = args.input

    client = GoogleGenAIClient(api_key=args.api_key)
    result = run_pipeline(raw_text, client, project_name=args.name)

    print("\n" + "=" * 60)
    print("ETL PIPELINE EXECUTION SUMMARY")
    print("=" * 60)
    print(f"Project ID        : #{result.project_id}")
    print(f"Project Name      : {result.project_name}")
    print(f"Building Type     : {result.building_type}")
    print(f"Validation Status : {result.validation_status.value}")
    print(f"Spaces Extracted  : {result.spaces_count}")
    print(f"Constraints Found : {result.constraints_count}")
    print(f"Grounding Score   : {result.grounding_match_rate:.1%}")
    print(f"Active Issues     : {result.issues_count}")
    print(f"Target Database   : {result.database_type}")
    print("=" * 60)


if __name__ == "__main__":
    main()
