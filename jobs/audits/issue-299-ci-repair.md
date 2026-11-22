# Issue 299: Jobs CI contract repair

Baseline: main at 74c65a9e6. The four reported modules reproduced all ten failures (67 tests passed).

## Findings and changes

- Metaphacts migrated from its old website to the department-scoped Digital Science Pinpoint feed in [b5038e69e](https://github.com/SteveHedden/open-knowledge-graphs/commit/b5038e69ed356826334f05ee9c4a4d73cd72bbbe). The production replay helper lacked the existing Pinpoint fixture mapping.
- SAP moved from jobs.sap.com to careers.sap.com in that same commit. The Task 44 historical capture retained its old absolute detail URL while its relative listing resolved against the new host. Replay now adapts a copy of that URL; the saved historical capture is unchanged. A negative test still rejects a detail URL from the old host.
- The historical Task 41 baseline predates those two migrations. An explicit before/after amendment ledger records only the field changes in the already-merged migration. Verification checks both the old field values and the resulting complete current contracts. Unapproved tenant changes and baseline alterations still fail. The original baseline is unchanged.
- A catalog entry named Infrastructure produced a false-positive match from “Senior Cloud Infrastructure Engineer.” The existing ambiguous-surface denylist now excludes standalone Infrastructure. A focused regression preserves the independent RDF mention.
- The Capital One test iterated page-registry metadata as though it contained resource slugs. It now restricts membership to resource/software sections. SPARQL now has an admitted resource page, so the expectation includes that mention and verifies the generic SPARQL job pill is suppressed to avoid duplication.

## Adjacent validation correction

The preceding first-import classification commit omitted its deterministic software-type JSON projection and refreshed snapshot manifest. The two QID entries and local candidate manifest were synchronized separately on main in commit 415b8fefa. Source retrieval time and catalog record membership are unchanged. This is a local candidate, not evidence of publication.

No production source endpoints, request limits, admission rules, or historical fixtures/baselines were changed. No refresh or publication workflow was dispatched.
