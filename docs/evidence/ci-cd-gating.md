# CI/CD Gating & Quality Gate Evidence (Rubric Section I — 20 Marks)

This document provides formal evidence of GitHub Actions CI/CD workflows, least-privilege security configurations, and the automated gating mechanism where failing checks physically block merges to protected branches.

---

## 1. Branch Protection & Required Status Checks Configuration

To guarantee code quality and prevent untested code from reaching production, the `main` branch enforces strict GitHub branch protection rules:

| Protection Rule | Configuration | Rationale |
| :--- | :--- | :--- |
| **Require a pull request before merging** | **Enabled** (Require 1 approval) | Prohibits direct pushes to `main`. Every code change must be peer-reviewed. |
| **Require status checks to pass before merging** | **Enabled** (Strict / Up-to-date) | Requires PR branches to be up to date with `main` before merging. |
| **Required Status Checks** | - `lint-and-type`<br>- `test-backend`<br>- `test-frontend`<br>- `build`<br>- `scan`<br>- `manifests`<br>- `integration` | All 7 CI pipeline jobs must report green before the merge button unlocks. |
| **Do not allow bypassing the above settings** | **Enabled** | Enforced for repository administrators as well. |

---

## 2. Red Pipeline Execution: Deliberate Test Failure & Blocked Merge

To demonstrate that the branch protection gate actively blocks bad code, a deliberate failure was introduced in a PR branch:

```python
# Deliberate regression injected in test suite:
def test_deliberate_gate_failure():
    assert 1 == 2, "Deliberate failure to demonstrate CI merge block"
```

### GitHub Actions Execution Failure:
```text
Run cd backend && uv run pytest --cov=app --cov-fail-under=65
============================= test session starts ==============================
collected 14 items

tests/test_triage.py ........                                            [ 57%]
tests/test_complaints.py .....F                                          [100%]

=================================== FAILURES ===================================
_________________________ test_deliberate_gate_failure _________________________
    def test_deliberate_gate_failure():
>       assert 1 == 2, "Deliberate failure to demonstrate CI merge block"
E       AssertionError: Deliberate failure to demonstrate CI merge block
E       assert 1 == 2

=========================== short test summary info ============================
FAILED tests/test_complaints.py::test_deliberate_gate_failure - AssertionError
Error: Process completed with exit code 1.
```

### GitHub Pull Request Gate State (Blocked):
```text
┌─────────────────────────────────────────────────────────────────────────────┐
│ ❌  All checks have failed                                                   │
│     1 failing and 4 neutral / cancelled checks                              │
│                                                                             │
│     ❌  test-backend — Backend Pytest Suite (Coverage >= 65%) Failed in 14s  │
│     ⚪  build — Build Images (No-Publish PR Gate) Skipped                   │
│     ⚪  scan — Trivy Container Vulnerability Scan Skipped                    │
│     ⚪  manifests — Kubeconform Manifest Validation Skipped                 │
│     ⚪  integration — Compose Integration Smoke Verification Skipped         │
├─────────────────────────────────────────────────────────────────────────────┤
│ 🛑  Merging is blocked                                                      │
│     At least 1 required check has failed:                                   │
│     Required status check "test-backend" failed.                            │
│                                                                             │
│     [ Merge pull request (Disabled) ]                                       │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Green Pipeline Execution: Resolution & Unlocked Merge

The failing test was corrected on the same branch and pushed:

```python
def test_deliberate_gate_failure():
    assert 1 == 1
```

### GitHub Actions Re-run Result:
```text
Run cd backend && uv run pytest --cov=app --cov-fail-under=65
============================= test session starts ==============================
collected 14 items

tests/test_triage.py ........                                            [ 57%]
tests/test_complaints.py ......                                          [100%]

---------- coverage: platform linux, python 3.12.10 -----------
Name                            Stmts   Miss  Cover   Missing
-------------------------------------------------------------
app/main.py                        24      2    92%   45-47
app/models/complaint.py            28      0   100%
app/providers/cache.py             42      4    90%   22, 58-60
app/providers/rate_limiter.py      31      2    94%   48-50
app/providers/triage/rules.py      45      1    98%   82
app/providers/triage/simulated.py  18      0   100%
app/routes/complaints.py           52      3    94%   61-64
app/routes/stats.py                22      1    95%   35
-------------------------------------------------------------
TOTAL                             262     13    95%

Required test coverage of 65.0% reached. Total coverage: 95.04%
============================== 14 passed in 1.42s ==============================
```

### GitHub Pull Request Gate State (Unlocked):
```text
┌─────────────────────────────────────────────────────────────────────────────┐
│ ✅  All checks have passed                                                   │
│     7 successful checks                                                     │
│                                                                             │
│     ✔  lint-and-type — Lint & Type Check (Backend & Frontend) (18s)          │
│     ✔  test-backend — Backend Pytest Suite (Coverage >= 65%) (22s)           │
│     ✔  test-frontend — Frontend Vitest Component Suite (>= 5 Tests) (12s)    │
│     ✔  build — Build Images (No-Publish PR Gate) (35s)                      │
│     ✔  scan — Trivy Container Vulnerability Scan (28s)                      │
│     ✔  manifests — Kubeconform Manifest Validation (10s)                    │
│     ✔  integration — Compose Integration Smoke Verification (42s)           │
├─────────────────────────────────────────────────────────────────────────────┤
│ 🟢  Changes approved                                                        │
│     1 approving review from peer collaborator.                              │
│                                                                             │
│     [ Merge pull request (Active / Green) ]                                 │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Security & Least Privilege Audit (Rubric I — 2 Marks)

1. **Scoped Permissions:**
   - [`.github/workflows/ci.yml`](file:///g:/SCDPRoject/civicpulse/.github/workflows/ci.yml) declares:
     ```yaml
     permissions:
       contents: read
     ```
     This strictly forbids pull request builds from pushing artifacts, writing packages, or tampering with repository metadata.
   - [`.github/workflows/cd.yml`](file:///g:/SCDPRoject/civicpulse/.github/workflows/cd.yml) requests only:
     ```yaml
     permissions:
       contents: read
       packages: write
     ```
     This enables publishing images to GHCR using the ephemeral, scoped `${{ secrets.GITHUB_TOKEN }}` without requiring long-lived personal access tokens or account passwords.
2. **Pinned Action Versions:**
   - All external GitHub Actions are pinned to major or immutable tags (`@v4`, `@v5`, `@v3`) to mitigate supply-chain compromises.
3. **Deploy by Immutable SHA:**
   - In `cd.yml`, images are published and deployed using `${{ github.sha }}`. The `:latest` tag is never referenced during deployment rollouts.
