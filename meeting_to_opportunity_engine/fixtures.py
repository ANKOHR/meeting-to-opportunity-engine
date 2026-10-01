"""Synthetic fixtures with independently enumerated, hand-computed expectations.

No randomness is used, so no random seed is needed. Five planted cases repeat
40 times: proposal, follow-up, request information, closed, no fit.
"""
from pathlib import Path
from .report import json_text

HEADER = "# SYNTHETIC fixture data; no real meetings or measured benefits\n"


def fixture_records(groups=40):
    outcomes = ["qualified", "interested", "needs_information", "closed", "no_fit"]
    records = []
    for group in range(groups):
        for index, outcome in enumerate(outcomes):
            records.append({"id": f"call-{group * 5 + index + 1:03d}", "synthetic": True,
                "source": "synthetic_fixture", "meeting_date": "2026-09-28", "as_of": "2026-09-30",
                "notes": ["Requested a proposal for stated GBP 100.00.", "Agreed follow-up.",
                          "Needs technical information.", "Opportunity closed.", "Explicitly no fit."][index],
                "outcome": outcome, "owner": "Henry", "due_date": "2026-09-29" if index < 3 else None,
                "amount": "100.00" if index == 0 else "0.00", "currency": "GBP"})
    return records


def expectations():
    # Hand calculation: 40 groups x 5 records, 3 actions/group, GBP 100/group.
    return {"synthetic": True, "calculation": "40 x 5 records; 40 x 3 overdue actions; 40 x GBP 100",
            "metrics": {"records": 200, "actions": 120, "overdue_actions": 120,
                        "outcome_counts": {"qualified": 40, "interested": 40, "needs_information": 40,
                                           "closed": 40, "no_fit": 40},
                        "stated_qualified_amount_gbp": "4000.00"},
            "action_ids": [f"call-{g * 5 + i:03d}" for g in range(40) for i in (1, 2, 3)]}


def generate(out):
    from .cli import atomic_write
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    atomic_write(out / "calls.json", HEADER + json_text({"synthetic": True, "records": fixture_records()}))
    atomic_write(out / "expectations.json", HEADER + json_text(expectations()))
    atomic_write(out / "tiny.json.example", HEADER + json_text({"synthetic": True, "records": fixture_records(1)}))
