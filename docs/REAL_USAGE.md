# KOSniper Real Usage

Copy-paste commands for scanning and verifying tender PDFs.

## Install

```bash
pip install -e .
```

## Run Demo (scan + verify)

```bash
bash scripts/demo_pack.sh "<PDF_PATH>" --out-dir /tmp/kos_demo_out
```

Example with fixture:

```bash
bash scripts/demo_pack.sh tests/fixtures/fixture_ko_page2.pdf --out-dir /tmp/kos_demo_out
```

## Verify Receipt

```bash
cat /tmp/kos_demo_out/verify_receipt.json
```

## Artifacts

After a successful run, the output directory contains:

| File | Description |
|------|-------------|
| `report.md` | Human-readable Markdown report |
| `evidence_pack.json` | Machine-readable evidence with verdicts |
| `document_map.json` | PDF metadata and SHA256 hash |
| `verify_receipt.json` | Verification receipt (written by `--receipt`) |

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | OK |
| 2 | Error (missing file, validation failure, etc.) |

## Fallback (without install)

If `kosniper` command is not available:

```bash
python -m kosniper.cli --pdf tender.pdf --scan --out-dir ./out
python -m kosniper.cli --verify-pack --in-dir ./out --receipt
```

The demo script auto-detects and uses the fallback if needed.
