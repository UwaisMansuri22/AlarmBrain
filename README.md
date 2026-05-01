# AlarmBrain

**AI-powered incident intelligence for on-call engineers.**

Transform raw CloudWatch alarms into actionable incident briefs — probable cause, immediate actions, and healthcare business impact — in seconds.

Built by someone who has resolved 500+ production incidents in regulated healthcare environments.

---

## The Problem

It's 2am. A CloudWatch alarm fires. You have minutes to understand what's wrong and what to do. The alarm tells you *something broke*. It doesn't tell you *why* or *what to do about it*.

On-call engineers waste precious minutes digging through metrics, logs, and past incidents trying to piece together context that should exist automatically.

---

## The Solution

**AlarmBrain** analyzes every CloudWatch alarm using:

1. **Intelligent Classification** — Identifies which AWS service is failing (Lambda, SQS, RDS, DynamoDB, OpenSearch, API Gateway)
2. **Domain-Specific Analysis** — Claude AI powered by 4+ years of healthcare platform operations
3. **Structured Output** — Incident brief with severity, probable cause, affected services, immediate actions, and escalation criteria
4. **ServiceNow Integration** — Enriches tickets automatically so on-call engineers have answers waiting

---

## How It Works
CloudWatch Alarm
↓
SNS Topic
↓
Lambda (AlarmBrain)
↓
Classify → Analyze → Store → Notify
↓
On-call Engineer Gets:

Incident ID
P1/P2/P3/P4 Severity
Why it happened (probable cause)
What to do first (immediate actions)
Who it affects (healthcare impact)
When to escalate


---

## Example Output

**Input:** Lambda throttle alarm during peak hours

**Output:**
```json
{
  "incident_id": "INC-ABC123",
  "severity": "P2",
  "probable_cause": "Lambda quote-processor-prod hit concurrency limit during 2-4pm EST peak window. Likely cause: reserved concurrency set too low or slow RDS queries holding connections.",
  "affected_services": ["quote-processor-prod", "SQS", "RDS"],
  "immediate_actions": [
    "Check SQS queue depth — if > 100K, escalate to P1",
    "Check Lambda reserved concurrency — increase from 500 to 1000 if headroom exists",
    "Query RDS for long-running queries via CloudWatch metrics"
  ],
  "healthcare_impact": "Insurance quote requests failing for end users during peak afternoon submission window",
  "escalate_if": "Queue depth exceeds 100K or throttling continues beyond 15 minutes",
  "runbook_reference": "RBK-LAMBDA-THROTTLE-001"
}
```

---

## Quick Start

### Prerequisites

- Python 3.9+
- AWS credentials configured (`aws configure`)
- Claude API key

### Local Testing (No AWS Required)

1. **Clone and setup:**
```bash
git clone https://github.com/UwaisMansuri22/AlarmBrain.git
cd AlarmBrain
pip install -r requirements.txt
export CLAUDE_API_KEY="your-api-key-here"
```

2. **Start the API:**
```bash
python3 -m uvicorn app.main:app --reload
```

3. **Test with a sample alarm:**
```bash
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d @tests/fixtures/lambda_throttle.json
```

You get back a structured incident brief in seconds.

---

## Project Structure
alarmbrain/
├── app/
│   ├── main.py              # FastAPI app + Lambda handler
│   ├── models.py            # Pydantic schemas
│   ├── classifier.py        # Alarm classification
│   ├── analyzer.py          # Claude API integration
│   ├── storage.py           # S3 storage
│   ├── notifier.py          # ServiceNow webhook
│   └── prompts/             # Domain-specific LLM prompts
│
├── infra/                   # Terraform (coming soon)
├── simulator/               # Test alarm publisher
├── tests/                   # Fixtures + tests
└── README.md

---

## The Prompts Are the Secret

The value of AlarmBrain comes from prompts in `app/prompts/`. They encode real operational knowledge:

- **Healthcare context** — understands patient impact
- **Cigna patterns** — knows which alarm combinations cascade
- **Diagnostic sequences** — step-by-step diagnosis
- **Severity heuristics** — when P1 vs P2 vs P3

Built from 4+ years of production on-call experience.

---

## API Endpoints

### POST `/analyze`
Test endpoint — analyze a single alarm

### POST `/webhook/sns`
Production endpoint — SNS trigger for Lambda

### GET `/incidents/{year}/{month}/{day}`
Retrieve incidents by date

### GET `/health`
Health check

---

## Testing

### Publish Test Alarms
```bash
python3 simulator/publish_alarm.py --type lambda_throttle
python3 simulator/publish_alarm.py --list
```

### Run Tests
```bash
pytest tests/ -v
```

---

## What This Proves (For Recruiting)

✅ Production-grade Python (FastAPI, Pydantic)
✅ AWS expertise (Lambda, SNS, S3)
✅ LLM integration (prompt engineering, structured outputs)
✅ SRE mindset (operational patterns, incident analysis)
✅ Shipping working code (local testing, deployment-ready)
✅ Healthcare domain knowledge (compliance, business impact)

---

## Author

**Uwais Mansuri**  
Cloud Platform & SRE Engineer | Healthcare Systems | AWS  

[Portfolio](https://uwaismansuri.com) · [LinkedIn](https://linkedin.com/in/uwais-mansuri) · [GitHub](https://github.com/UwaisMansuri22)

---

## License

MIT
