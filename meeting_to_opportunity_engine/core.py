"""Pure validation and action rules. Amounts are stated, never predicted revenue."""
from datetime import date
from decimal import Decimal, InvalidOperation


class InputError(ValueError):
    """Named, actionable input failure."""


OUTCOMES = {"qualified": "send_proposal", "interested": "follow_up",
            "needs_information": "request_information", "closed": None,
            "no_fit": None}
FIELDS = {"id", "synthetic", "source", "meeting_date", "as_of", "notes",
          "outcome", "owner", "due_date", "amount", "currency"}


def validate(record):
    if not isinstance(record, dict):
        raise InputError("SchemaError: record must be an object")
    missing = FIELDS - record.keys()
    extra = record.keys() - FIELDS
    if missing or extra:
        raise InputError(f"SchemaError: missing fields {sorted(missing)}; unknown fields {sorted(extra)}")
    for field in FIELDS - {"synthetic", "amount", "due_date"}:
        value = record[field]
        if not isinstance(value, str) or not value.strip() or len(value) > 100000:
            raise InputError(f"SchemaError: {field} must be nonempty text <= 100000 characters")
    if type(record["synthetic"]) is not bool:
        raise InputError("SchemaError: synthetic must be boolean")
    if record["source"] != ("synthetic_fixture" if record["synthetic"] else "henry_entered"):
        raise InputError("SchemaError: source must match synthetic provenance")
    if record["outcome"] not in OUTCOMES:
        raise InputError("SchemaError: outcome is unsupported")
    if record["currency"] != "GBP":
        raise InputError("SchemaError: currency must be GBP; no conversion or mixed totals")
    for field in ("meeting_date", "as_of", "due_date"):
        if field == "due_date" and record[field] is None:
            continue
        try:
            value = record[field]
            if not isinstance(value, str) or date.fromisoformat(value).isoformat() != value:
                raise ValueError()
        except (ValueError, TypeError):
            raise InputError(f"SchemaError: {field} must be YYYY-MM-DD") from None
    if record["meeting_date"] > record["as_of"]:
        raise InputError("SchemaError: meeting_date is future relative to as_of")
    if record["due_date"] is not None and record["due_date"] < record["meeting_date"]:
        raise InputError("SchemaError: due_date precedes meeting_date")
    if OUTCOMES[record["outcome"]] and record["due_date"] is None:
        raise InputError("SchemaError: due_date required for actionable outcome")
    if not OUTCOMES[record["outcome"]] and record["due_date"] is not None:
        raise InputError("SchemaError: due_date must be null for closed or no_fit")
    try:
        if not isinstance(record["amount"], str):
            raise ValueError()
        amount = Decimal(record["amount"])
        if not amount.is_finite() or amount < 0 or amount > Decimal("1000000000") or amount.as_tuple().exponent < -2:
            raise ValueError()
    except (InvalidOperation, ValueError):
        raise InputError("SchemaError: amount must be a decimal string from 0 to 1000000000 with <= 2 decimal places") from None
    return dict(record)


def compute(records):
    validated = [validate(r) for r in records]
    ids = set()
    for r in validated:
        if r["id"] in ids:
            raise InputError(f"SchemaError: duplicate id {r['id']!r}")
        ids.add(r["id"])
    validated.sort(key=lambda r: r["id"])
    actions = []
    counts = {outcome: 0 for outcome in sorted(OUTCOMES)}
    stated = Decimal(0)
    for r in validated:
        counts[r["outcome"]] += 1
        action = OUTCOMES[r["outcome"]]
        if r["outcome"] == "qualified":
            stated += Decimal(r["amount"])
        if action:
            actions.append({"id": r["id"], "action": action, "owner": r["owner"],
                            "due_date": r["due_date"], "overdue": r["due_date"] < r["as_of"],
                            "reason": f"Explicit outcome: {r['outcome']}", "synthetic": r["synthetic"]})
    synthetic = sum(r["synthetic"] for r in validated)
    return {"schema_version": 1, "provenance": {"synthetic_records": synthetic,
            "real_henry_entered_records": len(validated) - synthetic},
            "metrics": {"records": len(validated), "actions": len(actions),
                        "overdue_actions": sum(a["overdue"] for a in actions),
                        "outcome_counts": counts, "stated_qualified_amount_gbp": format(stated, ".2f")},
            "benefits": {"time_saved": "unmeasured", "money_saved": "unmeasured",
                         "predicted_revenue": "not estimated"},
            "actions": actions, "records": validated}
