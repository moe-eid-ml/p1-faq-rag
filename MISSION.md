# MISSION: Sniper Proof-First Pipeline v1

## What This Is
A RAG pipeline that returns **evidence-bound answers only**.  
Every claim links to a retrievable source. Unknown = explicit abstain.

## What This Is NOT
- A chatbot (no open-domain conversation)
- A summarizer (no synthesis without citation)
- A confidence guesser (no "I think…" outputs)

## Core Invariants
1. **No unsourced claims** — every assertion has a `source_id` or answer is YELLOW/RED
2. **Calibrated abstain** — "I don't know" beats hallucinated authority
3. **Traceable** — full provenance JSON per response, auditable in court

## Acceptance Criteria (v1 Gate)
| Criterion | Metric | Threshold |
|-----------|--------|-----------|
| False Green Rate | adversarial eval set | 0% (hard gate) |
| Abstain on OOD | out-of-scope queries | ≥95% YELLOW |
| Provenance completeness | responses with valid trace | 100% |
| Latency p95 | single query | <3s |

## Out of Scope (Parking Lot)
- Agentic multi-step reasoning (v2)
- Multimodal doc ingestion (v3)
- User preference learning (never, probably)

## Change Control
One intent per PR. Time cap: 4h dev / feature. Overflow → parking lot or kill.
