"""Pure Python Slack AI Sentinel Notifier.

Zero-server, embedded AI error diagnostic & Slack incident dispatcher.
Captures exceptions, asks Gemini for root-cause diagnosis, and posts directly to Slack Webhook.
"""

import os
import sys
import traceback
import requests
from typing import Optional, Dict, Any
from loguru import logger

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None
    types = None


def generate_ai_diagnosis(error_message: str, stack_trace: str, api_key: Optional[str] = None) -> str:
    """Invoke Gemini to generate a 3-bullet concise diagnosis & remediation advice."""
    key = api_key or os.getenv("GEMINI_API_KEY")
    if not key or not genai:
        return "• AI diagnosis unavailable (No Gemini API Key provided)."

    try:
        client = genai.Client(api_key=key)
        prompt = (
            f"You are an SRE AI Diagnostic Agent for an architectural data engineering pipeline.\n"
            f"An exception just occurred in our Streamlit application.\n\n"
            f"ERROR: {error_message}\n\n"
            f"STACK TRACE:\n{stack_trace[:1500]}\n\n"
            f"Please provide:\n"
            f"1. Root cause summary (1 sentence)\n"
            f"2. Practical immediate remediation step (1 sentence)\n"
            f"Keep the entire response under 4 lines."
        )

        response = client.models.generate_content(
            model="gemini-3.8-flash",
            contents=prompt,
        )
        return response.text.strip()
    except Exception as e:
        logger.warning(f"Could not generate AI diagnosis: {e}")
        return f"• Automated AI diagnosis could not complete: {e}"


def dispatch_to_slack(
    error: Exception | str,
    webhook_url: Optional[str] = None,
    stack_trace: Optional[str] = None,
    route: str = "/streamlit",
    gemini_api_key: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> bool:
    """Send structured incident alert with automated AI diagnosis to Slack."""
    target_url = webhook_url or os.getenv("SLACK_WEBHOOK_URL")
    if not target_url:
        logger.warning("[SlackNotifier] No Slack Webhook URL provided. Skipping notification.")
        return False

    try:
        error_str = str(error)
        if not stack_trace and isinstance(error, Exception):
            stack_trace = "".join(traceback.format_exception(type(error), error, error.__traceback__))

        # Generate Gemini AI diagnosis
        ai_diagnosis = generate_ai_diagnosis(error_str, stack_trace or "", api_key=gemini_api_key)

        # Build Slack Block Kit payload
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "🚨 Elyra AI Pipeline: Error Incident Alert",
                    "emoji": True,
                },
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Service:*\nElyra Data Engine"},
                    {"type": "mrkdwn", "text": f"*Route:*\n`{route}`"},
                ],
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*❌ Error Message:*\n```{error_str[:300]}```",
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*🤖 Gemini AI Diagnosis:*\n{ai_diagnosis}",
                },
            },
        ]

        if stack_trace:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Stack Trace Snippet:*\n```{stack_trace[-600:]}```",
                },
            })

        payload = {"blocks": blocks}
        logger.info(f"[SlackNotifier] Sending incident alert to Slack Webhook...")
        res = requests.post(target_url, json=payload, timeout=5)

        if res.status_code == 200:
            logger.success("[SlackNotifier] Alert successfully posted to Slack!")
            return True
        else:
            logger.warning(f"[SlackNotifier] Slack API returned status {res.status_code}: {res.text}")
            return False
    except Exception as e:
        logger.error(f"[SlackNotifier] Failed to dispatch incident to Slack: {e}")
        return False
