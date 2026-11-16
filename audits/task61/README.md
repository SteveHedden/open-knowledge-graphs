# Task 61 initial review — implemented, not published

**Superseded by the [review-checkpoint revision](revision-2/README.md).** The figures below describe the initial implementation at `3357028f7`; the original audit artifacts are retained.

Baseline: `640e5f1f2` (generation `20261115T203711Z-6a8316be5179`). Same frozen 40-page selection from Task 60, plus SHACL Play! and AWS Context Ontology Accelerator. No source fetch, Wikidata changes, paid classification calls or publication action.

## Results

- 42 pages / 200 displayed recommendations inspected, including all 17 newly selected sample suggestions and their source excerpts. New suggestions have direct use/support evidence; broad unchanged domain/type suggestions remain explicitly labeled as discovery connections.
- Across 1,623 published pages: 189 suggestions gained and 187 displaced. Every displaced suggestion still qualifies but falls outside the existing top five. Covered pages move from 1,586 to 1,587. No scoring weights, result cap or creator-only rules changed.
- SHACL Play!: RDF and SHACL now appear first as Uses, then FOOPS!, O’FAIRE and Protégé. ROBOT and SHACTOR are displaced from the five displayed results.
- AWS Context Ontology Accelerator: ELK, ontop, HermiT, LinkML and ontology-quality-suite remain in the same order. Its three Uses links now carry explicit upstream provenance.
- Separate catalog technology pills removed. Category/software-type badges and Jobs behavior preserved. Thirteen review/correction and Jobs artifacts remain byte-identical.

## Validation

Passed: 8 new normalization tests; 24 Task 60 recommendation tests; 34 existing relationship tests; 16 shared-tag tests; 16 classification-review tests; 9 page-membership tests; 15 snapshot/replay tests (122 tests total). Full staged catalog SHACL, shared-tag validation, RDF/JSON projection, declared terms, all recommendation paths/wording, 42-page HTML/JSON-LD parity and normalization replay idempotence pass. This is targeted validation, not a claim that the repository-wide suite is green.

## Unresolved tag evidence

431 of 504 current technology assignments support canonical Uses. The remaining 73 stay as metadata with their original review history. Their individual subjects, excerpts and dispositions are in [tag-use-audit.json](tag-use-audit.json).

| Reason | Count | Next step |
|---|---:|---|
| Title or review note only | 37 | Review an exact current description excerpt that establishes use/support. |
| Excerpt does not establish use/support | 21 | Verify a fuller authoritative description and submit a supported classification review. |
| Different relation context | 7 | Preserve the distinction; only add Uses with independent evidence. |
| Mention, negative or inverse relationship | 8 | Keep metadata or model the correct relationship separately; do not reverse it into Uses. |

Examples include GeoNames ontology (the database uses the ontology, not the reverse), IdRef (operated by SUDOC), title-only OWL/RDF names, and KGX’s isolated list of formats. No uncertain record was promoted just to increase coverage.

## Per-page before / after

The lists below preserve rank. [page-review.json](page-review.json) includes full source paths/provenance; [changes.json](changes.json) includes all catalog gains/losses with scoring evidence. [summary.json](summary.json) pins input hashes.

### Basic Formal Ontology

Before: Agronomy Ontology — Used by; Alzheimer's Disease Ontology — Used by; Apollo Structured Vocabulary — Used by; Cardiovascular Disease Ontology — Used by; Chemical Entities of Biological Interest — Used by.

After: Agronomy Ontology — Used by; Alzheimer's Disease Ontology — Used by; Apollo Structured Vocabulary — Used by; Cardiovascular Disease Ontology — Used by; Chemical Entities of Biological Interest — Used by.

No target changes.

### Biomimetic Ontology

Before: Basic Formal Ontology — Uses; Brick schema — Same domain: Engineering & Built Environment; Metadata4Ing — Same domain: Engineering & Built Environment; Ontology for Functionally Graded Materials — Same domain: Engineering & Built Environment; Petrochemical Ontology — Same domain: Engineering & Built Environment.

