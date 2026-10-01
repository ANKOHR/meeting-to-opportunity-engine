# Meeting-to-Opportunity Engine

`mtoe` converts structured call notes into next actions automatically. It is a local, CPU-only Python CLI with no dependencies, network calls, language models, or database. Explicit outcomes and agreed deadlines drive the rules. Free text is evidence retained in the report; the tool does not interpret it or invent commitments.

Hypothesis: a deterministic workflow with tested input facts can reliably turn recorded meeting outcomes into an auditable action queue. Henry is the intended first user for technical outbound.

## Quickstart

Requires Python 3.10+ and setuptools 68+ already available locally. Installation does not need the network:

```powershell
python -m pip install --no-build-isolation --no-deps --no-index -e .
mtoe fixtures --out demo
mtoe run --input demo
mtoe report --format md
python -m pytest -q
```

If pip warns that the user Scripts directory is absent from PATH, add the reported directory to your session PATH or invoke its `mtoe.exe` by full path. Installation above is fully offline.

Without installation, use `python -m meeting_to_opportunity_engine.cli` in place of `mtoe`. `run` stores `.mtoe-result.json` in the current directory. Reports recompute the facts from its validated input records. `--result` selects a different state file. Re-run after editing source data. Generated results and demo files are ignored by Git.

The standard demo uses 200 synthetic records. The shipped `examples/calls.json` is a five-record synthetic input: `mtoe run --input examples`, then `mtoe report --format md`. Alternatively, copy `demo/tiny.json.example` into a separate directory as `calls.json`, then run and report that directory. The five deliberately written cases cover each outcome. This is realistic synthetic evidence, not a real trial.

## Input reference

An input directory contains JSON files with exactly two top-level fields: `synthetic` (boolean) and `records` (list). Leading or standalone `#` comment lines are permitted. JSONL, CSV and YAML are rejected with a named format error. Other extensions are ignored. `expectations.json` is reserved ground truth and excluded from workflow input. Do not store real meeting records under that name. Input files and records are processed in a stable order; record ids must be unique across all files.

```json
{
  "synthetic": true,
  "records": [{
    "id": "example-001",
    "synthetic": true,
    "source": "synthetic_fixture",
    "meeting_date": "2026-09-28",
    "as_of": "2026-09-30",
    "notes": "Illustrative synthetic case: requested proposal for stated GBP 100.",
    "outcome": "qualified",
    "owner": "Henry",
    "due_date": "2026-10-02",
    "amount": "100.00",
    "currency": "GBP"
  }]
}
```

For Henry's own real data entered by him, set both synthetic flags to false and source to `henry_entered`. The source is a declaration, not independently verified ownership. Do not relabel third-party or illustrative data as Henry's real data. Keep real trial files outside this repository.

All record fields shown are required and extra fields are rejected. Strings must be nonempty, at most 100000 characters. Unicode and Windows paths are supported using normal JSON escaping. `notes` preserves raw notes; the operator must explicitly encode the agreed outcome, owner and deadline.

| Outcome | Action | Deadline |
| --- | --- | --- |
| qualified | send_proposal | Required |
| interested | follow_up | Required |
| needs_information | request_information | Required |
| closed | No action | Must be null |
| no_fit | No action | Must be null |

`qualified` means the operator explicitly recorded a proposal request; it is not a prediction of purchase. Actions preserve the input id, owner, deadline and rule reason. Overdue means due_date is strictly before that record's explicit `as_of`. No wall clock is read. Dates use exact YYYY-MM-DD. Future meetings relative to as_of are rejected; future commitments are valid. Deadlines before the meeting are rejected.

Amounts are decimal strings, nonnegative, finite, at most GBP 1000000000 with at most two decimal places. Only GBP is accepted so mixed currency totals cannot be silently added. The qualified amount is the exact Decimal sum of amounts on qualified records, regardless of whether an action is overdue. This is stated opportunity value, not a forecast, revenue, or savings. Nonqualified amounts are retained but excluded from that total. Input counts and outcome counts reconcile exactly.

## Subcommands

