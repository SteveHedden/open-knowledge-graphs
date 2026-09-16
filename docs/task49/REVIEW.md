# Task 49 — vocabulary proposal for review

**Status: proposed; approval requested before corpus backfill.**

This package proposes the maintained terms, identity rules and assignment model. It contains evidence discovery and a small set of contextual assignment examples. It does not change production vocabularies, catalog/jobs data, classification policy or public pages.

## Decisions to review

1. Reuse catalog identities in a tools/resources registry; add the **15 supplementary entities** below. For the six QIDs that already have two catalog pages, use the existing resource URI as the tagging identity and retain both page links.
2. Approve the **20 activity/use-case concepts** below, including four reused jobs activity identities. Keep recommendation systems deferred until a contextual example and definition are reviewed; its initial phrase probes found no hits.
3. Retain the **nine existing domain identities**, adding **Healthcare, Life sciences, Financial services, and Supply chain and commerce** as children. Change the General / Cross-domain scope rule so missing evidence stays unassigned.
4. Approve the applicability and assignment semantics below. Only contextual, evidence-supported assignments may be published after approval; these lexical discovery counts are not proposed blanket assignments.

## What the corpus supports

The local normalized corpus contains 8,629 record occurrences resolving to **2,907 posting identities**, including the 952 current published records and 1,955 historical-only identities, across **859 employer labels**. There are 2,949 retained text versions. Source identity, URLs, fingerprints and retained source occurrences remove known repeated records. This is not proof that every syndicated copy has been resolved: grouping by normalized employer and title yields 2,258 possible clusters, which can also combine genuinely distinct requisitions. Both measures are reported by term in [COVERAGE.md](COVERAGE.md).

The catalog contains **3,005 resource records and 316 software records**. Six QIDs span both datasets, giving **3,315 distinct catalog identities**. **1,282 resources and 10 software records have no description.** Titles can support a subject/domain assignment, but a resource's type or title alone rarely supports an assertion about technology use.

**188 current JDs end with an ellipsis/truncation marker.** This detects some truncated text; absence of a marker does not establish completeness. Historical evidence is explicitly tied to its source snapshot and must not silently be represented as current wording. The 20 synthetic jobs in `jobs/data/jobs.json` and runtime fixture runs are excluded from evidence. Raw responses and ZIP archives are inventoried separately, without double-counting them as new postings. The proposal uses stored descriptions and structured catalog metadata; it does not claim a fresh review of external documentation.

### How to read the coverage

Counts are **lexical discovery hits**, including title-only, boilerplate and ambiguous hits. They measure which candidate terms deserve contextual review, not how many entities should receive a tag. For example, employee medical insurance produces healthcare/finance hits, and a software “library” produces cultural-domain hits. These must be rejected during contextual classification. Existing domain assignments are not used as independent evidence for their own correctness.

Some signals are concentrated: taxonomy-management phrases occur in 94 posting identities but only 3 employer labels and 5 employer/title clusters. Semantic-search phrases occur in 166 identities across 18 employer labels and 35 clusters. This prevents repeated or location-specific advertisements from masquerading as broad employer demand. English phrase probes miss paraphrases and non-English wording; the approved contextual classifier must support abstention and multilingual source evidence.

## 1. Tools and resources: entities, not duplicate SKOS concepts

Every existing catalog entity is eligible for this registry, including entries without generated detail pages. Preserve existing types, labels, aliases, Wikidata identities and catalog links. Membership does not assert that a resource uses itself, that a job uses an employer's product, or that another entity uses the registered tool.

| Supplementary entity | Type | Identity suffix under `https://openknowledgegraphs.com/entities/` |
|---|---|---|
| Python | Programming language | `python` |
| Java | Programming language | `java` |
| JavaScript | Programming language | `javascript` |
| TypeScript | Programming language | `typescript` |
| SPARQL | Query language | `sparql` |
| Cypher | Query language | `cypher` |
| GQL | Query language | `gql` |
| SQL | Query language | `sql` |
| SHACL | Constraint language | `shacl` |
| SKOS | Knowledge organization model | `skos` |
| LangChain | Software framework | `langchain` |
| LangGraph | Software framework | `langgraph` |
| PyTorch | Software framework | `pytorch` |
| TensorFlow | Software framework | `tensorflow` |
| Elasticsearch | Search engine | `elasticsearch` |

