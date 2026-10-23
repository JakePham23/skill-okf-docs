#!/usr/bin/env python3
"""Validate OKF markdown docs. Usage: verify_okf.py <dir-or-file> ... ; exit 1 on errors."""
import re, sys, pathlib

TYPES = {"plan", "unittest", "verify", "spec", "adr", "bug", "docs", "review", "changelog", "runbook", "index"}
STATUS = {"draft", "approved", "in-progress", "done", "failed"}
HEADINGS = {
    "plan": ["Goal", "Scope", "Acceptance Criteria", "Tasks"],
    "unittest": ["Target", "Cases"],
    "verify": ["Commands", "Results", "Verdict"],
    "spec": ["Problem", "Requirements", "Design"],
    "adr": ["Context", "Decision", "Alternatives", "Consequences"],
    "bug": ["Symptom", "Root Cause", "Fix", "Regression Test"],
    "docs": ["Overview", "Usage", "Reference"],
    "review": ["Summary", "Findings", "Decision"],
    "changelog": ["Summary", "Changes"],
    "runbook": ["Preconditions", "Steps", "Rollback", "Checks"],
    "index": ["Documents"],
}

def parse(path):
    text = path.read_text(encoding="utf-8")
    m = re.match(r"\A\s*```yaml[ \t]*\n(.*?)\n```[ \t]*(?:\n|\Z)(.*)", text, re.S)
    if not m:
        return None, text
    meta = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip()
    return meta, m.group(2)

def refs(v):
    return [x.strip() for x in v.strip("[]").split(",") if x.strip()]

def table_rows(body, heading):
    sec = re.search(rf"^## {re.escape(heading)}\s*\n(.*?)(?=^## |\Z)", body, re.S | re.M)
    rows = []
    if sec:
        for line in sec.group(1).splitlines():
            if line.startswith("|") and not re.match(r"^\|[\s\-|]+\|?$", line):
                rows.append([c.strip() for c in line.strip("|").split("|")])
    return rows[1:] if rows else []

