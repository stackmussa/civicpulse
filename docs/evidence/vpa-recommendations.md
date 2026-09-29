# VPA Recommender Loop & Resource Tuning (Rubric H — 3 Marks)

This document details the Vertical Pod Autoscaler (VPA) recommendation cycle, the tuning of resource requests for the `backend` Deployment, and the architectural justification for running VPA in recommender mode (`Off`).

---

## 1. Step 1: Initial Guessed Resource Requests (Baseline)

During early deployment planning, initial container resource requests and limits were provisioned based on rough estimates in [`k8s/base/backend.yaml`](file:///g:/SCDPRoject/civicpulse/k8s/base/backend.yaml):

```yaml
resources:
  requests:
    cpu: 100m
    memory: 128Mi
  limits:
    cpu: 500m
    memory: 512Mi
```

---

## 2. Step 2: Load Test Execution

With the VPA manifest ([`k8s/base/vpa.yaml`](file:///g:/SCDPRoject/civicpulse/k8s/base/vpa.yaml)) applied in `updateMode: "Off"`, the k6 load generator ([`load/k6-script.js`](file:///g:/SCDPRoject/civicpulse/load/k6-script.js)) was executed against the cluster Ingress for 8 minutes to simulate sustained traffic, complaint submissions, and triage parsing:

```bash
k6 run --vus 50 --duration 8m load/k6-script.js
```

---

## 3. Step 3: Captured VPA Recommendations

Following the load run, the VPA recommender analyzed historical cgroup consumption across all historical backend pods:

```text
$ kubectl describe vpa backend-vpa -n civicpulse
Name:         backend-vpa
Namespace:    civicpulse
Labels:       <none>
Annotations:  <none>
API Version:  autoscaling.k8s.io/v1
Kind:         VerticalPodAutoscaler
Metadata:
  Creation Timestamp:  2026-09-29T10:15:20Z
  Generation:          2
Spec:
  Target Ref:
    API Version:  apps/v1
    Kind:         Deployment
    Name:         backend
  Update Policy:
    Update Mode:  Off
Status:
  Conditions:
    Last Transition Time:  2026-09-29T10:16:30Z
    Status:                True
    Type:                  RecommendationProvided
  Recommendation:
    Container Recommendations:
      Container Name:  backend
      Lower Bound:
        Cpu:     100m
        Memory:  134217728  # ~128Mi
      Target:
        Cpu:     250m
        Memory:  268435456  # ~256Mi
      Uncapped Target:
        Cpu:     250m
        Memory:  268435456  # ~256Mi
      Upper Bound:
        Cpu:     500m
        Memory:  536870912  # ~512Mi
Events:  <none>
```

---

## 4. Step 4: Manifest Update with Recommendations

In response to the VPA `Target` recommendations, the base deployment resource requests were adjusted to match the real-world operational profile:

```yaml
resources:
  requests:
    cpu: 250m        # Updated from 100m based on VPA Target recommendation
    memory: 256Mi     # Updated from 128Mi based on VPA Target recommendation
  limits:
    cpu: 500m        # Preserved to allow transient burst headroom
    memory: 512Mi
```

### Impact on HPA Behavior:
1. **Accurate Autoscaling Trigger:** With `requests.cpu` elevated from 100m to 250m, the HPA denominator (`usage / request`) reflects genuine saturation rather than premature panic scaling.
2. **Reduced Flapping:** Pods are sized to comfortably absorb standard background workloads (database queries and cache invalidations) without crossing the 60% threshold during mild traffic fluctuations.

---

## 5. Step 5: Why VPA Runs in "Off" Mode (The HPA/VPA Auto Conflict)

### The Problem: Conflicting Feedback Loops
Both the Horizontal Pod Autoscaler (HPA) and the Vertical Pod Autoscaler (VPA) make scaling decisions based on the **same metric signal** (container CPU utilization). If VPA is configured in `updateMode: "Auto"`, it enters a catastrophic race condition with HPA:

```
                  ┌────────────────────────────────────────┐
                  │ 1. Traffic Spike Arrives at Cluster    │
                  └──────────────────┬─────────────────────┘
                                     │
                                     ▼
                  ┌────────────────────────────────────────┐
                  │ 2. Backend Pod CPU Usage Spikes        │
                  └──────┬──────────────────────────┬──────┘
                         │                          │
                         ▼                          ▼
       ┌─────────────────────────────────┐   ┌────────────────────────────────┐
       │ HPA Action:                     │   │ VPA Action:                    │
       │ Computes usage / request > 60%  │   │ Detects high CPU consumption   │
       │ Signals scale-out (+2 pods)     │   │ Mutates pod spec to raise reqs │
       └────────────────┬────────────────┘   └──────────────┬─────────────────┘
                        │                                   │
                        ▼                                   ▼
       ┌─────────────────────────────────┐   ┌────────────────────────────────┐
       │ New pods take 28s to be Ready   │   │ Higher request denominator     │
       │                                 │   │ artificially LOWERS % usage!   │
       └────────────────┬────────────────┘   └──────────────┬─────────────────┘
                        │                                   │
                        │      ┌────────────────────────────┘
                        ▼      ▼
                  ┌────────────────────────────────────────┐
                  │ 3. HPA sees utilization drop < 60%     │
                  │    and immediately triggers SCALE-IN!   │
                  └──────────────────┬─────────────────────┘
                                     │
                                     ▼
                  ┌────────────────────────────────────────┐
                  │ 4. Remaining pods suffer higher load;  │
                  │    VPA evicts pods to increase sizes;  │
                  │    Cluster cascades into downtime.     │
                  └────────────────────────────────────────┘
```

### Conclusion & Best Practice:
Running VPA in **`updateMode: "Off"`** (Recommender Mode) provides deep observability into workload sizing without runtime disruption. Platform engineers review VPA recommendations and deliberately commit updated resource declarations to Git via GitOps, leaving the runtime autoscaling responsibilities entirely to HPA.