Definitions and aliases are in [entity-registry.json](entity-registry.json); the review RDF is in [proposed-vocabularies.ttl](proposed-vocabularies.ttl). No unverified supplementary Wikidata mappings are asserted. At implementation, reconcile these identities before minting anything in the maintained registry; exact label/alias collisions with the current catalog were checked.

**Existing identities to reuse:** Neo4j, Stardog, LOINC, RDF, RDF Schema, OWL, LinkML, Apache Jena and Amazon Neptune already have catalog identities. SPARQL, SHACL and SKOS do not have exact identity matches in the current catalog, despite the presence of many software tools that use them. “SPARQL.js” must not be treated as the SPARQL language itself.

**Existing dual-page QIDs:** BnF authorities, Framework, LinkML, National Library of Korea Linked Open Data, Open Knowledge Graphs and UniProt. The proposal selects each existing resource URI for tags and retains both catalog URLs; it does not remove, rename or redirect pages.

**Alias safeguards:** retain the reviewed catalog alias policy as a starting point, including acronym, context and employer guards. Do not treat organization names such as TopQuadrant as unconditional product aliases. “Neptune” needs database context; “OWL” needs semantic-technology context; “GQL” needs graph-query context. Cypher has its own identity; its useful Neo4j page can remain a related link. Registry types group entities but are not use-case tags. Only true equivalent names become aliases; broader discovery phrases remain separate matching probes.

## 2. Use cases and activities

The hierarchy below is a conceptual browsing hierarchy. `kind` distinguishes an activity from an application/use case. Parent selection includes descendants; an assignment can target the most specific evidenced term without materializing every ancestor as a separate asserted tag.

```text
Knowledge modeling [activity]
  Ontology engineering [activity]
  Taxonomy management [activity; reused jobs URI]
  Knowledge graph construction [activity]
Semantic integration [activity; reused jobs URI]
  Entity resolution [activity; reused jobs URI]
  RDF data mapping [activity]
Information retrieval [activity]
  Semantic search [use case]
  Retrieval-augmented generation [use case]
    GraphRAG [use case]
AI agent memory and context [use case]
Graph analytics [activity]
Graph reasoning [activity; reused jobs URI]
Data governance [activity]
  Provenance and lineage [activity]
  Data validation [activity]
Graph visualization [activity]
Fraud detection [use case]
Drug discovery [use case]
```

New activity IDs live under `https://openknowledgegraphs.com/vocabularies/activities/`. Reused terms retain the existing `https://openknowledgegraphs.com/jobs/vocab/activity-…` identities and their existing definitions, gaining membership in the shared scheme. No copied job-policy match terms or scoring metadata enter the descriptive assignment engine automatically.

Every term has a definition, parent, kind, discovery phrases and negative example in [TERMS.md](TERMS.md). The compact hierarchy intentionally omits speculative industry applications. Recommendation systems remains a deferred candidate in the audit, outside the proposed RDF scheme. A later review can add it with explicit assignment evidence.

**Important distinctions:**

- GraphRAG describes a retrieval application; a named GraphRAG software product needs its own entity resolution. Co-occurrence of a knowledge graph and LLM is insufficient.
- Graph reasoning means logical inference over graph knowledge. Generic problem solving or an LLM reasoning claim does not establish it.
- A Graph Database software type does not imply graph analytics; a SPARQL Tooling type does not imply semantic search.
- Ontology engineering describes work/capability; the existing software-type concept describes a class of tools. Relate them with an explicit capability mapping, not `owl:sameAs` or `skos:exactMatch`.
- A catalog vocabulary can support a use case through its stated purpose. It need not execute the activity itself. Assignment evidence records whether the subject performs, supports or is designed for the activity.

## 3. Domains

Keep the existing category scheme URI and all nine existing top-level concept URIs/definitions. The proposed hierarchy adds:

```text
Life Sciences & Healthcare
  Healthcare
  Life sciences
Finance & Business
  Financial services
  Supply chain and commerce
Geospatial
Government & Public Sector
International Development
Library & Cultural Heritage
Technology & Web
Environment & Agriculture
General / Cross-domain
```

A record may receive multiple specific domains when independently supported. Cross-cutting cases may have siblings or multiple branches; “healthcare AND finance” must be supported by actual application/work descriptions. Do not infer healthcare from LOINC alone or finance from the employer's industry. General / Cross-domain means evidenced broad applicability, not an unknown value. Preserve existing assignments as legacy/unverified until re-evaluated; unsupported legacy tags appear as unresolved changes in the eventual migration audit.

