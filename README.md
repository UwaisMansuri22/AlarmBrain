# AlarmBrain

AI-powered incident analysis for CloudWatch alarms. Transforms raw alerts into structured incident briefs with probable cause, immediate actions, and healthcare business impact.

Built from 4+ years of production on-call experience in regulated healthcare.

---

## What It Does

CloudWatch alarm → Classify → Analyze with Claude → Store → Notify ServiceNow

**Input:** Raw CloudWatch alarm JSON  
**Output:** Structured incident brief with severity (P1-P4), probable cause, immediate actions, and escalation criteria

---

## Example

**Input:** Lambda throttling alarm

**Output:**
```json
{
  "incident_id": "INC-ABC123",
  "severity": "P2",
  "probable_cause": "Lambda function hit concurrency limit during peak window. Reserved concurrency set too low.",
  "immediate_actions": [
    "Check SQS queue depth — if > 100K, escalate to P1",
    "Increase Lambda reserved concurrency from 500 to 1000",
    "Query RDS for slow queries via CloudWatch"
  ],
  "healthcare_impact": "Insurance quote requests failing for end users",
  "escalate_if": "Queue depth exceeds 100K or throttling continues 15+ minutes"
}
```

---

## Quick Start

```bash
git clone https://github.com/UwaisMansuri22/AlarmBrain.git
cd AlarmBrain
pip install -r requirements.txt

export CLAUDE_API_KEY="sk-..."
python3 -m uvicorn app.main:app --reload

curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d @tests/fixtures/lambda_throttle.json
```

---

## Project Structure

**Core Application**

- `app/main.py` — FastAPI app with Lambda handler
- `app/models.py` — Pydantic data schemas
- `app/classifier.py` — Identifies alarm type across 8 AWS services
- `app/analyzer.py` — Claude API integration for incident analysis
- `app/storage.py` — S3 storage with local fallback
- `app/notifier.py` — ServiceNow webhook payload formatting
- `app/prompts/` — Domain-specific prompts encoding healthcare operational knowledge

**Infrastructure & Testing**

- `infra/` — Terraform for Lambda, SNS, S3 deployment
- `simulator/` — CLI tool to publish test alarms
- `tests/` — Test fixtures and unit tests

---

## API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/analyze` | Analyze a single alarm |
| POST | `/webhook/sns` | SNS trigger from CloudWatch |
| GET | `/incidents/{year}/{month}/{day}` | Retrieve incidents by date |
| GET | `/health` | Health check |

---

## Testing

```bash
python3 simulator/publish_alarm.py --type lambda_throttle
python3 simulator/publish_alarm.py --list
pytest tests/ -v
```

---

## Tech Stack

FastAPI + Mangum · Claude API · S3 · Python 3.9+

---

## Author

**Uwais Mansuri**  
Cloud Platform & SRE Engineer

[Portfolio](https://uwaismansuri.com) | [LinkedIn](https://linkedin.com/in/uwais-mansuri) | [GitHub](https://github.com/UwaisMansuri22)

License: MIT
