"""Factory that instantiates the active triage provider from TRIAGE_PROVIDER."""

from __future__ import annotations

from app.core.config import settings
from app.schemas.triage import TriageProvider


def get_triage_provider() -> TriageProvider:
    """Return the provider indicated by the TRIAGE_PROVIDER setting."""
    name = settings.TRIAGE_PROVIDER.lower()

    if name in ("llm", "groq"):
        from app.providers.triage.llm import LLMTriage

        return LLMTriage()
    elif name == "ollama":
        from app.providers.triage.ollama import OllamaTriage

        return OllamaTriage()
    elif name == "simulated":
        from app.providers.triage.simulated import SimulatedTriage

        return SimulatedTriage()
    elif name == "simulated:fail":
        from app.providers.triage.simulated import SimulatedTriage

        return SimulatedTriage(fail=True)
    else:
        # Default to rules-based — always available, never fails
        from app.providers.triage.rules import RuleBasedTriage

        return RuleBasedTriage()
