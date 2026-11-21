# Tagging taxonomy revision and classification review — November 21, 2026

The domain and activity vocabularies remain separate from the named-entity index.
Software types 0.2.0 adds Metadata Management and clarifies ontology-model quality
checking versus validating instance data. Categories 1.1.1 removes an accidental
editing instruction without changing the meaning of General / Cross-domain.

The homepage renders domain children beneath their parents. Existing transitive
parent matching is retained; IDs and bookmark parameters are unchanged. The RDF
controlled-vocabulary projection now exposes `broader` links. Asset content hashes
are updated to prevent stale browser/CDN JavaScript and CSS.

## Review scope and limits

- 138 software records: 120 accepted and 18 deferred after a second evidence review.
  The software JSON reports retain the initial and superseding decisions.
- 425 job records across 214 normalized source groups: 292 accepted, 133 deferred.
  Supported tags are retained on deferred records. Most unresolved jobs have
  truncated source excerpts; two require a more precise domain decision.
  The final and qualified reports supersede earlier decisions for the same ID.
- 863 resource records: 440 accepted and 423 deferred for descriptive evidence or
  identity/admission checks. No records were removed or admitted by this work.
- 110 existing resource classifications revalidated after editorial cleanup of
  General / Cross-domain. Their source content and assignments are unchanged.
  This is not 110 newly classified resources.

Exact evidence and immutable review results are retained through the standard
classification importer. No paid classifier, Wikidata edit, admission exception,
or forced catch-all classification is used. Remaining records still require
review. A deferred review is not completed tagging and must remain in the inbox.

## Validation

- Semantic architecture tests, including RDF-derived parent projections.
- Classification-review lifecycle tests.
- Browser regression tests and hierarchy DOM/matching checks.
- Full staged shared-tag validation and RDF/JSON parity before publication.

Publication must use the coordinated catalog publisher and saved dataset snapshots.
The publisher applies these review results to current evidence; incompatible new
source content stays pending rather than receiving stale assignments.

Final validation results and lifecycle counts are recorded in staged-summary.json.
Detail-page regeneration retains exactly 1,354 resource and 280 software pages
from the verified baseline. Recommendation evidence is rebuilt from the new
classifications. The known-record fixture for OKG expects its reviewed Metadata
Management software type rather than Ontology Engineering.
