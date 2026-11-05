"""Tests for Slack AI Sentinel telemetry client and zero-server notifier."""

from unittest.mock import patch, MagicMock
from src.monitoring.sentinel import SlackSentinel, init_sentinel, report_error
from src.monitoring.slack_notifier import dispatch_to_slack, generate_ai_diagnosis


def test_slack_sentinel_report_error_success():
    sentinel = SlackSentinel("https://mock-slack-sentinel.vercel.app")

    with patch("requests.post") as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        success = sentinel.report_error(
            error=ValueError("Invalid room size"),
            route="/test",
            metadata={"source": "pytest"},
        )

        assert success is True
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert args[0] == "https://mock-slack-sentinel.vercel.app/api/telemetry/error"
        payload = kwargs["json"]
        assert payload["message"] == "Invalid room size"
        assert payload["route"] == "/test"
        assert payload["metadata"]["source"] == "pytest"


def test_slack_sentinel_empty_url_returns_false():
    sentinel = SlackSentinel("")
    success = sentinel.report_error("some error")
    assert success is False


def test_init_and_global_report_error():
    init_sentinel("https://bot.example.com")
    with patch("requests.post") as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        success = report_error("Global incident alert")
        assert success is True


def test_dispatch_to_slack_direct_webhook():
    webhook = "https://hooks.slack.com/services/T00/B00/XXXXX"
    with patch("requests.post") as mock_post, patch("src.monitoring.slack_notifier.generate_ai_diagnosis") as mock_diag:
        mock_diag.return_value = "• Cause: API rate limit\n• Fix: Wait 60s"
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_post.return_value = mock_resp

        ok = dispatch_to_slack(
            error=RuntimeError("503 Overloaded"),
            webhook_url=webhook,
            route="/streamlit",
        )
        assert ok is True
        mock_post.assert_called_once()
        payload = mock_post.call_args[1]["json"]
        assert "blocks" in payload
        # Ensure header and AI diagnosis are present in Slack blocks
        block_text = str(payload["blocks"])
        assert "🚨 Elyra AI Pipeline: Error Incident Alert" in block_text
        assert "503 Overloaded" in block_text
