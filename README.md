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

## Architecture
app/
├── main.py           # FastAPI + Lambda handler
├── models.py         # Pydantic schemas
├── classifier.py     # Alarm type detection
├── analyzer.py       # Claude API integration
├── storage.py        # S3 storage
├── notifier.py       # ServiceNow webhook
└── prompts/          # Domain-specific LLM prompts
infra/               # Terraform
simulator/           # Test alarm publisher
tests/               # Fixtures + tests

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

**Runtime:** FastAPI + Mangum  
**LLM:** Claude API  
**Storage:** S3 with local fallback  
**Language:** Python 3.9+

---

## Author

**Uwais Mansuri**  
Cloud Platform & SRE Engineer

[Portfolio](https://uwaismansuri.com) | [LinkedIn](https://linkedin.com/in/uwais-mansuri) | [GitHub](https://github.com/UwaisMansuri22)

License: MIT
