# ADR 0004: PII Governance and Hosted LLM Data Privacy

## Status
Accepted

## Context
Citizen complaints submitted to municipal platforms frequently contain sensitive Personally Identifiable Information (PII), including:
- Citizen names and phone numbers
- Specific residential street addresses and apartment numbers
- Details regarding private domestic disputes or sensitive property damage

Free-tier hosted LLM providers have distinct data retention and training policies:
1. **Google AI Studio (Gemini Free Tier):** Google's terms state that prompts submitted on non-paid tiers may be reviewed by human annotators and utilized to train future models.
2. **Groq Developer Tier:** Groq does not retain prompt payloads for model training, operating solely as an inference accelerator.
3. **Ollama:** Self-hosted on-premises container. Zero network egress; zero external data leakage.

## Decision
We enforce a multi-layered data governance policy:
1. **PII Isolation:** The backend data model strictly segregates `reporter_contact` from `complaint_text`.
2. **Sanitized Payload Delivery:** Under no circumstances is `reporter_contact` (phone number, email) ever included in the prompt payload sent to hosted LLM endpoints. Only sanitized complaint text and general sector location are transmitted for classification.
3. **Primary Hosted Provider (Groq):** Groq is selected as the default primary provider for cloud triage due to its non-training privacy policy and sub-second inference speeds.
4. **Offline Zero-Leakage Mode (Ollama):** For sensitive municipal environments, CivicPulse provides a fully offline `OllamaTriage` container (`llama3.2:1b`) operating within the isolated Docker network with zero internet routing.

## Consequences
- **Privacy Compliance:** Contact details are protected in PostgreSQL and never leak to external cloud providers.
- **Architectural Flexibility:** Municipalities with strict data residency laws can seamlessly switch `TRIAGE_PROVIDER=ollama` without any application refactoring.
