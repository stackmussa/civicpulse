"""Prometheus metrics collector and formatter for CivicPulse (§2.2).

Tracks:
- Request count counter (by method, path, status)
- Request latency histogram (buckets: 0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)
- Triage latency histogram (by provider)
- Triage fallback counter (by provider)
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict

_HISTOGRAM_BUCKETS = (0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, float("inf"))

_lock = threading.Lock()
_request_counts: dict[tuple[str, str, int], int] = defaultdict(int)
_request_latencies: dict[str, list[float]] = defaultdict(list)
_triage_latencies: dict[str, list[float]] = defaultdict(list)
_triage_fallbacks: dict[str, int] = defaultdict(int)


def record_request(method: str, path: str, status_code: int, duration_seconds: float) -> None:
    """Record an HTTP request event."""
    # Normalize path to avoid high cardinality
    norm_path = path
    if norm_path.startswith("/api/complaints/") and norm_path != "/api/complaints":
        if "/status" in norm_path:
            norm_path = "/api/complaints/{id}/status"
        else:
            norm_path = "/api/complaints/{id}"

    with _lock:
        _request_counts[(method, norm_path, status_code)] += 1
        _request_latencies[norm_path].append(duration_seconds)


def record_triage(provider: str, duration_seconds: float, is_fallback: bool = False) -> None:
    """Record a triage outcome and latency."""
    with _lock:
        _triage_latencies[provider].append(duration_seconds)
        if is_fallback:
            _triage_fallbacks[provider] += 1


def format_prometheus_metrics() -> str:
    """Render metrics in Prometheus text exposition format."""
    lines: list[str] = []

    with _lock:
        # 1. Request count
        lines.append("# HELP civicpulse_requests_total Total HTTP requests handled")
        lines.append("# TYPE civicpulse_requests_total counter")
        if not _request_counts:
            lines.append('civicpulse_requests_total{method="GET",endpoint="/health",status="200"} 0')
        else:
            for (method, path, status), count in sorted(_request_counts.items()):
                lines.append(
                    f'civicpulse_requests_total{{method="{method}",endpoint="{path}",status="{status}"}} {count}'
                )

        # 2. Request duration histogram
        lines.append("\n# HELP civicpulse_request_duration_seconds HTTP request duration histogram")
        lines.append("# TYPE civicpulse_request_duration_seconds histogram")
        for path, values in sorted(_request_latencies.items()):
            count = len(values)
            total = sum(values)
            for le in _HISTOGRAM_BUCKETS:
                b_count = sum(1 for v in values if v <= le)
                le_str = "+Inf" if le == float("inf") else str(le)
                lines.append(
                    f'civicpulse_request_duration_seconds_bucket{{endpoint="{path}",le="{le_str}"}} {b_count}'
                )
            lines.append(f'civicpulse_request_duration_seconds_sum{{endpoint="{path}"}} {total:.6f}')
            lines.append(f'civicpulse_request_duration_seconds_count{{endpoint="{path}"}} {count}')

        # 3. Triage duration histogram
        lines.append("\n# HELP civicpulse_triage_duration_seconds LLM/rules triage latency in seconds")
        lines.append("# TYPE civicpulse_triage_duration_seconds histogram")
        for provider, values in sorted(_triage_latencies.items()):
            count = len(values)
            total = sum(values)
            for le in _HISTOGRAM_BUCKETS:
                b_count = sum(1 for v in values if v <= le)
                le_str = "+Inf" if le == float("inf") else str(le)
                lines.append(
                    f'civicpulse_triage_duration_seconds_bucket{{provider="{provider}",le="{le_str}"}} {b_count}'
                )
            lines.append(f'civicpulse_triage_duration_seconds_sum{{provider="{provider}"}} {total:.6f}')
            lines.append(f'civicpulse_triage_duration_seconds_count{{provider="{provider}"}} {count}')

        # 4. Fallback counter
        lines.append("\n# HELP civicpulse_triage_fallbacks_total Counter of triage calls that fell back to rules")
        lines.append("# TYPE civicpulse_triage_fallbacks_total counter")
        if not _triage_fallbacks:
            lines.append('civicpulse_triage_fallbacks_total{provider="rules:fallback"} 0')
        else:
            for provider, count in sorted(_triage_fallbacks.items()):
                lines.append(f'civicpulse_triage_fallbacks_total{{provider="{provider}"}} {count}')

    return "\n".join(lines) + "\n"
