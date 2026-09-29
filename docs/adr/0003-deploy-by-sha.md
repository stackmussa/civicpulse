# ADR 0003: Immutable Container Deployment by Git Commit SHA

## Status
Accepted

## Context
Deploying software using floating tags such as `:latest` or branch names introduces critical operational risks:
1. **Non-Determinism:** "What version is running in production?" cannot be answered definitively because `:latest` mutates on every push.
2. **Unreliable Rollbacks:** Re-applying a manifest targeting `:latest` pulls whatever was most recently built, not the stable prior release.
3. **Caching Anomalies:** Kubernetes kubelet nodes with `imagePullPolicy: IfNotPresent` will execute stale containers if `:latest` is already present locally.

## Decision
We mandate immutable deployments:
1. Every container image built by our CI/CD pipeline is tagged with the exact 40-character Git commit SHA (`${{ github.sha }}`).
2. While `:latest` may be published for human convenience, it is strictly forbidden in Kubernetes deployment manifests and production Compose configurations (enforced via `scripts/check_submission.py`).
3. Kubernetes manifests use Kustomize image transformers to inject the commit SHA at deployment time:
   ```yaml
   images:
     - name: backend
       newName: ghcr.io/stackmussa/civicpulse-backend
       newTag: ${COMMIT_SHA}
   ```

## Consequences
- **Complete Traceability:** Running `kubectl get deployment backend -o yaml` provides the exact commit hash, enabling instant `git show <sha>` auditability.
- **Instant Rollback:** Rollbacks can be executed imperatively (`kubectl rollout undo`) or declaratively by reapplying the previous commit SHA.
- **Cache Safety:** Nodes always pull and cache immutable layers reliably without risk of stale execution.
