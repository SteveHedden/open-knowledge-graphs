# Task 49 backfill audit

Processed **6,268 source records/versions**, including **1,998 historical-only versions**. Historical descriptions and unpublished suggestions remain local.

## Coverage of current published records

| Record type | Records | Tools/resources | Activities/use cases | Domains | Limited text |
|---|---:|---:|---:|---:|---:|
| resource | 3,004 | 98 | 89 | 1,991 | 2,655 |
| software | 316 | 248 | 109 | 240 | 199 |
| jobs | 950 | 500 | 529 | 501 | 190 |

## Changes from previous descriptive tags

Legacy resource categories, page-backed job catalog mentions and supplementary job tags are mapped to the shared identities for this comparison. Qualification evidence, roles and source-provided job categories remain separate. Counts below are assignment changes across current records, not distinct entities.

| Dimension | Added | Retained | Removed | Records still unassigned |
|---|---:|---:|---:|---:|
| tools | 2,339 | 1,433 | 128 | 3,424 |
| activities | 2,360 | 0 | 0 | 3,543 |
| domains | 2,057 | 811 | 2,193 | 1,538 |

## Job evidence and duplicate limits

The retained corpus contains **2,907 distinct job identities** across snapshots. Current observed demand is **522 active eligible posting fingerprints** across **97 employer identities/normalized labels**. Known duplicate fingerprints are collapsed. Unresolved syndication and employer aliases can remain; these are not estimates of all market vacancies.

**1,242 candidate assignments/diagnostics** remain unpublished. Missing tags indicate insufficient accepted evidence. Truncated source descriptions are preserved and flagged.

## Representative accepted evidence

### resource

- **EDDA Study Designs Taxonomy → Medical Subject Headings** (automated, description): “Terms for study designs from MeSH, NCI Thesaurus, Emtree, HTA Database Canadian Repository”
- **EDDA Study Designs Taxonomy → NCI Metathesaurus** (automated, description): “Enriched with terms from NCI Metathesaurus”
- **DOAP → Resource Description Framework** (automated, description): “RDF/OWL schema for describing software projects”
- **DOAP → Web Ontology Language** (automated, description): “RDF/OWL schema for describing software projects”
- **Cell Markers Ontology → Knowledge modeling** (automated, description): “integrates cell type markers for cells in the Cell Ontology”
- **Cell Markers Ontology → Semantic integration** (automated, description): “integrates cell type markers for cells in the Cell Ontology”
- **Library of Congress Name Authority File → Entity resolution** (automated, description): “authoritative data for names of persons, organizations, events, places, and titles for subsequent uniform access to bibliographic resources”
- **Library of Congress Name Authority File → Information retrieval** (automated, description): “for subsequent uniform access to bibliographic resources”
- **Bibliographia Medica Čechoslovaca → Healthcare** (automated, description): “national registering bibliographies in the field of medicine and healthcare”
- **Bibliographia Medica Čechoslovaca → Library & Cultural Heritage** (automated, description): “national registering bibliographies in the field of medicine and healthcare”
- **Biological and Environmental Research Ontology → Environment & Agriculture** (automated, title): “Biological and Environmental Research Ontology”
- **Biological and Environmental Research Ontology → Life sciences** (automated, title): “Biological and Environmental Research Ontology”

### software

- **maplib → Python** (automated, description): “High-performance Python/Rust framework”
- **maplib → RDF Schema** (automated, description): “RDFS reasoning”
- **KGX → ArangoDB** (automated, description): “across RDF, Neo4j, ArangoDB, and other formats”
- **KGX → Biolink Model** (automated, description): “conforming to the Biolink Model across RDF, Neo4j, ArangoDB, and other formats”
- **maplib → Data validation** (automated, description): “SHACL validation”
- **maplib → Graph reasoning** (automated, description): “RDFS reasoning”
- **Cognee → AI agent memory and context** (automated, description): “persistent memory for AI agents”
- **Cognee → Knowledge graph construction** (automated, description): “framework that builds ontology-grounded knowledge graphs as persistent memory for AI agents”
- **4store → Technology & Web** (automated, description): “RDF database system”
- **ABECTO → Technology & Web** (automated, description): “software for the comparison and evaluation of ontologies and knowledge graphs”

### jobs

