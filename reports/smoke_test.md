# Smoke tests

## Docs + IDs smoke test

Commit: ee4068d1f96548e24d4d7e81a272e0c1e8b9fa5b
Mode: Hybrid
Include: —
Exclude: —
Lang: auto
Query: i want money

Output header:
Time: 2025-12-22 21:52:25 UTC • Mode: Hybrid • k=3 • lang=en

(top 2 sources):
[1] What documents do I need for Wohngeld? - ID (passport/ID card) - Rental contract - Current rent certificate - Proof of income (last 12 months) - Proof of heating/utility costs  — wohngeld_en.txt • en • updated 2025-11-11

[2] What are the requirements for Wohngeld? - Main residence in Germany - Not simultaneously receiving housing costs via Bürgergeld - Income within legal limits (depends on household size, rent, location)  — wohngeld_en.txt • en • updated 2025-11-11

Notes:

* Include is empty (—) so retrieval is over the full corpus; results still come from wohngeld_en.txt because it matches strongly and q_lang=en is preferred.
* Mode=Hybrid means TF-IDF candidate pool is reranked by semantic scores (UI hybrid path).

## Docs + IDs smoke test (Include=wohngeld, good query)

Commit: c7dd46a
Mode: Hybrid
Include: wohngeld
Exclude: —
Lang: auto
Query: How long does a Wohngeld application take?

Output header:
Time: 2025-12-22 22:16:22 UTC • Mode: Hybrid • k=3 • lang=en

(top 3 sources):
[1] How long does the application take? - Typically 4–8 weeks (depends on authority workload and completeness of documents)  — wohngeld_en.txt • en • updated 2025-11-11
[2] What documents do I need for Wohngeld? - ID (passport/ID card) - Rental contract - Current rent certificate - Proof of income (last 12 months) - Proof of heating/utility costs  — wohngeld_en.txt • en • updated 2025-11-11
[3] What are the requirements for Wohngeld? - Main residence in Germany - Not simultaneously receiving housing costs via Bürgergeld - Income within legal limits (depends on household size, rent, location)  — wohngeld_en.txt • en • updated 2025-11-11

Notes:

* Include=wohngeld forces filename filtering via file_ok(), so only wohngeld* files survive post-retrieval.
* q_lang=en → _prefer_lang prioritizes EN passages; backfill only if EN results < k.

