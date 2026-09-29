# CivicPulse Operations Runbook

## 1. System Overview & Architecture
CivicPulse runs as five cooperating services:
- **Frontend:** Nginx serving React 18 SPA (Port 80/5173).
- **Backend:** FastAPI + Uvicorn ASGI application (Port 8000).
- **Database:** PostgreSQL 16 on persistent volume `pgdata` (Port 5432).
- **Cache & Limiter:** Redis 7 with AOF on volume `redisdata` (Port 6379).
- **AI Triage:** Hosted LLM (Groq/Gemini) or local containerized Ollama (`llama3.2:1b`).

---

## 2. Deployment Procedures

### Local Development (Docker Compose)
```bash
# 1. Clone & environment setup
git clone https://github.com/stackmussa/civicpulse.git
cd civicpulse
cp .env.example .env

# 2. Boot development stack with hot-reload
docker compose up -d

# 3. Apply database migrations
docker compose exec backend alembic upgrade head

# 4. Seed sample complaints (idempotent)
docker compose exec backend python scripts/seed.py

# 5. Verify system health & readiness
curl -i http://localhost:8000/health
curl -i http://localhost:8000/ready
```

### Production Deployment (Kubernetes via Kustomize)
```bash
# 1. Apply namespace and production overlays
kubectl apply -k k8s/overlays/prod

# 2. Monitor rollout status
kubectl rollout status deployment/backend -n civicpulse --timeout=120s
kubectl rollout status deployment/frontend -n civicpulse --timeout=120s

# 3. Check pods and HPA status
kubectl get pods -n civicpulse
kubectl get hpa -n civicpulse
```

---

## 3. Rollback Procedures

### Rapid Emergency Rollback (Imperative — 3 a.m. Response)
If a bad deployment is active and degrading traffic:
```bash
# Immediately undo to the prior revision
kubectl rollout undo deployment/backend -n civicpulse
kubectl rollout undo deployment/frontend -n civicpulse

# Verify rollback status
kubectl rollout status deployment/backend -n civicpulse
```

### Declarative Rollback (Auditable — Post-Incident Fix)
Once immediate stability is restored, reconcile Git with production:
```bash
# Re-apply the manifest targeting the prior stable Git SHA
git checkout <PREVIOUS_STABLE_SHA>
kubectl apply -k k8s/overlays/prod
```

---

## 4. Reading Structured JSON Logs

CivicPulse emits structured JSON lines exclusively to `stdout`. Every log line includes `timestamp`, `level`, `request_id`, `logger`, and message metadata.

```bash
# Stream live backend logs with pretty-printed JSON
kubectl logs -n civicpulse deploy/backend -f | jq .

# Filter for warnings and errors only
kubectl logs -n civicpulse deploy/backend -f | jq 'select(.level=="WARNING" or .level=="ERROR")'

# Trace a specific request by X-Request-ID
kubectl logs -n civicpulse deploy/backend | jq 'select(.request_id=="<UUID>")'
```

---

## 5. Troubleshooting Triage Failures

If complaints are failing to classify or latency spikes:

### Step 1: Check Telemetry Endpoint
Inspect `/api/meta/providers` to view active provider and recent outcomes:
```bash
curl http://localhost:8000/api/meta/providers | jq .
```
- If `fallback: true` is climbing, the cloud LLM is degraded, timing out (>10s), or rate-limited.
- Note: The system automatically falls back to `RuleBasedTriage` (`triaged_by: rules:fallback`), so citizens will never receive 500 errors.

### Step 2: Check API Keys and Rate Limits
- Inspect Redis rate limiter: `docker compose exec redis redis-cli KEYS "civicpulse:ratelimit:*"`
- Check if your Groq/Gemini free-tier token quota has been exhausted.

### Step 3: Switch to Offline Triage Mode
If the cloud provider is down, switch to local rule-based or Ollama triage without downtime:
```bash
# In .env or Kubernetes ConfigMap:
TRIAGE_PROVIDER=rules
# Or for local offline AI:
TRIAGE_PROVIDER=ollama
```
Restart backend pods to reload configuration:
```bash
kubectl rollout restart deployment/backend -n civicpulse
```
