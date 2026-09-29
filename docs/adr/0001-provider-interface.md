# ADR 0001: Triage Provider Protocol and Factory Abstraction

## Status
Accepted

## Context
Every municipal intake platform requires automated classification to route citizen complaints effectively. However, the triage engine cannot be coupled to a single vendor or static heuristic. The system must support:
1. Fast, high-accuracy inference in production (hosted LLMs like Groq).
2. Offline, zero-data-leakage execution (containerized Ollama).
3. Instant deterministic fallback when cloud providers are degraded or rate-limited (`RuleBasedTriage`).
4. Hermetic, reproducible CI test suites that never make network calls or incur flaky delays (`SimulatedTriage`).

## Decision
We adopted Python's structural subtyping (`typing.Protocol` with `@runtime_checkable`) to define the `TriageProvider` interface:
```python
class TriageProvider(Protocol):
    name: str
    async def triage(self, text: str, location: str) -> TriageResult: ...
```
Providers are instantiated via a factory pattern (`get_triage_provider()`) keyed by the `TRIAGE_PROVIDER` environment variable.

## Consequences
- **Loose Coupling:** Routes and services depend exclusively on the abstract contract, never on concrete vendor SDKs.
- **Resilience:** If an external LLM fails, times out (10s cap), or throws a 429, the system automatically falls back to `RuleBasedTriage` without bubbling a 500 error to the citizen.
- **Determinism:** CI pipelines pin `TRIAGE_PROVIDER=simulated`, guaranteeing 100% green test passes with zero network dependency.
