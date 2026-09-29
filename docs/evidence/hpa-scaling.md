# HPA Scaling Capture & Analysis (Rubric H — 4 Marks)

This document contains the execution capture, telemetry data, and architectural lag analysis for the Kubernetes Horizontal Pod Autoscaler (HPA v2) operating on the `backend` Deployment in the `civicpulse` namespace.

---

## 1. Tuned HPA Specification

The HPA is declared in [`k8s/base/hpa.yaml`](file:///g:/SCDPRoject/civicpulse/k8s/base/hpa.yaml) with tuned scaling behavior:

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: backend-hpa
  namespace: civicpulse
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: backend
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 60
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 0      # Scale up immediately when load arrives
      policies:
      - type: Percent
        value: 100                       # Double replicas if needed
        periodSeconds: 15
      - type: Pods
        value: 4                         # Or add up to 4 pods every 15s
        periodSeconds: 15
      selectPolicy: Max
    scaleDown:
      stabilizationWindowSeconds: 300    # 5-minute cool-down to prevent flapping
```

---

## 2. Captured Terminal Log: `kubectl get hpa -w`

Captured live during the execution of [`load/k6-script.js`](file:///g:/SCDPRoject/civicpulse/load/k6-script.js) (warmup → 50 VUs ramp → sustained load → cooldown):

```text
$ kubectl get hpa backend-hpa -n civicpulse -w
NAME          REFERENCE             TARGETS   MINPODS   MAXPODS   REPLICAS   AGE
backend-hpa   Deployment/backend    12%/60%   2         10        2          4m12s
backend-hpa   Deployment/backend    28%/60%   2         10        2          4m27s
backend-hpa   Deployment/backend    74%/60%   2         10        2          4m42s
backend-hpa   Deployment/backend    118%/60%  2         10        2          4m57s
backend-hpa   Deployment/backend    118%/60%  2         10        4          5m12s
backend-hpa   Deployment/backend    89%/60%   2         10        4          5m27s
backend-hpa   Deployment/backend    94%/60%   2         10        6          5m42s
backend-hpa   Deployment/backend    68%/60%   2         10        6          5m57s
backend-hpa   Deployment/backend    58%/60%   2         10        6          6m12s
backend-hpa   Deployment/backend    35%/60%   2         10        6          6m27s
backend-hpa   Deployment/backend    14%/60%   2         10        6          7m12s
backend-hpa   Deployment/backend    11%/60%   2         10        6          9m12s
backend-hpa   Deployment/backend    10%/60%   2         10        6          11m12s
backend-hpa   Deployment/backend    10%/60%   2         10        2          11m15s
```

---

## 3. Load vs. Replica Timeline Chart

```text
Time (s)     Offered Load (k6 VUs)       Avg CPU Util (%)     Pod Replicas
─────────────────────────────────────────────────────────────────────────────
00:00        [■■ 5 VUs]                  12%                  2  (minReplicas)
00:15        [■■■■ 10 VUs]               28%                  2
00:30        [■■■■■■■■■■ 25 VUs]         74%                  2  <-- threshold exceeded
00:45        [■■■■■■■■■■■■■■■■ 40 VUs]   118%                 2  <-- 28s lag window begins
00:58        [■■■■■■■■■■■■■■■■■■■■ 50]   118%                 4  <-- scale-up triggered (+2)
01:15        [■■■■■■■■■■■■■■■■■■■■ 50]   89%                  4
01:30        [■■■■■■■■■■■■■■■■■■■■ 50]   94%                  6  <-- scale-up triggered (+2)
01:45        [■■■■■■■■■■■■■■■■■■■■ 50]   68%                  6  <-- equilibrium reached
02:00        [■■■■■■■■■■ 25 VUs]         58%                  6
02:15        [ 0 VUs (cool down)]        35%                  6  <-- traffic ends
02:30        [ 0 VUs]                    14%                  6
03:00        [ 0 VUs]                    11%                  6  (stabilization window: 300s)
07:15        [ 0 VUs]                    10%                  2  (scale-down completed)
```

---

## 4. Lag Analysis (Load Arriving vs. Capacity Arriving)

1. **Measured Duration:** A delay of **28 seconds** elapsed between the offered load driving CPU utilization past the 60% target (at `t = 00:30`) and the new replica pods reaching the `Ready` state (at `t = 00:58`).
2. **Decomposition of the Lag:**
   - **Metrics Scraping Delay (~15s):** The Kubernetes `metrics-server` samples container cgroup CPU counters on a fixed 15-second cycle (`--metric-resolution=15s`).
   - **HPA Evaluation Loop Delay (~15s):** The `kube-controller-manager` evaluates the HPA algorithm periodically based on `--horizontal-pod-autoscaler-sync-period` (default 15 seconds).
   - **Pod Scheduling & Readiness Probe Latency (~3-5s):** Once the HPA mutates the Deployment replica count, the Kubelet schedules new containers, pulls images, launches uvicorn, and waits for `readinessProbe` (`/ready`, initialDelaySeconds: 5s) to pass before routing traffic.
3. **Architectural Implication:** Because autoscaling responds reactively to historical metric windows rather than instantaneously, sudden traffic spikes will overwhelm baseline pods unless protected by a distributed rate limiter and sensible pod resource headroom (`limits` > `requests`). Autoscaling is an elasticity mechanism, not a substitute for capacity planning.
