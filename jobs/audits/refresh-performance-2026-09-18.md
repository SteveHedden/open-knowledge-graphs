# Jobs refresh investigation — 2026-09-18

The user requested cancellation of recovery run 35353452771 and investigation of multi-hour jobs refreshes. The run was cancelled before tagging or publication. The separately verified Open University slug repair was already merged in PR 79.

## Evidence

- Successful run 34823146093 (2026-09-14) took approximately 2h32m. Its diagnostics show all 40 sources refreshed, without source failures. Most adapters recorded only an initial `pipeline` progress marker, so the existing elapsedSeconds values do not measure complete source duration.
- Recovery run 35353452771 started 2026-09-18 13:59 UTC and was cancelled at 14:44 UTC. Its old logs do not identify the active source or internal phase at cancellation. No claim is made that a particular source stalled.
- Offline cProfile on the 952-job snapshot from main b2060f48: loading the catalog index took 0.218 seconds; one full catalog-mention pass took 78.690 seconds over 1,551 patterns, with approximately 2.95 million regex finditer calls. No network requests were involved. This is a local profiled measurement, not a GitHub runner benchmark.

## Findings

`task42_nightly` runs isolated source workers in bounded batches, then calls `_replay_source` serially for each successfully fetched source. Each replay invokes `run_pipeline`, which reconciles the combined source snapshots, catalog-matches the resulting jobs, builds RDF and publishes the intermediate local snapshot. Thus unchanged jobs are repeatedly matched across the source replay loop. Forty equivalent 79-second matching passes alone would cost about 53 minutes locally; actual corpus sizes, runner speed and network phases vary. This establishes repeated local computation as a material contributor, not a complete attribution of historical runtime.

The source wall-clock cap applies to workers, not the parent's replay phase. The worst-case workflow estimate budgets fetch batches and discovery overhead but does not explicitly budget serial replay. Existing worker progress files cover only selected HTTP adapters and previously were not streamed to Actions logs.

## Implemented instrumentation

Flush structured timestamped progress lines to stdout: refresh plan, cadence retention, batch/source lifecycle, 30-second source heartbeats with allowlisted request counters, source timeouts, replay lifecycle, catalog index/matching, fetching/normalization, RDF generation, snapshot writing, and discovery. Record worker/replay elapsed times in nightly diagnostics. Report completed workers immediately rather than waiting for a slower preceding worker. Do not print descriptions, response bodies, headers, or request URLs/query strings.

## Implemented performance fix

Nightly source workers and replays now stage normalized, classified, reconciled JSON and source evidence without catalog enrichment or RDF generation. After all source outcomes have been applied, the parent performs catalog matching, job normalization tags, RDF generation and validation once on the combined candidate. Standalone source refreshes retain their existing complete-publication behavior. The candidate replaces live runtime only after finalization and discovery succeed. Runs with no successful refresh retain the existing snapshot without rebuilding it.

This removes full-corpus matching and RDF generation from every intermediate replay, and avoids redundant worker builds. Reconciliation and JSON staging still happen per replay; network fetching remains subject to the existing limits. It does not eliminate the one final matching pass or contextual classification of new/changed jobs. Existing shared-tag caches and committed RDF assessments continue to support reuse.

Validation: two source fixture refreshes produce byte-identical jobs JSON, run metadata, source snapshots and Turtle against eager publication. Tests prohibit catalog matching and RDF building during deferred replay, verify one final materialization, preserve failed-source last-good evidence, and verify that finalization failure leaves the live directory byte-identical. Real-world end-to-end timing remains to be measured on the next instrumented refresh; the 78.690-second profiled baseline above is not a post-change workflow measurement.
