"""Production Gemini Client with structured outputs, retry logging, and automatic fallback."""

import json
import os
from typing import Optional
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None
    types = None

from src.models.canonical import BuildingRequirementsExtraction
from src.extractors.protocol import LLMClientProtocol
from src.extractors.prompt import EXTRACTION_SYSTEM_PROMPT


def _log_retry_attempt(retry_state):
    """Callback to log clear retry information before sleeping."""
    exception = retry_state.outcome.exception() if retry_state.outcome else "Unknown error"
    wait_time = retry_state.next_action.sleep if retry_state.next_action else 0
    attempt = retry_state.attempt_number
    logger.warning(
        f"[Retry {attempt}/3] Gemini extraction failed with error: {exception}. "
        f"Waiting {wait_time:.1f}s before next attempt..."
    )


class GoogleGenAIClient(LLMClientProtocol):
    """Production client calling Google GenAI API with primary model and automatic fallback."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: str = "gemini-3.5-flash-lite",
        fallback_model: str = "gemini-2.5-flash-lite",
    ):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model_name = model_name
        self.primary_model = model_name
        self.fallback_model = fallback_model
        if not self.api_key:
            logger.warning("No GEMINI_API_KEY provided. Calls to GoogleGenAIClient will fail unless mocked or configured.")

        self._client = None
        if genai and self.api_key:
            self._client = genai.Client(api_key=self.api_key)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        before_sleep=_log_retry_attempt,
        reraise=True,
    )
    def _call_model(self, model: str, transcript: str) -> str:
        logger.info(f"Invoking {model} for requirement extraction ({len(transcript)} chars)...")

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
            model=model,
            contents=prompt,
            config=config,
        )
        return response.text

    def extract(self, transcript: str) -> BuildingRequirementsExtraction:
        if not self._client:
            if not self.api_key:
                raise ValueError("Missing Gemini API Key. Provide api_key or set GEMINI_API_KEY in environment.")
            if not genai:
                raise ImportError("google-genai package is not installed.")
            self._client = genai.Client(api_key=self.api_key)

        raw_json = None
        # Try Primary Model
        try:
            raw_json = self._call_model(self.primary_model, transcript)
        except Exception as primary_exc:
            if self.fallback_model and self.fallback_model != self.primary_model:
                logger.warning(
                    f"Primary model '{self.primary_model}' exhausted all retries ({primary_exc}). "
                    f"Automatically switching to fallback model '{self.fallback_model}'..."
                )
                try:
                    raw_json = self._call_model(self.fallback_model, transcript)
                except Exception as fallback_exc:
                    logger.error(f"Fallback model '{self.fallback_model}' also failed ({fallback_exc}).")
                    raise fallback_exc from primary_exc
            else:
                raise primary_exc

        logger.debug(f"Received raw JSON response: {raw_json[:300]}...")

        # Parse and validate with Pydantic
        data = json.loads(raw_json)
        return BuildingRequirementsExtraction.model_validate(data)


