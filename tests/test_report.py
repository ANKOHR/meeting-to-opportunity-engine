import json
from meeting_to_opportunity_engine.core import compute
from meeting_to_opportunity_engine.fixtures import fixture_records, expectations
from meeting_to_opportunity_engine.report import render


def test_report_matches_ground_truth_exact():
    report = json.loads(render(compute(fixture_records()), "json"))
    assert report["metrics"] == expectations()["metrics"]


def test_report_zero_false_positives():
    result = compute(fixture_records())
    actual = {a["id"] for a in result["actions"]}
    expected = set(expectations()["action_ids"])
    assert actual - expected == set()
    assert expected - actual == set()
    assert len(result["actions"]) == len(actual) == 120


def test_report_carries_provenance_banner():
    records = fixture_records(1)
    records[0].update(synthetic=False, source="henry_entered")
    for fmt in ("md", "json"):
        text = render(compute(records), fmt)
        assert "4 synthetic fixture records" in text
        assert "1 real records" in text
        assert "not independently verified" in text


def test_hypothetical_figures_labelled():
    for fmt in ("md", "json"):
        text = render(compute(fixture_records()), fmt)
        assert "unmeasured" in text
        assert "not estimated" in text
    assert "not expected revenue" in render(compute(fixture_records()), "md")


def test_no_em_dashes_in_outputs():
    records = fixture_records(1)
    records[0]["notes"] = "hello" + chr(0x2014) + "world"
    records[0]["owner"] = chr(0x2014)
    for fmt in ("md", "json"):
        assert chr(0x2014) not in render(compute(records), fmt)
    assert json.loads(render(compute(records), "json"))["records"][0]["notes"] == records[0]["notes"]
