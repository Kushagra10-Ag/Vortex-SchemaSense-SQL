import json
import re
import sqlite3

import db
import prompts
from llm import call_llm
from validator import validate_select_only


def extract_json(text: str):
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M).strip()
    try:
        return json.loads(text)
    except Exception:
        m = re.search(r"\{.*\}", text, flags=re.S)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                return None
    return None


def extract_sql_plain(text: str) -> str:
    """v1 returns free text: take a fenced block if present, else the whole reply."""
    m = re.search(r"```(?:sql)?\s*(.*?)```", text, flags=re.S | re.I)
    return (m.group(1) if m else text).strip()


def _gen_sql(question, version):
    name = "sql_generation" if version in ("v1", "v2", "v3") else "p2_sql_generation"
    system, user = prompts.load(version, name)
    schema = db.SCHEMA_PLAIN if version == "v1" else db.SCHEMA_DESCRIBED
    raw = call_llm(system, prompts.render(user, schema=schema, question=question), prompts.SETTINGS[version])
    if version == "v1":
        return extract_sql_plain(raw), None
    data = extract_json(raw)
    if not data:
        return "", "model did not return valid JSON"
    return (data.get("sql") or ""), data.get("reason")


def run(question: str, version: str = "final", explain: bool = False, max_repairs: int = 2) -> dict:
    """version: v1 | v2 | v3 (SQL generation only) | final (P1 ambiguity + P2 + P3 repair + optional P4)."""
    out = {"question": question, "version": version, "status": None, "sql": "", "rows": [], "cols": [], "note": ""}

    if version == "final":
        system, user = prompts.load("final", "p1_ambiguity")
        raw = call_llm(system, prompts.render(user, schema=db.SCHEMA_DESCRIBED, question=question), prompts.SETTINGS["final"])
        data = extract_json(raw) or {}
        if data.get("clear") is False:
            out.update(status="clarify", note=data.get("question", ""))
            return out

    sql, reason = _gen_sql(question, version)
    if not sql:
        out.update(status="no_answer", note=reason or "no SQL produced", sql="")
        return out

    for attempt in range(max_repairs + 1):
        ok, why = validate_select_only(sql)
        if not ok:
            out.update(status="blocked", sql=sql, note=why)
            return out
        try:
            cols, rows = db.run_readonly(sql)
            out.update(status="ok", sql=sql, cols=cols, rows=rows, note=f"repairs used: {attempt}")
            break
        except sqlite3.Error as e:
            out.update(status="error", sql=sql, note=str(e))
            if version != "final" or attempt == max_repairs:
                return out
            system, user = prompts.load("final", "p3_repair")
            fixed = extract_json(call_llm(system, prompts.render(user, schema=db.SCHEMA_DESCRIBED, question=question,
                                                                  failed_sql=sql, error=str(e)), prompts.SETTINGS["final"])) or {}
            sql = fixed.get("sql") or ""
            if not sql:
                return out

    if explain and out["status"] == "ok":
        system, user = prompts.load("final", "p4_explanation")
        out["explanation"] = call_llm(system, prompts.render(user, question=question, sql=out["sql"],
                                      rows=json.dumps(out["rows"][:20])), prompts.SETTINGS["final"]).strip()
    return out
