"""Unit tests for the three-tier validation engine and deterministic grounding."""

import pytest
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
from src.validators.grounding import find_quote_offsets, ground_extraction
from src.validators.rules import Severity, ThreeTierValidator, ValidationStatus


def test_find_quote_offsets_exact_match():
    text = "We want a master bedroom with at least 18 square meters and 2 bathrooms."
    quote = "at least 18 square meters"
    start, end, hallucinated = find_quote_offsets(text, quote)
    assert not hallucinated
    assert start == 30
    assert end == 55
    assert text[start:end] == quote


def test_find_quote_offsets_hallucination_detected():
    text = "We need an open kitchen connected to living room."
    quote = "master bedroom should be 25 m2"
    start, end, hallucinated = find_quote_offsets(text, quote)
    assert hallucinated
    assert start is None
    assert end is None


def test_ground_extraction_updates_provenance():
    transcript = "I need a single family house. The living room should be 40 square meters."
    extraction = BuildingRequirementsExtraction(
        project=ProjectMetadata(
            provenance=FieldProvenance(quote="single family house")
        ),
        constraints=[
            Constraint(
                constraint_id="c_lr_area",
                target_space="living_room",
                attribute=ConstraintAttribute.area,
                operator=ConstraintOperator.eq,
                value=40.0,
                unit=MeasurementUnit.m2,
                provenance=FieldProvenance(quote="40 square meters"),
            )
        ],
    )

    grounded = ground_extraction(extraction, transcript)
    assert not grounded.project.provenance.is_hallucinated
    assert grounded.project.provenance.char_start == 9
    assert grounded.constraints[0].provenance.char_start == 56


def test_validator_passes_on_clean_data():
    extraction = BuildingRequirementsExtraction(
        project=ProjectMetadata(project_name="Valid House"),
        spaces=[
            SpaceRequirement(space_id="mbr", space_type=SpaceType.master_bedroom, quantity=1),
            SpaceRequirement(space_id="bath", space_type=SpaceType.bathroom, quantity=2),
        ],
        constraints=[
            Constraint(
                constraint_id="c1",
                target_space="mbr",
                attribute=ConstraintAttribute.minimum_area,
                operator=ConstraintOperator.gte,
                value=20.0,
                unit=MeasurementUnit.m2,
            )
        ],
    )
    validator = ThreeTierValidator()
    report = validator.validate(extraction)
    assert report.status == ValidationStatus.PASSED
    assert len(report.issues) == 0


def test_validator_flags_unusual_room_area_warning():
    extraction = BuildingRequirementsExtraction(
        spaces=[
            SpaceRequirement(space_id="br1", space_type=SpaceType.bedroom, quantity=1),
        ],
        constraints=[
            Constraint(
                constraint_id="c1",
                target_space="br1",
                attribute=ConstraintAttribute.area,
                operator=ConstraintOperator.eq,
                value=75.0,  # Warning: typical bedroom is 6-40 m2
                unit=MeasurementUnit.m2,
            )
        ],
    )
    validator = ThreeTierValidator()
    report = validator.validate(extraction)
    assert report.status == ValidationStatus.WARNING
    assert any(i.rule_id == "RULE_UNUSUAL_ROOM_AREA" for i in report.issues)


def test_validator_fails_on_physically_impossible_area():
    extraction = BuildingRequirementsExtraction(
        spaces=[
            SpaceRequirement(space_id="br1", space_type=SpaceType.bedroom, quantity=1),
        ],
        constraints=[
            Constraint(
                constraint_id="c1",
                target_space="br1",
                attribute=ConstraintAttribute.area,
                operator=ConstraintOperator.eq,
                value=1.5,  # Error: < hard min 2.5 m2
                unit=MeasurementUnit.m2,
            )
        ],
    )
    validator = ThreeTierValidator()
    report = validator.validate(extraction)
    assert report.status == ValidationStatus.FAILED
    assert any(i.rule_id == "RULE_PHYSICALLY_IMPOSSIBLE_AREA" for i in report.issues)


def test_validator_detects_contradictory_relationship():
    space = SpaceRequirement(
        space_id="kitchen_1",
        space_type=SpaceType.kitchen,
        relationships=[
            SpatialRelationship(relation_type=SpatialRelationshipType.open_plan_with, target_space="living_room"),
            SpatialRelationship(relation_type=SpatialRelationshipType.separated_from, target_space="living_room"),
        ],
    )
    extraction = BuildingRequirementsExtraction(spaces=[space])
    validator = ThreeTierValidator()
    report = validator.validate(extraction)
    assert report.status == ValidationStatus.FAILED
    assert any(i.rule_id == "RULE_CONTRADICTORY_RELATIONSHIP" for i in report.issues)


def test_validator_detects_conflicting_constraint_bounds():
    extraction = BuildingRequirementsExtraction(
        spaces=[
            SpaceRequirement(space_id="mbr", space_type=SpaceType.master_bedroom),
        ],
        constraints=[
            Constraint(
                constraint_id="c_min",
                target_space="mbr",
                attribute=ConstraintAttribute.area,
                operator=ConstraintOperator.gte,
                value=30.0,
                unit=MeasurementUnit.m2,
            ),
            Constraint(
                constraint_id="c_max",
                target_space="mbr",
                attribute=ConstraintAttribute.area,
                operator=ConstraintOperator.lte,
                value=15.0,  # min (30) > max (15) -> conflict!
                unit=MeasurementUnit.m2,
            ),
        ],
    )
    validator = ThreeTierValidator()
    report = validator.validate(extraction)
    assert report.status == ValidationStatus.FAILED
    assert any(i.rule_id == "RULE_IMPOSSIBLE_CONSTRAINT_BOUNDS" for i in report.issues)
