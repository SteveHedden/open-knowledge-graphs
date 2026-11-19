# Issue 293 admission review

Reviewed November 18, 2026. Tracking: https://github.com/SteveHedden/open-knowledge-graphs/issues/293

## Decisions

| Candidate | Wikidata | Decision | Basis |
| --- | --- | --- | --- |
| Microsoft GraphRAG | Q142208316 | Approved; awaiting publication | Software library with explicit knowledge graph construction purpose. |
| Repo Mind Light | Q142208317 | Approved; awaiting publication | Existing AI agent memory software route; public runnable container and incremental on-disk repository context. |
| GraphRAG Zero | Q142208315 | Rejected under current OKG admission scope | Documented graph-guided retrieval component; evidence does not establish knowledge graph construction or independent agent-memory functionality. A Wikidata item and a uses relationship do not by themselves establish OKG eligibility. |

No new Wikidata classes or item-specific exceptions were added. Zero's proprietary license is not the reason for exclusion. Repo Mind Light's license stays unset pending clarification of the container label's scope.

## General rule and cohort

Require software ancestry (`P31/P279* Q7397`) AND exact use (`P366 Q120971305`, knowledge graph construction). Class ancestry is allowed, purpose ancestry is not. The checked query returns GraphRAG and Biopragmatics Stack only; see `purpose-cohort.json`. The latter is an identifiable software suite whose official site describes interconnected tools for biomedical data and knowledge processing, distinct from its component tools. Neither generic RAG nor information retrieval nor merely consuming a KG qualifies. Existing metadata and page gates remain unchanged.

## Primary evidence

- GraphRAG pipeline: https://microsoft.github.io/graphrag/index/default_dataflow/
- GraphRAG repository: https://github.com/microsoft/graphrag
- Repo Mind Light architecture, availability and Zero's proprietary status: https://githubnext.com/projects/repo-mind-light/
- Microsoft Research description of Zero: https://www.microsoft.com/en-us/research/story/the-evolution-of-graphrag-advancing-systems-and-evaluation-together/
- Biopragmatics Stack: https://biopragmatics.github.io/ and https://github.com/biopragmatics

## Classification preparation

The two approved Microsoft records were fetched with the normal metadata query and projection functions into an isolated local staging snapshot. Evidence-bound reviews assign Technology & Web to both, Knowledge Graph Construction software type and construction/RAG activities to GraphRAG, and AI Agent Tooling software type to Repo Mind Light. All dimensions were reviewed; no unsupported tools or activities were inferred for Repo Mind Light. The original graph-producing pipeline documents exportable graph artifacts, distinguishing GraphRAG from agent runtime memory.

Only the immutable review log and exact evidence snapshots accompany the code. Temporary software datasets and backlog outputs are not published or committed. The publisher must revalidate these reviews against the actual overnight inputs. Any upstream content change correctly makes them pending again.

## Remaining verification

After merge, allow scheduled software refresh and publication. Verify the two approved QIDs, licensing fields, classifications and individual pages live before closing #293. No workflow dispatch is part of this change. Zero has a completed scope decision; licensing clarification for Repo Mind Light remains a separate unresolved metadata question.
