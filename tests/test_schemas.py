"""Tests for Canonical Pydantic schemas."""

import pytest
from pydantic import ValidationError
from src.models.canonical import (
    BuildingType,
    SpaceType,
    SpatialRelationshipType,
    ConstraintAttribute,
    ConstraintOperator,
    MeasurementUnit,
    FieldProvenance,
    SpatialRelationship,
    SpaceRequirement,
    Constraint,
    ProjectMetadata,
    BuildingRequirementsExtraction,
)


def test_field_provenance_creation():
    prov = FieldProvenance(
        quote="The master bedroom should be at least 18 square meters.",
        char_start=10,
        char_end=64,
        confidence=0.98,
    )
    assert prov.quote == "The master bedroom should be at least 18 square meters."
    assert prov.char_start == 10
    assert prov.char_end == 64
    assert prov.confidence == 0.98
    assert not prov.is_hallucinated


def test_space_requirement_with_relationships():
    rel = SpatialRelationship(
        relation_type=SpatialRelationshipType.open_plan_with,
        target_space="living_room",
    )
    space = SpaceRequirement(
        space_id="kitchen_1",
        space_type=SpaceType.kitchen,
        quantity=1,
        relationships=[rel],
    )
    assert space.space_id == "kitchen_1"
    assert space.space_type == SpaceType.kitchen
    assert len(space.relationships) == 1
    assert space.relationships[0].relation_type == SpatialRelationshipType.open_plan_with


def test_constraint_validation():
    constraint = Constraint(
        constraint_id="c_mbr_area",
        target_space="master_bedroom_1",
        attribute=ConstraintAttribute.minimum_area,
        operator=ConstraintOperator.gte,
        value=18.0,
        unit=MeasurementUnit.m2,
    )
    assert constraint.value == 18.0
    assert constraint.operator == ConstraintOperator.gte
    assert constraint.unit == MeasurementUnit.m2


def test_invalid_negative_quantity_raises_validation_error():
    with pytest.raises(ValidationError):
        SpaceRequirement(
            space_id="bad_space",
            space_type=SpaceType.bedroom,
            quantity=0,  # ge=1 violated
        )


def test_building_requirements_extraction_serialization():
    payload = {
        "project": {
            "project_name": "Modern Villa",
            "building_type": "villa",
            "target_stories": 2,
            "total_area_target_m2": 220.0,
        },
        "spaces": [
            {
                "space_id": "living_room_1",
                "space_type": "living_room",
                "quantity": 1,
            },
            {
                "space_id": "bedroom_1",
                "space_type": "bedroom",
                "quantity": 3,
            },
        ],
        "constraints": [
            {
                "constraint_id": "c1",
                "target_space": "living_room_1",
                "attribute": "area",
                "operator": ">=",
                "value": 35.0,
                "unit": "m2",
            }
        ],
    }

    model = BuildingRequirementsExtraction.model_validate(payload)
    assert model.project.building_type == BuildingType.villa
    assert len(model.spaces) == 2
    assert model.constraints[0].value == 35.0

    # Ensure clean json serialization
    json_str = model.model_dump_json()
    assert "Modern Villa" in json_str

