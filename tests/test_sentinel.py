"""Tests for Slack AI Sentinel telemetry client."""

from unittest.mock import patch, MagicMock
from src.monitoring.sentinel import SlackSentinel, init_sentinel, report_error


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
