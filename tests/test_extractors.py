"""Tests for LLM extractor adapters and protocols."""

from src.models.canonical import (
    BuildingRequirementsExtraction,
    ProjectMetadata,
    SpaceRequirement,
    SpaceType,
    BuildingType,
)
from src.extractors.protocol import LLMClientProtocol
from src.extractors.mock_client import MockLLMClient
from src.extractors.gemini_client import GoogleGenAIClient


def test_mock_client_implements_protocol():
    client = MockLLMClient()
    assert isinstance(client, LLMClientProtocol)


def test_mock_client_returns_canned_extraction():
    expected = BuildingRequirementsExtraction(
        project=ProjectMetadata(
            project_name="Test Project",
            building_type=BuildingType.single_family_house,
            target_stories=2,
        ),
        spaces=[
            SpaceRequirement(
                space_id="br1",
                space_type=SpaceType.bedroom,
                quantity=3,
            )
        ],
    )

    client = MockLLMClient(canned_response=expected)
    result = client.extract("I want a 2-story single family house with 3 bedrooms.")

    assert result.project.project_name == "Test Project"
    assert result.project.target_stories == 2
    assert len(result.spaces) == 1
    assert result.spaces[0].quantity == 3


def test_mock_client_subtext_registration():
    client = MockLLMClient()
    special_res = BuildingRequirementsExtraction(
        project=ProjectMetadata(project_name="Duplex Case")
    )
    client.register_case("duplex", special_res)

    res = client.extract("We need a duplex apartment.")
    assert res.project.project_name == "Duplex Case"

    res_empty = client.extract("Something completely different.")
    assert res_empty.project.project_name == "PreFab Residential Project"


def test_gemini_client_instantiation():
    # Instantiation without key should log warning and not crash
    client = GoogleGenAIClient(api_key="fake_test_key")
    assert isinstance(client, LLMClientProtocol)
    assert client.model_name == "gemini-3.8-flash"

