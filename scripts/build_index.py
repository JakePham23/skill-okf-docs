#!/usr/bin/env python3
"""Regenerate INDEX.md for an OKF docs directory. Usage: build_index.py [dir] (default docs/okf)."""
import sys, pathlib, datetime
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from verify_okf import parse, refs

ORDER = ["spec", "adr", "plan", "unittest", "verify", "bug", "review", "docs", "changelog", "runbook"]

def main(argv):
    d = pathlib.Path(argv[0] if argv else "docs/okf")
    d.mkdir(parents=True, exist_ok=True)
    items = {}
    for f in sorted(d.rglob("*.md")):
        meta, _ = parse(f)
        if not meta or meta.get("okf") != "1" or meta.get("type") == "index":
            continue
        meta["_path"] = f.relative_to(d).as_posix()
        items[meta.get("id", f.stem)] = meta
    key = lambda i: (ORDER.index(items[i].get("type")) if items[i].get("type") in ORDER else 99, i)
    rows = []
    for i in sorted(items, key=key):
        m = items[i]
        rows.append(f"| {i} | {m.get('type','')} | [{m.get('title','')}]({m['_path']}) | "
                    f"{m.get('status','')} | {', '.join(refs(m.get('refs','[]')))} | {m.get('parent','')} |")
    seen, tree = set(), []
    def kids(i):
        sub = [j for j, m in items.items() if m.get("parent") == i]
        sub += [j for j, m in items.items() if m.get("type") != "plan" and i in refs(m.get("refs", "[]"))]
        return sorted(dict.fromkeys(sub), key=key)
    def walk(i, depth):
        if i in seen: return
        seen.add(i)
        m = items[i]
        tree.append(f"{'  ' * depth}- {i} {m.get('title','')} [{m.get('status','')}]")
        for j in kids(i): walk(j, depth + 1)
    for i in sorted(items, key=key):
        m = items[i]
        if m.get("type") == "plan" and not m.get("parent"):
            walk(i, 0)
    others = [i for i in sorted(items, key=key) if i not in seen]
    counts = {}
    for m in items.values(): counts[m.get("type")] = counts.get(m.get("type"), 0) + 1
    out = ["```yaml", "okf: 1", "type: index", "id: INDEX", "title: OKF Index", "status: done",
           f"created: {datetime.date.today().isoformat()}", "refs: []", "```", "",
           "# OKF Index", "", "## Overview", "",
           "- " + ", ".join(f"{t}: {n}" for t, n in sorted(counts.items())) if counts else "- (empty)", "",
           "## Documents", "", "| ID | Type | Title | Status | Refs | Parent |",
           "|----|------|-------|--------|------|--------|"] + rows + ["", "## Hierarchy", ""]
    out += tree or ["- (no plans)"]
    out += ["", "## Not under a plan", ""] + ([f"- {i} {items[i].get('title','')}" for i in others] or ["- (none)"])
    (d / "INDEX.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"INDEX.md written: {len(items)} doc(s)")
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
