import pytest
from meeting_to_opportunity_engine.core import compute, InputError
from meeting_to_opportunity_engine.fixtures import fixture_records


def test_core_actions_trace_to_explicit_outcome():
    result = compute(fixture_records(1))
    assert [a["action"] for a in result["actions"]] == ["send_proposal", "follow_up", "request_information"]
    assert result["metrics"]["stated_qualified_amount_gbp"] == "100.00"
    assert result["metrics"]["records"] == sum(result["metrics"]["outcome_counts"].values())


@pytest.mark.parametrize("field,value", [("amount", "-1"), ("amount", "NaN"),
    ("amount", "Infinity"), ("amount", "1.001"), ("amount", "1000000001"),
    ("amount", 10), ("meeting_date", "2099-01-01"), ("as_of", "yesterday"),
    ("synthetic", 1), ("source", "unknown"), ("outcome", "probably interested"),
    ("notes", "x" * 100001), ("currency", "USD"), ("due_date", None),
    ("due_date", "2026-01-01"), ("meeting_date", "20260928")], ids=[f"invalid-{i}" for i in range(16)])
def test_rejects_adversarial_values(field, value):
    r = fixture_records(1)[0]
    r[field] = value
    with pytest.raises(InputError, match=field):
        compute([r])


def test_duplicate_ids():
    r = fixture_records(1)[0]
    with pytest.raises(InputError, match="duplicate id"):
        compute([r, r])


def test_schema_drift():
    r = fixture_records(1)[0]
    r["inferred_revenue"] = "5"
    with pytest.raises(InputError, match="inferred_revenue"):
        compute([r])


def test_future_commitment_allowed():
    r = fixture_records(1)[0]
    r["due_date"] = "2026-10-05"
    assert not compute([r])["actions"][0]["overdue"]


def test_handles_unicode_and_long_inputs():
    r = fixture_records(1)[0]
    r["notes"] = "你好 café \U0001f600 C:\\Users\\Henry " * 2000
    assert compute([r])["records"][0]["notes"] == r["notes"]


def test_decimal_totals_exact_and_nonmutating():
    records = fixture_records(1)
    records[0]["amount"] = "0.10"
    records[1]["outcome"] = "qualified"
    records[1]["amount"] = "0.20"
    assert compute(records)["metrics"]["stated_qualified_amount_gbp"] == "0.30"
    assert records[0]["amount"] == "0.10"
