# Related-resource recommendations

Task 60 refines the deterministic graph scorer. It does not use embeddings,
classifiers, LLM explanations, vendor-name inference, or resource-pair exceptions.
Resources and software share a candidate corpus. Jobs do not participate.

## Qualification and ranking

The source facts remain unchanged. Each derived recommendation has an auditable
primary graph path. Canonical catalog URLs resolve Wikidata identities; the
original identity bridge is included in direct-path evidence.

| Rule | Predicates and path | Weight | Qualification and displayed reason |
| --- | --- | ---: | --- |
| Direct use | `okg:uses`, target `okg:wikidataId` | 120 | Forward **Uses**, reverse **Used by** |
| Direct containment | `dcterms:isPartOf`, target `okg:wikidataId` | 120 | Forward **Part of**, reverse **Has part** |
| Shared parent | Two `dcterms:isPartOf` edges | 100 | Parent must itself be cataloged, with at most 6 members across the candidate catalogs; **Both part of** |
| Same repository | Two `okg:sourceRepo` edges | 90 | Exact normalized repository, never hosting account alone; **Same repository** |
| Same namespace family | Two `okg:namespaceURI` edges | 70 | Exact normalized base path, never host alone; **Same namespace family** |
| Specific shared class | Two `okg:sourceType` edges | 65 | Explicit reviewed allowlist, 2–64 members across all records; **Both classified as** |
| Resource domain | Two `okg:category` edges | 60 | Same maintained domain, resource-to-resource only; **Same domain: Healthcare** |
| Software type | Two `okg:softwareType` edges | 60 | Same maintained functional type, software-to-software only; **Same software type: Ontology Engineering** |
| Same creator (support only) | Two `okg:creator` edges | 4 | Never generates or qualifies a candidate and never supplies the primary reason |

Every path has two source triples. There is no arbitrary transitive traversal.
The direct rules allow reverse *recommendations*, not reversed source claims.
No implementation relationship is synthesized from a uses claim.

The class allowlist and labels are in `APPROVED_SHARED_CLASSES`. Its reviewed
Wikidata definitions are captured in `audits/task60/2026-11-14/`. Functional classes
include triplestore, graph database management system, ontology editor, and graph
visualization software; bounded reference classes include unit ontology and name
authority file. Unknown classes are supporting evidence only. Data format,
proprietary software, programming-language libraries, general RDF vocabulary,
and generic ontology/software classes cannot qualify independently. The broad
“graph database” class is also insufficient: the captured cohort mixes datasets
and engines under it. A separate graph database **management system** class is
approved. This does not change the source classifications.

The fixed degree cap of 64 accommodates the reviewed functional classes (the
largest graph-engine class has 33 records in the captured cohort), while bounding
class-only fan-out. It is not a percentile or evidence of specificity. Changes to
the allowlist require review of class meaning and member examples. Narrow classes
are not automatically approved merely because few catalog records use them.

Broad discovery uses the maintained `vocabularies/categories.ttl` and
`vocabularies/software-types.ttl` concept identities and labels. Exact shared
classifications qualify on their own. General / Cross-domain, missing categories,
unknown concepts and generic RDF types do not. Software domain categories do not
qualify tools: sharing Technology & Web must not reconnect unrelated tools.
Cross-catalog recommendations continue to require a closer graph path. There is no
classification hierarchy traversal or guessed category assignment. Developer Library
is accepted as a maintained functional software type for broader discovery; a generic
Wikidata programming-language-library class alone remains insufficient.

Within closer graph matches, shared domain/type contributes only 4 points, so the
new 60-point admission score does not overwhelm existing structural ranking.
Other corroborating scores are creator, supporting source type and language = 4,
normalized RDF type = 3, license = 2, and token overlap = 3 with Jaccard >= .25 and
at least two shared tokens. These never qualify a pair alone. The threshold is 60.
Shared creator cannot qualify even with an artificially large configured score.

Ranking has three strict tiers: direct uses/containment first; other approved
structural/specific-class paths second; broader domain/type discovery last. Within
each tier use descending score then canonical URL. Select at most five distinct
target identities total, never five per kind. The same Wikidata entity cannot
recommend itself through its other catalog page. Primary reason priority is direct
use, containment, shared parent, repository, namespace, specific class, software
type, domain. Each reason states only the actual connection; broad discovery never
claims compatibility, equivalence or close topical similarity. Score components
remain in diagnostics. Empty results remain valid for records without a qualifying
connection; no unclassified fallback fills slots.

## Projections and publication

`okg:relatedTo` remains the compatibility link set. Each source also links to
`okg:Recommendation` nodes with target, rank, title, reason code, direction,
display text and a canonical JSON array of original evidence triples. These
properties are declared and constrained in `ontology.ttl`.

The existing `relatedTools` JSON array adds `recommendationId`, `rank`, and
`reason` (code, direction, text, path). Array order follows explicit rank. Legacy
link-only snapshots can still be read; the publisher recomputes them. HTML keeps
one **Related resources** section. Each compact card is one link: the relationship
label appears above the title, and any category/class qualifier appears beneath it.
Cards size to their content in a responsive three/two/one-column grid. The renderer
splits the existing reason at its first colon; RDF, JSON and JSON-LD wording remains
unchanged. HTML validation reconstructs the visible label and qualifier and compares
the result with the original reason. Legacy page markup remains readable. Schema.org `mentions` retains its existing
meaning; separate absolute OKG properties serialize the recommendation nodes in
JSON-LD, so “uses” is never misrepresented as an implementation assertion.

The coordinated publisher combines pinned resource/software graphs, recomputes
recommendations, then recomputes once more using the final surviving page set in
`generate_pages.py --refresh-shared-projections`. An unavailable target cannot
consume a top-five slot. RDF, JSON and pages share the surviving relationships.
No foreign resource records are copied into the other dataset. Independent
snapshot validation checks its local facts and projections; full evidence
validation requires both graphs at assembly. Shared tags, classification reviews,
job data and source membership are untouched.

The current coverage policy is unchanged: decline reporting remains nonblocking.
This implementation does not dispatch Actions, modify Wikidata, or authorize a
release. The existing nightly-publication instruction still applies.

## Reproduce the evaluation

Freeze `ontologies.ttl`, `software.ttl`, both matching JSON projections,
`page_qids.json`, `manifest.json`, and the reviewed `frozen-sample.json` in one
input directory. The evaluator verifies the artifacts against the pinned
manifest and sample hashes, and writes only to a different output directory:

```sh
python scripts/evaluate_related_resources.py \
  --input-dir /path/to/frozen-inputs \
  --output-dir /path/to/evaluation
```

The evaluator checks full-cohort source preservation, deterministic ordering,
evidence, RDF/JSON projection, and RDF/JSON-LD/HTML explanations on the frozen
sample. It produces previews, coverage, all gained/lost links and score evidence.
Relevance judgments are recorded separately; they are not inferred by this script.
