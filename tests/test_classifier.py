import pytest
from app.models import AlarmPayload
from app.classifier import classify_alarm, get_alarm_type_description


def make_alarm(metric_name: str, namespace: str, alarm_name: str = "test-alarm") -> AlarmPayload:
    """Helper to create test alarms quickly."""
    return AlarmPayload(**{
        "AlarmName": alarm_name,
        "AlarmDescription": "Test alarm",
        "AWSAccountId": "123456789012",
        "NewStateValue": "ALARM",
        "NewStateReason": "Threshold crossed",
        "StateChangeTime": "2024-01-15T14:03:15.123Z",
        "Region": "us-east-1",
        "Trigger": {
            "MetricName": metric_name,
            "Namespace": namespace,
            "Statistic": "Sum",
            "Dimensions": [{"name": "FunctionName", "value": "test-function"}],
            "Period": 60,
            "Threshold": 100.0,
            "ComparisonOperator": "GreaterThanThreshold"
        }
    })


class TestLambdaAlarms:
    def test_lambda_throttle(self):
        alarm = make_alarm("Throttles", "AWS/Lambda")
        assert classify_alarm(alarm) == "lambda_throttle"

    def test_lambda_errors(self):
        alarm = make_alarm("Errors", "AWS/Lambda")
        assert classify_alarm(alarm) == "lambda_error"


class TestSQSAlarms:
    def test_sqs_depth(self):
        alarm = make_alarm("ApproximateNumberOfMessagesVisible", "AWS/SQS")
        assert classify_alarm(alarm) == "sqs_depth_high"

    def test_sqs_message_age(self):
        alarm = make_alarm("ApproximateAgeOfOldestMessage", "AWS/SQS")
        assert classify_alarm(alarm) == "sqs_message_age_high"


class TestRDSAlarms:
    def test_rds_cpu(self):
        alarm = make_alarm("CPUUtilization", "AWS/RDS")
        assert classify_alarm(alarm) == "rds_cpu_high"

    def test_rds_connections(self):
        alarm = make_alarm("DatabaseConnections", "AWS/RDS")
        assert classify_alarm(alarm) == "rds_connections_exhausted"

    def test_rds_latency(self):
        alarm = make_alarm("ReadLatency", "AWS/RDS")
        assert classify_alarm(alarm) == "rds_latency_high"


class TestAPIGatewayAlarms:
    def test_apigw_5xx(self):
        alarm = make_alarm("5XXError", "AWS/ApiGateway")
        assert classify_alarm(alarm) == "alb_5xx"

    def test_apigw_4xx(self):
        alarm = make_alarm("4XXError", "AWS/ApiGateway")
        assert classify_alarm(alarm) == "apigateway_4xx"


class TestDynamoDBAlarms:
    def test_dynamo_write_throttle(self):
        alarm = make_alarm("ConsumedWriteCapacityUnits", "AWS/DynamoDB")
        assert classify_alarm(alarm) == "dynamodb_write_throttle"

    def test_dynamo_read_throttle(self):
        alarm = make_alarm("ConsumedReadCapacityUnits", "AWS/DynamoDB")
        assert classify_alarm(alarm) == "dynamodb_read_throttle"


class TestOpenSearchAlarms:
    def test_opensearch_memory(self):
        alarm = make_alarm("JVMMemoryPressure", "AWS/ES")
        assert classify_alarm(alarm) == "opensearch_memory_high"

    def test_opensearch_health(self):
        alarm = make_alarm("ClusterHealthStatus", "AWS/ES")
        assert classify_alarm(alarm) == "opensearch_unhealthy"


class TestUnknownAlarms:
    def test_unknown_returns_unknown(self):
        alarm = make_alarm("SomeRandomMetric", "AWS/SomeService")
        assert classify_alarm(alarm) == "unknown"


class TestDescriptions:
    def test_description_exists_for_known_type(self):
        desc = get_alarm_type_description("lambda_throttle")
        assert len(desc) > 0
        assert desc != "Unknown alarm type"

    def test_description_for_unknown(self):
        desc = get_alarm_type_description("unknown")
        assert "manual" in desc.lower() or "unknown" in desc.lower()
