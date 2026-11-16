"""Replayable catalog use projection. Never modifies immutable classification reviews.

Wikidata identity bridges, not labels, resolve targets. Legacy P2283 edges are
retained separately before rebuilding the union with current evidenced tags.
Jobs retain their independent mention/skill model.
"""
import hashlib
import json
import re
from pathlib import Path
from rdflib import Graph, URIRef, Literal
from rdflib.namespace import RDF, OWL, DCTERMS
from semantic_config import OKG

VERSION = '1'
CATALOG = ('https://openknowledgegraphs.com/resource/', 'https://openknowledgegraphs.com/software/')


def wikidata(value):
    match = re.fullmatch(r'(?:Q|https?://(?:www\.)?wikidata.org/(?:entity/|wiki/|wiki/Special:EntityData/))(\d+|Q\d+)', str(value))
    return 'http://www.wikidata.org/entity/Q'+match[1].removeprefix('Q') if match else None


class Identities:
    def __init__(self, graph):
        self.links = {}
        def link(a,b):
            a,b=str(a),str(b)
            self.links.setdefault(a,set()).add(b);self.links.setdefault(b,set()).add(a)
        for predicate in (OKG.wikidataId, OWL.sameAs, OKG.catalogPage):
            for a,b in graph.subject_objects(predicate):
                if isinstance(a,URIRef) and isinstance(b,URIRef):link(a,b)
        for value in list(self.links):
            if (entity:=wikidata(value)):link(value,entity)
        self.cache={}

    def canonical(self,value):
        value=str(value)
        if value in self.cache:return self.cache[value]
        seen=set();pending=[value]
        while pending:
            node=pending.pop()
            if node in seen:continue
            seen.add(node);pending.extend(self.links.get(node,()))
        entities={wikidata(x) for x in seen}-{None}
        result=next(iter(entities)) if len(entities)==1 else None if len(entities)>1 else value
        for node in seen:self.cache[node]=result
        return result


# This is a conservative check on an existing accepted assignment, not an entity
# classifier or a general English parser. Only the target-bearing relationship
# in the saved excerpt can establish support. Its surrounding source clause can
# disqualify clipped negation, inverse direction or non-current claims.
CLAUSE_BOUNDARY = re.compile(
    r'[;!?]|\.(?=\s|$)|\b(?:but|whereas|although|however|without|unless|instead of|rather than)\b'
    r'|,?\s+(?:and|while)\s+(?=(?:it|they|we|this|the tool|the project|'
    r'uses|supports|validates|implements|generates|processes|renders|stores)\b)'
    r'|,\s*(?=(?:it|they|we|this|the tool|the project|tool)\b)', re.I)
NON_CURRENT = re.compile(
    r"\b(?:cannot|can['’]t|couldn['’]t|doesn['’]t|don['’]t|isn['’]t|aren['’]t|won['’]t|"
    r"not|never|no longer|no support|unsupported|unavailable|unimplemented|lack\w*|without|unless|instead of|rather than|"
    r"will|would|could|may|might|shall|should|plan\w*|propos\w*|intend\w*|aim\w*|hope\w*|expect\w*|"
    r"future|upcoming|next (?:release|version|year|month)|eventually|soon|roadmap|wish\w*|previously|formerly|used to|deprecated|removed)\b", re.I)
OTHER_RELATION = re.compile(
    r'\b(?:mention\w*|reading list|discuss\w*|compar\w*|document(?:s|ed|ing)|'
    r'refer(?:s|red|ring)? to|unlike|used by|operated by|profile of|module of)\b', re.I)