The existing category definitions refer to resources. The shared assignment model interprets a resource's subject, software's stated application, or a job's work context against those same subject definitions. Organizations, people and source services have different applicability, below.

## Representative contextual assignments

See [EXAMPLES.md](EXAMPLES.md) for source excerpts and [example-assignments.ttl](example-assignments.ttl) for proposal-state RDF evidence. These examples were contextually examined for this proposal; **they are not human-approved tags**.

- **Graphwise — Semantic AI Engineer:** GraphRAG/RAG work, with Python/Java alternatives and preferred semantic technologies. Domain stays unknown: enterprise work does not itself establish an industry domain.
- **Accenture — Data Platform Engineer:** ontology engineering, knowledge modeling and semantic search. Python appears under “Good to Have Skills”; its internal evidence status is preferred. Do not infer a domain from consulting clients mentioned in employer boilerplate.
- **Keypixel — AI Architect:** Stardog, LangChain and Python; RAG; Healthcare. Healthcare is stated alongside HIPAA/PHI/EHR in the role's key skills, rather than inferred from an employer or tool. Its short description warrants limited-text caution even without an ellipsis.
- **Stardog catalog record:** SPARQL and OWL support; Graph reasoning. Stardog's own identity is not a technology-use assignment to itself.
- **LOINC catalog record:** Healthcare, supported by “identifying medical laboratory observations.” No technology-use or activity assertion follows just from its being a vocabulary.
- **CPR Ontology catalog record:** Healthcare from “ontology for computer-based patient record systems.”

A concrete cross-dimension example is **Stardog + RAG + Healthcare** in the Keypixel posting. This establishes one observed conjunction; it is not a claim about market prevalence.

## Inventory and migration map

| Existing source or projection | Proposed relationship / migration |
|---|---|
| `vocabularies/categories.ttl`, `okg:category` | Keep category identities/predicate; allow multiple values and shared applicability. Add four reviewed children. Remove fallback-to-General inference. |
| `vocabularies/software-types.ttl`, `okg:softwareType` | Keep the ten functional software types separate. Explicit capability mappings can relate relevant types to activities, but never automatically assert all capabilities for every instance. |
| `jobs/vocabularies/kg-jobs.ttl`: seven role concepts | Retain role classification separately. Job titles can supply evidence for contextual interpretation, not automatic cross-dimension tags. |
| Thirteen KG skill/technology concepts | Resolve RDF/RDFS/OWL/SPARQL/SHACL/SKOS/LinkML/Neo4j to entities; relate GraphRAG to the use-case concept. Knowledge Graph, Semantic Web and Linked Data remain paradigms/skills, not invented tool identities. Graph Database remains a tool type/policy concept. |
| Four jobs activity concepts | Reuse identities and definitions in the shared activity scheme. Preserve their original qualification behavior. |
| First-party `PolicyConcept`, `RoleFamily`, policy term and source-strip rules | Eligibility/scoring and boilerplate processing remain separate. Descriptive assignments cannot feed back into qualification or active membership. |
| `jobs/catalog-mention-policy.json`; `catalogMentions`; `schema:mentions` | Preserve mention evidence; resolve to one registry identity. A mention alone need not become an accepted use/support assignment. Keep useful page links. |
| `jobTags` in `job_normalization.py` | Resolve Cypher/GQL/SPARQL to language entities and remove duplicate chip paths. Cypher's related Neo4j link is not its identity. Provider `tags` remain source categories unless independently reviewed. |
| `curation/classifications.ttl`; `data/categories.json`; `data/software_types.json` | Preserve reviewed curation separately from proposed automated assignments. Export JSON from authoritative RDF; replace single-category cache assumptions. |
| `ontology.ttl` resource shape | Remove `okg:category` maxCount 1; broaden its existing resource-only domain safely. Add assignment constraints. Keep independent software-type constraints unless separately needed. |
| `scripts/category_classifier.py`, `scripts/fetch_data.py` | Replace exactly-one-domain prompts/data fields with shared evidence-backed multi-assignment processing. Reuse stable URI registry. |
| `scripts/semantic_config.py`, `catalog_snapshot.py`, `validate_catalog.py`, manifests | Validate proposed target classes, hierarchy, registry identity uniqueness, evidence and RDF/JSON parity; version the outputs consistently. |
| `site/app.js`, `scripts/generate_pages.py`, `jobs/site`, jobs generators | Multi-valued chips and filters; OR within/AND across dimensions; descendant expansion; provenance inspection without required/preferred UI. |
| `api/src/index.js`, `api/src/semantic.js` | Shared filter semantics and arrays; regenerate semantic projection/index metadata with the new vocabulary version. |
| `mcp-server/src/okg_mcp/{models,client,server,format}.py` | Migrate typed API contracts and rendering along with API consumers. Preserve existing resource URLs and useful filter links. |
| `organizations.ttl`, organization JSON and producers | Keep kind/role classifications and producer relationships separate from these dimensions. |

