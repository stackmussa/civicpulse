#!/usr/bin/env python3
"""Submission Pre-Flight Check Script for CivicPulse (Assignment 1).

Catches mechanical failures and automatic deduction triggers (§5.3):
- .env tracked in git (-20)
- Unpinned base images (-8)
- Published database/cache ports in compose.prod.yaml (-8)
- :latest tags deployed in Kubernetes manifests (-8)
- GitHub Actions publish/deploy jobs missing 'needs:' (-8)
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def check_git_env() -> list[str]:
    """Check if .env is tracked in git."""
    issues = []
    try:
        res = subprocess.run(
            ["git", "ls-files", ".env"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        if res.stdout.strip():
            issues.append("CRITICAL: .env file is tracked in git repository! (-20 deduction)")
    except Exception as e:
        issues.append(f"Warning: unable to check git status: {e}")
    return issues


def check_dockerfiles() -> list[str]:
    """Check that Dockerfile base images are pinned and not using unpinned/latest tags."""
    issues = []
    dockerfiles = list(ROOT.glob("**/Dockerfile"))
    for df in dockerfiles:
        content = df.read_text(encoding="utf-8")
        for line in content.splitlines():
            line = line.strip()
            if line.upper().startswith("FROM "):
                image = line.split()[1]
                if image.startswith("--platform"):
                    image = line.split()[2]
                if ":" not in image or image.endswith(":latest"):
                    issues.append(
                        f"Deduction risk in {df.relative_to(ROOT)}: "
                        f"Unpinned base image '{image}' (must pin version or digest, -8 deduction)"
                    )
    return issues


def check_compose_prod() -> list[str]:
    """Check that compose.prod.yaml does not publish DB or Redis ports and has no build: keys."""
    issues = []
    compose_prod = ROOT / "compose.prod.yaml"
    if not compose_prod.exists():
        return issues

    content = compose_prod.read_text(encoding="utf-8")
    if "build:" in content:
        issues.append("compose.prod.yaml should not contain 'build:' keys (must use immutable image tags)")

    # Check for published DB or redis ports in prod
    in_postgres = False
    in_redis = False
    for line in content.splitlines():
        trimmed = line.strip()
        if trimmed.startswith("postgres:"):
            in_postgres = True
            in_redis = False
        elif trimmed.startswith("redis:"):
            in_redis = True
            in_postgres = False
        elif trimmed.startswith("ports:") and (in_postgres or in_redis):
            service = "postgres" if in_postgres else "redis"
            issues.append(
                f"Deduction risk: Published port found on {service} in compose.prod.yaml (-8 deduction)"
            )
    return issues


def check_k8s_manifests() -> list[str]:
    """Check Kubernetes manifests for :latest image tags and placeholder secrets."""
    issues = []
    k8s_dir = ROOT / "k8s"
    if not k8s_dir.exists():
        return issues

    for yml in k8s_dir.glob("**/*.yaml"):
        content = yml.read_text(encoding="utf-8")
        for line in content.splitlines():
            trimmed = line.strip()
            if trimmed.startswith("image:") and trimmed.endswith(":latest"):
                issues.append(
                    f"Deduction risk in {yml.relative_to(ROOT)}: "
                    f"Deploying :latest tag in Kubernetes manifest (-8 deduction)"
                )
    return issues


def check_workflows() -> list[str]:
    """Check that publish/deploy jobs in GitHub workflows have 'needs:' gates."""
    issues = []
    wf_dir = ROOT / ".github" / "workflows"
    if not wf_dir.exists():
        return issues

    cd_file = wf_dir / "cd.yml"
    if cd_file.exists():
        content = cd_file.read_text(encoding="utf-8")
        if "build-push:" in content and "needs:" not in content.split("build-push:")[1].split("\n\n")[0]:
            issues.append("cd.yml: build-push job must have a 'needs:' gate on test (-8 deduction)")
        if "deploy-k8s:" in content and "needs:" not in content.split("deploy-k8s:")[1].split("\n\n")[0]:
            issues.append("cd.yml: deploy-k8s job must have a 'needs:' gate on build-push (-8 deduction)")
    return issues


def main() -> int:
    print("=" * 60)
    print("CivicPulse Submission Pre-Flight Lint (Assignment 1 §5.3)")
    print("=" * 60)

    checks = [
        ("Git Secret Hygiene (.env)", check_git_env),
        ("Dockerfile Base Image Pinning", check_dockerfiles),
        ("Production Compose Security", check_compose_prod),
        ("Kubernetes Manifest Declarations", check_k8s_manifests),
        ("CI/CD Workflow Gating", check_workflows),
    ]

    total_issues = 0
    for name, check_fn in checks:
        print(f"\n[+] Checking: {name}...")
        issues = check_fn()
        if issues:
            for issue in issues:
                print(f"  [X] {issue}")
                total_issues += 1
        else:
            print("  [OK] Passed")

    print("\n" + "=" * 60)
    if total_issues == 0:
        print("[SUCCESS] Pre-flight check PASSED cleanly! Zero deduction triggers found.")
        print("=" * 60)
        return 0
    else:
        print(f"[WARNING] Found {total_issues} issue(s) that must be resolved.")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())