# Verbs take a target/complement, rather than borrowing a noun such as "library"
# from anywhere in the excerpt. The intervening complement cannot contain a new
# predicate or subject; noun lists (e.g. RDF, OWL and SHACL) remain supported.
ACTION = re.compile(
    r'\b(?:us(?:e[sd]?|ing)|support(?:s|ed|ing)?|based on|built on|building on|'
    r'implement(?:s|ed|ing)?|extend(?:s|ed|ing)?|integrat(?:e[sd]?|ing)|validat(?:e[sd]?|ing)|quer(?:y|ies|ying)|stor(?:e[sd]?|ing)|'
    r'serializ(?:e[sd]?|ing)|pars(?:e[sd]?|ing)|convert(?:s|ed|ing)?|transform(?:s|ed|ing)?|express(?:es|ed|ing)?|represent(?:s|ed|ing)?|written in|'
    r'infer(?:s|red|ring)?|materializ(?:e[sd]?|ing)|leverag(?:e[sd]?|ing)|generat(?:e[sd]?|ing)|publish(?:es|ed|ing)?|export(?:s|ed|ing)?|import(?:s|ed|ing)?|'
    r'manag(?:e[sd]?|ing)|edit(?:s|ed|ing)?|render(?:s|ed|ing)?|visuali[sz](?:e[sd]?|ing)|process(?:es|ed|ing)?|construct(?:s|ed|ing)?|serv(?:e[sd]?|ing)|sketch(?:es|ed|ing)?|execut(?:e[sd]?|ing)|predict(?:s|ed|ing)?|translat(?:e[sd]?|ing)|mapping|'
    r'conform(?:s|ed|ing)? to|refinement to|derived from|working with|extension of|'
    r'(?:library|framework|toolkit|engine|browser|inference|store|format|validator|editor|visualization|protocol) for|'
    r'converter from|configurable with)\b', re.I)
NEW_PREDICATE = re.compile(
    r'\b(?:is|are|was|were|has|have|it|they|we|which|that|requires?|'
    r'mention\w*|discuss\w*|document\w*|list(?:s|ed|ing)?|describ\w*|compar\w*)\b', re.I)
TECHNICAL_ROLE = re.compile(
    r'\b(?:support|implementation|extension|integration|validation|reason(?:er|ing)|'
    r'inference|bindings|interpreter|materialization|generation|processing|mapping|'
    r'parser|processor|converter|engine|instance|expression|representation|library|libraries|framework|triplestore|quadstore|database|store|'
    r'format|encoding|ontology|ontologies|vocabulary|vocabularies|schema|graph|graphs|'
    r'data|tool|toolkit|suite|plugin|memory|modeling|class definitions)\b', re.I)
ROLE_MODIFIERS = re.compile(
    r"^(?:(?:['’]s)|[\s/(),:.-]|\b(?:and|or|2|1|dl|rl|el|lite|plus|rdf|rdfs|owl|skos|shacl|sparql|"
    r'turtle|xml|json|ld|semantic|web|knowledge|triple|quad|stream|query|data|logical|surfaces|cli|rust|python|javascript|rml|r2rml|yarrrml|list|of|dict|table|storage|'
    r'based|compliant|compatible|aligned|design|patterns|modular)\b)*$', re.I)


def clauses(text):
    """Yield source offsets, retaining subordinators in their own clause.

    In "uses SHACL without a server", without belongs to the second clause.
    In "works without SHACL", the target belongs to that second clause instead.
    Sentence breaks do not split dotted identifiers such as Schema.org.
    """
    start = 0
    for boundary in CLAUSE_BOUNDARY.finditer(text):
        if boundary.start() > start:
            yield start, boundary.start(), text[start:boundary.start()]
        start = boundary.start() if boundary.group().strip().lower() in (
            'without', 'unless', 'instead of', 'rather than') else boundary.end()
    if start < len(text):
        yield start, len(text), text[start:]


