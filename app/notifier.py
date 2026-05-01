import json
from app.models import IncidentBrief


class SNOWNotifier:
    """
    Notifies ServiceNow about the incident brief.
    
    In production: calls ServiceNow REST API to create/update tickets
    For this project: logs the payload so you can see what would be sent
    
    The payload schema is identical to what the real ServiceNow API expects.
    """
    
    def __init__(self, webhook_url: str = None):
        """
        Args:
            webhook_url: ServiceNow webhook endpoint (not used in mock mode)
        """
        self.webhook_url = webhook_url
    
    def notify(self, brief: IncidentBrief) -> dict:
        """
        Send incident brief to ServiceNow.
        
        In production, this would POST to the ServiceNow REST API.
        For demo/testing, we log the payload and return it.
        """
        
        # Build the ServiceNow ticket payload
        payload = self._build_snow_payload(brief)
        
        # In production: POST to webhook_url
        # For now: log it so recruiter can see the schema
        print("\n" + "=" * 70)
        print("SERVICENOW WEBHOOK PAYLOAD")
        print("=" * 70)
        print(json.dumps(payload, indent=2))
        print("=" * 70 + "\n")
        
        return payload
    
    def _build_snow_payload(self, brief: IncidentBrief) -> dict:
        """
        Build the ServiceNow ticket payload from an IncidentBrief.
        
        This schema matches ServiceNow's incident REST API.
        """
        
        severity_map = {
            "P1": "1",  # Critical
            "P2": "2",  # High
            "P3": "3",  # Medium
            "P4": "4",  # Low
        }
        
        return {
            "short_description": f"[{brief.severity}] {brief.alarm_name}",
            "description": self._build_description(brief),
            "urgency": severity_map.get(brief.severity, "3"),
            "impact": severity_map.get(brief.severity, "3"),
            "assignment_group": "Cloud Platform - On-Call",
            "category": "Cloud Infrastructure",
            "subcategory": "AWS Monitoring",
            "cmdb_ci": brief.alarm_type,
            "u_alarm_id": brief.incident_id,
            "u_probable_cause": brief.probable_cause,
            "u_healthcare_impact": brief.healthcare_impact,
            "u_runbook": brief.runbook_reference,
            "u_immediate_actions": "\n".join(brief.immediate_actions),
            "u_escalate_if": brief.escalate_if,
        }
    
    def _build_description(self, brief: IncidentBrief) -> str:
        """Build the ticket description from incident brief."""
        
        lines = [
            f"Incident ID: {brief.incident_id}",
            f"Generated: {brief.generated_at}",
            f"Alarm Type: {brief.alarm_type}",
            f"Severity: {brief.severity}",
            "",
            "PROBABLE CAUSE:",
            brief.probable_cause,
            "",
            "AFFECTED SERVICES:",
            "\n".join(f"- {svc}" for svc in brief.affected_services),
            "",
            "IMMEDIATE ACTIONS:",
            "\n".join(f"{i}. {action}" for i, action in enumerate(brief.immediate_actions, 1)),
            "",
            "HEALTHCARE IMPACT:",
            brief.healthcare_impact,
            "",
            "ESCALATE IF:",
            brief.escalate_if,
            "",
            "RUNBOOK REFERENCE:",
            brief.runbook_reference,
        ]
        
        return "\n".join(lines)