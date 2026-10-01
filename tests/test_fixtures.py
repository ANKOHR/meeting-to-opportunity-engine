import json
from meeting_to_opportunity_engine.fixtures import generate, expectations, fixture_records
from meeting_to_opportunity_engine.cli import load_input, read_json
from meeting_to_opportunity_engine.core import compute


def test_fixtures_labelled_synthetic(tmp_path):
    generate(tmp_path)
    for p in tmp_path.iterdir():
        assert p.read_text(encoding="utf-8").startswith("# SYNTHETIC")
        assert read_json(p)["synthetic"] is True
    assert len(load_input(tmp_path)) == 200
    assert all(r["synthetic"] for r in load_input(tmp_path))


def test_fixture_ground_truth_matches_hand_computed():
    result = compute(fixture_records())
    assert result["metrics"] == expectations()["metrics"]
    assert [a["id"] for a in result["actions"]] == expectations()["action_ids"]


def test_corrupted_input_changes_computed_figures(tmp_path):
    generate(tmp_path)
    payload = read_json(tmp_path / "calls.json")
    payload["records"][0]["outcome"] = "no_fit"
    payload["records"][0]["due_date"] = None
    (tmp_path / "calls.json").write_text(json.dumps(payload), encoding="utf-8")
    result = compute(load_input(tmp_path))
    assert result["metrics"]["actions"] == 119
    assert result["metrics"]["stated_qualified_amount_gbp"] == "3900.00"
    assert result["metrics"] != expectations()["metrics"]


def test_expectations_are_not_workflow_input(tmp_path):
    generate(tmp_path)
    (tmp_path / "expectations.json").write_text("broken", encoding="utf-8")
    assert compute(load_input(tmp_path))["metrics"]["records"] == 200
