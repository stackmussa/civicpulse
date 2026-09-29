"""Triage result schema and provider Protocol used by all triage implementations."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from pydantic import BaseModel, Field

from app.models.complaint import Category, Priority


class TriageResult(BaseModel):
    """Structured output from any triage provider."""

    category: Category
    priority: Priority
    summary: str = Field(max_length=140)
    confidence: float = Field(ge=0.0, le=1.0)


@runtime_checkable
class TriageProvider(Protocol):
    """Interface that every triage implementation must satisfy."""

    name: str

    async def triage(self, text: str, location: str) -> TriageResult: ...
