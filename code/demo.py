"""Interactive demo: python code/demo.py   (final pipeline; shows the SQL beside the answer)"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import db
import pipeline

if not db.DB_PATH.exists():
    db.build_db()
print("Ask a question about the retail database (blank line to quit).")
while True:
    q = input("\nQuestion> ").strip()
    if not q:
        break
    r = pipeline.run(q, "final", explain=True)
    if r["status"] == "clarify":
        print("Clarifying question:", r["note"])
    elif r["status"] == "ok":
        print("SQL:", r["sql"])
        print("Rows:", r["rows"][:10])
        print("Answer:", r.get("explanation", ""))
    else:
        print(f"Not run ({r['status']}):", r["note"])