def target_capability(text, target):
    """Recognize a target-bound capability within the saved excerpt only."""
    before, after = text[:target.start()], text[target.end():]
    for action in reversed(list(ACTION.finditer(before))):
        complement = before[action.end():]
        if len(complement.split()) <= 12 and not NEW_PREDICATE.search(complement):
            return action.start(), target.end()
        # An earlier verb must not jump across a nearer unrelated predicate.
        break
    # A technology modifying a capability: "SHACL validation", "OWL 2 DL
    # reasoner", "RDF/OWL ontologies". Unknown intervening words fail closed.
    for role in TECHNICAL_ROLE.finditer(after):
        if ROLE_MODIFIERS.fullmatch(after[:role.start()]):
            return target.start(), target.end() + role.end()
        break
    # Intrinsic implementation links and capability complements whose action
    # precedes the target: "library for X", "inference over X", "extension of X".
    if re.search(r'\b(?:library|libraries|framework|toolkit|tool|engine|browser|'
                 r'visualizer|editor|reasoner|inference|implementation|extension|'
                 r'store|triplestore|mapping|format|syntax|federation)\s+(?:for|of|over|in|with|on)\s+(?:the\s+)?$', before, re.I):
        return 0, target.end()
    modifier = re.match(r"(?:['’]s)?\s*[- ](?:based|compatible|compliant|aligned)\b", after, re.I)
    if modifier:
        return target.start(), target.end() + modifier.end()
    bundle = re.match(r'^(?:-[\w]+)?(?:\s*(?:,|and)\s*[\w-]+)*\s*,?\s*bundled\b', after, re.I)
    if bundle:
        return target.start(), target.end() + bundle.end()
    return None


def description_status(quote, source, aliases):
    from shared_tags import clean, normalize_evidence
    import unicodedata

    variants = {clean(unicodedata.normalize('NFC', quote)), normalize_evidence(quote)}
    target_re = re.compile(r'(?<!\w)(?:' + '|'.join(
        re.escape(a) for a in sorted(set(aliases), key=len, reverse=True) if a) + r')(?!\w)', re.I)
    statuses = []
    # Locate every occurrence; a clipped or repeated ambiguous excerpt must not
    # silently inherit a different occurrence's current positive interpretation.
    occurrences = set()
    for variant in variants:
        if variant:
            occurrences.update((m.start(), m.end()) for m in re.finditer(re.escape(variant), source))
    for quote_start, quote_end in sorted(occurrences):
        for start, end, context in clauses(source):
            excerpt = source[max(start, quote_start):min(end, quote_end)] if start < quote_end and end > quote_start else ''
            targets = list(target_re.finditer(excerpt))
            if not targets:
                continue
            for target in targets:
                relation = target_capability(excerpt, target)
                offset = max(start, quote_start) - start
                target_start = offset + target.start()
                target_end = offset + target.end()
                # Read omitted qualifiers before the target's relationship, not
                # arbitrary negative/temporal words elsewhere in the description.
                relationship_end = offset + relation[1] if relation else target_end
                prefix = context[:target_start]
                suffix = context[relationship_end:]
                future_qualifier = re.match(
                    r'\s*(?:[,(:-]\s*)?(?:(?:only )?(?:in |after )?(?:a |the )?(?:future|upcoming|next (?:release|version|year|month))\b|'
                    r'(?:will|would|may|might)\b|(?:is )?not (?:supported|implemented|available|used|enabled)\b|(?:(?:which |that )?is |was )?(?:planned|proposed|expected|coming|pending|scheduled|'
                    r'unavailable|unsupported|removed|deprecated)\b)', suffix, re.I)
                if (NON_CURRENT.search(prefix) or future_qualifier or
                        re.search(r'\b(?:non|anti)-$', prefix, re.I) or
                        re.match(r'-free\b', context[target_end:], re.I)):
                    statuses.append('negated-conditional-or-non-current-relationship')
                elif OTHER_RELATION.search(prefix) or re.search(r'\babout\s*$', prefix, re.I) or re.match(
                    r'\s+(?:is |was )?(?:mentioned|listed|discussed|planned)\b', context[target_end:], re.I):
                    statuses.append('mention-or-different-relationship')
                elif re.match(r'\s+(?:is|are|was|were|has|have|will|would|could|may|might)\b', context[target_end:], re.I):
                    statuses.append('ambiguous-target-relationship')
                elif re.match(r'\s+(?:documentation|tutorials?|examples?|articles?|references?)\b', context[target_end:], re.I):
                    statuses.append('mention-or-different-relationship')
                elif relation:
                    statuses.append('supported')
                else:
                    statuses.append('excerpt-does-not-establish-use-or-support')
    if 'supported' in statuses and all(status in ('supported', 'excerpt-does-not-establish-use-or-support') for status in statuses):
        return 'supported'
    return next((status for status in statuses if status != 'supported'),
                'target-not-explicit-in-excerpt')