| Command | Example | Behavior |
| --- | --- | --- |
| fixtures | `mtoe fixtures --out demo` | Generate labelled 200-record fixtures and expectations |
| run | `mtoe run --input demo --result result.json` | Validate, compute and atomically persist results |
| report | `mtoe report --result result.json --format json --out report.json` | Recompute and render persisted input evidence |
| actions | `mtoe actions --input demo` | Compute an action queue without saving state |
| qualify | `mtoe qualify --input demo` | Select explicitly qualified calls without inferring interest |

All subcommands have `--help` and examples. Markdown and JSON reports have a provenance banner and full input evidence, so every action and amount can be traced. JSON output is sorted and ASCII escaped; Markdown embeds escaped JSON for user strings to avoid mojibake, markup injection, and prohibited punctuation. Identical input gives byte-identical output on repeated runs. Fixture generation uses no randomness and therefore no seed.

## Architecture

```text
Local JSON call facts -> CLI parser and schema validation -> pure core.compute
                                                          -> action rules
                                                          -> exact totals
                                                          -> provenance counts
                                  -> atomic local result -> report recomputation
                                                          -> Markdown or JSON
Fixture generator -> labelled calls + independent hand-computed expectations
```

## Honesty boundary and fixture policy

The engine computes from explicit inputs. It does not discover buyers, interpret arbitrary notes, estimate opportunity probability, predict revenue, or measure time saved. Time saved and money saved are always marked `unmeasured`; predicted revenue is `not estimated` in CLI results and reports. No hypothetical savings figure is shipped. The GBP 100 example is illustrative synthetic input, not measured demand.

Every generated fixture file starts with a SYNTHETIC header and has `synthetic: true`. Every call also has a synthetic flag and source. File and record declarations must agree. Report banners give separate synthetic and declared Henry-entered counts even for mixed inputs. Empty reports have zeros and still carry provenance. Fixture expectations are independently enumerated from 40 repetitions of five cases: 200 records, 40 per outcome, 120 actions, all 120 overdue, GBP 4000 stated qualified amount. The engine never reads those expectations. Tests modify fixture input to prove outputs change and corrupt expectations to prove independence.

Acceptance evidence is synthetic only. Exact fixture matching, zero planted false positives, and performance do not establish accuracy on messy real calls. No claim of time saved or real commercial demand follows from those tests.

## Errors and limitations

Named errors return exit code 2 without a traceback: `MissingInput` includes a usage hint, `ParseError` names the file and physical JSON line, `SchemaError` names the field and file/record where available, `ReadError` names the file, and `WriteError` names the destination. Duplicate JSON keys are rejected (line 1 is the document-level key error location), as are duplicate ids, unknown fields, negative/nonfinite amounts, oversized strings and schema drift. Malformed unsupported formats are rejected rather than guessed. Files are never silently discarded because of invalid records.

Writes use a same-directory temporary file and atomic replacement. Failed writes leave no partial report file and preserve an existing destination. Parent directories for result/report paths must exist. Fixture generation creates its directory; its files are individually atomic, not a multi-file transaction. Source fixtures may be overwritten deliberately by regenerating the same output directory. A failed run preserves the previous result file; do not interpret that previous report as a successful new run. Strict schema and fixed action types may require manual correction for nuanced commitments. There is no deduplication by person or semantic analysis, only unique record ids.

## Evidence-based improvement hook and verdict

After two weeks of real use, Henry should hand-check all actions in a sample of at least 30 calls (or every call if fewer) and record false positives, missing actions, incorrect owner/deadline, sample size and run count. Metric: calls with any incorrect or missing action divided by calls reviewed. Record denominator and raw judgments; an empty sample is unmeasured, never zero error. Also record whether the tool was actually used. An error rate above 10 percent or no use triggers a documented top-cause fix or a kill decision. The initial evidence-based improvement is strict explicit outcome encoding rather than keyword matching: negation and ambiguous interest cannot safely imply a commitment. Tests demonstrate unsupported ambiguous outcomes are rejected, and no_fit never creates actions.

See `EVIDENCE.md` and `VERDICT.md`. No two-week results are fabricated. At the end of the window, choose expand for daily use or revenue, integrate for heavy overlap with a sibling, commercialise for a buyer willing to pay as-is, maintain for portfolio evidence, or kill for no use or failure to meet acceptance. Record the reason and evidence. The build stops at local verification and commits; publication is handled separately.
