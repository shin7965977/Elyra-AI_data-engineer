"""Slack AI Sentinel - Python & Streamlit Client SDK.

Telemetry client for reporting errors and incident diagnostics to Slack AI Sentinel.
Repository: https://github.com/shin7965977/slack-ai-sentinel
"""

import os
import sys
import traceback
import requests
from typing import Optional, Callable, Dict, Any
from functools import wraps
from loguru import logger


class SlackSentinel:
    def __init__(self, endpoint_url: str, service_name: str = "Elyra AI Data Engine"):
        self.endpoint_url = endpoint_url.rstrip("/")
        self.service_name = service_name

    def report_error(
        self,
        error: Exception | str,
        stack_trace: Optional[str] = None,
        route: str = "/streamlit",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Report an error or exception directly to the Slack Sentinel Telemetry API."""
        if not self.endpoint_url:
            return False

        try:
            error_message = str(error)
            if not stack_trace and isinstance(error, Exception):
                stack_trace = "".join(traceback.format_exception(type(error), error, error.__traceback__))

            payload = {
                "message": error_message,
                "stack": stack_trace or "",
                "route": route,
                "userAgent": f"{self.service_name} (Python {sys.version.split()[0]})",
                "fingerprint": f"elyra-{abs(hash(error_message)) % 1000000:x}",
            }

            if metadata:
                payload["metadata"] = metadata

            target_url = self.endpoint_url
            if not target_url.endswith("/api/telemetry/error"):
                target_url = f"{target_url}/api/telemetry/error"

            logger.info(f"[SlackSentinel] Dispatching error incident to {target_url}...")
            res = requests.post(target_url, json=payload, timeout=5)
            if res.status_code == 200:
                logger.success("[SlackSentinel] Incident successfully reported to Slack AI Sentinel!")
                return True
            else:
                logger.warning(f"[SlackSentinel] Received status code {res.status_code}: {res.text}")
                return False
        except Exception as e:
            logger.warning(f"[SlackSentinel] Failed to report incident to Slack: {e}")
            return False

    def guard(self, route: str = "/"):
        """Decorator to wrap function executions with automatic incident reporting."""
        def decorator(func: Callable):
            @wraps(func)
            def wrapper(*args, **kwargs):
                try:
                    return func(*args, **kwargs)
                except Exception as exc:
                    self.report_error(exc, route=route)
                    raise exc
            return wrapper
        return decorator


# Default global instance helper
_default_sentinel: Optional[SlackSentinel] = None


def init_sentinel(
    endpoint_url: Optional[str] = None,
    service_name: str = "Elyra AI Data Engine",
) -> Optional[SlackSentinel]:
    """Initialize the global Slack Sentinel client using parameter or environment variable."""
    global _default_sentinel
    url = endpoint_url or os.getenv("SLACK_SENTINEL_URL")
    if not url:
        return None

    _default_sentinel = SlackSentinel(url, service_name)
    return _default_sentinel


def get_sentinel() -> Optional[SlackSentinel]:
    return _default_sentinel


def report_error(
    error: Exception | str,
    route: str = "/",
    stack_trace: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> bool:
    if not _default_sentinel:
        return False
    return _default_sentinel.report_error(error, stack_trace=stack_trace, route=route, metadata=metadata)