def assignment_status(graph, assignment, fields, term):
    from shared_tags import evidence_matches
    field=str(graph.value(assignment,OKG.sourceField) or '')
    quote=str(graph.value(assignment,OKG.supportingText) or '')
    relation=str(graph.value(assignment,OKG.relationContext) or '')
    state=str(graph.value(assignment,OKG.reviewState) or '')
    if state not in ('reviewed','automated'):return 'unaccepted-review-state'
    if relation not in ('uses','supports'):return 'relationship-is-not-use-or-support'
    if field not in ('description','programmingLanguages'):return 'title-or-review-note-is-not-use-evidence'
    if not evidence_matches(quote,fields.get(field,'')):return 'stale-or-missing-excerpt'
    aliases=[term.get('label',''),*term.get('aliases',[])]
    if not any(a and re.search(r'(?<!\w)'+re.escape(a)+r'(?!\w)',quote,re.I) for a in aliases):
        return 'target-not-explicit-in-excerpt'
    if field=='programmingLanguages':return 'supported'
    return description_status(quote, fields[field], aliases)

def normalize(graph, identities=None, terms=None):
    """Replace only derived use assertions, keeping all original evidence intact."""
    identities=identities or Identities(graph);terms=terms or {}
    audit=[]
    owners={s for s in graph.subjects(OKG.wikidataId,None) if str(s).startswith(CATALOG)}
    for owner in sorted(owners,key=str):
        # Old snapshots have only P2283 in uses. Capture it once; never treat a
        # previously generated reviewed edge as a new upstream statement.
        if not graph.value(owner,OKG.usesProjectionVersion):
            for target in list(graph.objects(owner,OKG.uses)):
                graph.add((owner,OKG.sourceUses,target))
        for node in list(graph.objects(owner,OKG.useAssertion)):
            graph.remove((node,None,None))
        for pred in (OKG.uses,OKG.useAssertion,OKG.mentionsResource,OKG.usesResource):graph.remove((owner,pred,None))
        graph.set((owner,OKG.usesProjectionVersion,Literal(VERSION)))
        supports={}
        for target in sorted(graph.objects(owner,OKG.sourceUses),key=str):
            canonical=identities.canonical(target)
            if canonical and canonical!=identities.canonical(owner):
                supports.setdefault(canonical,[]).append({'kind':'wikidata','predicate':'http://www.wikidata.org/prop/direct/P2283','target':str(target),'source':str(graph.value(owner,OKG.wikidataId))})
        assessment=graph.value(owner,OKG.tagAssessment)
        from shared_tags import fields as normalize_fields
        raw={'description':str(graph.value(owner,OKG.description) or ''),'title':str(graph.value(owner,OKG.title) or '')}
        raw['programmingLanguages']=sorted(str(x) for x in graph.objects(owner,OKG.programmingLanguage))
        fields=normalize_fields(raw,'software')
        snapshot=graph.value(assessment,OKG.evidenceSnapshot) if assessment else None
        if snapshot:
            saved=json.loads(str(snapshot))
            language=saved.get('programmingLanguages','')
            if set(language.split(', '))==set(raw['programmingLanguages']):
                fields['programmingLanguages']=language

        for assignment in sorted(graph.objects(assessment,OKG.tagAssignment),key=str) if assessment else []:
            if str(graph.value(assignment,OKG.tagDimension))!='tools':continue
            target=graph.value(assignment,OKG.tagTarget)
            status=assignment_status(graph,assignment,fields,terms.get(str(target),{}))
            field=str(graph.value(assignment,OKG.sourceField) or '')
            if snapshot and saved.get(field)!=fields.get(field):status='stale-assessment-field'
            canonical=identities.canonical(target)
            if not canonical:status='ambiguous-identity'
            elif canonical==identities.canonical(owner):status='self-reference'
            audit.append({'subject':str(owner),'assignment':str(assignment),'target':str(target),'status':status})
            if status!='supported':
                graph.add((owner,OKG.mentionsResource,target));continue
            evidence={'kind':'classification','assignment':str(assignment),'target':str(target)}
            for key,pred in [('field',OKG.sourceField),('quote',OKG.supportingText),('reviewState',OKG.reviewState),('method',OKG.classificationMethod),('relation',OKG.relationContext),('source',DCTERMS.source)]:
                evidence[key]=str(graph.value(assignment,pred) or '')
            supports.setdefault(canonical,[]).append(evidence)
        for target,sources in sorted(supports.items()):
            node=URIRef(str(owner)+'#use-'+hashlib.sha256(target.encode()).hexdigest()[:20])
            graph.add((owner,OKG.uses,URIRef(target)));graph.add((owner,OKG.useAssertion,node))
            graph.add((node,RDF.type,OKG.UseAssertion));graph.add((node,OKG.useTarget,URIRef(target)))
            graph.add((node,OKG.useEvidence,Literal(json.dumps(sources,sort_keys=True,separators=(',',':')))))
    return audit


