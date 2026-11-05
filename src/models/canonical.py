"""Canonical data models for architectural building requirements."""

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict


class BuildingType(str, Enum):
    single_family_house = "single_family_house"
    multi_family_house = "multi_family_house"
    apartment = "apartment"
    villa = "villa"
    duplex = "duplex"
    tiny_house = "tiny_house"
    office = "office"
    other = "other"


class SpaceType(str, Enum):
    bedroom = "bedroom"
    master_bedroom = "master_bedroom"
    bathroom = "bathroom"
    powder_room = "powder_room"
    kitchen = "kitchen"
    living_room = "living_room"
    dining_room = "dining_room"
    home_office = "home_office"
    storage = "storage"
    garage = "garage"
    balcony = "balcony"
    terrace = "terrace"
    hallway = "hallway"
    utility_room = "utility_room"
    basement = "basement"
    other = "other"


class SpatialRelationshipType(str, Enum):
    open_plan_with = "open_plan_with"
    connected_to = "connected_to"
    adjacent_to = "adjacent_to"
    separated_from = "separated_from"
    soundproofed_from = "soundproofed_from"


class ConstraintAttribute(str, Enum):
    area = "area"
    minimum_area = "minimum_area"
    maximum_area = "maximum_area"
    width = "width"
    length = "length"
    ceiling_height = "ceiling_height"
    count = "count"


class ConstraintOperator(str, Enum):
    gte = ">="
    lte = "<="
    eq = "=="
    gt = ">"
    lt = "<"


class MeasurementUnit(str, Enum):
    m2 = "m2"
    m = "m"
    cm = "cm"


class FieldProvenance(BaseModel):
    model_config = ConfigDict(extra="ignore")

    quote: str = Field(..., description="Exact textual quote extracted from the source transcript")
    char_start: Optional[int] = Field(None, description="0-indexed start character offset in original transcript")
    char_end: Optional[int] = Field(None, description="0-indexed end character offset in original transcript")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence score of the extraction (0.0 to 1.0)")
    is_hallucinated: bool = Field(default=False, description="Flagged true if quote cannot be grounded in raw transcript")


class SpatialRelationship(BaseModel):
    model_config = ConfigDict(extra="ignore")

    relation_type: SpatialRelationshipType
    target_space: str = Field(..., description="Target space identifier, e.g., 'living_room'")
    provenance: Optional[FieldProvenance] = None


class SpaceRequirement(BaseModel):
    model_config = ConfigDict(extra="ignore")

    space_id: str = Field(..., description="Unique space key, e.g. 'master_bedroom_1', 'bedroom_2'")
    space_type: SpaceType
    quantity: int = Field(default=1, ge=1, description="Quantity of rooms of this type")
    relationships: List[SpatialRelationship] = Field(default_factory=list)
    notes: Optional[str] = None
    provenance: Optional[FieldProvenance] = None


class Constraint(BaseModel):
    model_config = ConfigDict(extra="ignore")

    constraint_id: str = Field(..., description="Unique constraint key, e.g. 'c_master_bedroom_area'")
    target_space: str = Field(..., description="Space ID or Space Type targeted by this constraint")
    attribute: ConstraintAttribute
    operator: ConstraintOperator
    value: float = Field(..., description="Numerical constraint value")
    unit: MeasurementUnit
    provenance: Optional[FieldProvenance] = None


class ProjectMetadata(BaseModel):
    model_config = ConfigDict(extra="ignore")

    project_name: Optional[str] = Field(default="PreFab Residential Project")
    building_type: BuildingType = Field(default=BuildingType.single_family_house)
    target_stories: Optional[int] = Field(default=None, ge=1, le=10)
    total_area_target_m2: Optional[float] = Field(default=None, ge=0.0)
    budget_notes: Optional[str] = None
    provenance: Optional[FieldProvenance] = None


class BuildingRequirementsExtraction(BaseModel):
    model_config = ConfigDict(extra="ignore")

    project: ProjectMetadata = Field(default_factory=ProjectMetadata)
    spaces: List[SpaceRequirement] = Field(default_factory=list)
    constraints: List[Constraint] = Field(default_factory=list)

