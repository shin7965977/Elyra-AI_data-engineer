"""Integration tests for the end-to-end pipeline."""

import pytest
from sqlalchemy import create_engine
from src.extractors.mock_client import MockLLMClient
from src.models.canonical import (
    BuildingRequirementsExtraction,
    BuildingType,
    Constraint,
    ConstraintAttribute,
    ConstraintOperator,
    FieldProvenance,
    MeasurementUnit,
    ProjectMetadata,
    SpaceRequirement,
    SpaceType,
    SpatialRelationship,
    SpatialRelationshipType,
)
from src.pipeline import run_pipeline
from src.db.models import ProjectRecord, SpaceRecord, ConstraintRecord, ValidationLogRecord
from src.db.connection import get_session, init_db


def test_pipeline_end_to_end():
    transcript = (
        "We are designing a modern villa. It must have 3 bedrooms, 2 bathrooms, and a kitchen open plan with living room. "
        "The master bedroom must be at least 18 square meters."
    )

    canned = BuildingRequirementsExtraction(
        project=ProjectMetadata(
            project_name="Modern Villa Project",
            building_type=BuildingType.villa,
            target_stories=2,
            provenance=FieldProvenance(quote="modern villa"),
        ),
        spaces=[
            SpaceRequirement(
                space_id="mbr",
                space_type=SpaceType.master_bedroom,
                quantity=1,
                provenance=FieldProvenance(quote="master bedroom"),
            ),
            SpaceRequirement(
                space_id="br",
                space_type=SpaceType.bedroom,
                quantity=2,
                provenance=FieldProvenance(quote="3 bedrooms"),
            ),
            SpaceRequirement(
                space_id="bath",
                space_type=SpaceType.bathroom,
                quantity=2,
                provenance=FieldProvenance(quote="2 bathrooms"),
            ),
            SpaceRequirement(
                space_id="kitchen",
                space_type=SpaceType.kitchen,
                quantity=1,
                relationships=[
                    SpatialRelationship(
                        relation_type=SpatialRelationshipType.open_plan_with,
                        target_space="living_room",
                    )
                ],
                provenance=FieldProvenance(quote="kitchen open plan with living room"),
            ),
        ],
        constraints=[
            Constraint(
                constraint_id="c_mbr_min_area",
                target_space="mbr",
                attribute=ConstraintAttribute.minimum_area,
                operator=ConstraintOperator.gte,
                value=18.0,
                unit=MeasurementUnit.m2,
                provenance=FieldProvenance(quote="at least 18 square meters"),
            )
        ],
    )

    mock_client = MockLLMClient(canned_response=canned)
    test_engine = create_engine("sqlite:///:memory:")

    result = run_pipeline(transcript, mock_client, db_engine=test_engine)

    assert result.project_id == 1
    assert result.project_name == "Modern Villa Project"
    assert result.building_type == "villa"
    assert result.spaces_count == 4
    assert result.constraints_count == 1
    assert result.grounding_match_rate == 1.0
    assert result.validation_status.value == "PASSED"

    # Verify directly from database
    with get_session(test_engine) as session:
        proj = session.get(ProjectRecord, result.project_id)
        assert proj is not None
        assert proj.building_type == "villa"
        assert len(proj.spaces) == 4
        assert len(proj.constraints) == 1
        assert proj.constraints[0].value == 18.0
        assert proj.constraints[0].unit == "m2"
        assert proj.raw_transcript == transcript
        assert "Modern Villa Project" in proj.raw_payload
