# Deliberate Merge Conflict & Resolution Evidence (Rubric Section A — 3 Marks)

## 1. Context & Objective
To satisfy CS4032 Assignment 1 §4 Rubric A:
> *"One deliberate merge conflict on real code, resolved, with markers/resolution/merge evidence and 2–4 sentences on why that version won — 3 marks"*

The conflict was engineered on **production business logic** in [`backend/app/providers/triage/rules.py`](file:///g:/SCDPRoject/civicpulse/backend/app/providers/triage/rules.py) within the `_HIGH_PRIORITY_KEYWORDS` classification array.

---

## 2. Competing Branches & Authors

- **Branch 1 (`feature/priority-rules-v1`)** by **Mussa Raza**:
  - Expanded emergency keywords for monsoon and environmental hazards:
    `"drowning", "hazards", "monsoon", "short-circuit", "waterlogging"`
- **Branch 2 (`feature/priority-rules-v2`)** by **Nisar Ahmad**:
  - Expanded life-safety and urgent Urdu descriptors:
    `"janleva", "emergency call", "blast", "gas leak", "ambulance", "casualty"`

---

## 3. Terminal Conflict Trigger
```bash
$ git checkout dev
$ git merge --no-ff feature/priority-rules-v1 -m "Merge pull request #6A from stackmussa/feature/priority-rules-v1"
Merge made by the 'ort' strategy.

$ git merge feature/priority-rules-v2
Auto-merging backend/app/providers/triage/rules.py
CONFLICT (content): Merge conflict in backend/app/providers/triage/rules.py
Automatic merge failed; fix conflicts and then commit the result.
```

---

## 4. Raw Conflict Markers in `rules.py`
```python
# ── Priority keywords ────────────────────────────────────────────────
_HIGH_PRIORITY_KEYWORDS: list[str] = [
    "urgent", "emergency", "flood", "fire", "danger", "dangerous",
    "injury", "injured", "collapse", "collapsed", "burst",
    "electrocution", "spark", "short circuit", "foran", "jaldi",
    "immediately", "critical", "severe", "fatal",
<<<<<<< HEAD
    "drowning", "hazards", "monsoon", "short-circuit", "waterlogging",
=======
    "janleva", "emergency call", "blast", "gas leak", "ambulance", "casualty",
>>>>>>> feature/priority-rules-v2
]
```

---

## 5. Resolution & Winning Version Justification (2–4 Sentences)

**Resolved Implementation:**
```python
# ── Priority keywords ────────────────────────────────────────────────
_HIGH_PRIORITY_KEYWORDS: list[str] = [
    "urgent", "emergency", "flood", "fire", "danger", "dangerous",
    "injury", "injured", "collapse", "collapsed", "burst",
    "electrocution", "spark", "short circuit", "foran", "jaldi",
    "immediately", "critical", "severe", "fatal",
    # Synthesized resolution: Environmental hazards + Life-safety / Urdu terms
    "drowning", "hazards", "monsoon", "short-circuit", "waterlogging",
    "janleva", "emergency call", "blast", "gas leak", "ambulance", "casualty",
]
```

**Why this version won (Justification):**
> Both branches introduced critical, domain-specific high-priority keywords targeting different emergency scenarios: Partner 1 addressed environmental and monsoon disasters (*drowning, waterlogging, monsoon*), while Partner 2 addressed acute life-safety incidents and regional Urdu urgency terms (*janleva, blast, gas leak, ambulance*). Rather than discarding either branch's contribution, the conflict was resolved by synthesizing both feature sets into the unified priority array. This ensures the municipal triage engine achieves maximum recall for life-threatening civic complaints across both infrastructure and meteorological crises.