After: Basic Formal Ontology — Uses; Brick schema — Same domain: Engineering & Built Environment; Metadata4Ing — Same domain: Engineering & Built Environment; Ontology for Functionally Graded Materials — Same domain: Engineering & Built Environment; Petrochemical Ontology — Same domain: Engineering & Built Environment.

No target changes.

### Controlled Vocabulary for Dublin Core format

Before: American Folklore Society Ethnographic Thesaurus — Same resource type: Controlled Vocabulary; Anatomical Therapeutic Chemical Classification System — Same resource type: Controlled Vocabulary; Australian and New Zealand Standard Classification of Occupations identifier — Same resource type: Controlled Vocabulary; Australian education vocabularies — Same resource type: Controlled Vocabulary; Basic Geo (WGS84 lat/long) Vocabulary — Same resource type: Controlled Vocabulary.

After: American Folklore Society Ethnographic Thesaurus — Same resource type: Controlled Vocabulary; Anatomical Therapeutic Chemical Classification System — Same resource type: Controlled Vocabulary; Australian and New Zealand Standard Classification of Occupations identifier — Same resource type: Controlled Vocabulary; Australian education vocabularies — Same resource type: Controlled Vocabulary; Basic Geo (WGS84 lat/long) Vocabulary — Same resource type: Controlled Vocabulary.

No target changes.

### DCAT

Before: NORIA-O — Used by; Addiction Ontology — Same resource type: Knowledge Graph; Adverse Event Reporting Ontology — Same resource type: Knowledge Graph; Agronomy Ontology — Same resource type: Knowledge Graph; Allotrope Merged Ontology Suite — Same resource type: Knowledge Graph.

After: NORIA-O — Used by; Addiction Ontology — Same resource type: Knowledge Graph; Adverse Event Reporting Ontology — Same resource type: Knowledge Graph; Agronomy Ontology — Same resource type: Knowledge Graph; Allotrope Merged Ontology Suite — Same resource type: Knowledge Graph.

No target changes.

### Framework

Before: Artificial Intelligence Knowledge Graph — Same resource type: Knowledge Graph; BabelNet — Same resource type: Knowledge Graph; ExO — Same resource type: Knowledge Graph; Drosophila development — Same resource type: Knowledge Graph; BioPortal — Same resource type: Knowledge Graph.

After: Artificial Intelligence Knowledge Graph — Same resource type: Knowledge Graph; BabelNet — Same resource type: Knowledge Graph; ExO — Same resource type: Knowledge Graph; Drosophila development — Same resource type: Knowledge Graph; BioPortal — Same resource type: Knowledge Graph.

No target changes.

### Gene Ontology

Before: Cell Ontology — Used by; Software Ontology — Used by; Phenotype And Trait Ontology — Used by; Agronomy Ontology — Used by; Behaviour Change Intervention Ontology — Used by.

After: Cell Ontology — Used by; Software Ontology — Used by; Phenotype And Trait Ontology — Used by; Agronomy Ontology — Used by; Behaviour Change Intervention Ontology — Used by.

No target changes.

### GeoSPARQL

Before: ontop — Used by; Lightweight Image Ontology (LIO) — Same domain: Technology & Web; Actionable Intelligence Retrieval System — Same domain: Technology & Web; Algorithm-Implementation-Execution Ontology Design Pattern — Same domain: Technology & Web; Artificial Intelligence Knowledge Graph — Same domain: Technology & Web.

After: ontop — Used by; Lightweight Image Ontology (LIO) — Same domain: Technology & Web; Actionable Intelligence Retrieval System — Same domain: Technology & Web; Algorithm-Implementation-Execution Ontology Design Pattern — Same domain: Technology & Web; Artificial Intelligence Knowledge Graph — Same domain: Technology & Web.

No target changes.

### Glossary of Procurement Terms

Before: Australian Governments' Interactive Functions Thesaurus — Same domain: Government & Public Sector; Central Archive Module — Same domain: Government & Public Sector; Central Product Classification — Same domain: Supply chain and commerce; Common Procurement Vocabulary — Same domain: Government & Public Sector; Corporate body name authority list — Same domain: Government & Public Sector.

