#!/usr/bin/env python3
"""Deterministic graph-evidence recommendations across OKG resource catalogs."""

from __future__ import annotations

import json
import re
from collections import Counter
from functools import lru_cache
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable, Mapping
from urllib.parse import urlsplit, urlunsplit

from rdflib import Graph, Literal, URIRef
from rdflib.namespace import DCTERMS, RDF, RDFS, SKOS, XSD

from semantic_config import OKG


QID_RE = re.compile(r"(Q\d+)$")
TOKEN_RE = re.compile(r"[a-z0-9]+")
MULTI_TENANT_REPOSITORY_HOSTS = frozenset(
    {
        "bitbucket.org",
        "github.com",
        "gitlab.com",
    }
)
TEXT_STOP_WORDS = frozenset(
    {
        "about",
        "and",
        "data",
        "for",
        "from",
        "graph",
        "knowledge",
        "ontology",
        "resource",
        "semantic",
        "software",
        "that",
        "the",
        "this",
        "tool",
        "using",
        "vocabulary",
        "with",
    }
)

# Degree is a corpus filter, not proof of semantic specificity. These broad
# artifact classes are supporting evidence even in a small catalog. Keep this
# policy at class level, never as exceptions for individual resource pairs.
BROAD_SOURCE_TYPES = frozenset(
    f"http://www.wikidata.org/entity/{qid}"
    for qid in (
        "Q595971",     # graph database: mixes datasets with engines
        "Q494823",     # data format
        "Q13136",      # reference work
        "Q7397",       # software
        "Q8513",       # database
        "Q1469824",    # controlled vocabulary
        "Q324254",     # ontology
        "Q33002955",   # knowledge graph
        "Q124653107",  # semantic web software
    )
)
MAX_SHARED_SOURCE_TYPE_DEGREE = 64
SOURCE_TYPE_DEGREE_RATIONALE = (
    "Only reviewed specific classes qualify; a fixed maximum of 64 members "
    "across all catalog records bounds fan-out. Rarity never establishes specificity."
)


@dataclass(frozen=True)
class SimilarityConfig:
    """Public scoring contract. An approved graph path or catalog classification is mandatory."""

    direct_relationship: int = 120
    direct_uses: int = 120
    shared_parent: int = 100
    shared_source_type: int = 65
    supporting_source_type: int = 4
    same_repository: int = 90
    same_namespace_family: int = 70
    shared_creator: int = 4
    shared_category: int = 60
    shared_software_type: int = 60
    shared_resource_type: int = 60
    shared_rdf_type: int = 3
    shared_programming_language: int = 4
    shared_license: int = 2
    text_similarity: int = 3
    text_similarity_floor: float = 0.25
    score_threshold: int = 60
    max_related: int = 5
    max_shared_parent_degree: int = 6
    max_shared_source_type_degree: int = MAX_SHARED_SOURCE_TYPE_DEGREE

    def __post_init__(self) -> None:
        if self.score_threshold <= 0:
            raise ValueError("score_threshold must be positive")
        if not 1 <= self.max_related <= 5:
            raise ValueError("max_related must be between one and five")
        if self.max_shared_parent_degree < 2:
            raise ValueError("max_shared_parent_degree must be at least two")
        if self.max_shared_source_type_degree < 2:
            raise ValueError("max_shared_source_type_degree must be at least two")
        if not 0.0 <= self.text_similarity_floor <= 1.0:
            raise ValueError("text_similarity_floor must be between zero and one")


DEFAULT_CONFIG = SimilarityConfig()


@dataclass(frozen=True)
class ResourceFeatures:
    subject: URIRef
    source_entities: frozenset[str]
    parents: frozenset[str]
    uses: frozenset[str]
    source_types: frozenset[str]
    creators: frozenset[str]
    repositories: frozenset[str]
    namespace_families: frozenset[str]
    categories: frozenset[str]
    software_types: frozenset[str]
    rdf_types: frozenset[str]
    programming_languages: frozenset[str]
    licenses: frozenset[str]
    text_tokens: frozenset[str]


@dataclass(frozen=True)
class SimilarityContext:
    """Corpus facts used to decide whether shared identity is discriminating."""

    parent_degrees: Mapping[str, int]
    catalog_source_entities: frozenset[str]
    source_type_degrees: Mapping[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class ScoreComponent:
    feature: str
    score: int
    evidence: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "feature": self.feature,
            "score": self.score,
            "evidence": list(self.evidence),
        }


@dataclass(frozen=True)
class PairScore:
    subject: str
    candidate: str
    score: int
    qualifies: bool
    qualifying_reasons: tuple[str, ...]
    components: tuple[ScoreComponent, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "subject": self.subject,
            "candidate": self.candidate,
            "score": self.score,
            "qualifies": self.qualifies,
            "qualifyingReasons": list(self.qualifying_reasons),
            "components": [component.as_dict() for component in self.components],
        }


