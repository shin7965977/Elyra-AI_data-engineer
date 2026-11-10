"""Three-tier architectural validation rules and conflict detection engine."""

from enum import Enum
from typing import Dict, List, Optional, Tuple
from pydantic import BaseModel, Field
from src.models.canonical import (
    BuildingRequirementsExtraction,
    ConstraintAttribute,
    ConstraintOperator,
    MeasurementUnit,
    SpaceType,
    SpatialRelationshipType,
)


class Severity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


class ValidationStatus(str, Enum):
    PASSED = "PASSED"
    WARNING = "WARNING"
    FAILED = "FAILED"


class ValidationIssue(BaseModel):
    rule_id: str
    tier: int
    severity: Severity
    target_field: str
    message: str


class ValidationReport(BaseModel):
    status: ValidationStatus
    total_spaces: int
    total_constraints: int
    grounding_match_rate: float
    issues: List[ValidationIssue] = Field(default_factory=list)


# Realistic residential architectural dimension ranges (in m2)
RESIDENTIAL_AREA_LIMITS: Dict[SpaceType, Tuple[float, float, float, float]] = {
    # format: (min_warning, max_warning, hard_min_fail, hard_max_fail)
    SpaceType.bedroom: (6.0, 40.0, 2.5, 100.0),
    SpaceType.master_bedroom: (10.0, 60.0, 4.0, 150.0),
    SpaceType.bathroom: (2.0, 25.0, 1.2, 50.0),
    SpaceType.powder_room: (1.2, 8.0, 0.8, 15.0),
    SpaceType.kitchen: (5.0, 50.0, 2.5, 120.0),
    SpaceType.living_room: (12.0, 100.0, 5.0, 300.0),
    SpaceType.dining_room: (8.0, 50.0, 4.0, 120.0),
    SpaceType.home_office: (4.0, 35.0, 2.0, 80.0),
    SpaceType.storage: (1.0, 30.0, 0.5, 100.0),
    SpaceType.garage: (12.0, 80.0, 8.0, 200.0),
}