def main(args):
    files = []
    for a in args or ["."]:
        p = pathlib.Path(a)
        files += sorted(p.rglob("*.md")) if p.is_dir() else [p]
    docs, errors = {}, []
    index_doc = None
    for f in files:
        meta, body = parse(f)
        if meta is None:
            if re.search(r"^okf:\s*1\s*$", body, re.M):
                errors.append(f"{f}: OKF metadata must be a ```yaml block at the very top of the file (no '---' frontmatter, nothing before it)")
            continue
        if meta.get("okf") != "1":
            continue  # not an OKF doc
        err = lambda msg, f=f: errors.append(f"{f}: {msg}")
        t = meta.get("type")
        if t not in TYPES:
            err(f"invalid type '{t}'"); continue
        for k in ("id", "title", "status", "created", "refs"):
            if k not in meta: err(f"missing metadata key '{k}'")
        if meta.get("status") not in STATUS: err(f"invalid status '{meta.get('status')}'")
        if "<" in meta.get("title", ""): err("title still a placeholder")
        for h in (["Goal", "Scope", "Milestones"] if meta.get("kind") == "master" else HEADINGS[t]):
            if not re.search(rf"^## {re.escape(h)}\s*$", body, re.M): err(f"missing section '## {h}'")
        if t == "index":
            index_doc = (meta, body, f); continue
        docs[meta.get("id")] = (t, meta, body, f)
    if not docs:
        errors.append("no OKF documents found")
    for id_, (t, meta, body, f) in docs.items():
        err = lambda msg, f=f: errors.append(f"{f}: {msg}")
        for r in refs(meta.get("refs", "")):
            if r not in docs: err(f"ref '{r}' not found")
        parent = meta.get("parent")
        if parent and (parent not in docs or docs[parent][1].get("kind") != "master"):
            err(f"parent '{parent}' must be an existing master plan")
        if t == "plan" and meta.get("kind") == "master":
            kids = {i for i, d in docs.items() if d[1].get("parent") == id_}
            listed = {r[0] for r in table_rows(body, "Milestones") if r}
            if not kids: err("master plan has no sub-plans (set 'parent: <id>' in sub-plans)")
            for k in sorted(kids - listed): err(f"sub-plan {k} missing in Milestones")
            for k in sorted(listed - kids): err(f"Milestones lists unknown sub-plan {k}")
            if meta.get("status") == "done" and any(docs[k][1].get("status") != "done" for k in kids):
                err("master plan is done but a sub-plan is not done")
        plan_ids = [r for r in refs(meta.get("refs", "")) if r in docs and docs[r][0] == "plan"]
        if t in ("unittest", "verify") and not plan_ids:
            err("must reference a plan"); continue
        if t == "spec" and not re.search(r"^- R\d+:", body, re.M): err("no requirements (- R1: ...)")
        if t == "bug":
            sec = re.search(r"^## Regression Test\s*\n(.*?)(?=^## |\Z)", body, re.S | re.M)
            if not sec or not sec.group(1).strip() or "<" in sec.group(1): err("Regression Test is empty/placeholder")
        if t == "review":
            if not re.search(r"^## Decision\s*\n+\s*(APPROVE|CHANGES_REQUESTED)\b", body, re.M):
                err("Decision must be APPROVE or CHANGES_REQUESTED")
        if t == "plan" and meta.get("kind") != "master":
            acs = re.findall(r"^- AC(\d+):", body, re.M)
            if not acs: err("no acceptance criteria (- AC1: ...)")
            for tid, serves in re.findall(r"^- \[[ xX]\] (T\d+):.*?\(serves: ([^)]*)\)", body, re.M):
                for ac in refs("[" + serves + "]"):
                    if ac.replace("AC", "") not in acs: err(f"{tid} serves unknown {ac}")
        if t in ("unittest", "verify"):
            acs = {"AC" + n for n in re.findall(r"^- AC(\d+):", docs[plan_ids[0]][2], re.M)}
        if t == "unittest":
            covered = set()
            for r in table_rows(body, "Cases"):
                if len(r) < 5:
                    err(f"malformed case row {r}"); continue
                if r[4] not in {"PASS", "FAIL", "SKIP", "TODO"}: err(f"{r[0]}: bad status '{r[4]}'")
                covered |= set(re.findall(r"AC\d+", r[1]))
            for ac in sorted(acs - covered): err(f"{ac} has no test case")
            for ac in sorted(covered - acs): err(f"case covers unknown {ac}")
        if t == "verify":
            rows = table_rows(body, "Results")
            res = {r[0]: r for r in rows if len(r) >= 3}
            for ac in sorted(acs - set(res)): err(f"{ac} missing in Results")
            for ac, r in res.items():
                if r[1] not in {"PASS", "FAIL"}: err(f"{ac}: result must be PASS/FAIL, got '{r[1]}'")
                elif r[1] == "PASS" and not r[2]: err(f"{ac}: PASS without evidence")
            vm = re.search(r"^## Verdict\s*\n+\s*(PASS|FAIL)\b", body, re.M)
            if not vm: err("Verdict must be PASS or FAIL")
            elif vm.group(1) == "PASS":
                if any(r[1] != "PASS" for r in res.values()): err("Verdict PASS but some AC is not PASS")
                for u in refs(meta.get("refs", "")):
                    if u in docs and docs[u][0] == "unittest" and "| FAIL |" in docs[u][2]:
                        err(f"Verdict PASS but {u} contains FAIL cases")
            if not table_rows(body, "Commands"): err("no commands recorded")
    if len(docs) >= 2 or index_doc:
        if not index_doc:
            errors.append("missing INDEX.md - run: python scripts/build_index.py <dir>")
        else:
            listed = {r[0] for r in table_rows(index_doc[1], "Documents") if r}
            for i in sorted(set(docs) - listed): errors.append(f"{index_doc[2]}: index stale, missing {i} - rerun build_index.py")
            for i in sorted(listed - set(docs)): errors.append(f"{index_doc[2]}: index lists unknown {i} - rerun build_index.py")
    for m in errors: print("ERROR", m)
    print(f"{len(docs)} doc(s) checked, {len(errors)} error(s)")
    return 1 if errors else 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
