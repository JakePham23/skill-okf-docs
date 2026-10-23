# okf-docs

A skill that enables AI coding agents to generate structured Markdown documentation following the Open Knowledge Format (OKF) and self-verify the results.

## Core Workflow

`spec` → `plan` → `unittest` → `verify` → `docs` → `changelog`

## Key Features

- **10 Document Types:** `plan`, `unittest`, `verify`, `spec`, `adr`, `bug`, `docs`, `review`, `changelog`, `runbook`
- **Auto-generated Index:** Automatically maintains `INDEX.md`, supporting both master plans and sub-plans.
- **Universal Metadata:** Uses ```` ```yaml ```` code blocks at the top of files for frontmatter metadata, ensuring full compatibility and preview support across all Markdown viewers.
- **Automated Validation:** Includes `verify_okf.py` to check whether Acceptance Criteria (AC) have corresponding tests, verifications contain actual evidence, and indexes remain up to date.