@lru_cache(maxsize=1)
def discovery_classifications():
    """Use the catalog's maintained vocabularies, not an extra project allowlist."""
    root = Path(__file__).resolve().parents[1] / 'vocabularies'
    result = {}
    for key, filename, concept_class, scheme in (
        ('shared_category', 'categories.ttl', OKG.Category, 'categories'),
        ('shared_software_type', 'software-types.ttl', OKG.SoftwareType, 'software-types'),
    ):
        graph = Graph().parse(root / filename)
        labels = {}
        for concept in graph.subjects(RDF.type, concept_class):
            if concept == OKG.GeneralCrossDomain:
                continue  # An explicitly cross-domain resource has no shared subject domain.
            if (concept, SKOS.inScheme, URIRef('https://openknowledgegraphs.com/vocabularies/' + scheme)) not in graph:
                continue
            label = graph.value(concept, SKOS.prefLabel) or graph.value(concept, RDFS.label)
            if label:
                labels[str(concept)] = str(label)
        result[key] = labels
    # Only maintained resource kinds qualify, never the abstract Resource base
    # or Software. Keep this fallback distinct from specific Wikidata classes.
    ontology = Graph().parse(root.parent / 'ontology.ttl')
    result['shared_resource_type'] = {
        str(kind): str(ontology.value(kind, RDFS.label))
        for kind in ontology.subjects(RDFS.subClassOf, OKG.Resource)
        if kind != OKG.Software and (kind, RDF.type, RDFS.Class) in ontology
    }
    return result


def discovery_values(features, feature):
    # Domain discovery connects resources; functional-type discovery connects tools.
    # A ubiquitous software domain must not connect unrelated tools or cross catalogs.
    kind, values = {'shared_category': ('resource', features.categories),
                    'shared_software_type': ('software', features.software_types),
                    'shared_resource_type': ('resource', features.rdf_types)}[feature]
    if not str(features.subject).startswith('https://openknowledgegraphs.com/' + kind + '/'):
        return frozenset()
    return values & discovery_classifications()[feature].keys()


def _iri_values(graph: Graph, subject: URIRef, predicate: URIRef) -> frozenset[str]:
    return frozenset(
        str(value)
        for value in graph.objects(subject, predicate)
        if isinstance(value, URIRef)
    )


def _literal_values(graph: Graph, subject: URIRef, predicate: URIRef) -> frozenset[str]:
    return frozenset(
        str(value).strip().casefold()
        for value in graph.objects(subject, predicate)
        if isinstance(value, Literal) and str(value).strip()
    )


def _wikidata_entity(value: str) -> str | None:
    match = QID_RE.search(value.rstrip("/"))
    if not match:
        return None
    return f"http://www.wikidata.org/entity/{match.group(1)}"


def canonical_repository(value: str) -> str | None:
    """Normalize one repository URL without equating repositories by owner."""
    parsed = urlsplit(value.strip())
    if parsed.scheme.casefold() not in {"http", "https"} or not parsed.netloc:
        return None
    host = parsed.hostname.casefold() if parsed.hostname else ""
    if not host:
        return None
    port = parsed.port
    authority = host if port is None else f"{host}:{port}"
    path = re.sub(r"/+", "/", parsed.path).rstrip("/")
    if path.casefold().endswith(".git"):
        path = path[:-4]
    if not path:
        return None
    path_segments = tuple(segment for segment in path.split("/") if segment)
    if host in MULTI_TENANT_REPOSITORY_HOSTS and len(path_segments) < 2:
        # A single path segment on these hosts identifies an account, workspace,
        # or group—not a repository. Treating it as structural evidence would
        # relate every resource that merely cites the same hosting organization.
        return None
    return urlunsplit(("https", authority, path, "", ""))


def namespace_family(value: str) -> str | None:
    """Return a conservative family key: scheme, authority, and full base path.

    A host by itself is deliberately not a family. Query strings, fragments,
    and a trailing namespace delimiter are presentation differences only.
    """
    parsed = urlsplit(value.strip())
    scheme = parsed.scheme.casefold()
    if not scheme:
        return None
    if parsed.netloc:
        host = parsed.hostname.casefold() if parsed.hostname else ""
        if not host:
            return None
        port = parsed.port
        authority = host if port is None else f"{host}:{port}"
        path = re.sub(r"/+", "/", parsed.path).rstrip("/#")
        if not path:
            return None
        return urlunsplit((scheme, authority, path, "", ""))
    path = parsed.path.rstrip("/#")
    return f"{scheme}:{path}" if path else None


