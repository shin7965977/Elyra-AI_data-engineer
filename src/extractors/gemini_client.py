"""Production Gemini 3.8 Flash Client with structured outputs and resilience."""

import json
import os
from typing import Optional
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None
    types = None

from src.models.canonical import BuildingRequirementsExtraction
from src.extractors.protocol import LLMClientProtocol
from src.extractors.prompt import EXTRACTION_SYSTEM_PROMPT


class GoogleGenAIClient(LLMClientProtocol):
    """Production client calling Google GenAI API with Gemini 3.8 Flash."""

    def __init__(self, api_key: Optional[str] = None, model_name: str = "gemini-3.8-flash"):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model_name = model_name
        if not self.api_key:
            logger.warning("No GEMINI_API_KEY provided. Calls to GoogleGenAIClient will fail unless mocked or configured.")

        self._client = None
        if genai and self.api_key:
            self._client = genai.Client(api_key=self.api_key)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    def extract(self, transcript: str) -> BuildingRequirementsExtraction:
        if not self._client:
            if not self.api_key:
                raise ValueError("Missing Gemini API Key. Provide api_key or set GEMINI_API_KEY in environment.")
            if not genai:
                raise ImportError("google-genai package is not installed.")
            self._client = genai.Client(api_key=self.api_key)

        logger.info(f"Invoking {self.model_name} for requirement extraction ({len(transcript)} chars)...")

        prompt = (
            f"Here is the raw customer conversation/requirements text:\n"
            f"\"\"\"\n{transcript}\n\"\"\"\n\n"
            f"Extract all architectural requirements, spaces, constraints, and exact verbatim quotes strictly following the schema."
        )

        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=BuildingRequirementsExtraction,
            system_instruction=EXTRACTION_SYSTEM_PROMPT,
            temperature=0.0,
        )

        response = self._client.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config=config,
        )

        raw_json = response.text
        logger.debug(f"Received raw JSON response: {raw_json[:300]}...")

        # Parse and validate with Pydantic
        data = json.loads(raw_json)
        return BuildingRequirementsExtraction.model_validate(data)

