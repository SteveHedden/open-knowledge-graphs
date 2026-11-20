# Auryn admission review — issue 296

Reviewed November 19, 2026. Decision: include Auryn as a distinct software entry through the existing software (`Q7397`) plus knowledge graph construction purpose (`P366 Q120971305`) route. No new class or item-specific exception.

## Identity and sourcing

Name/alias searches (Auryn, CodeGraph Auryn, FalkorDB Auryn) and official/repository URL searches found no matching Wikidata software item. The live catalog contained FalkorDB but not Auryn. The named product has its own repository, package, documentation, license and release history, establishing a clearly identifiable entity supported by substantive public references. It is not the database, company, or a general method.

Created https://www.wikidata.org/wiki/Q142219047 (revision 2572414222); all eight sourced statements and labels/description/aliases verified by readback. Claims: software; knowledge graph construction purpose; uses FalkorDB Q141103185; MIT license; Python; official website; repository; version 0.8.2 with November 18, 2026 release-date qualifier.

Primary sources:
- https://www.falkordb.com/products/codegraph-auryn/
- https://github.com/FalkorDB/Auryn
- https://github.com/FalkorDB/Auryn/blob/main/pyproject.toml
- https://github.com/FalkorDB/Auryn/blob/main/packages/core/src/auryn/core/graph_model.py
- https://github.com/FalkorDB/Auryn/blob/main/LICENSE
- https://github.com/FalkorDB/FalkorDB/blob/main/LICENSE
- https://github.com/FalkorDB/Auryn/releases/tag/v0.8.2

Auryn constructs typed code entities and explicit relationships (calls, inheritance, dependencies) in a queryable property graph. Its package explicitly describes a knowledge graph. RDF/OWL compatibility is not claimed. It exposes this graph to coding agents through MCP; admission does not rely solely on the agent interface or on vector similarity search.

## License scope

Auryn's repository license is MIT. FalkorDB's database license is SSPL v1. Record the uses relationship and preserve the separate license on each item; do not assign SSPL to Auryn or describe the whole stack as MIT. No vendor performance claim has been independently verified or incorporated into catalog metadata.

## Classification

Prepared a standard evidence-bound review against the verified Wikidata title, description and Python language statement in an isolated staging catalog. Assign Technology & Web, primary software type Knowledge Graph Construction, construction activity, and Python. The property graph is independently queryable in FalkorDB and viewable by humans, supporting construction as the primary type. AI agent context is documented, but the current classification contract supports only one primary software type. All review dimensions considered; the direct uses-FalkorDB relationship comes from Wikidata rather than an inferred tag.

Only the immutable classification review and its exact evidence are committed. The temporary staging dataset is not published. The normal publisher must revalidate source-content and vocabulary compatibility against the next imported record. Keep #296 open until the software entry, licensing, relationship and classifications are verified live.
