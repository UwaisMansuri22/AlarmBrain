import json
import os
from fastapi import FastAPI, HTTPException
from mangum import Mangum
import logging

from app.models import AlarmPayload, SNSEvent, IncidentBrief
from app.classifier import classify_alarm
from app.analyzer import IncidentAnalyzer
from app.storage import IncidentStorage
from app.notifier import SNOWNotifier


# ── Setup ─────────────────────────────────────────────────────────────────

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AlarmBrain",
    description="AI-powered incident intelligence for on-call engineers",
    version="0.1.0"
)

analyzer = IncidentAnalyzer()
storage = IncidentStorage()
notifier = SNOWNotifier()


# ── Health check ──────────────────────────────────────────────────────────

@app.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "healthy", "service": "AlarmBrain"}


# ── SNS webhook — CloudWatch alarms come in here ──────────────────────────

@app.post("/webhook/sns")
def handle_sns_event(event: dict):
    """
    Lambda handler for SNS events from CloudWatch alarms.
    
    CloudWatch → SNS Topic → Lambda → this endpoint
    
    The alarm JSON arrives as a string inside SNS message.
    We parse it, classify it, analyze it, store it, notify SNOW.
    """
    
    try:
        # Parse SNS event
        sns_event = SNSEvent(**event)
        
        # Extract the CloudWatch alarm from inside the SNS message
        sns_record = sns_event.Records[0]
        alarm_json_str = sns_record.Sns.Message
        alarm_json = json.loads(alarm_json_str)
        
        # Parse into AlarmPayload
        alarm = AlarmPayload(**alarm_json)
        
        logger.info(f"Received alarm: {alarm.alarm_name}")
        
        # Classify and analyze
        brief = analyzer.analyze(alarm)
        
        logger.info(f"Generated incident brief: {brief.incident_id} ({brief.severity})")
        
        # Store to S3
        s3_key = storage.save(brief)
        logger.info(f"Stored to S3: {s3_key}")
        
        # Notify ServiceNow
        snow_payload = notifier.notify(brief)
        
        return {
            "status": "success",
            "incident_id": brief.incident_id,
            "severity": brief.severity,
            "s3_key": s3_key
        }
    
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse alarm JSON: {e}")
        raise HTTPException(status_code=400, detail="Invalid alarm JSON")
    except Exception as e:
        logger.error(f"Error processing alarm: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Test endpoint — POST a CloudWatch alarm for testing ───────────────────

@app.post("/analyze")
def analyze_alarm(alarm: AlarmPayload):
    """
    Test endpoint: POST a CloudWatch alarm payload and get back the incident brief.
    
    Useful for testing without SNS trigger.
    
    Example:
    curl -X POST http://localhost:8000/analyze \
      -H "Content-Type: application/json" \
      -d @tests/fixtures/lambda_throttle.json
    """
    
    try:
        logger.info(f"Analyzing alarm: {alarm.alarm_name}")
        
        # Analyze
        brief = analyzer.analyze(alarm)
        
        # Store to S3
        s3_key = storage.save(brief)
        
        # Notify SNOW
        snow_payload = notifier.notify(brief)
        
        return {
            "incident_brief": brief.dict(),
            "s3_key": s3_key,
            "snow_payload": snow_payload
        }
    
    except Exception as e:
        logger.error(f"Error analyzing alarm: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Retrieve incidents by date ────────────────────────────────────────────

@app.get("/incidents/{year}/{month}/{day}")
def get_incidents_by_date(year: str, month: str, day: str):
    """
    Retrieve all incidents for a specific date.
    
    Example: GET /incidents/2024/01/15
    """
    
    try:
        incidents = storage.get_incidents_by_date(year, month, day)
        return {
            "date": f"{year}-{month}-{day}",
            "count": len(incidents),
            "incidents": incidents
        }
    except Exception as e:
        logger.error(f"Error retrieving incidents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Retrieve single incident by ID ────────────────────────────────────────

@app.get("/incidents/{year}/{month}/{day}/{incident_id}")
def get_incident(year: str, month: str, day: str, incident_id: str):
    """
    Retrieve a specific incident by ID and date.
    
    Example: GET /incidents/2024/01/15/INC-ABC123
    """
    
    try:
        incident = storage.get_incident_by_id(incident_id, year, month, day)
        if not incident:
            raise HTTPException(status_code=404, detail="Incident not found")
        return incident
    except Exception as e:
        logger.error(f"Error retrieving incident: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── API docs ──────────────────────────────────────────────────────────────

@app.get("/docs")
def docs():
    """FastAPI auto-generated docs at /docs"""
    pass


# ── Lambda handler ────────────────────────────────────────────────────────

# This is what AWS Lambda calls when SNS triggers the function
handler = Mangum(app)


# ── Local testing ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)