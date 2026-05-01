#!/usr/bin/env python3
"""
AlarmBrain Alarm Simulator

Publishes realistic test alarms to SNS topic so you can test the full pipeline
without waiting for real CloudWatch alarms.

Usage:
    python simulator/publish_alarm.py --type lambda_throttle
    python simulator/publish_alarm.py --type sqs_depth_high --region us-west-2
    python simulator/publish_alarm.py --list

Examples:
    # Publish Lambda throttle alarm
    python simulator/publish_alarm.py --type lambda_throttle
    
    # Publish SQS depth alarm to different region
    python simulator/publish_alarm.py --type sqs_depth_high --region us-west-2
    
    # List all available alarm types
    python simulator/publish_alarm.py --list
"""

import json
import argparse
import sys
from pathlib import Path

import boto3


# Map alarm types to fixture files
ALARM_TYPES = {
    "lambda_throttle": "lambda_throttle.json",
    "sqs_depth_high": "sqs_depth_high.json",
    "rds_cpu_high": "rds_cpu_high.json",
    "alb_5xx": "alb_5xx.json",
    "ec2_cpu_high": "ec2_cpu_high.json",
}

FIXTURES_DIR = Path(__file__).parent.parent / "tests" / "fixtures"


def load_fixture(alarm_type: str) -> dict:
    """Load a CloudWatch alarm fixture JSON file."""
    fixture_path = FIXTURES_DIR / ALARM_TYPES.get(alarm_type)
    
    if not fixture_path.exists():
        raise FileNotFoundError(
            f"Fixture not found: {fixture_path}\n"
            f"Available types: {', '.join(ALARM_TYPES.keys())}"
        )
    
    with open(fixture_path, "r") as f:
        return json.load(f)


def publish_alarm(
    alarm_type: str,
    region: str = "us-east-1",
    topic_arn: str = None
) -> str:
    """
    Publish a test alarm to SNS.
    
    Args:
        alarm_type: Type of alarm (lambda_throttle, sqs_depth_high, etc.)
        region: AWS region
        topic_arn: SNS topic ARN (if not provided, constructs from environment)
    
    Returns:
        Message ID of published alarm
    """
    
    # Load fixture
    print(f"📋 Loading {alarm_type} fixture...")
    alarm_payload = load_fixture(alarm_type)
    
    # Get SNS topic ARN if not provided
    if not topic_arn:
        # Try to get from environment variable
        import os
        topic_arn = os.getenv("SNS_TOPIC_ARN")
        if not topic_arn:
            print("\n⚠️  SNS_TOPIC_ARN not set. Please set it:")
            print("   export SNS_TOPIC_ARN='arn:aws:sns:us-east-1:123456789012:alarmbrain-alarms'")
            sys.exit(1)
    
    # Publish to SNS
    sns = boto3.client("sns", region_name=region)
    
    try:
        print(f"📤 Publishing to SNS topic: {topic_arn}")
        response = sns.publish(
            TopicArn=topic_arn,
            Message=json.dumps(alarm_payload),
            Subject=f"AlarmBrain Test: {alarm_type.replace('_', ' ').title()}"
        )
        
        message_id = response["MessageId"]
        print(f"✅ Published successfully!")
        print(f"   Message ID: {message_id}")
        print(f"   Alarm Type: {alarm_type}")
        print(f"   Region: {region}")
        print(f"\n💡 Check your Lambda logs or S3 incident_history folder in ~5 seconds")
        
        return message_id
    
    except Exception as e:
        print(f"❌ Error publishing alarm: {e}")
        print("\nMake sure you have AWS credentials configured:")
        print("   aws configure")
        sys.exit(1)


def list_alarm_types():
    """List all available alarm types."""
    print("Available alarm types:\n")
    for alarm_type in ALARM_TYPES.keys():
        print(f"  • {alarm_type}")
    print(f"\nUsage: python simulator/publish_alarm.py --type <al