def sources_for(graph,owner,target):
    sources=[]
    for node in graph.objects(owner,OKG.useAssertion):
        if str(graph.value(node,OKG.useTarget))==str(target):
            sources.extend(json.loads(str(graph.value(node,OKG.useEvidence))))
    return sorted(sources,key=lambda x:json.dumps(x,sort_keys=True))


def normalize_catalogs(root,graphs=None,terms=None):
    root=Path(root)
    if terms is None:
        path=root/'data/tag-vocabularies.json'
        terms={t['id']:t for t in json.loads(path.read_text())['terms']} if path.exists() else {}
    from shared_tags import registry_graph
    graphs=graphs or {k:Graph().parse(root/f'data/{v}.ttl') for k,v in [('resource','ontologies'),('software','software')]}
    corpus=registry_graph(terms)
    for graph in graphs.values():corpus+=graph
    identities=Identities(corpus);audit=[]
    for graph in graphs.values():audit+=normalize(graph,identities,terms)
    return graphs,audit


def projection(graph,owner):
    if not graph.value(owner,OKG.usesProjectionVersion):return None
    return [{'id':str(target),'sources':sources_for(graph,owner,target)}
            for target in sorted(graph.objects(owner,OKG.uses),key=str)]


def validate(graph,identities,terms):
    expected=Graph()
    for triple in graph:expected.add(triple)
    normalize(expected,identities,terms)
    owners={s for s in graph.subjects(OKG.usesProjectionVersion,None)}
    for owner in owners:
        for predicate in (OKG.uses,OKG.mentionsResource,OKG.useAssertion):
            assert set(graph.objects(owner,predicate))==set(expected.objects(owner,predicate)),(owner,'use projection mismatch')
        assert not list(graph.objects(owner,OKG.usesResource)),(owner,'legacy catalog usesResource assertion')
        for node in expected.objects(owner,OKG.useAssertion):
            assert set(graph.predicate_objects(node))==set(expected.predicate_objects(node)),(owner,'use evidence mismatch')