After: Australian Governments' Interactive Functions Thesaurus — Same domain: Government & Public Sector; Central Archive Module — Same domain: Government & Public Sector; Central Product Classification — Same domain: Supply chain and commerce; Common Procurement Vocabulary — Same domain: Government & Public Sector; Corporate body name authority list — Same domain: Government & Public Sector.

No target changes.

### General Ontology for Linguistic Description

Before: Ontologies of Linguistic Annotation — Same domain: Language & Linguistics; Arabic Ontology — Same domain: Language & Linguistics; LexInfo — Same domain: Language & Linguistics; Lexvo.org Ontology — Same domain: Language & Linguistics; OntoLex — Same domain: Language & Linguistics.

After: Ontologies of Linguistic Annotation — Same domain: Language & Linguistics; Arabic Ontology — Same domain: Language & Linguistics; LexInfo — Same domain: Language & Linguistics; Lexvo.org Ontology — Same domain: Language & Linguistics; OntoLex — Same domain: Language & Linguistics.

No target changes.

### gUFO

Before: Descriptive Ontology for Linguistic and Cognitive Engineering — Same resource type: Ontology; General Formal Ontology — Same resource type: Ontology; gist — Same resource type: Ontology; CIDOC Conceptual Reference Model — Same resource type: Ontology; Cyc — Same resource type: Ontology.

After: Descriptive Ontology for Linguistic and Cognitive Engineering — Same resource type: Ontology; General Formal Ontology — Same resource type: Ontology; gist — Same resource type: Ontology; CIDOC Conceptual Reference Model — Same resource type: Ontology; Cyc — Same resource type: Ontology.

No target changes.

### Lightweight Information Describing Objects

Before: DDB Provenance Vocabulary — Has part; LIDO Terminology — Has part; Electronic Theses and Dissertations Metadata Standard — Same domain: Library & Cultural Heritage; Encoded Archival Context — Same domain: Library & Cultural Heritage; Lifecycle Data Requirements Guide — Same domain: Library & Cultural Heritage.

After: DDB Provenance Vocabulary — Has part; LIDO Terminology — Has part; Electronic Theses and Dissertations Metadata Standard — Same domain: Library & Cultural Heritage; Encoded Archival Context — Same domain: Library & Cultural Heritage; Lifecycle Data Requirements Guide — Same domain: Library & Cultural Heritage.

No target changes.

### Neo4j Ontology Graph Specification

Before: LinkML — Same resource type: Ontology Language; Ontological Modeling Language — Same resource type: Ontology Language; Dolfin — Same resource type: Ontology Language; Gellish — Same resource type: Ontology Language; Object Process Methodology — Same resource type: Ontology Language.

After: LinkML — Same resource type: Ontology Language; Ontological Modeling Language — Same resource type: Ontology Language; Dolfin — Same resource type: Ontology Language; Gellish — Same resource type: Ontology Language; Object Process Methodology — Same resource type: Ontology Language.

No target changes.

### Ontology for Rehabilitation [Traumatic Brain Injury]

Before: Basic Formal Ontology — Uses; ACGT Master Ontology — Same domain: Healthcare; Brucellosis Ontology — Same domain: Healthcare; Cerebrotendinous Xanthomatosis Ontology — Same domain: Healthcare; CHRONIOUS Ontology Suite — Same domain: Healthcare.

After: Basic Formal Ontology — Uses; ACGT Master Ontology — Same domain: Healthcare; Brucellosis Ontology — Same domain: Healthcare; Cerebrotendinous Xanthomatosis Ontology — Same domain: Healthcare; CHRONIOUS Ontology Suite — Same domain: Healthcare.

No target changes.

### Plant Trait Ontology

Before: Agronomy Ontology — Used by; C. elegans development ontology — Same domain: Life sciences; C. elegans Gross Anatomy Ontology — Same domain: Life sciences; Drug Ontology — Same domain: Life sciences; Glycan Naming and Subsumption Ontology (GNOme) — Same domain: Life sciences.

