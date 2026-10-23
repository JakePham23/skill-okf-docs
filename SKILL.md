---
name: okf-docs
description: "Generate and verify structured OKF-style Markdown documents for AI coding work: plan, unit-test spec, verification report, plus spec, ADR, bug/RCA, docs, code review, changelog and runbook. Use whenever the user asks to write a plan, task breakdown, test plan, unit test spec, acceptance criteria, verify/check report, technical spec, architecture decision, bug report/root cause, documentation, review notes, changelog or runbook, or says 'okf', 'plan.md', 'unittest.md', 'verify.md', 'lập kế hoạch', 'viết unit test', 'kiểm tra lại', 'tài liệu'. Use it even when the user only asks for one document, so IDs stay traceable. Also maintains INDEX.md and a master plan with sub-plans for large multi-part work."
---

# OKF Docs: plan -> unittest -> verify

Produces three linked Markdown documents with a fenced ```yaml metadata block and stable IDs,
then mechanically verifies them. Reply in the user's language; keep IDs, keys
and headings in English.

> Assumption: "OKF" is treated as the format defined in this skill. If the user
> has an official OKF spec, read it first and adapt `assets/` templates and
> `scripts/verify_okf.py` to it.

## Workflow

1. **Plan** - copy `assets/plan.md`, fill it in. Every goal becomes
   acceptance criteria `AC1, AC2...`; every work item becomes a task `T1, T2...`
   that lists the ACs it serves. Write to `docs/okf/PLAN-<nnn>.md`.
2. **Unittest** - copy `assets/unittest.md`. Each test case `TC1...` must name
   the AC(s) it covers in the `Covers` column. Every AC needs >= 1 case,
   including at least one edge/error case for non-trivial ACs.
   Write to `docs/okf/UT-<nnn>.md`, `refs: [PLAN-<nnn>]`.
3. **Implement** the tests as real code (if the user wants code), and the feature.
4. **Verify** - actually run the test/lint/build commands. Copy
   `assets/verify.md` and record real command, exit code and a short output
   excerpt. Never write PASS without having executed something or inspected
   concrete evidence. Write to `docs/okf/VR-<nnn>.md`.
5. **Index + check**: `python scripts/build_index.py docs/okf` then
   `python scripts/verify_okf.py docs/okf/`
   Fix every error and rerun until it exits 0.

If the user asks for only one document, still create it with correct
metadata block and IDs, and say which linked documents are missing.

## Document types

Pick only what the task needs; do not generate all of them by default.

| Type | Prefix | Template | Use when |
|------|--------|----------|----------|
| plan | PLAN | assets/plan.md | any non-trivial change; defines ACs |
| unittest | UT | assets/unittest.md | tests for a plan's ACs |
| verify | VR | assets/verify.md | after implementing; proves ACs |
| spec | SPEC | assets/spec.md | new feature/system needing requirements and design before a plan |
| adr | ADR | assets/adr.md | a technical decision with trade-offs worth recording |
| bug | BUG | assets/bug.md | bug fix: symptom, root cause, fix, regression test |
| docs | DOC | assets/docs.md | user/API/module documentation |
| review | RV | assets/review.md | code review findings and decision |
| changelog | CL | assets/changelog.md | release notes for a change |
| runbook | RB | assets/runbook.md | deploy/migrate/rollback procedures |
| index | INDEX | generated | table of contents of all docs; never write by hand |

Typical flows: feature = spec -> plan -> unittest -> verify -> docs -> changelog;
bugfix = bug -> unittest -> verify; risky op = adr + runbook.
Link documents with `refs`. A bug doc must name a real regression test;
a review must end with APPROVE or CHANGES_REQUESTED.

## Index and master plan

- **INDEX.md**: after creating or changing any doc, run
  `python scripts/build_index.py docs/okf` to regenerate `docs/okf/INDEX.md`
  (documents table, plan hierarchy, docs not under a plan). Never edit it by
  hand. The validator fails if the index is missing or stale once a directory
  has 2+ docs.
- **Master plan**: when work splits into several parts, copy
  `assets/master-plan.md` (`kind: master`, id `PLAN-000`) and make each part a
  normal plan with `parent: PLAN-000` in its metadata block. List every sub-plan in
  the master's `## Milestones` table. Each sub-plan keeps its own ACs, unittest
  and verify. The master has no ACs of its own and cannot be `done` until all
  sub-plans are `done`.
- Small work (one plan) needs no master plan, but still gets an index.

## Format rules

- **Metadata block**: the FIRST thing in every OKF file is a fenced block opened
  with ```yaml and closed with ``` (never `---` frontmatter, which does not
  preview in Markdown viewers; nothing may come before it). Keys: `okf: 1`,
  `type` (plan, unittest, verify, spec, adr, bug, docs, review, changelog,
  runbook, index), `id`, `title`, `status` (draft|approved|in-progress|done|failed),
  `created` (YYYY-MM-DD), `refs` (list of doc ids; unittest and verify must
  reference the plan). Optional on plans: `kind: master`, `parent: <master id>`.
  Values are plain text, one `key: value` per line, no nesting.

  Example start of a file:

  ````markdown
  ```yaml
  okf: 1
  type: plan
  id: PLAN-001
  title: Add slugify helper
  status: draft
  created: 2026-10-23
  refs: []
  ```

  # Add slugify helper
  ````

  (This skill's own SKILL.md keeps normal `---` frontmatter; that rule only
  applies to the OKF documents you generate.)
- Required headings per type are in the templates; do not rename them.
- Task status uses checkboxes: `- [ ]` / `- [x]`. Mark `[x]` only after the work
  is done.
- Test status values: `PASS`, `FAIL`, `SKIP`, `TODO`. Verify uses PASS/FAIL only.
- Verdict in verify doc: `PASS` only if every AC is PASS and no FAIL remains;
  otherwise `FAIL` with a "Follow-ups" list.

## Honesty rules

- If a command could not be run (no network, missing deps), record it as
  `NOT RUN` with the reason, and set that AC to FAIL or mark verdict `FAIL`.
  Do not claim success.
- If the validator fails, report the errors to the user rather than editing
  the validator to pass.
