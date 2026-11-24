# Search Optimization Implementation Plan

**Goal** — Let researchers diagnose gaps in their search profile, test revisions, and approve a verified configuration change.

**Architecture** — The existing FastAPI settings page hosts Deep Chat and the evidence workbench. A local SQLite journal records conversation, labelled evidence, trial results and review decisions. LangGraph checkpoints orchestrate source verification, bounded experiments and the review pause. The profile editor and optimisation service share the existing configuration schema and atomic file writer.

**Stack** — FastAPI, Deep Chat, LangGraph, SQLite, and the optional Python MCP SDK.

## Implementation and acceptance

1. Extend `neurodaily/task_runs.py`, `neurodaily/digest.py`, and the formal run routes. Checkpoint completed sources and processing stages. Validate restart, cancellation and safe use of delivery receipts with `tests/test_task_runs.py`.
2. Add `neurodaily/optimization_evidence.py` and extend the three built-in presets. Capture dated source output, broad/control queries and known identifiers. Compare candidates on the same frozen corpus. Verify that missing labels, partial coverage and failed probes cannot pass the review gate.
3. Add `neurodaily/optimization_store.py` and `neurodaily/optimization.py`. Persist scoped conversation, jobs and labels. Test repeated revisions, independent validation, rejection of unapproved changes, version conflicts, applying and rollback with `tests/test_optimization.py`.
4. Connect the `/api/optimization` router and local Deep Chat assets to Settings. Test the progression from user message through evidence, candidates and review, and verify the existing search preview is available with AI disabled.
5. Expose read-only MCP tools using the same results and profile scoping. Run the full test suite, build and inspect the wheel, and check the desktop bundle configuration for dependencies and packaged assets.