def _text_tokens(graph: Graph, subject: URIRef) -> frozenset[str]:
    content = " ".join(
        str(value)
        for predicate in (OKG.title, OKG.description)
        for value in graph.objects(subject, predicate)
        if isinstance(value, Literal)
    ).casefold()
    return frozenset(
        token
        for token in TOKEN_RE.findall(content)
        if len(token) >= 4 and token not in TEXT_STOP_WORDS
    )


def features_for_resource(graph: Graph, subject: URIRef) -> ResourceFeatures:
    source_entities = frozenset(
        entity
        for value in _iri_values(graph, subject, OKG.wikidataId)
        if (entity := _wikidata_entity(value)) is not None
    )
    repositories = frozenset(
        normalized
        for value in _iri_values(graph, subject, OKG.sourceRepo)
        if (normalized := canonical_repository(value)) is not None
    )
    namespace_families = frozenset(
        family
        for value in _iri_values(graph, subject, OKG.namespaceURI)
        if (family := namespace_family(value)) is not None
    )
    return ResourceFeatures(
        subject=subject,
        source_entities=source_entities,
        parents=_iri_values(graph, subject, DCTERMS.isPartOf),
        uses=_iri_values(graph, subject, OKG.uses),
        source_types=_iri_values(graph, subject, OKG.sourceType),
        creators=_iri_values(graph, subject, OKG.creator),
        repositories=repositories,
        namespace_families=namespace_families,
        categories=_iri_values(graph, subject, OKG.category),
        software_types=_iri_values(graph, subject, OKG.softwareType),
        rdf_types=_iri_values(graph, subject, RDF.type),
        programming_languages=_literal_values(graph, subject, OKG.programmingLanguage),
        licenses=_iri_values(graph, subject, OKG.hasLicense),
        text_tokens=_text_tokens(graph, subject),
    )


def _comparable_subjects(graph: Graph) -> list[URIRef]:
    return sorted(
        {
            subject
            for subject in graph.subjects(OKG.wikidataId, None)
            if isinstance(subject, URIRef)
            and str(subject).startswith(('https://openknowledgegraphs.com/resource/', 'https://openknowledgegraphs.com/software/'))
            and (subject, OKG.homepage, None) in graph
        },
        key=str,
    )


def build_similarity_context(graphs: Iterable[Graph]) -> SimilarityContext:
    """Count source types across all records; parent context uses page candidates."""
    parent_members: dict[str, set[str]] = {}
    source_type_members: dict[str, set[str]] = {}
    catalog_source_entities: set[str] = set()
    for graph in graphs:
        for subject in set(graph.subjects(OKG.wikidataId, None)):
            if not isinstance(subject, URIRef):
                continue
            features = features_for_resource(graph, subject)
            for source_type in features.source_types:
                source_type_members.setdefault(source_type, set()).add(str(subject))
            # Page eligibility still controls parent/candidate behavior; it must
            # not control the apparent rarity of a source type.
            if (subject, OKG.homepage, None) not in graph:
                continue
            catalog_source_entities.update(features.source_entities)
            for parent in features.parents:
                parent_members.setdefault(parent, set()).add(str(subject))
    return SimilarityContext(
        parent_degrees={parent: len(members) for parent, members in parent_members.items()},
        catalog_source_entities=frozenset(catalog_source_entities),
        source_type_degrees={
            source_type: len(members) for source_type, members in source_type_members.items()
        },
    )


def _intersection(left: frozenset[str], right: frozenset[str]) -> tuple[str, ...]:
    return tuple(sorted(left & right))


# Reviewed class-level policy, never resource-pair exceptions. Unknown classes
# remain corroborating evidence until their meaning is reviewed. The bound is
# fixed; rarity alone never establishes specificity.
APPROVED_SHARED_CLASSES = {
    "Q108810446": "graph visualization software",
    "Q105846678": "unit ontology",
    "Q119509990": "name authority file",
    "Q120910071": "ontology design pattern",
    "Q1235236": "document-oriented database management system",
    "Q125577535": "SPARQL engine",
    "Q139700003": "tariff nomenclature",
    "Q19915239": "taxonomy of birds",
    "Q26261192": "SPARQL endpoint",
    "Q2943035": "medication classification",
    "Q3932296": "relational database management system",
    "Q3539533": "triplestore",
    "Q453843": "ontology editor",
    "Q137916409": "graph database management system",
    "Q61782519": "health data interoperability standard",
    "Q7247163": "procedure code",
    "Q856567": "cataloguing rules",
}


def _source_type_qualifies(
    source_type: str, context: SimilarityContext, config: SimilarityConfig
) -> bool:
    return (
        source_type not in BROAD_SOURCE_TYPES
        and source_type.startswith("http://www.wikidata.org/entity/")
        and source_type.rsplit("/", 1)[-1] in APPROVED_SHARED_CLASSES
        and 2 <= context.source_type_degrees.get(source_type, 0)
        <= config.max_shared_source_type_degree
    )


