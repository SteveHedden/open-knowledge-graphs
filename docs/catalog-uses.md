# Canonical catalog use relationships

Resource and software catalogs use `okg:uses` for the union of imported Wikidata P2283 facts and currently supported technology classifications. Jobs retain `okg:usesResource` and their existing mention/skill presentation. Categories, activities and software types are unchanged.

## Identity and evidence

`catalog_uses.py` resolves explicit Wikidata IDs, Wikidata entity/page IRIs, registry `owl:sameAs` links and `okg:catalogPage` links. It never resolves by name. Components with conflicting Wikidata IDs fail closed. Self-links are excluded. Targets without a published catalog page remain metadata; the recommender only selects verified catalog pages.

Each canonical edge has one `okg:UseAssertion` with a target and JSON evidence list. Imported evidence records P2283, original target and source item. Classification evidence retains the assignment URI, exact excerpt, source field, review state, method, relation context and source. Both evidence sources survive when they support the same edge. A direct relationship still scores once under the existing recommender.

Classification replay runs existing freshness, correction and review checks first. A further conservative use-evidence boundary accepts current description/programming-language evidence with explicit target naming and actual use/support cues. Titles, bare names, inverse relationships, negative statements and other relationship contexts are retained as `okg:mentionsResource`; their immutable review records are not changed. This boundary may defer real relationships when the saved excerpt is insufficient. Resolve those cases through an evidence-backed review/correction with an exact current description excerpt, rather than weakening the boundary or adding product exceptions. Domain-specific representation cues cover existing RDF/OWL/SKOS/SHACL/SPARQL descriptions.

## Replay and migration

On the first replay of an old catalog snapshot, existing `okg:uses` edges (the prior P2283-only projection) are saved as `okg:sourceUses`. New ingestion also records these source edges. `okg:usesProjectionVersion` prevents later replays from accidentally promoting derived classification edges into upstream facts. Each replay rebuilds the union and evidence nodes from source edges plus current accepted assessments; removing or invalidating a classification removes its derived support without removing an independently supported P2283 edge.

Review JSONL logs and human corrections remain immutable and are replayed by the existing workflow. No Wikidata mutation or fresh source fetch is needed for this internal migration. Existing generation snapshots remain readable; the coordinated publication path normalizes and reprojects them using the current code.

## Consumer compatibility

Catalog RDF consumers should migrate from `okg:usesResource` to `okg:uses` for actual use relationships. `okg:mentionsResource` is explicitly weaker. `sharedTags.tools` remains available with its original classification evidence, including deferred mentions; consumers must not interpret every tag as a use assertion. The additive JSON `uses` array contains canonical target `id` and `sources`. Legacy snapshots without normalization do not claim this new projection.

`relatedTools` keeps its existing structure, with optional `reason.sources` for use evidence. RDF recommendations and embedded JSON-LD carry the matching `okg:evidenceSources` JSON literal. Page JSON-LD also contains all canonical `okg:uses` targets, including those outside the five displayed suggestions. Resource/software technology links are displayed only in Related resources; category/software-type badges and Jobs pills remain unchanged.

Publication is a separate step. The Task 61 review in `audits/task61/` is generated from a frozen local catalog replay; it is not a production deployment.
