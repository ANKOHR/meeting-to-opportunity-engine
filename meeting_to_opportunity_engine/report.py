"""Deterministic rendering, with provenance and unmeasured benefits on every report."""
import json


def json_text(value):
    # Escape punctuation and Unicode so output has no em dash even in user notes.
    return json.dumps(value, sort_keys=True, indent=2, ensure_ascii=True) + "\n"


def banner(result):
    p = result["provenance"]
    return (f"Data provenance: {p['synthetic_records']} synthetic fixture records; "
            f"{p['real_henry_entered_records']} real records declared as Henry's own hand-entered data. "
            "Provenance is input-declared, not independently verified.")


def render(result, format_name):
    provenance = banner(result)
    if format_name == "json":
        return json_text({"banner": provenance, **result})
    m = result["metrics"]
    lines = ["# Meeting-to-Opportunity Engine", "", provenance, "",
             f"Records: {m['records']}", f"Actions: {m['actions']}",
             f"Overdue actions: {m['overdue_actions']}",
             f"Stated qualified amount GBP: {m['stated_qualified_amount_gbp']}",
             "This is an input-stated amount, not expected revenue or money saved.", "",
             "Time saved: unmeasured. Money saved: unmeasured. Predicted revenue: not estimated.",
             "No illustrative or hypothetical benefit is presented as measured.", "", "## Outcome counts", ""]
    lines += [f"{key}: {value}" for key, value in m["outcome_counts"].items()]
    lines += ["", "## Next actions", ""]
    for a in result["actions"]:
        lines.append(json_text(a).strip())
    lines += ["", "## Input evidence", "", "Each action links to its input id. Full validated input records follow.",
              "", "```json", json_text(result["records"]).strip(), "```", ""]
    return "\n".join(lines)
