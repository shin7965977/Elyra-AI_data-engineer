"""Deterministic grounding and provenance alignment engine."""

import re
from typing import Optional, Tuple
from loguru import logger
from src.models.canonical import BuildingRequirementsExtraction, FieldProvenance


def find_quote_offsets(raw_text: str, quote: str) -> Tuple[Optional[int], Optional[int], bool]:
    """Locate the exact character offsets of a quote in the raw text.

    Returns:
        (char_start, char_end, is_hallucinated)
    """
    if not quote or not raw_text:
        return None, None, True

    # 1. Exact string match
    idx = raw_text.find(quote)
    if idx != -1:
        return idx, idx + len(quote), False

    # 2. Case-insensitive exact match
    lower_raw = raw_text.lower()
    lower_quote = quote.lower()
    idx = lower_raw.find(lower_quote)
    if idx != -1:
        return idx, idx + len(quote), False

    # 3. Normalized whitespace match
    clean_quote = " ".join(quote.split())
    clean_raw = " ".join(raw_text.split())
    if clean_quote.lower() in clean_raw.lower():
        # Match using regex ignoring consecutive whitespaces
        pattern = re.escape(clean_quote).replace(r"\ ", r"\s+")
        match = re.search(pattern, raw_text, re.IGNORECASE)
        if match:
            return match.start(), match.end(), False

    # Quote cannot be grounded in the raw transcript -> Hallucination
    logger.warning(f"Grounding failure: Quote '{quote[:40]}...' not found in transcript.")
    return None, None, True


def ground_extraction(extraction: BuildingRequirementsExtraction, raw_transcript: str) -> BuildingRequirementsExtraction:
    """Ground all field provenances in an extraction against the raw transcript."""
    # 1. Project provenance
    if extraction.project.provenance:
        start, end, hallucinated = find_quote_offsets(raw_transcript, extraction.project.provenance.quote)
        extraction.project.provenance.char_start = start
        extraction.project.provenance.char_end = end
        extraction.project.provenance.is_hallucinated = hallucinated
        if hallucinated:
            extraction.project.provenance.confidence = 0.0

    # 2. Spaces & space relationships provenance
    for space in extraction.spaces:
        if space.provenance:
            start, end, hallucinated = find_quote_offsets(raw_transcript, space.provenance.quote)
            space.provenance.char_start = start
            space.provenance.char_end = end
            space.provenance.is_hallucinated = hallucinated
            if hallucinated:
                space.provenance.confidence = 0.0

        for rel in space.relationships:
            if rel.provenance:
                start, end, hallucinated = find_quote_offsets(raw_transcript, rel.provenance.quote)
                rel.provenance.char_start = start
                rel.provenance.char_end = end
                rel.provenance.is_hallucinated = hallucinated
                if hallucinated:
                    rel.provenance.confidence = 0.0

    # 3. Constraints provenance
    for constraint in extraction.constraints:
        if constraint.provenance:
            start, end, hallucinated = find_quote_offsets(raw_transcript, constraint.provenance.quote)
            constraint.provenance.char_start = start
            constraint.provenance.char_end = end
            constraint.provenance.is_hallucinated = hallucinated
            if hallucinated:
                constraint.provenance.confidence = 0.0

    return extraction