class ThreeTierValidator:
    """Orchestrator for Schema, Domain, and Semantic validation tiers."""

    def validate(self, extraction: BuildingRequirementsExtraction, raw_transcript: Optional[str] = None) -> ValidationReport:
        issues: List[ValidationIssue] = []

        # Tier 1: Schema & Data Integrity Invariants
        self._check_tier1_schema_invariants(extraction, issues)

        # Tier 2: Architectural Domain Bounds
        self._check_tier2_architectural_domain(extraction, issues)

        # Tier 3: Semantic Contradictions & Conflicts
        self._check_tier3_conflicts(extraction, issues)

        # Compute Grounding statistics
        total_provenances = 0
        matched_provenances = 0

        # Check all provenances
        if extraction.project.provenance:
            total_provenances += 1
            if not extraction.project.provenance.is_hallucinated:
                matched_provenances += 1
            else:
                issues.append(
                    ValidationIssue(
                        rule_id="RULE_GROUNDING_HALLUCINATION",
                        tier=1,
                        severity=Severity.WARNING,
                        target_field="project.provenance",
                        message=f"Project quote could not be grounded in raw transcript: '{extraction.project.provenance.quote[:50]}...'",
                    )
                )

        for space in extraction.spaces:
            if space.provenance:
                total_provenances += 1
                if not space.provenance.is_hallucinated:
                    matched_provenances += 1
                else:
                    issues.append(
                        ValidationIssue(
                            rule_id="RULE_GROUNDING_HALLUCINATION",
                            tier=1,
                            severity=Severity.WARNING,
                            target_field=f"spaces.{space.space_id}.provenance",
                            message=f"Space quote could not be grounded in raw transcript: '{space.provenance.quote[:50]}...'",
                        )
                    )

        for constraint in extraction.constraints:
            if constraint.provenance:
                total_provenances += 1
                if not constraint.provenance.is_hallucinated:
                    matched_provenances += 1
                else:
                    issues.append(
                        ValidationIssue(
                            rule_id="RULE_GROUNDING_HALLUCINATION",
                            tier=1,
                            severity=Severity.WARNING,
                            target_field=f"constraints.{constraint.constraint_id}.provenance",
                            message=f"Constraint quote could not be grounded in raw transcript: '{constraint.provenance.quote[:50]}...'",
                        )
                    )

        grounding_rate = (matched_provenances / total_provenances) if total_provenances > 0 else 1.0

        # Determine overall status
        has_error = any(issue.severity == Severity.ERROR for issue in issues)
        has_warning = any(issue.severity == Severity.WARNING for issue in issues)

        if has_error:
            status = ValidationStatus.FAILED
        elif has_warning:
            status = ValidationStatus.WARNING
        else:
            status = ValidationStatus.PASSED

        return ValidationReport(
            status=status,
            total_spaces=len(extraction.spaces),
            total_constraints=len(extraction.constraints),
            grounding_match_rate=round(grounding_rate, 4),
            issues=issues,
        )

    def _check_tier1_schema_invariants(self, extraction: BuildingRequirementsExtraction, issues: List[ValidationIssue]):
        # Ensure spaces have unique space_ids
        seen_ids = set()
        for space in extraction.spaces:
            if space.space_id in seen_ids:
                issues.append(
                    ValidationIssue(
                        rule_id="RULE_DUPLICATE_SPACE_ID",
                        tier=1,
                        severity=Severity.ERROR,
                        target_field=f"spaces.{space.space_id}",
                        message=f"Duplicate space_id '{space.space_id}' detected.",
                    )
                )
            seen_ids.add(space.space_id)

            if space.quantity <= 0:
                issues.append(
                    ValidationIssue(
                        rule_id="RULE_NON_POSITIVE_QUANTITY",
                        tier=1,
                        severity=Severity.ERROR,
                        target_field=f"spaces.{space.space_id}.quantity",
                        message=f"Space quantity must be positive, found {space.quantity}.",
                    )
                )

        # Ensure constraints have non-empty values and valid units
        for constraint in extraction.constraints:
            if constraint.value <= 0:
                issues.append(
                    ValidationIssue(
                        rule_id="RULE_NON_POSITIVE_CONSTRAINT_VALUE",
                        tier=1,
                        severity=Severity.ERROR,
                        target_field=f"constraints.{constraint.constraint_id}.value",
                        message=f"Constraint value must be positive, found {constraint.value}.",
                    )
                )

    def _check_tier2_architectural_domain(self, extraction: BuildingRequirementsExtraction, issues: List[ValidationIssue]):
        space_type_map = {s.space_id: s.space_type for s in extraction.spaces}

        for constraint in extraction.constraints:
            if constraint.attribute in (ConstraintAttribute.area, ConstraintAttribute.minimum_area, ConstraintAttribute.maximum_area):
                if constraint.unit == MeasurementUnit.m2:
                    # Resolve space type
                    target_st = space_type_map.get(constraint.target_space)
                    if not target_st:
                        # Maybe target_space is space_type directly (e.g. 'bedroom')
                        try:
                            target_st = SpaceType(constraint.target_space)
                        except ValueError:
                            target_st = None

                    if target_st and target_st in RESIDENTIAL_AREA_LIMITS:
                        min_w, max_w, hard_min, hard_max = RESIDENTIAL_AREA_LIMITS[target_st]
                        val = constraint.value

                        if val < hard_min:
                            issues.append(
                                ValidationIssue(
                                    rule_id="RULE_PHYSICALLY_IMPOSSIBLE_AREA",
                                    tier=2,
                                    severity=Severity.ERROR,
                                    target_field=f"constraints.{constraint.constraint_id}",
                                    message=f"Area {val} m² for {target_st.value} is below absolute architectural minimum ({hard_min} m²).",
                                )
                            )
                        elif val > hard_max:
                            issues.append(
                                ValidationIssue(
                                    rule_id="RULE_PHYSICALLY_IMPOSSIBLE_AREA",
                                    tier=2,
                                    severity=Severity.ERROR,
                                    target_field=f"constraints.{constraint.constraint_id}",
                                    message=f"Area {val} m² for {target_st.value} exceeds absolute architectural maximum ({hard_max} m²).",
                                )
                            )
                        elif val < min_w or val > max_w:
                            issues.append(
                                ValidationIssue(
                                    rule_id="RULE_UNUSUAL_ROOM_AREA",
                                    tier=2,
                                    severity=Severity.WARNING,
                                    target_field=f"constraints.{constraint.constraint_id}",
                                    message=f"Area {val} m² for {target_st.value} is outside typical German/European residential range ({min_w}-{max_w} m²).",
                                )
                            )

    def _check_tier3_conflicts(self, extraction: BuildingRequirementsExtraction, issues: List[ValidationIssue]):
        # 1. Contradictory spatial relationships
        for space in extraction.spaces:
            rel_types = set()
            for r in space.relationships:
                rel_types.add((r.relation_type, r.target_space))

            # Check if open_plan_with and separated_from target the same space
            for rel_type, target in rel_types:
                if rel_type == SpatialRelationshipType.open_plan_with:
                    if (SpatialRelationshipType.separated_from, target) in rel_types:
                        issues.append(
                            ValidationIssue(
                                rule_id="RULE_CONTRADICTORY_RELATIONSHIP",
                                tier=3,
                                severity=Severity.ERROR,
                                target_field=f"spaces.{space.space_id}",
                                message=f"Contradictory relationship: space '{space.space_id}' is marked as both 'open_plan_with' and 'separated_from' target '{target}'.",
                            )
                        )

        # 2. Conflicting constraint ranges on the same space and attribute
        constraints_by_target_attr = {}
        for c in extraction.constraints:
            key = (c.target_space, c.attribute, c.unit)
            constraints_by_target_attr.setdefault(key, []).append(c)

        for (target, attr, unit), c_list in constraints_by_target_attr.items():
            min_val = None
            max_val = None
            for c in c_list:
                if c.operator in (ConstraintOperator.gte, ConstraintOperator.gt):
                    min_val = max(min_val or c.value, c.value)
                elif c.operator in (ConstraintOperator.lte, ConstraintOperator.lt):
                    max_val = min(max_val or c.value, c.value)

            if min_val is not None and max_val is not None and min_val > max_val:
                issues.append(
                    ValidationIssue(
                        rule_id="RULE_IMPOSSIBLE_CONSTRAINT_BOUNDS",
                        tier=3,
                        severity=Severity.ERROR,
                        target_field=f"constraints.{target}.{attr.value}",
                        message=f"Conflicting constraints on '{target}': required minimum ({min_val} {unit.value}) exceeds required maximum ({max_val} {unit.value}).",
                    )
                )