def score_pair(
    left: ResourceFeatures,
    right: ResourceFeatures,
    config: SimilarityConfig = DEFAULT_CONFIG,
    context: SimilarityContext | None = None,
) -> PairScore:
    if left.subject == right.subject:
        raise ValueError("A resource cannot be scored against itself")

    components: list[ScoreComponent] = []
    qualifying_reasons: list[str] = []

    direct_evidence = []
    if left.parents & right.source_entities:
        direct_evidence.append(f"{left.subject} dcterms:isPartOf {right.subject}")
    if right.parents & left.source_entities:
        direct_evidence.append(f"{right.subject} dcterms:isPartOf {left.subject}")
    if direct_evidence:
        components.append(
            ScoreComponent(
                "direct_relationship",
                config.direct_relationship,
                tuple(sorted(direct_evidence)),
            )
        )
        qualifying_reasons.append("direct_relationship")

    uses_evidence = []
    if left.uses & right.source_entities:
        uses_evidence.append(f"{left.subject} okg:uses {right.subject}")
    if right.uses & left.source_entities:
        uses_evidence.append(f"{right.subject} okg:uses {left.subject}")
    if uses_evidence:
        components.append(
            ScoreComponent("direct_uses", config.direct_uses, tuple(sorted(uses_evidence)))
        )
        qualifying_reasons.append("direct_uses")

    shared_parents = _intersection(left.parents, right.parents)
    if context is not None:
        shared_parents = tuple(
            parent
            for parent in shared_parents
            if parent in context.catalog_source_entities
            and context.parent_degrees.get(parent, 2) <= config.max_shared_parent_degree
        )
    if shared_parents:
        components.append(
            ScoreComponent("shared_parent", config.shared_parent, shared_parents)
        )
        qualifying_reasons.append("shared_parent")

    shared_source_types: tuple[str, ...] = ()
    if context is not None:
        shared_source_types = tuple(
            source_type
            for source_type in _intersection(left.source_types, right.source_types)
            if _source_type_qualifies(source_type, context, config)
        )
    if shared_source_types:
        components.append(
            ScoreComponent(
                "shared_source_type", config.shared_source_type, shared_source_types
            )
        )
        qualifying_reasons.append("shared_source_type")

    supporting_types = tuple(sorted(
        (left.source_types & right.source_types) - set(shared_source_types)
    ))
    if supporting_types:
        components.append(ScoreComponent(
            "supporting_source_type", config.supporting_source_type, supporting_types
        ))

    structural_specs = (
        ("same_repository", config.same_repository, left.repositories, right.repositories),
        (
            "same_namespace_family",
            config.same_namespace_family,
            left.namespace_families,
            right.namespace_families,
        ),
    )
    for feature, weight, left_values, right_values in structural_specs:
        evidence = _intersection(left_values, right_values)
        if evidence:
            components.append(ScoreComponent(feature, weight, evidence))
            qualifying_reasons.append(feature)

    # Broader discovery is independently eligible, but always ranks below closer paths.
    has_closer_path = bool(qualifying_reasons)
    for feature, weight in (('shared_category', config.shared_category),
                            ('shared_software_type', config.shared_software_type),
                            ('shared_resource_type', config.shared_resource_type)):
        evidence = tuple(sorted(discovery_values(left, feature) & discovery_values(right, feature)))
        if evidence:
            # Within the last tier prefer matching artifact profiles over a
            # broad overlap (e.g. KG vs a resource typed both KG and Ontology).
            if feature == 'shared_resource_type' and not has_closer_path:
                union = discovery_values(left, feature) | discovery_values(right, feature)
                weight += round(10 * len(evidence) / len(union))
            components.append(ScoreComponent(feature, 4 if has_closer_path else weight, evidence))
            qualifying_reasons.append(feature)

    # Authorship corroborates an independently qualified path; it never admits a pair.
    weak_specs = (
        ("shared_creator", config.shared_creator, left.creators, right.creators),
        ("shared_rdf_type", config.shared_rdf_type, left.rdf_types, right.rdf_types),
        (
            "shared_programming_language",
            config.shared_programming_language,
            left.programming_languages,
            right.programming_languages,
        ),
        ("shared_license", config.shared_license, left.licenses, right.licenses),
    )
    for feature, weight, left_values, right_values in weak_specs:
        evidence = _intersection(left_values, right_values)
        if evidence:
            components.append(ScoreComponent(feature, weight, evidence))

    shared_tokens = left.text_tokens & right.text_tokens
    token_union = left.text_tokens | right.text_tokens
    if len(shared_tokens) >= 2 and token_union:
        similarity = len(shared_tokens) / len(token_union)
        if similarity >= config.text_similarity_floor:
            evidence = (*sorted(shared_tokens), f"jaccard={similarity:.6f}")
            components.append(ScoreComponent("text_similarity", config.text_similarity, evidence))

    score = sum(component.score for component in components)
    qualifies = bool(qualifying_reasons) and score >= config.score_threshold
    return PairScore(
        subject=str(left.subject),
        candidate=str(right.subject),
        score=score,
        qualifies=qualifies,
        qualifying_reasons=tuple(qualifying_reasons),
        components=tuple(components),
    )