### Applicability by entity type

| Entity type | Tools/resources dimension | Activities/use cases | Domain |
|---|---|---|---|
| Job posting, including retained/inactive records | Technologies/resources used, supported or requested in role-specific text | Work performed or applications built | Explicit work/application subject |
| Ontology, vocabulary, taxonomy, KG, ontology language, standard | Evidenced dependencies, supported formats or interoperating resources; distinguish reference-only mentions | Documented purpose or supported work | Subject matter |
| Software | Evidenced languages, frameworks, supported resources or integrations; never self | Documented capabilities and applications | Explicit application domains; unknown for a generic tool unless broad applicability is evidenced |
| Organization | Not applicable in this phase | Not applicable in this phase | Not applicable in this phase; do not inherit job or product domains |
| Person/creator, license, career source, source dataset, policy/mapping node | Not applicable | Not applicable | Not applicable |
| Supplementary language/framework/model entity | Registry membership; not itself automatically backfilled | Not automatically backfilled outside the catalog | Not automatically backfilled outside the catalog |

Use an assessment record per applicable subject/dimension with `assigned`, `unassigned`, `insufficient-evidence`, or `not-applicable`. Unknown is an assessment state, not a domain concept and not a fake tag. No tag count minimum applies.

## Assignment and refresh contract

Proposed explicit predicates: **`okg:usesResource`**, **`okg:hasActivity`**, and existing **`okg:category`**. An evidence node identifies subject, predicate, target, source file/URL, source field, exact supporting phrase, normalized-text offsets, content hash, vocabulary version, classification-method version, method and review state. For usesResource, `relationContext` distinguishes uses/supports/depends-on/requested-skill; for hasActivity it distinguishes performs/supports/intended-use. A reference-only mention stays a mention.

Assignments in this package are proposed evidence nodes only. Production direct triples will be materialized only from publishable decisions. Store a stable decision key `(subject, dimension, target)` and evidence identity separately so text changes do not destroy a reviewed correction. Human rejection is a durable negative decision, not an absent tag.

Required/preferred/contextual/unspecified belongs only in RDF assignment evidence. Preserve alternatives (“Python, Java, or Scala”) as a requirement group; do not imply that all three are independently mandatory. The general tag-inspection projection exposes source, phrase, method and review state but excludes requirement status and requirement-group metadata, as required by Task 49.

Cache contextual classification by normalized meaningful source text plus structured evidence fields, vocabulary version/content digest, alias/disambiguation policy digest, classifier/prompt/model version and applicability version. Ignore refresh timestamps and formatting-only text differences. Reclassify on meaningful text, concept definition/hierarchy/alias, or classifier changes. Keep human decisions in a separate override store; reclassification may flag stale reviewed evidence for review but may not overwrite it. A reviewed rejected tag remains rejected.

Reuse deterministic entity matching, then contextual LLM classification for actual application/work meaning, with exact source support and abstention. Discovery probes do not authorize publishing. Apply existing reviewed boilerplate removal to a matching copy and preserve original descriptions; validate source offsets against the original/normalized text mapping. Ambiguous suggestions stay unpublished. New terms/hierarchy changes require review; newly admitted catalog identities enter automatically.

## Validation and next step

The proposal validator parses RDF, checks concept definitions/hierarchy cycles and targets, verifies one registry identity per catalog Wikidata entity, preserves all existing catalog links, verifies source hashes and examples against stored text, and checks that deferred concepts and assignment triples are absent from the proposal scheme. A rerun checks reproducibility of generated artifacts.

After your vocabulary review, the remaining Task 49 work is the maintained implementation, contextual full-corpus backfill, before/after assignment audit, UI/API/search/refresh migration, regression and semantic validation, followed by the existing reviewed merge/publication process. **Task 49 remains in progress.**
