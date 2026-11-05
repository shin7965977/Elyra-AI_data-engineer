"""Abstract protocol for building requirement extractors."""

from typing import Protocol, runtime_checkable
from src.models.canonical import BuildingRequirementsExtraction


@runtime_checkable
class LLMClientProtocol(Protocol):
    """Protocol defining the interface for an architectural requirement extractor."""

    def extract(self, transcript: str) -> BuildingRequirementsExtraction:
        """Extract structured building requirements from raw conversational text.

        Args:
            transcript: Raw customer conversation or requirement text.

        Returns:
            BuildingRequirementsExtraction canonical model.
        """
        ...