def _index(
    features: Iterable[ResourceFeatures],
    attribute: str,
) -> dict[str, set[URIRef]]:
    result: dict[str, set[URIRef]] = {}
    for feature_set in features:
        for value in getattr(feature_set, attribute):
            result.setdefault(value, set()).add(feature_set.subject)
    return result


def add_related_resources(
    graph: Graph,
    dataset: str,
    config: SimilarityConfig = DEFAULT_CONFIG,
    context: SimilarityContext | None = None,
    candidate_graph: Graph | None = None,
    eligible_urls: set[str] | None = None,
) -> dict[str, object]:
    """Replace related links in one graph and return deterministic diagnostics."""
    clear_recommendations(graph)
    corpus = candidate_graph if candidate_graph is not None else graph
    subjects = _comparable_subjects(graph)
    candidates_in_corpus = _comparable_subjects(corpus)
    if eligible_urls is not None:
        subjects = [s for s in subjects if str(s) in eligible_urls]
        candidates_in_corpus = [s for s in candidates_in_corpus if str(s) in eligible_urls]
    feature_map = {subject: features_for_resource(corpus, subject) for subject in candidates_in_corpus}
    feature_values = list(feature_map.values())
    indexes = {
        attribute: _index(feature_values, attribute)
        for attribute in (
            "source_entities",
            "parents",
            "uses",
            "source_types",
            "categories",
            "software_types",
            "rdf_types",
            "repositories",
            "namespace_families",
        )
    }
    context = context or build_similarity_context((corpus,))
    suppressed_shared_parents = []
    for parent in sorted(indexes["parents"]):
        degree = context.parent_degrees.get(parent, len(indexes["parents"][parent]))
        reasons = []
        if parent not in context.catalog_source_entities:
            reasons.append("parent_not_cataloged")
        if degree > config.max_shared_parent_degree:
            reasons.append("degree_exceeds_limit")
        if reasons:
            suppressed_shared_parents.append(
                {"parent": parent, "memberCount": degree, "reasons": reasons}
            )
    suppressed_shared_source_types = []
    for source_type in sorted(indexes["source_types"]):
        degree = context.source_type_degrees.get(
            source_type, len(indexes["source_types"][source_type])
        )
        reasons = []
        if source_type in BROAD_SOURCE_TYPES:
            reasons.append("broad_source_type")
        if source_type.rsplit("/", 1)[-1] not in APPROVED_SHARED_CLASSES:
            reasons.append("unreviewed_or_nonspecific_class")
        if degree > config.max_shared_source_type_degree:
            reasons.append("degree_exceeds_limit")
        if reasons:
            suppressed_shared_source_types.append(
                {
                    "sourceType": source_type,
                    "memberCount": degree,
                    "reasons": reasons,
                }
            )

    selected_scores: list[PairScore] = []
    structural_candidate_count = 0
    below_threshold_count = 0
    for subject in subjects:
        features = feature_map[subject]
        candidates: set[URIRef] = set()
        for attribute in ("repositories", "namespace_families"):
            for value in getattr(features, attribute):
                candidates.update(indexes[attribute].get(value, set()))
        for feature, attribute in (('shared_category', 'categories'), ('shared_software_type', 'software_types'), ('shared_resource_type', 'rdf_types')):
            for value in discovery_values(features, feature):
                candidates.update(indexes[attribute].get(value, set()))
        for parent in features.parents:
            if (
                parent in context.catalog_source_entities
                and context.parent_degrees.get(parent, 0) <= config.max_shared_parent_degree
            ):
                candidates.update(indexes["parents"].get(parent, set()))
        for parent in features.parents:
            candidates.update(indexes["source_entities"].get(parent, set()))
        for source_entity in features.source_entities:
            candidates.update(indexes["parents"].get(source_entity, set()))
            candidates.update(indexes["uses"].get(source_entity, set()))
        for used_entity in features.uses:
            candidates.update(indexes["source_entities"].get(used_entity, set()))
        for source_type in features.source_types:
            if _source_type_qualifies(source_type, context, config):
                candidates.update(indexes["source_types"].get(source_type, set()))
        candidates.discard(subject)
        candidates = {c for c in candidates if not (features.source_entities & feature_map[c].source_entities)}

        scored: list[PairScore] = []
        for candidate in sorted(candidates, key=str):
            result = score_pair(
                features,
                feature_map[candidate],
                config,
                context,
            )
            structural_candidate_count += 1
            if result.qualifies:
                scored.append(result)
            else:
                below_threshold_count += 1
        scored.sort(key=ranking_key)
        selected_entities = set()
        distinct = []
        for result in scored:
            identities = feature_map[URIRef(result.candidate)].source_entities
            if identities & selected_entities:
                continue
            selected_entities.update(identities)
            distinct.append(result)
            if len(distinct) == config.max_related:
                break
        for rank, result in enumerate(distinct, 1):
            graph.add((subject, OKG.relatedTo, URIRef(result.candidate)))
            write_recommendation(graph, corpus, result, rank)
            selected_scores.append(result)

    selected_scores.sort(key=lambda result: (result.subject, *ranking_key(result)))
    reason_distribution = Counter(
        reason for result in selected_scores for reason in result.qualifying_reasons
    )
    return {
        "dataset": dataset,
        "candidateResourceCount": len(subjects),
        "structuralCandidateCount": structural_candidate_count,
        "belowThresholdCount": below_threshold_count,
        "suppressedSharedParentCount": len(suppressed_shared_parents),
        "suppressedSharedParents": suppressed_shared_parents,
        "suppressedSharedSourceTypeCount": len(suppressed_shared_source_types),
        "suppressedSharedSourceTypes": suppressed_shared_source_types,
        "selectedRelationshipCount": len(selected_scores),
        "qualifyingReasonDistribution": dict(sorted(reason_distribution.items())),
        "relationships": [result.as_dict() for result in selected_scores],
    }