After: Agronomy Ontology — Used by; C. elegans development ontology — Same domain: Life sciences; C. elegans Gross Anatomy Ontology — Same domain: Life sciences; Drug Ontology — Same domain: Life sciences; Glycan Naming and Subsumption Ontology (GNOme) — Same domain: Life sciences.

No target changes.

### Polythematic Structured Subject Heading System

Before: UNESCO Thesaurus — Same resource type: Controlled Vocabulary; AIATSIS Place Thesaurus — Same resource type: Controlled Vocabulary; AIATSIS Subject Thesaurus — Same resource type: Controlled Vocabulary; American Folklore Society Ethnographic Thesaurus — Same resource type: Controlled Vocabulary; Aquatic Sciences and Fisheries Thesaurus — Same resource type: Controlled Vocabulary.

After: UNESCO Thesaurus — Same resource type: Controlled Vocabulary; AIATSIS Place Thesaurus — Same resource type: Controlled Vocabulary; AIATSIS Subject Thesaurus — Same resource type: Controlled Vocabulary; American Folklore Society Ethnographic Thesaurus — Same resource type: Controlled Vocabulary; Aquatic Sciences and Fisheries Thesaurus — Same resource type: Controlled Vocabulary.

No target changes.

### PROV-O: The PROV Ontology

Before: NORIA-O — Used by; Core organization ontology — Used by; Library of Ontologies — Same domain: Technology & Web; RDF Mapping Language — Same domain: Technology & Web; Semantic Sensor Network Ontology — Same domain: Technology & Web.

After: NORIA-O — Used by; Core organization ontology — Used by; Library of Ontologies — Same domain: Technology & Web; RDF Mapping Language — Same domain: Technology & Web; Semantic Sensor Network Ontology — Same domain: Technology & Web.

No target changes.

### Schema.org

Before: Behaviour Change Intervention Ontology — Used by; Croissant — Used by; Actionable Intelligence Retrieval System — Same domain: Technology & Web; Algorithm-Implementation-Execution Ontology Design Pattern — Same domain: Technology & Web; auth/acl Ontology — Same domain: Technology & Web.

After: GS1 Web Vocabulary — Used by; Schema.org Accessibility Properties for Discoverability Vocabulary — Used by; Behaviour Change Intervention Ontology — Used by; Croissant — Used by; Actionable Intelligence Retrieval System — Same domain: Technology & Web.

Change: direct use evidence enters the existing ranking; lower-ranked qualifying peers leave the five-result list.

### sldt-semantic-models

Before: dpp: namespace — Same domain: Supply chain and commerce; EPCIS — Same domain: Supply chain and commerce; Vehicle Sales Ontology — Same domain: Supply chain and commerce; GS1 Core Business Vocabulary — Same domain: Supply chain and commerce; GS1 Web Vocabulary — Same domain: Supply chain and commerce.

After: Resource Description Framework — Uses; dpp: namespace — Same domain: Supply chain and commerce; EPCIS — Same domain: Supply chain and commerce; Vehicle Sales Ontology — Same domain: Supply chain and commerce; GS1 Core Business Vocabulary — Same domain: Supply chain and commerce.

Change: direct use evidence enters the existing ranking; lower-ranked qualifying peers leave the five-result list.

### SNOMED CT

Before: ClinicalTrials.gov — Same domain: Healthcare; DailyMed — Same domain: Healthcare; digital health and medical technologies — Same domain: Healthcare; Orphanet Ontology of Rare Diseases — Same domain: Healthcare; Cochrane Core Ontology — Same domain: Healthcare.

After: ClinicalTrials.gov — Same domain: Healthcare; DailyMed — Same domain: Healthcare; digital health and medical technologies — Same domain: Healthcare; Orphanet Ontology of Rare Diseases — Same domain: Healthcare; Cochrane Core Ontology — Same domain: Healthcare.

No target changes.

### Universal Decimal Classification

Before: American Folklore Society Ethnographic Thesaurus — Same domain: Library & Cultural Heritage; Canadian Subject Headings — Same domain: Library & Cultural Heritage; Controlled Vocabulary for Rare Materials Cataloging — Same domain: Library & Cultural Heritage; CRediT — Same domain: Library & Cultural Heritage; DDB Provenance Vocabulary — Same domain: Library & Cultural Heritage.

