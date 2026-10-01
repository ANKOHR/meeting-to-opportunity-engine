import json
from pathlib import Path
import subprocess
import sys
import time
import pytest
from meeting_to_opportunity_engine.cli import main, load_input, InputError
from meeting_to_opportunity_engine.fixtures import generate, expectations


def test_run_completes_on_fixture(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    generate("demo")
    start = time.perf_counter()
    assert main(["run", "--input", "demo"]) == 0
    assert main(["report", "--format", "md"]) == 0
    assert time.perf_counter() - start < 5
    assert "Data provenance:" in capsys.readouterr().out


def test_empty_input_renders_without_traceback(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    Path("empty").mkdir()
    assert main(["run", "--input", "empty"]) == 0
    capsys.readouterr()
    assert main(["report", "--format", "json"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["metrics"]["records"] == 0
    assert report["metrics"]["actions"] == 0
    assert report["metrics"]["stated_qualified_amount_gbp"] == "0.00"


def test_malformed_input_named_error(tmp_path, capsys):
    path = tmp_path / "broken.json"
    path.write_text('# SYNTHETIC\n{\n bad}', encoding="utf-8")
    assert main(["run", "--input", str(tmp_path)]) == 2
    error = capsys.readouterr().err
    assert "ParseError" in error and "broken.json" in error and "line 3" in error
    assert "Traceback" not in error


@pytest.mark.parametrize("suffix", ["csv", "yaml", "jsonl"])
def test_unsupported_formats_named_error(tmp_path, suffix, capsys):
    (tmp_path / ("broken." + suffix)).write_text("bad", encoding="utf-8")
    assert main(["actions", "--input", str(tmp_path)]) == 2
    assert "unsupported format" in capsys.readouterr().err


def test_determinism_byte_identical(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    generate("demo")
    original = Path("demo/calls.json").read_bytes()
    generate("demo")
    assert Path("demo/calls.json").read_bytes() == original
    main(["run", "--input", "demo"])
    state = Path(".mtoe-result.json").read_bytes()
    main(["report", "--format", "md", "--out", "first.md"])
    main(["run", "--input", "demo"])
    main(["report", "--format", "md", "--out", "second.md"])
    assert state == Path(".mtoe-result.json").read_bytes()
    assert Path("first.md").read_bytes() == Path("second.md").read_bytes()


def test_cli_smoke_all_subcommands(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    assert main(["fixtures", "--out", "demo"]) == 0
    for name in ("run", "actions", "qualify"):
        assert main([name, "--input", "demo"]) == 0
    for fmt in ("json", "md"):
        assert main(["report", "--format", fmt]) == 0
    for name in ("fixtures", "run", "report", "actions", "qualify"):
        with pytest.raises(SystemExit) as error:
            main([name, "--help"])
        assert error.value.code == 0
    output = capsys.readouterr().out
    assert chr(0x2014) not in output


def test_missing_input_named_error(tmp_path, capsys):
    assert main(["run", "--input", str(tmp_path / "absent")]) == 2
    assert "MissingInput" in capsys.readouterr().err


def test_report_write_failure_no_partial_files(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    generate("demo")
    main(["run", "--input", "demo"])
    capsys.readouterr()
    before = sorted(p.name for p in tmp_path.iterdir())
    assert main(["report", "--out", str(tmp_path)]) == 2
    assert "WriteError" in capsys.readouterr().err
    assert sorted(p.name for p in tmp_path.iterdir()) == before


def test_result_recomputed_instead_of_trusting_cached_metrics(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    generate("demo")
    main(["run", "--input", "demo"])
    capsys.readouterr()
    path = Path(".mtoe-result.json")
    state = json.loads(path.read_text())
    state["metrics"]["actions"] = 999
    path.write_text(json.dumps(state), encoding="utf-8")
    main(["report", "--format", "json"])
    assert json.loads(capsys.readouterr().out)["metrics"]["actions"] == 120


def test_real_handwritten_five_record_workflow(tmp_path, monkeypatch, capsys):
    from meeting_to_opportunity_engine.fixtures import fixture_records
    monkeypatch.chdir(tmp_path)
    Path("real").mkdir()
    records = fixture_records(1)
    for record in records:
        record.update(synthetic=False, source="henry_entered")
    Path("real/calls.json").write_text(json.dumps({"synthetic": False, "records": records}), encoding="utf-8")
    assert main(["run", "--input", "real"]) == 0
    capsys.readouterr()
    assert main(["report", "--format", "md"]) == 0
    text = capsys.readouterr().out
    assert "5 real records" in text and "Actions: 3" in text


def test_invalid_cached_result_named_error(tmp_path, capsys):
    path = tmp_path / "state.json"
    path.write_text("{}")
    assert main(["report", "--result", str(path)]) == 2
    assert "SchemaError" in capsys.readouterr().err


def test_duplicate_json_keys_rejected(tmp_path, capsys):
    (tmp_path / "calls.json").write_text('{"synthetic":true,"synthetic":false,"records":[]}')
    assert main(["run", "--input", str(tmp_path)]) == 2
    assert "duplicate JSON key" in capsys.readouterr().err


def test_module_entrypoint_process(tmp_path):
    project = str(Path(__file__).resolve().parents[1])
    import os
    env = dict(os.environ, PYTHONPATH=project)
    process = subprocess.run([sys.executable, "-m", "meeting_to_opportunity_engine.cli",
                              "fixtures", "--out", str(tmp_path / "demo")],
                             cwd=tmp_path, env=env, capture_output=True, text=True)
    assert process.returncode == 0
    assert "SYNTHETIC" in process.stdout
    assert process.stderr == ""


def test_failed_run_preserves_previous_result(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    generate("demo")
    assert main(["run", "--input", "demo"]) == 0
    previous = Path(".mtoe-result.json").read_bytes()
    Path("demo/calls.json").write_text("invalid")
    assert main(["run", "--input", "demo"]) == 2
    assert Path(".mtoe-result.json").read_bytes() == previous


def test_report_missing_parent_named_error(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    generate("demo")
    main(["run", "--input", "demo"])
    capsys.readouterr()
    assert main(["report", "--out", "missing/report.md"]) == 2
    assert "WriteError" in capsys.readouterr().err
    assert not Path("missing").exists()
