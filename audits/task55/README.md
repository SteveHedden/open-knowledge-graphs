# Task 55 evidence

Baseline: main `84f94eebd3414deb0bf155e4a02fdfd0acd66627`, jobs snapshot
`6b1512aaa18a4e281f5ffa457add8643af2ce250`. Compare the consecutive deployed
September 20 and 21 commits recorded in `date-evidence.json`; do not attribute
changes using an arbitrary local copy.

- Current records: 786 → 778. Visible on September 21: **361 → 356**.
- All five confirmed visible Booz Allen pairs collapse with both source occurrences.
  Three additional non-visible pairs meet the same explicit employer/requisition/
  location contract. No title-only merging occurs.
- 95 retained jobs recover earlier supported discovery dates from 165 committed
  snapshot revisions, covering 12,600 historical record IDs. Absence from the
  bounded current sample does not make these historical jobs public again.
- 77 existing records changed source date fields across the consecutive baseline
  snapshots. All 67 Accenture changes are present in raw Workday `startDate` values.
  The raw `postedOn` field also changed; no relative-date arithmetic is used.
- Jooble's `updated` field was incorrectly projected as posting time. The raw-backed
  corrections and official field documentation are recorded in `date-evidence.json`.
  Actual posting dates for these rows are unknown. Himalayas uses explicit `pubDate`;
  its changed publication date is retained without inferring the reason upstream.

`corpus-report.json` records merges, retained candidates, discovery backfill and
pinned Git history. `date-evidence.json` contains bounded public field extracts,
source run IDs and SHA-256 hashes of the privately retained Workday payloads.
Full private responses are not committed. The confirmed-pair fixture retains the
public source excerpts and provenance needed for reproducible network-free tests.

The migrated ledger and public records ship through the normal reviewed release;
see `docs/job-identity-and-dates.md` for runtime ownership, display and recovery.

Local validation: 266 repository tests and 362 jobs tests are covered by the full
suite runs plus passing focused corrections; 55 API and 20 MCP tests pass. The
repository run exposed two stale assertions for already-deployed Task 52 release
metadata; the jobs run exposed historical source-IRI migration and optional
diagnostic-shape issues. Those checks now pass. The complete final commit will
also receive the normal GitHub CI check before merge. All 14 browser tests pass,
as do 15 snapshot tests and 10 focused Task 55 identity/date/durability tests.
Full-corpus validation preserves every surviving job's content, active state,
qualification evidence and shared assignments. Twenty Jooble posting-date fields
are corrected to source update dates from raw evidence.
