"""Layer 1 safety: parse the SQL and allow exactly one SELECT statement."""
import sqlglot
from sqlglot import exp

_NAMES = ["Insert", "Update", "Delete", "Drop", "Create", "Alter", "AlterTable", "Command", "Merge", "Pragma", "TruncateTable"]
_FORBIDDEN = tuple(getattr(exp, n) for n in _NAMES if hasattr(exp, n))


def validate_select_only(sql: str):
    """Return (ok, reason)."""
    if not sql or not sql.strip():
        return False, "empty SQL"
    try:
        statements = [s for s in sqlglot.parse(sql, read="sqlite") if s is not None]
    except Exception as e:  # sqlglot raises ParseError / TokenError
        return False, f"could not parse SQL: {str(e)[:120]}"
    if len(statements) != 1:
        return False, "exactly one statement is allowed"
    tree = statements[0]
    if not isinstance(tree, (exp.Select, exp.Union)):
        return False, f"only SELECT is allowed, got {type(tree).__name__}"
    if tree.find(*_FORBIDDEN):
        return False, "write or schema-changing keyword found"
    return True, "ok"
