"""Deterministic Mock LLM client for zero-cost, offline testing and CI/CD."""

from typing import Dict, Optional
from src.models.canonical import BuildingRequirementsExtraction
from src.extractors.protocol import LLMClientProtocol


class MockLLMClient(LLMClientProtocol):
    """Mock extractor providing predictable canned responses."""

    def __init__(self, canned_response: Optional[BuildingRequirementsExtraction] = None):
        self._canned_response = canned_response
        self._transcripts_log = []
        self._custom_mappings: Dict[str, BuildingRequirementsExtraction] = {}

    def register_case(self, transcript_substring: str, response: BuildingRequirementsExtraction):
        """Register a canned response triggered when a transcript contains the substring."""
        self._custom_mappings[transcript_substring] = response

    def set_default(self, response: BuildingRequirementsExtraction):
        self._canned_response = response

    def extract(self, transcript: str) -> BuildingRequirementsExtraction:
        self._transcripts_log.append(transcript)
        for key, resp in self._custom_mappings.items():
            if key in transcript:
                return resp.model_copy(deep=True)

        if self._canned_response:
            return self._canned_response.model_copy(deep=True)

        return BuildingRequirementsExtraction()