After: American Folklore Society Ethnographic Thesaurus — Same domain: Library & Cultural Heritage; Canadian Subject Headings — Same domain: Library & Cultural Heritage; Controlled Vocabulary for Rare Materials Cataloging — Same domain: Library & Cultural Heritage; CRediT — Same domain: Library & Cultural Heritage; DDB Provenance Vocabulary — Same domain: Library & Cultural Heritage.

No target changes.

### Apache Jena Fuseki

Before: Apache Jena — Both classified as: triplestore; Apache Marmotta — Both classified as: triplestore; Apache Rya — Both classified as: triplestore; ArcadeDB — Both classified as: graph database management system; OrientDB — Both classified as: graph database management system.

After: Apache Jena — Both classified as: triplestore; Apache Marmotta — Both classified as: triplestore; Apache Rya — Both classified as: triplestore; ArcadeDB — Both classified as: graph database management system; OrientDB — Both classified as: graph database management system.

No target changes.

### Apache Jena

Before: Apache Marmotta — Both classified as: triplestore; Apache Rya — Both classified as: triplestore; Apache Jena Fuseki — Both classified as: triplestore; Blazegraph — Both classified as: triplestore; Mulgara — Both classified as: triplestore.

After: TopBraid SHACL API — Used by; SANSA — Used by; Apache Marmotta — Both classified as: triplestore; Apache Rya — Both classified as: triplestore; Apache Jena Fuseki — Both classified as: triplestore.

Change: direct use evidence enters the existing ranking; lower-ranked qualifying peers leave the five-result list.

### Context Ontology Accelerator

Before: ELK — Uses; ontop — Uses; HermiT — Uses; LinkML — Same software type: Ontology Engineering; ontology-quality-suite — Same software type: Ontology Engineering.

After: ELK — Uses; ontop — Uses; HermiT — Uses; LinkML — Same software type: Ontology Engineering; ontology-quality-suite — Same software type: Ontology Engineering.

No target changes.

### Graphameleon Web extension

Before: YARRRML Parser — Same software type: RDF Data Mapping / ETL; Chimera — Same software type: RDF Data Mapping / ETL; CoW — Same software type: RDF Data Mapping / ETL; D2RQ — Same software type: RDF Data Mapping / ETL; Dragoman RDF mapping optimizer — Same software type: RDF Data Mapping / ETL.

After: Resource Description Framework — Uses; YARRRML Parser — Same software type: RDF Data Mapping / ETL; Chimera — Same software type: RDF Data Mapping / ETL; CoW — Same software type: RDF Data Mapping / ETL; D2RQ — Same software type: RDF Data Mapping / ETL.

Change: direct use evidence enters the existing ranking; lower-ranked qualifying peers leave the five-result list.

### LinkML-Scala

Before: SANSA — Same software type: Developer Library; Elda Linked Data API — Same software type: Developer Library; neosemantics — Same software type: Developer Library; pySHACL — Same software type: Developer Library; Raptor RDF Syntax Library — Same software type: Developer Library.

After: LinkML — Uses; SANSA — Same software type: Developer Library; Elda Linked Data API — Same software type: Developer Library; neosemantics — Same software type: Developer Library; pySHACL — Same software type: Developer Library.

Change: direct use evidence enters the existing ranking; lower-ranked qualifying peers leave the five-result list.

### NebulaGraph

Before: OrientDB — Both classified as: graph database management system; TypeDB — Both classified as: graph database management system; FlockDB — Both classified as: graph database management system; Blazegraph — Both classified as: graph database management system; Neo4j — Both classified as: graph database management system.

After: OrientDB — Both classified as: graph database management system; TypeDB — Both classified as: graph database management system; FlockDB — Both classified as: graph database management system; Blazegraph — Both classified as: graph database management system; Neo4j — Both classified as: graph database management system.

No target changes.

### Neo4j

Before: Linkurious Enterprise — Used by; neosemantics — Used by; Open Research Knowledge Graph — Used by; OrientDB — Both classified as: graph database management system; Blazegraph — Both classified as: graph database management system.

