"""Base triage provider — re-exports the Protocol and TriageResult."""

from app.schemas.triage import TriageProvider, TriageResult

__all__ = ["TriageProvider", "TriageResult"]
