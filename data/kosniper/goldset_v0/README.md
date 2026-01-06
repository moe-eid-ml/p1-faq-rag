# KOSniper Gold Test Set v0

Purpose: small, manually-labeled tender packs used for CI/adversarial regression tests.

Folders:
- raw/: source tender packs (PDF/ZIP) OR placeholders if files can’t be committed
- labels/: human labels (JSON) aligned to a stable schema
- meta/: provenance + notes (where sourced, date, license notes)

Rule: labels must always point to evidence (doc_id + page_number + snippet and/or offsets).
