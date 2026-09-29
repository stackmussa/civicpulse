# AI Assistance Disclosure (§5.5)

In accordance with course policy (§5.5), this document transparently details the utilization of AI tools during the development of CivicPulse.

---

## 1. Tools Employed
- **Antigravity AI (Google DeepMind)**
- **Claude / Gemini / Groq API models**

---

## 2. Components Shaped or Assisted by AI
1. **Pydantic Validation & Triage Schema Design:**
   - AI tools were utilized to generate initial boilerplate models for `TriageResult` and FastAPI exception overrides.
   - *Manual Verification & Modification:* Manually restricted field lengths (140 char summary cap, 10–2000 char complaint length constraint) to match strict PostgreSQL DB-level check constraints.
2. **Idempotent Seed Complaints Generation:**
   - Generated initial realistic Urdu-English complaint phrasing reflecting authentic municipal scenarios across Islamabad, Rawalpindi, and Lahore.
   - *Manual Verification:* Audited categories to guarantee balanced distribution across `water`, `electricity`, `roads`, `sanitation`, and `streetlights`. Derived deterministic UUIDv5 hashes from complaint texts to guarantee idempotency.
3. **K6 Load Testing Multi-Stage Script:**
   - AI drafted the ramp-up stages for k6.
   - *Manual Verification:* Adjusted request distribution ratios (40% cached stats, 30% list, 30% complaint triage) to realistically simulate load on Redis and CPU.

---

## 3. Independent Verification & Team Ownership
Every architectural decision, state transition table, Kubernetes manifest probe configuration, and Docker isolation rule was verified, tested, and understood by both team members (**Mussa Raza** and **Nisar Ahmad**) for oral defense at the course viva.
