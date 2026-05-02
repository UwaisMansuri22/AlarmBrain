import json
import os
from pathlib import Path
import anthropic
from dotenv import load_dotenv

from app.models import AlarmPayload, AlarmType, IncidentBrief
from app.classifier import classify_alarm, get_alarm_type_description

load_dotenv(Path(__file__).parent.parent / "tests" / "fixtures" / ".env")


class IncidentAnalyzer:
    """
    Takes a classified alarm and uses Claude to generate a structured incident brief.

    Design:
    - Load domain-specific prompts (encodes 4 years of operational knowledge)
    - Call Claude API with alarm context
    - Parse structured JSON response
    - Return IncidentBrief object
    """

    def __init__(self):
        self.client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.prompts_dir = Path(__file__).parent / "prompts"
        self.system_prompt = self._load_prompt("system.txt")
    
    def _load_prompt(self, filename: str) -> str:
        """Load a prompt file from app/prompts/"""
        path = self.prompts_dir / filename
        if not path.exists():
            raise FileNotFoundError(f"Prompt file not found: {path}")
        return path.read_text()
    
    def analyze(self, alarm: AlarmPayload) -> IncidentBrief:
        """
        Main entry point: classify alarm, load domain context, call Claude, return brief.
        """
        
        # Step 1: Classify the alarm
        alarm_type = classify_alarm(alarm)
        alarm_description = get_alarm_type_description(alarm_type)
        
        # Step 2: Load domain-specific prompt for this alarm type
        domain_prompt = self._get_domain_prompt(alarm_type)
        
        # Step 3: Build the full user message with alarm context
        user_message = self._build_user_message(alarm, alarm_type, alarm_description, domain_prompt)
        
        # Step 4: Call Claude
        response = self._call_claude(user_message)
        
        # Step 5: Parse response and create IncidentBrief
        brief = self._parse_response(response, alarm, alarm_type)
        
        return brief
    
    def _get_domain_prompt(self, alarm_type: AlarmType) -> str:
        """Load the domain-specific prompt for this alarm type."""
        prompt_map = {
            "lambda_throttle": "lambda_throttle.txt",
            "lambda_timeout": "lambda_throttle.txt",  # Reuse Lambda prompt
            "lambda_error": "lambda_throttle.txt",
            "sqs_depth_high": "sqs_depth_high.txt",
            "sqs_message_age_high": "sqs_depth_high.txt",
            "rds_cpu_high": "rds_cpu_high.txt",
            "rds_connections_exhausted": "rds_cpu_high.txt",
            "rds_latency_high": "rds_cpu_high.txt",
            "alb_5xx": "alb_5xx.txt",
            "apigateway_4xx": "alb_5xx.txt",
        }
        
        filename = prompt_map.get(alarm_type)
        if not filename:
            # For unknown types, return a generic fallback
            return "Analyze this alarm and determine probable cause, affected services, and remediation steps."
        
        return self._load_prompt(filename)
    
    def _build_user_message(
        self,
        alarm: AlarmPayload,
        alarm_type: AlarmType,
        alarm_description: str,
        domain_prompt: str
    ) -> str:
        """Construct the full prompt to send to Claude."""
        
        return f"""
DOMAIN CONTEXT:
{domain_prompt}

ALARM DETAILS:
Alarm Name: {alarm.alarm_name}
Alarm Type: {alarm_type} ({alarm_description})
AWS Account: {alarm.aws_account_id}
Region: {alarm.region}
Timestamp: {alarm.state_change_time}

Metric: {alarm.trigger.metric_name}
Namespace: {alarm.trigger.namespace}
Current State Reason: {alarm.new_state_reason}
Threshold: {alarm.trigger.threshold}
Comparison: {alarm.trigger.comparison_operator}

Affected Resource Dimensions:
{json.dumps([d.model_dump() for d in alarm.trigger.dimensions], indent=2)}

Now analyze this alarm. Respond ONLY with a valid JSON object matching this exact schema:
{{
  "severity": "P1 or P2 or P3 or P4",
  "probable_cause": "One sentence explanation",
  "affected_services": ["service1", "service2"],
  "immediate_actions": ["Step 1", "Step 2", "Step 3"],
  "healthcare_impact": "How this affects patients/claims",
  "escalate_if": "Condition for escalation",
  "runbook_reference": "RBK-NAME or 'none'"
}}

Do not include markdown. Do not include any text outside the JSON object.
"""
    
    def _call_claude(self, user_message: str) -> str:
        """Call Claude API and return the response text."""
        
        message = self.client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system=self.system_prompt,
            messages=[
                {"role": "user", "content": user_message}
            ]
        )
        
        return message.content[0].text
    
    def _parse_response(
        self,
        response: str,
        alarm: AlarmPayload,
        alarm_type: AlarmType
    ) -> IncidentBrief:
        """Parse Claude's JSON response into an IncidentBrief object."""
        
        try:
            # Claude should return pure JSON
            data = json.loads(response)
        except json.JSONDecodeError as e:
            # If parsing fails, return a fallback brief
            print(f"Failed to parse Claude response: {e}")
            print(f"Raw response: {response}")
            data = {
                "severity": "P2",
                "probable_cause": "Unknown — LLM analysis failed",
                "affected_services": [alarm.trigger.namespace],
                "immediate_actions": ["Check CloudWatch logs", "Contact on-call lead"],
                "healthcare_impact": "Service degradation possible",
                "escalate_if": "No improvement in 5 minutes",
                "runbook_reference": "none"
            }
        
        # Create IncidentBrief from Claude's response
        brief = IncidentBrief(
            alarm_name=alarm.alarm_name,
            alarm_type=alarm_type,
            severity=data.get("severity", "P3"),
            probable_cause=data.get("probable_cause", "Unknown"),
            affected_services=data.get("affected_services", []),
            immediate_actions=data.get("immediate_actions", []),
            healthcare_impact=data.get("healthcare_impact", "Unknown"),
            escalate_if=data.get("escalate_if", "Unknown"),
            runbook_reference=data.get("runbook_reference", "none")
        )
        
        return brief