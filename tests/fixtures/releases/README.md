# Wikidata release examples

Read-only captures from Special:EntityData on 2026-09-20. Each item retains its
revision ID and unmodified P348/P577 claims, including ranks, qualifiers and
references. Other claims are intentionally omitted. These are source fixtures,
not assertions that all items have a release.

- Q3475322 Schema.org: preferred 30.1, paired date 2026-09-15.
- Q141112433 Raptor: preferred 2.0.16, paired date 2023-03-01; normal statements
  include higher-looking versions that must not override preferred rank.
- Q4866972 Basic Formal Ontology, Q135085 Gene Ontology, Q54872 RDF and
  Q140523058 SAMM: no P348 statements in these captures.

Verify a capture against `https://www.wikidata.org/w/index.php?oldid=REVISION`.
A missing P348 does not mean a project has never released anything; it means
this Wikidata-based integration cannot claim a release from those statements.