After: Linkurious Enterprise — Used by; neosemantics — Used by; Open Research Knowledge Graph — Used by; OrientDB — Both classified as: graph database management system; Blazegraph — Both classified as: graph database management system.

No target changes.

### NitrosBase

Before: MarkLogic — Both classified as: triplestore; ArangoDB — Both classified as: graph database management system; AllegroGraph — Both classified as: graph database management system; Blazegraph — Both classified as: graph database management system; Polypheny — Both classified as: graph database management system.

After: MarkLogic — Both classified as: triplestore; ArangoDB — Both classified as: graph database management system; AllegroGraph — Both classified as: graph database management system; Blazegraph — Both classified as: graph database management system; Polypheny — Both classified as: graph database management system.

No target changes.

### OntOlogy Pitfall Scanner!

Before: Intentional Arrangement SKOS Editor — Same software type: Ontology Engineering; OntoBricks — Same software type: Ontology Engineering; Ontofox — Same software type: Ontology Engineering; PoolParty Semantic Suite — Same software type: Ontology Engineering; SHACTOR — Same software type: Ontology Engineering.

After: Intentional Arrangement SKOS Editor — Same software type: Ontology Engineering; OntoBricks — Same software type: Ontology Engineering; Ontofox — Same software type: Ontology Engineering; PoolParty Semantic Suite — Same software type: Ontology Engineering; SHACTOR — Same software type: Ontology Engineering.

No target changes.

### Ontotext GraphDB

Before: Blazegraph — Both classified as: graph database management system; Stardog — Both classified as: graph database management system; Apache Rya — Both classified as: triplestore; Mulgara — Both classified as: triplestore; AllegroGraph — Both classified as: graph database management system.

After: Resource Description Framework — Uses; Blazegraph — Both classified as: graph database management system; Stardog — Both classified as: graph database management system; Apache Rya — Both classified as: triplestore; Mulgara — Both classified as: triplestore.

Change: direct use evidence enters the existing ranking; lower-ranked qualifying peers leave the five-result list.

### Owlready2

Before: CubicWeb — Same software type: Developer Library; cwm — Same software type: Developer Library; EMMOntoPy — Same software type: Developer Library; KGX — Same software type: Developer Library; pySHACL — Same software type: Developer Library.

After: CubicWeb — Same software type: Developer Library; cwm — Same software type: Developer Library; EMMOntoPy — Same software type: Developer Library; KGX — Same software type: Developer Library; pySHACL — Same software type: Developer Library.

No target changes.

### Oxigraph

Before: SPARQL — Uses; Apache Marmotta — Both classified as: triplestore; Apache Rya — Both classified as: triplestore; Dgraph — Both classified as: graph database management system; FlockDB — Both classified as: graph database management system.

After: Resource Description Framework — Uses; SPARQL — Uses; Apache Marmotta — Both classified as: triplestore; Apache Rya — Both classified as: triplestore; Dgraph — Both classified as: graph database management system.

Change: direct use evidence enters the existing ranking; lower-ranked qualifying peers leave the five-result list.

### Protégé

Before: Software Ontology — Used by; WebProtégé — Both classified as: ontology editor; dot15926 — Both classified as: ontology editor; CMAP Tools — Both classified as: ontology editor; Hozo — Both classified as: ontology editor.

After: Software Ontology — Used by; WebProtégé — Both classified as: ontology editor; dot15926 — Both classified as: ontology editor; CMAP Tools — Both classified as: ontology editor; Hozo — Both classified as: ontology editor.

No target changes.

### RDF4J

Before: metaphactory — Used by; neosemantics — Same software type: Developer Library; RDFUnit — Same software type: Developer Library; TopBraid SHACL API — Same software type: Developer Library; EMMOntoPy — Same software type: Developer Library.

After: metaphactory — Used by; neosemantics — Same software type: Developer Library; RDFUnit — Same software type: Developer Library; TopBraid SHACL API — Same software type: Developer Library; EMMOntoPy — Same software type: Developer Library.

No target changes.

### RDFLib

