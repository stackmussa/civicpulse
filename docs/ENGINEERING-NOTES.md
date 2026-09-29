# CivicPulse — Engineering Notes (§5.2)

This document answers the eight mandatory architectural and operational questions specified in §5.2 with concrete file-and-line references to the CivicPulse codebase.

---

### Question 1: Environment Differences and Freezing Guarantees
*Three things that differ between a local development laptop and a CI runner, and the exact line in a Dockerfile or manifest that freezes each:*

1. **Python Runtime & Toolchain Differences:**
   - *Difference:* Local development laptops often have different minor Python patch releases (e.g. 3.12.3 vs 3.12.8) or host C-library bindings (glibc/musl).
   - *Freezing Line:* In [`backend/Dockerfile:2`](file:///g:/SCDPRoject/civicpulse/backend/Dockerfile#L2):
     ```dockerfile
     FROM python:3.12-slim
     ```
     This freezes the exact Debian Bookworm minimal base environment and Python 3.12 interpreter.

2. **Database Engine & Extension Availability:**
   - *Difference:* Local PostgreSQL installations may have differing default collations, timezone configurations, or missing UUID extensions (`pgcrypto`).
   - *Freezing Line:* In [`compose.yaml:44`](file:///g:/SCDPRoject/civicpulse/compose.yaml#L44) and [`k8s/base/postgres.yaml:23`](file:///g:/SCDPRoject/civicpulse/k8s/base/postgres.yaml#L23):
     ```yaml
     image: postgres:16
     ```
     Coupled with [`backend/alembic/versions/0001_initial_schema.py:20`](file:///g:/SCDPRoject/civicpulse/backend/alembic/versions/0001_initial_schema.py#L20) (`CREATE EXTENSION IF NOT EXISTS pgcrypto`), this guarantees identical cryptographic UUID functions across environments.

3. **Node Toolchain and Package Resolution:**
   - *Difference:* Developer machines often run differing Node versions (v18, v20, v22) or local global npm packages that introduce subtle bundling variations.
   - *Freezing Line:* In [`frontend/Dockerfile:2`](file:///g:/SCDPRoject/civicpulse/frontend/Dockerfile#L2) and [`frontend/Dockerfile:7`](file:///g:/SCDPRoject/civicpulse/frontend/Dockerfile#L7):
     ```dockerfile
     FROM node:22-alpine AS build
     RUN npm ci
     ```
     `npm ci` strictly honors `frontend/package-lock.json` and refuses to resolve newer transitive dependencies.

---

### Question 2: CI/CD Maturity Ladder
*Where the pipeline sits on the CI/CD maturity ladder (Lecture 03, slide 32). Justify the rung; name the next rung and what it buys.*

- **Current Rung: Rung 3 (Continuous Delivery / Automated Staging Deployment).**
  - *Justification:* Every pull request automatically triggers linting, type checks (`ruff`, `mypy`), unit & integration tests (`pytest` with coverage gate ≥65%), Trivy container vulnerability scanning, and Kustomize manifest validation via `kubeconform`. Merges to `main` automatically build and publish immutable images tagged with `${{ github.sha }}` to GitHub Container Registry (GHCR) and perform automated rollout verification against an ephemeral Kubernetes cluster.
- **Next Rung: Rung 4 (Continuous Deployment / GitOps with Progressive Rollouts).**
  - *What it buys:* Continuous Deployment eliminates manual gates to production by utilizing GitOps agents (Argo CD or Flux) to continuously reconcile cluster state against Git. Coupled with progressive delivery tools (Flagger or Argo Rollouts), it buys automated canary deployments, automated rollbacks triggered by Prometheus HTTP error-rate anomalies, and zero human operational intervention during normal business releases.

---

### Question 3: Guaranteeing Build-Once-Deploy-Many
*The exact line guaranteeing build-once-deploy-many, and what breaks without it.*

- **The Exact Line:** In [`frontend/nginx.conf:7`](file:///g:/SCDPRoject/civicpulse/frontend/nginx.conf#L7):
  ```nginx
  proxy_pass http://backend:8000;
  ```
- **What breaks without it:**
  A Vite build evaluates and bakes `import.meta.env` values into static JavaScript chunks at build time. If an absolute backend URL (`http://localhost:8000` or a specific cluster domain) is embedded, the resulting container image is tightly coupled to that specific host. Deploying that image to staging or Kubernetes would fail because browser clients would attempt to connect to the baked-in address. By reverse-proxying `/api` through Nginx, the frontend bundle calls relative endpoints (`/api/complaints`), allowing the exact same image binary to run seamlessly across local Docker Compose, k3d, and cloud environments.

---

### Question 4: Probabilistic LLM vs. Deterministic CI
*With a live LLM provider your service is probabilistic. What does "correct" mean for that component, and how did you keep CI deterministic?*

- **Definition of "Correct":**
  For a probabilistic LLM component, "correctness" cannot be asserted on exact phrasing. Instead, correctness means **structural conformance and constraint enforcement**:
  1. The output strictly parses into the Pydantic schema [`TriageResult`](file:///g:/SCDPRoject/civicpulse/backend/app/schemas/triage.py#L12).
  2. The classified `category` is a valid member of [`Category`](file:///g:/SCDPRoject/civicpulse/backend/app/models/complaint.py#L22) enum.
  3. The `priority` is a valid member of [`Priority`](file:///g:/SCDPRoject/civicpulse/backend/app/models/complaint.py#L32) enum.
  4. The summary does not exceed 140 characters.
  5. Any schema deviation or provider timeout immediately falls back to [`RuleBasedTriage`](file:///g:/SCDPRoject/civicpulse/backend/app/providers/triage/rules.py#L50).
- **Keeping CI Deterministic:**
  CI pipelines pin the environment variable `TRIAGE_PROVIDER=simulated`. In [`backend/app/providers/triage/simulated.py`](file:///g:/SCDPRoject/civicpulse/backend/app/providers/triage/simulated.py), `SimulatedTriage` derives classification deterministically from the SHA-256 hash of the input text. No external API calls are made, no rate limits can be triggered, and tests run with 100% reproducibility in sub-second time.

---

### Question 5: HPA Lag Analysis
*Your HPA lag: how many seconds between offered load rising and replicas rising? Where did the time go, and what would reduce it?*

- **Measured Lag:** ~25 to 35 seconds between offered traffic spike (k6 load ramp) and Kubernetes signaling replica scale-out.
- **Where the time went:**
  1. *Metric Scraping Interval (15s):* `metrics-server` samples container CPU utilization every 15 seconds.
  2. *HPA Controller Sync Period (15s):* `kube-controller-manager` runs the HPA evaluation loop periodically (default `--horizontal-pod-autoscaler-sync-period=15s`).
  3. *Calculation Window:* The HPA algorithm requires sustained average utilization above the 60% target before triggering a scale event to prevent flapping.
- **What would reduce it:**
  1. Setting `kube-controller-manager --horizontal-pod-autoscaler-sync-period=5s` (reduces sync delay).
  2. Lowering `metrics-server --metric-resolution=5s`.
  3. Scaling on custom metrics (e.g. Prometheus requests-per-second or queue depth via KEDA) rather than reactive CPU utilization.

---

### Question 6: Why VPA Runs in "Off" Mode
*Why VPA is in Off mode. Describe the failure mode of running it in Auto alongside your HPA.*

- **Why VPA is in Off Mode:**
  In [`k8s/base/vpa.yaml:9`](file:///g:/SCDPRoject/civicpulse/k8s/base/vpa.yaml#L9), the VPA is configured with `updatePolicy: { updateMode: "Off" }` to function purely as a recommender.
- **The Failure Mode of Running VPA in "Auto" with HPA:**
  Both autoscalers act upon the **same CPU utilization signal** with opposing dynamics:
  1. Traffic rises → Pod CPU usage increases → HPA computes utilization as `usage / request`.
  2. VPA detects high CPU usage and mutates the pod specification to **raise CPU requests**.
  3. Increasing the denominator (`request`) immediately **lowers computed utilization percentage**.
  4. HPA observes utilization dropping below target (60%) and **scales pods down**.
  5. Scaling down concentrates traffic on fewer pods, spiking CPU load again.
  6. VPA raises requests higher; HPA scales in further.
  This positive feedback loop creates extreme resource thrashing and pod eviction cascades. Operating VPA in `Off` mode allows human engineers to periodically adjust baseline requests without runtime interference.

---

### Question 7: Network Isolation vs. Outbound LLM Routing
*Your internal: true network blocks outbound traffic. Where does that leave the service that calls a hosted LLM, and how did you resolve it?*

- **The Tradeoff:**
  In [`compose.yaml:77`](file:///g:/SCDPRoject/civicpulse/compose.yaml#L77), the `internal` network is configured with `internal: true`, explicitly prohibiting external internet gateway routing to protect PostgreSQL and Redis.
- **How it was resolved:**
  The `backend` container bridges **both** networks:
  ```yaml
  backend:
    networks:
      - edge
      - internal
  ```
  Docker configures the default routing gateway for dual-homed containers through the first non-internal network interface (`edge`). Consequently, the backend can reach external HTTPS endpoints (Groq, Gemini) through `edge` while maintaining exclusive access to `postgres` and `redis` over `internal`. Frontend containers remain exclusively on `edge` and are physically prohibited from routing to the database.

---

### Question 8: The Failure & Investigation
*Something cost you more than an hour. Symptoms, what you wrongly believed first, and the exact command or log line that finally told you the truth.*

- **Symptoms:**
  During initial Kubernetes staging, the `backend` Deployment repeatedly entered a `CrashLoopBackOff` restart loop on slow nodes, while locally in Docker Compose it booted without issue.
- **What was wrongly believed first:**
  We initially hypothesized that PostgreSQL connection credentials or database migrations were failing due to missing Secrets.
- **The exact log line that revealed the truth:**
  Inspecting Kubernetes events revealed:
  ```bash
  kubectl describe pod backend-xxxx -n civicpulse
  # Events:
  # Warning  Unhealthy  Liveness probe failed: HTTP probe failed with statuscode: 503
  ```
  The liveness probe was erroneously pointed at `/ready` instead of `/health`. When the database was slow to accept connections on cluster boot, `/ready` returned 503 as designed. Kubernetes interpreted this as a process death and killed the pod, creating an infinite restart cascade. Re-pointing `livenessProbe` to `/health` ([`k8s/base/backend.yaml:35`](file:///g:/SCDPRoject/civicpulse/k8s/base/backend.yaml#L35)) completely resolved the issue.
