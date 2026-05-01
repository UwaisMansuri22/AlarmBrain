from app.models import AlarmPayload, AlarmType


def classify_alarm(alarm: AlarmPayload) -> AlarmType:
    """
    Classify a CloudWatch alarm into one of our known types.
    
    Strategy: Check high-frequency alarms first (Lambda throttles, SQS depth),
    then secondary alarms (RDS, API Gateway). Fall back to 'unknown'.
    
    From 4 years at Cigna: these 4 alarm types caused 80% of production incidents.
    Check them in order of frequency.
    """
    
    namespace = alarm.trigger.namespace.lower()
    metric = alarm.trigger.metric_name.lower()
    
    # ── Priority 1: Lambda Throttles (most critical) ────────────────────────
    if namespace == "aws/lambda":
        if "throttles" in metric:
            return "lambda_throttle"
        if "duration" in metric and "exceeded" in alarm.new_state_reason.lower():
            return "lambda_timeout"
        if "errors" in metric:
            return "lambda_error"
    
    # ── Priority 2: SQS Queue Depth (causes cascading failures) ─────────────
    if namespace == "aws/sqs":
        if "approximatenumberofmessagesvisible" in metric or "depth" in metric.lower():
            return "sqs_depth_high"
        if "approximateageofoldestmessage" in metric:
            return "sqs_message_age_high"
    
    # ── Priority 3: RDS Connection + Performance ──────────────────────────
    if namespace == "aws/rds":
        if "databaseconnections" in metric:
            return "rds_connections_exhausted"
        if "cpuutilization" in metric:
            return "rds_cpu_high"
        if "readlatency" in metric or "writelatency" in metric:
            return "rds_latency_high"
    
    # ── Priority 4: API Gateway Errors ───────────────────────────────────
    if namespace == "aws/apigateway":
        if "5xxerror" in metric or "5xx" in metric.lower():
            return "alb_5xx"  # Reuse 5xx handler for both ALB and API Gateway
        if "4xxerror" in metric:
            return "apigateway_4xx"
    
    # ── Secondary: DynamoDB ─────────────────────────────────────────────
    if namespace == "aws/dynamodb":
        if "consumedwritecapacityunits" in metric:
            return "dynamodb_write_throttle"
        if "consumedreadcapacityunits" in metric:
            return "dynamodb_read_throttle"
        if "usererrors" in metric:
            return "dynamodb_user_error"
    
    # ── Secondary: OpenSearch ───────────────────────────────────────────
    if namespace == "aws/es" or "opensearch" in namespace.lower():
        if "jvmemmorypressure" in metric or "memory" in metric.lower():
            return "opensearch_memory_high"
        if "clusterhealthstatus" in metric:
            return "opensearch_unhealthy"
        if "diskspace" in metric.lower():
            return "opensearch_disk_full"
    
    # ── Secondary: EC2 Autoscaling ──────────────────────────────────────
    if namespace == "aws/ec2":
        if "cpu" in metric.lower():
            return "ec2_cpu_high"
        if "statuscheck" in metric.lower():
            return "ec2_status_check_failed"
    
    # ── Catch-all ────────────────────────────────────────────────────────
    return "unknown"


def get_alarm_type_description(alarm_type: AlarmType) -> str:
    """Return a human-readable description of the alarm type."""
    
    descriptions = {
        "lambda_throttle": "Lambda function concurrency limit reached",
        "lambda_timeout": "Lambda function execution exceeded timeout",
        "lambda_error": "Lambda function returned errors",
        "sqs_depth_high": "SQS queue has high message backlog",
        "sqs_message_age_high": "SQS messages aging without processing",
        "rds_connections_exhausted": "RDS connection pool at capacity",
        "rds_cpu_high": "RDS instance CPU utilization high",
        "rds_latency_high": "RDS read/write latency elevated",
        "alb_5xx": "API/ALB returning 5xx errors to clients",
        "apigateway_4xx": "API Gateway returning 4xx errors",
        "dynamodb_write_throttle": "DynamoDB write capacity exhausted",
        "dynamodb_read_throttle": "DynamoDB read capacity exhausted",
        "dynamodb_user_error": "DynamoDB user errors detected",
        "opensearch_memory_high": "OpenSearch JVM memory pressure critical",
        "opensearch_unhealthy": "OpenSearch cluster health degraded",
        "opensearch_disk_full": "OpenSearch disk space critical",
        "ec2_cpu_high": "EC2 instance CPU utilization high",
        "ec2_status_check_failed": "EC2 instance status check failed",
        "unknown": "Unknown alarm type - manual inspection required",
    }
    
    return descriptions.get(alarm_type, "Unknown alarm type")