"""Usage: python code/run_tests.py v1   (or v2 | v3 | final). Writes test-data/results/<version>.csv"""
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import db
import pipeline

ROOT = Path(__file__).resolve().parent.parent


def norm(rows):
    return sorted(tuple(round(c, 2) if isinstance(c, float) else c for c in r) for r in rows)


def main(version):
    if not db.DB_PATH.exists():
        db.build_db()
    cases = json.loads((ROOT / "test-data" / "test_cases.json").read_text(encoding="utf-8"))
    results, passed = [], 0
    for c in cases:
        try:
            out = pipeline.run(c["question"], version)
        except Exception as e:
            out = {"status": "crash", "sql": "", "rows": [], "note": f"{type(e).__name__}: {e}"[:200]}
        exp_kind = c["expect"]
        if exp_kind == "result":
            _, gold_rows = db.run_readonly(c["gold_sql"])
            ok = out["status"] == "ok" and norm(out["rows"]) == norm(gold_rows)
        elif exp_kind == "clarify":
            ok = out["status"] == "clarify"
        else:  # refuse
            ok = out["status"] in ("blocked", "no_answer")
        passed += ok
        results.append({"test_no": c["id"], "type": c["type"], "question": c["question"], "expected": exp_kind,
                        "status": out["status"], "generated_sql": out["sql"], "note": out["note"], "pass": "Pass" if ok else "Fail"})
        print(f"Test {c['id']:>2} [{c['type']:<7}] {'Pass' if ok else 'FAIL'}  status={out['status']}")
    path = ROOT / "test-data" / "results" / f"{version}.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(results[0].keys()))
        w.writeheader()
        w.writerows(results)
    crashes = sum(r["status"] == "crash" for r in results)
    print(f"\n{version}: {passed}/{len(cases)} passed. Details saved to {path}")
    if crashes:
        print(f"WARNING: {crashes} tests CRASHED (the model call failed). These are not real failures: do NOT record these numbers. Fix the error and rerun.")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "final")