- **Senior Knowledge Graph Engineer → Cypher** (automated, description): “writing optimized Cypher and SPARQL queries, implementing NL2Query tools for agents”
- **Senior Knowledge Graph Engineer → LangChain** (automated, description): “Experience building entity extraction pipelines using modern NLP frameworks (LangChain, LlamaIndex, spaCy) or LLM-based structured extraction”
- **Data Modeler → Amazon Neptune** (automated, description): “knowledge graph infrastructure (e.g. Neo4j, Amazon Neptune, Stardog)”
- **Data Modeler → Dublin Core Metadata Element Set** (automated, description): “open standards such as schema.org, Dublin Core, or domain-specific vocabularies.”
- **Knowledge Engineer → Data governance** (automated, description): “Set standards for ontology design, semantic modeling, metadata management, data governance, lineage”
- **Knowledge Engineer → Entity resolution** (automated, description): “Practical experience with NLP techniques, search techniques, prompt engineering, entity extraction, entity resolution, semantic search”
- **Knowledge Engineer → Data governance** (automated, description): “Set standards for ontology design, semantic modeling, metadata management, data governance, lineage”
- **Knowledge Engineer → Entity resolution** (automated, description): “Practical experience with NLP techniques, search techniques, prompt engineering, entity extraction, entity resolution, semantic search”
- **Knowledge Engineer → Financial services** (automated, description): “The role must bring relevant industry experience across domains such as BFSI, healthcare, retail, telecom, manufacturing, energy, public sector, or life sciences”
- **Knowledge Engineer → Government & Public Sector** (automated, description): “The role must bring relevant industry experience across domains such as BFSI, healthcare, retail, telecom, manufacturing, energy, public sector, or life sciences”
- **Knowledge Engineer → Financial services** (automated, description): “The role must bring relevant industry experience across domains such as BFSI, healthcare, retail, telecom, manufacturing, energy, public sector, or life sciences”
- **Knowledge Engineer → Government & Public Sector** (automated, description): “The role must bring relevant industry experience across domains such as BFSI, healthcare, retail, telecom, manufacturing, energy, public sector, or life sciences”

## Cross-dimension observations

Tools and domains explicitly assigned to the same active posting (counts overlap):

- Resource Description Framework + General / Cross-domain: 89 postings.
- SPARQL + General / Cross-domain: 87 postings.
- Python + General / Cross-domain: 85 postings.
- Neo4j + General / Cross-domain: 84 postings.
- SHACL + General / Cross-domain: 80 postings.
- Amazon Neptune + General / Cross-domain: 77 postings.
- Stardog + General / Cross-domain: 75 postings.
- Web Ontology Language + General / Cross-domain: 74 postings.
- PyTorch + General / Cross-domain: 74 postings.
- TensorFlow + General / Cross-domain: 74 postings.

## Interpretation

The comparison measures catalog coverage against observed hiring demand. A catalog tool counts as its own available catalog entity without a self-use assertion. Resource/software overlap is deduplicated in the combined count. Parent filters include descendants; counts across tags overlap and must not be summed.

The six-record GPT-5.4 pilot corrected Java omissions and unsupported job-domain inferences after prompt refinement. A subsequent spot audit found title-only activity inferences in earlier Anthropic output; those are retained as unpublished suggestions. These checks do not establish a corpus-wide accuracy score.

## Validation checkpoint

- 4,270 current records and 9,000 accepted assignments pass RDF/JSON parity, target, exact-evidence, no-self-use and protected-field checks against `9233ee2f`.
- Original descriptions, catalog identities, job qualification/evidence, active membership and source occurrences are unchanged.
- All 1,011 previously verified detail pages were regenerated with unchanged membership.
- Catalog validation and both snapshot manifests pass. The retained category-coverage warning (100% → 66.3%) reflects removal of unsupported catch-all assignments.
- Root regression tests pass after updating the expected multi-valued fields, vocabulary version and assignment-level provenance contract. The preexisting jobs fixture failures were repaired by using a page-backed RDF mention in the source fixture and respecting current page membership in the pinned Capital One test; ingestion and eligibility logic were not changed.
- Local browser verification: the unfiltered comparison shows 3,314 unique catalog entities and 522 distinct active eligible jobs; Neo4j filtering shows 3 software entities and 248 jobs.
