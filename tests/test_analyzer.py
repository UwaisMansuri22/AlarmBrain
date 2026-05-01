import pytest
import json
from unittest.mock import MagicMock, patch
from app.models import AlarmPayload, IncidentBrief
from app.analyzer import IncidentAnalyzer


def make_lambda_alarm() -> AlarmPayload:
    return AlarmPayload(**{
        "AlarmName": "quote-processor-throttles-high",
        "AlarmDescription": "Lambda throttling detected",
        "AWSAccountId": "123456789012",
        "NewStateValue": "ALARM",
        "NewStateReason": "Threshold Crossed: 450 throttles",
        "StateChangeTime": "2024-01-15T14:03:15.123Z",
        "Region": "us-east-1",
        "Trigger": {
            "MetricName": "Throttles",
            "Namespace": "AWS/Lambda",
            "Statistic": "Sum",
            "Dimensions": [{"name": "FunctionName", "value": "quote-processor-prod"}],
            "Period": 60,
            "Threshold": 100.0,
            "ComparisonOperator": "GreaterThanThreshold"
        }
    })


MOCK_CLAUDE_RESPONSE = json.dumps({
    "severity": "P2",
    "probable_cause": "Lambda concurrency limit reached during peak load",
    "affected_services": ["quote-processor-prod", "SQS"],
    "immediate_actions": [
        "Check reserved concurrency",
        "Check SQS queue depth",
        "Review RDS connections"
    ],
    "healthcare_impact": "Insurance quote requests failing for end users",
    "escalate_if": "Throttles exceed 1000 in 5 minutes",
    "runbook_reference": "RBK-LAMBDA-THROTTLE-001"
})


class TestIncidentAnalyzer:

    @patch("app.analyzer.anthropic.Anthropic")
    def test_analyze_returns_incident_brief(self, mock_anthropic):
        # Mock Claude API response
        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client
        mock_message = MagicMock()
        mock_message.content[0].text = MOCK_CLAUDE_RESPONSE
        mock_client.messages.create.return_value = mock_message

        analyzer = IncidentAnalyzer()
        alarm = make_lambda_alarm()
        brief = analyzer.analyze(alarm)

        assert isinstance(brief, IncidentBrief)
        assert brief.severity == "P2"
        assert brief.alarm_type == "lambda_throttle"
        assert brief.alarm_name == "quote-processor-throttles-high"
        assert len(brief.immediate_actions) == 3
        assert brief.runbook_reference == "RBK-LAMBDA-THROTTLE-001"

    @patch("app.analyzer.anthropic.Anthropic")
    def test_analyze_generates_incident_id(self, mock_anthropic):
        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client
        mock_message = MagicMock()
        mock_message.content[0].text = MOCK_CLAUDE_RESPONSE
        mock_client.messages.create.return_value = mock_message

        analyzer = IncidentAnalyzer()
        alarm = make_lambda_alarm()
        brief = analyzer.analyze(alarm)

        assert brief.incident_id.startswith("INC-")
        assert len(brief.incident_id) > 4

    @patch("app.analyzer.anthropic.Anthropic")
    def test_analyze_handles_bad_json_gracefully(self, mock_anthropic):
        # Claude returns malformed JSON — should fall back gracefully
        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client
        mock_message = MagicMock()
        mock_message.content[0].text = "This is not JSON"
        mock_client.messages.create.return_value = mock_message

        analyzer = IncidentAnalyzer()
        alarm = make_lambda_alarm()
        brief = analyzer.analyze(alarm)

        # Should still return a brief, not crash
        assert isinstance(brief, IncidentBrief)
        assert brief.severity == "P2"  # fallback default