def diagnostics_document(
    catalogs: Iterable[dict[str, object]],
    config: SimilarityConfig = DEFAULT_CONFIG,
    source_audit: dict[str, object] | None = None,
) -> dict[str, object]:
    document = {
        "schemaVersion": "2.0.0",
        "scoringConfig": asdict(config),
        "scoringPolicyRationale": {
            "maxSharedSourceTypeDegree": SOURCE_TYPE_DEGREE_RATIONALE,
            "broadSourceTypes": sorted(BROAD_SOURCE_TYPES),
            "approvedSharedClasses": APPROVED_SHARED_CLASSES,
            "approvedClassMaxDegree": config.max_shared_source_type_degree,
        },
        "catalogs": sorted(catalogs, key=lambda catalog: str(catalog["dataset"])),
    }
    if source_audit is not None:
        document["sourceRelationshipAudit"] = source_audit
    return document


def write_diagnostics_atomic(payload: dict[str, object], destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(destination)


def ranking_key(result: PairScore):
    # Direct source relationships outrank every indirect combination.
    direct = bool({'direct_uses', 'direct_relationship'} & set(result.qualifying_reasons))
    close = bool(set(result.qualifying_reasons) - {'shared_category', 'shared_software_type', 'shared_resource_type'})
    classified = bool({'shared_category', 'shared_software_type'} & set(result.qualifying_reasons))
    tier = 0 if direct else 1 if close else 2 if classified else 3
    return (tier, -result.score, result.candidate)


def clear_recommendations(graph: Graph):
    for node in list(graph.objects(None, OKG.recommendation)):
        graph.remove((node, None, None))
    graph.remove((None, OKG.recommendation, None))
    graph.remove((None, OKG.relatedTo, None))


def _label(graph, value):
    node = URIRef(value)
    for predicate in (OKG.name, OKG.title, RDFS.label):
        labels = sorted(str(v) for v in graph.objects(node, predicate) if isinstance(v, Literal))
        if labels:
            return labels[0]
    for subject, identity in graph.subject_objects(OKG.wikidataId):
        if _wikidata_entity(str(identity)) == value:
            label = graph.value(subject, OKG.title)
            if label:
                return str(label)
    return value


def primary_reason(graph: Graph, result: PairScore):
    """Choose one honest, deterministic explanation from actual graph triples.

    Each path is stored as original triples, including the target's Wikidata
    identity bridge for direct relationships. No relationship is inferred from
    a vendor name, a label, or unstructured text.
    """
    left, right = URIRef(result.subject), URIRef(result.candidate)

    def triple(s, p, o):
        return {'subject': str(s), 'predicate': str(p), 'object': str(o)}

    for predicate, forward_code, reverse_code, forward_text, reverse_text in (
        (OKG.uses, 'uses', 'used_by', 'Uses', 'Used by'),
        (DCTERMS.isPartOf, 'part_of', 'has_part', 'Part of', 'Has part'),
    ):
        for origin, destination, code, direction, label in (
            (left, right, forward_code, 'forward', forward_text),
            (right, left, reverse_code, 'reverse', reverse_text),
        ):
            for value in sorted(graph.objects(origin, predicate), key=str):
                for identity in sorted(graph.objects(destination, OKG.wikidataId), key=str):
                    if isinstance(value, URIRef) and _wikidata_entity(str(identity)) == str(value):
                        reason=dict(code=code, direction=direction, text=label,
                                    path=[triple(origin,predicate,value), triple(destination,OKG.wikidataId,identity)])
                        if predicate == OKG.uses:
                            from catalog_uses import sources_for
                            sources=sources_for(graph,origin,value)
                            if sources:reason['sources']=sources
                        return reason
    components = {c.feature: c for c in result.components}
    for feature, predicate, prefix in (
        ('shared_parent', DCTERMS.isPartOf, 'Both part of: '),
        ('same_repository', OKG.sourceRepo, 'Same repository'),
        ('same_namespace_family', OKG.namespaceURI, 'Same namespace family'),
        ('shared_source_type', OKG.sourceType, 'Both classified as: '),
        ('shared_software_type', OKG.softwareType, 'Same software type: '),
        ('shared_category', OKG.category, 'Same domain: '),
        ('shared_resource_type', RDF.type, 'Same resource type: '),
    ):
        if feature not in result.qualifying_reasons:
            continue
        evidence = components[feature].evidence[0]
        normalizer = canonical_repository if feature=='same_repository' else namespace_family if feature=='same_namespace_family' else str
        path=[]
        for subject in (left,right):
            value=next(v for v in sorted(graph.objects(subject,predicate),key=str)
                       if isinstance(v,URIRef) and normalizer(str(v))==evidence)
            path.append(triple(subject,predicate,value))
        text = prefix
        if feature=='shared_source_type':
            text += APPROVED_SHARED_CLASSES[evidence.rsplit('/',1)[-1]]
        elif feature in ('shared_category', 'shared_software_type', 'shared_resource_type'):
            text += discovery_classifications()[feature][evidence]
        elif feature == 'shared_parent':
            label = _label(graph,evidence)
            text = prefix + label if label != evidence else 'Shared parent'
        return dict(code=feature,direction='shared',text=text,path=path)
    raise ValueError('Qualified recommendation has no explainable graph path')


RECOMMENDATION_FIELDS = {
    'code': OKG.reasonCode, 'direction': OKG.reasonDirection,
    'text': OKG.reasonText,
}


def write_recommendation(graph, corpus, result, rank):
    import hashlib
    node=URIRef(result.subject+'#recommendation-'+hashlib.sha256(result.candidate.encode()).hexdigest()[:20])
    subject,target=URIRef(result.subject),URIRef(result.candidate)
    reason=primary_reason(corpus,result)
    graph.add((subject,OKG.recommendation,node))
    graph.add((node,RDF.type,OKG.Recommendation))
    graph.add((node,OKG.recommendationTarget,target))
    graph.add((node,OKG.recommendationRank,Literal(rank,datatype=XSD.integer)))
    title=corpus.value(target,OKG.title) or corpus.value(target,RDFS.label)
    if title is None: raise ValueError(f'Recommendation target lacks a title: {target}')
    graph.add((node,OKG.targetTitle,Literal(str(title))))
    for key,predicate in RECOMMENDATION_FIELDS.items():graph.add((node,predicate,Literal(reason[key])))
    graph.add((node,OKG.evidencePath,Literal(json.dumps(reason['path'],sort_keys=True,separators=(',',':')))))
    if reason.get('sources'):graph.add((node,OKG.evidenceSources,Literal(json.dumps(reason['sources'],sort_keys=True,separators=(',',':')))))


def project_recommendations(graph, subject):
    """Project explicit rank and evidence; retain legacy link-only compatibility."""
    entries=[];seen=set()
    for node in graph.objects(subject,OKG.recommendation):
        target=graph.value(node,OKG.recommendationTarget)
        if target is None or (subject,OKG.relatedTo,target) not in graph:continue
        reason={key:str(graph.value(node,predicate)) for key,predicate in RECOMMENDATION_FIELDS.items()}
        reason['path']=json.loads(str(graph.value(node,OKG.evidencePath)))
        sources=graph.value(node,OKG.evidenceSources)
        if sources:reason['sources']=json.loads(str(sources))
        entries.append({'title':str(graph.value(node,OKG.targetTitle)), 'canonicalUrl':str(target),
                        'recommendationId':str(node),'rank':int(graph.value(node,OKG.recommendationRank)), 'reason':reason})
        seen.add(target)
    entries.sort(key=lambda e:(e['rank'],e['canonicalUrl']))
    legacy=[]
    for target in graph.objects(subject,OKG.relatedTo):
        if target in seen:continue
        title=graph.value(target,OKG.title)
        if isinstance(target,URIRef) and title:
            legacy.append({'title':str(title),'canonicalUrl':str(target)})
    return entries+sorted(legacy,key=lambda e:(e['title'].casefold(),e['canonicalUrl']))


def recommendation_jsonld(entry):
    """Absolute OKG predicates extend Schema.org without changing mentions."""
    if 'reason' not in entry:return None
    reason=entry['reason'];node={'@id':entry['recommendationId'],'@type':str(OKG.Recommendation),
        str(OKG.recommendationTarget):{'@id':entry['canonicalUrl']},
        str(OKG.recommendationRank):entry['rank'],str(OKG.targetTitle):entry['title'],
        str(OKG.evidencePath):json.dumps(reason['path'],sort_keys=True,separators=(',',':'))}
    for key,predicate in RECOMMENDATION_FIELDS.items():node[str(predicate)]=reason[key]
    if reason.get('sources'):node[str(OKG.evidenceSources)]=json.dumps(reason['sources'],sort_keys=True,separators=(',',':'))
    return node


def refresh_recommendations(root: Path, eligible_urls: set[str] | None = None):
    """Recompute on assembled catalogs and, finally, on surviving page membership.

    Normalize supported catalog uses, then rebuild derived recommendations.
    Source records, classifications and shared tag assessments are untouched.
    """
    stems={'resource':'ontologies','software':'software'}
    graphs={k:Graph().parse(root/f'data/{v}.ttl') for k,v in stems.items()}
    from catalog_uses import normalize_catalogs
    graphs,_=normalize_catalogs(root,graphs)
    corpus=Graph()
    for graph in graphs.values():corpus+=graph
    context=build_similarity_context(graphs.values());diagnostics=[]
    for kind,graph in graphs.items():
        diagnostics.append(add_related_resources(graph,kind,context=context,candidate_graph=corpus,eligible_urls=eligible_urls))
        path=root/f'data/{stems[kind]}.json';payload=json.loads(path.read_text())
        for item in payload['items']:
            from catalog_uses import projection as use_projection
            item['uses']=use_projection(graph,URIRef(item['canonicalUrl']))
            related=project_recommendations(graph,URIRef(item['canonicalUrl']))
            if related:item['relatedTools']=related
            else:item.pop('relatedTools',None)
        path.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n')
        graph.serialize(root/f'data/{stems[kind]}.ttl',format='turtle')
    return diagnostics


def validate_recommendations(graph: Graph, corpus: Graph | None = None, *, complete: bool = True):
    """Check that displayed reasons still follow the admitted source graph."""
    corpus = corpus if corpus is not None else graph
    if not any(graph.triples((None, OKG.recommendation, None))):
        return  # Legacy snapshot: recomputed by the coordinated publisher.
    context = build_similarity_context((corpus,))
    subjects = set(graph.subjects(OKG.relatedTo,None)) | set(graph.subjects(OKG.recommendation,None))
    for subject in subjects:
        nodes=list(graph.objects(subject,OKG.recommendation))
        entries=project_recommendations(graph,subject)
        assert len(nodes)==len(entries)<=5, (subject,'recommendation cardinality')
        assert [e['rank'] for e in entries]==list(range(1,len(entries)+1)), (subject,'rank sequence')
        assert len({e['canonicalUrl'] for e in entries})==len(entries), (subject,'duplicate target')
        assert {e['canonicalUrl'] for e in entries}==set(map(str,graph.objects(subject,OKG.relatedTo))), (subject,'link parity')
        for entry in entries:
            target=URIRef(entry['canonicalUrl'])
            assert str(target).startswith(('https://openknowledgegraphs.com/resource/','https://openknowledgegraphs.com/software/')), (subject,'non-catalog target')
            # Independent snapshots cannot resolve another catalog's records.
            # Validate all locally owned evidence now; assembly validates the
            # complete path and re-ranks against both authoritative graphs.
            partial_target = not complete and (target,OKG.wikidataId,None) not in corpus
            for edge in entry['reason']['path']:
                triple = tuple(URIRef(edge[k]) for k in ('subject','predicate','object'))
                if not partial_target or (triple[0],None,None) in corpus:
                    assert triple in corpus, (subject,'unsupported evidence')
            if partial_target:
                continue
            assert entry['title']==str(corpus.value(target,OKG.title) or corpus.value(target,RDFS.label)), (subject,'target title')
            pair=score_pair(features_for_resource(corpus,subject),features_for_resource(corpus,target),context=context)
            assert pair.qualifies, (subject,'unqualified pair')
            assert entry['reason']==primary_reason(corpus,pair), (subject,'misleading reason')