Before: EMMOntoPy — Same software type: Developer Library; KGX — Same software type: Developer Library; CubicWeb — Same software type: Developer Library; cwm — Same software type: Developer Library; Owlready2 — Same software type: Developer Library.

After: OWL-RL — Used by; Resource Description Framework — Uses; EMMOntoPy — Same software type: Developer Library; KGX — Same software type: Developer Library; CubicWeb — Same software type: Developer Library.

Change: direct use evidence enters the existing ranking; lower-ranked qualifying peers leave the five-result list.

### Relate by Neo4j

Before: no recommendations.

After: no recommendations.

No target changes.

### Relationship Visualizer

Before: edgextract — Both classified as: graph visualization software; Linkurious Enterprise — Both classified as: graph visualization software; Meurs Challenger — Both classified as: graph visualization software; SEN — Both classified as: graph visualization software; Wikiframe Visual Graph — Both classified as: graph visualization software.

After: edgextract — Both classified as: graph visualization software; Linkurious Enterprise — Both classified as: graph visualization software; Meurs Challenger — Both classified as: graph visualization software; SEN — Both classified as: graph visualization software; Wikiframe Visual Graph — Both classified as: graph visualization software.

No target changes.

### SHACL Play!

Before: FOOPS! — Same software type: Ontology Engineering; O’FAIRE — Same software type: Ontology Engineering; Protégé — Same software type: Ontology Engineering; ROBOT is an OBO Tool — Same software type: Ontology Engineering; SHACTOR — Same software type: Ontology Engineering.

After: Resource Description Framework — Uses; SHACL — Uses; FOOPS! — Same software type: Ontology Engineering; O’FAIRE — Same software type: Ontology Engineering; Protégé — Same software type: Ontology Engineering.

Change: direct use evidence enters the existing ranking; lower-ranked qualifying peers leave the five-result list.

### Skosmos

Before: no recommendations.

After: no recommendations.

No target changes.

### Stardog

Before: Ontotext GraphDB — Both classified as: graph database management system; AllegroGraph — Both classified as: graph database management system; Amazon Neptune — Both classified as: graph database management system; Blazegraph — Both classified as: graph database management system; NitrosBase — Both classified as: graph database management system.

After: Resource Description Framework — Uses; Web Ontology Language — Uses; Ontotext GraphDB — Both classified as: graph database management system; AllegroGraph — Both classified as: graph database management system; Amazon Neptune — Both classified as: graph database management system.

Change: direct use evidence enters the existing ranking; lower-ranked qualifying peers leave the five-result list.

### Triplewave

Before: Jelly — Same software type: Stream Processing; CQELS — Same software type: Stream Processing; Kolibrie SPARQL engine — Same software type: Stream Processing; SMASSIF-RML — Same software type: Stream Processing; ssb-consum-up — Same software type: Stream Processing.

After: Resource Description Framework — Uses; Jelly — Same software type: Stream Processing; CQELS — Same software type: Stream Processing; Kolibrie SPARQL engine — Same software type: Stream Processing; SMASSIF-RML — Same software type: Stream Processing.

Change: direct use evidence enters the existing ranking; lower-ranked qualifying peers leave the five-result list.

### WebProtégé

Before: Protégé — Both classified as: ontology editor; Knoodl — Both classified as: ontology editor; OntoWiki — Both classified as: ontology editor; CMAP Tools — Both classified as: ontology editor; dot15926 — Both classified as: ontology editor.

After: Web Ontology Language — Uses; Protégé — Both classified as: ontology editor; Knoodl — Both classified as: ontology editor; OntoWiki — Both classified as: ontology editor; CMAP Tools — Both classified as: ontology editor.

Change: direct use evidence enters the existing ranking; lower-ranked qualifying peers leave the five-result list.

## Reproduce

Use an untouched checkout of the pinned baseline and a separate staging copy containing the patched scripts and ontology. Replay `scripts/shared_tags.py --root STAGE --only catalog`, refresh recommendations against the unchanged `data/page_qids.json` membership, then run `python audits/task61/evaluate.py BASE STAGE`. The script compares protected fields and immutable files, validates every relationship and writes the review artifacts. No network or source refresh is required.
