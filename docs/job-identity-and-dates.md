# Job identity and discovery dates

A refresh updates the current bounded sample; it does not establish a new job's
identity merely because an aggregator supplied a new ID.

## Ownership and conservative matching

`jobs/scripts/reconcile.py` retains the existing first-party/aggregator matching
contract. After that reconciliation, `job_identity.py` handles recurring identity
across the resulting records, including same-source aggregator duplicates.

A merge requires a reviewed employer identity, explicit employer requisition, and
identical structured location/workplace signature. First-party employer identities
come from the existing reviewed registry. The bounded additional employer policy
in `jobs/curation/job-identity-policy.json` recognizes only the exact reviewed
Booz Allen Hamilton name and its explicit `Job Number: Rddddddd` description field.
Titles, title suffixes, description similarity, and matching location alone never
establish identity. Conflicting requisitions, employers, expiry, employment types,
or differing/missing locations remain separate with diagnostics. Multiple locations
are not flattened into a single employer-wide requisition.

The existing canonical ID wins when known. Initial selection prefers first-party
records, then earliest supported discovery time, then ID. All source occurrences
are retained. When the selected occurrence disappears but a verified replacement
remains, the public ID persists while its external posting link and content follow
the current source occurrence. No old posting is reintroduced just because it is
in history. Qualification and active/expiration filtering remain independent.
Missing expiry on a replacement cannot erase an already known expiry.

`data/jobs/identity-history.json` is a versioned identity ledger, carried atomically
through runtime, promotion, immutable jobs snapshots, manifests and publication.
It contains IDs, identity keys, dates and source links, not full descriptions or
private adapter payloads. Entries remain after a record leaves the bounded sample
so restoration does not reset discovery. A pre-ledger pinned snapshot cannot erase
the reviewed backfill. Subsequent snapshot writers carry the ledger normally under
the existing serialized refresh and stale-writer protections.

## Date semantics and display

- `firstSeenAt`: earliest supported capture by OKG, not employer posting time or
  first qualification. Desktop and mobile label it **Added to OKG**. The jobs list
  defaults to descending discovery time; unknown dates sort last.
- `datePosted`: source-provided publication date. **Posted** remains separately
  visible and sortable. Source changes do not create new discoveries.
- `sourceUpdatedDate`: separately known source update date, represented as
  `schema:dateModified` with day precision in RDF. It is not a posting date.
- `retrievedAt` / `lastSeenAt`: acquisition observations, never posting dates.

Workday's explicit `jobPostingInfo.startDate` remains the posting-date source.
The retained September 20 and 21 responses prove all 67 observed Accenture changes
were upstream `startDate` changes. We cannot infer whether these represent actual
reposts or employer maintenance, and do not rewrite them or infer a separate repost
time. Relative labels such as `postedOn` are retained in the audit as evidence,
not converted using today's clock.

Jooble's API documents `updated` as the last vacancy update. The former adapter
incorrectly exposed it as `datePosted`. It now supplies `sourceUpdatedDate`; the
posting date remains unknown. Retained old-adapter rows are migrated consistently.
The release's corrections are checked against the committed raw response. See
[Jooble's response contract](https://help.jooble.org/en/support/solutions/articles/60001448238).

## Diagnostics and recovery

`run.json.reconciliation.recurringIdentity` reports merged rows, canonical/source
IDs, unresolved candidates, new discoveries, and posting-date changes. The nightly
report also retains each source replay's diagnostics; a job discovered during an
earlier replay remains visible there even if later replays have no new discovery.
Posting-date diagnostics concern current canonical projections, not inferred
employer activity. The ledger prevents repeat discovery events on identical runs.

The initial migration (`audits/task55/migrate.py`) reads pinned committed history,
backfills supported earliest capture dates, and processes only the current sample
for publication. It saves predecessor RDF before rebuilding so the normal
classification projection can reuse evidence. Follow it with:

```
python scripts/shared_tags.py --only jobs
python scripts/validate_shared_tags.py
```

Stage newly generated deployed files (including `data/jobs/identity-history.json`)
before finalizing manifests in a Git checkout: coverage includes tracked files.
Then finalize both jobs and catalog manifests, run required validation against the
complete staged tree, and release
through the coordinated publisher. Never delete the ledger to repair a failed
refresh. Restore the complete last-good jobs snapshot instead; preserve the ledger
when introducing snapshots that predate it. To reproduce the original migration,
use its recorded base commit and the migration script in a separate checkout.
Historical discovery is limited to retained captures: neither a posting date nor
a retrieval-time guess fills an unknown historical date.

## Task 54 handoff

Homepage activity should consume canonical job IDs and `firstSeenAt` from published
jobs; use the identity ledger when reconciling restored/aliased occurrences.
A changed `datePosted`, refreshed `lastSeenAt`, or new occurrence ID is not an
addition event. This task adds no competing event feed or homepage redesign.
