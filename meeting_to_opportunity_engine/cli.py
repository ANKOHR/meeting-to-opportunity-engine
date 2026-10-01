"""Local file CLI. No network, models, predictions, or inferred commitments."""
import argparse
import json
import os
from pathlib import Path
import sys
import tempfile
from .core import InputError, compute
from .report import json_text, render


STATE = Path(".mtoe-result.json")


def atomic_write(path, text):
    path = Path(path)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n",
                                         dir=path.parent, delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(text)
        os.replace(temporary, path)
    except OSError as error:
        raise InputError(f"WriteError: {path}: {error.strerror}") from None
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def read_json(path):
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise InputError(f"ReadError: {path}: line 1: {error}") from None
    # Header comments keep their physical lines for accurate parse errors.
    text = "\n".join("" if line.lstrip().startswith("#") else line for line in text.split("\n"))
    try:
        def unique_pairs(pairs):
            value = {}
            for key, item in pairs:
                if key in value:
                    raise InputError(f"ParseError: {path}: line 1: duplicate JSON key {key}")
                value[key] = item
            return value
        return json.loads(text, object_pairs_hook=unique_pairs)
    except json.JSONDecodeError as error:
        raise InputError(f"ParseError: {path}: line {error.lineno}: {error.msg}") from None


def load_input(directory):
    directory = Path(directory)
    if not directory.is_dir():
        raise InputError(f"MissingInput: {directory}; use mtoe fixtures --out demo, then --input demo")
    records = []
    try:
        paths = sorted(directory.iterdir())
    except OSError as error:
        raise InputError(f"ReadError: {directory}: line 1: {error.strerror}") from None
    for path in paths:
        if path.name == "expectations.json" or not path.is_file():
            continue
        if path.suffix.lower() in {".csv", ".yaml", ".yml", ".jsonl"}:
            raise InputError(f"SchemaError: {path}: line 1: unsupported format; use JSON")
        if path.suffix.lower() != ".json":
            continue
        value = read_json(path)
        if not isinstance(value, dict) or set(value) != {"synthetic", "records"}:
            raise InputError(f"SchemaError: {path}: line 1: expected synthetic and records fields")
        if type(value["synthetic"]) is not bool or not isinstance(value["records"], list):
            raise InputError(f"SchemaError: {path}: line 1: invalid synthetic or records field")
        for index, record in enumerate(value["records"], 1):
            try:
                from .core import validate
                validate(record)
                if record["synthetic"] != value["synthetic"]:
                    raise InputError("SchemaError: synthetic disagrees with file label")
            except InputError as error:
                raise InputError(f"{error}; file {path}: record {index}") from None
            records.append(record)
    return records


def parser():
    p = argparse.ArgumentParser(description="Compute next actions from explicit call-note facts. Benefits remain unmeasured.")
    subs = p.add_subparsers(dest="command", required=True)
    f = subs.add_parser("fixtures", help="Generate 200 labelled synthetic calls", epilog="Example: mtoe fixtures --out demo")
    f.add_argument("--out", required=True)
    for name, description in [("run", "Compute and persist a workflow result"),
                              ("actions", "List next actions computed from input"),
                              ("qualify", "List explicitly qualified calls and their stated amounts")]:
        s = subs.add_parser(name, help=description, description=description,
                            epilog=f"Example: mtoe {name} --input demo")
        s.add_argument("--input", required=True)
        if name == "run":
            s.add_argument("--result", default=str(STATE))
    r = subs.add_parser("report", help="Render persisted results with provenance", epilog="Example: mtoe report --format md")
    r.add_argument("--format", choices=["md", "json"], default="md")
    r.add_argument("--result", default=str(STATE))
    r.add_argument("--out")
    return p


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        if args.command == "fixtures":
            from .fixtures import generate
            generate(args.out)
            print("Generated 200 SYNTHETIC records. Benefits: unmeasured.")
        elif args.command == "report":
            saved = read_json(Path(args.result))
            if not isinstance(saved, dict) or saved.get("schema_version") != 1 or not isinstance(saved.get("records"), list):
                raise InputError(f"SchemaError: {args.result}: expected schema_version 1 and records")
            text = render(compute(saved["records"]), args.format)
            if args.out:
                atomic_write(args.out, text)
            else:
                print(text, end="")
        else:
            result = compute(load_input(args.input))
            if args.command == "run":
                atomic_write(args.result, json_text(result))
                print(render(result, "json"), end="")
            else:
                from .report import banner
                selected = result["actions"] if args.command == "actions" else [r for r in result["records"] if r["outcome"] == "qualified"]
                print(json_text({"banner": banner(result), "benefits": result["benefits"], "items": selected}), end="")
        return 0
    except InputError as error:
        print(str(error).encode("ascii", "backslashreplace").decode("ascii"), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
