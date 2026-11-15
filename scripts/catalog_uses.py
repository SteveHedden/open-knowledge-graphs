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


# These are conservative evidence boundaries, not a new entity classifier. An
# existing accepted assignment and exact current excerpt are prerequisites.
NEGATIVE = re.compile(r'\b(?:mention\w*|reading list|unlike|instead of|without|does not|no longer|not support\w*|used by|operated by|profile of|module of)\b',re.I)
CAPABILITY = re.compile(r'\b(?:us(?:e[sd]?|ing)|support\w*|based|built|building on|bindings|interpreter|infer\w*|materializ\w*|leverag\w*|federat\w*|implement\w*|extend\w*|integrat\w*|validat\w*|quer(?:y|ies|ying)|stor\w*|triplestore|quadstore|serializ\w*|pars\w*|convert\w*|transform\w*|mapp?ing\w*|express\w*|represent\w*|written|library|libraries|framework|reason\w*|generat\w*|publish\w*|export\w*|import\w*|manag\w*|edit\w*|render\w*|visual\w*|process\w*|construct\w*|bundled|instance|refinement|derived|conform\w*|compatible|format|encoding)\b',re.I)
REPRESENTATION = re.compile(r'\b(?:RDF|RDFS|OWL(?:2)?|SKOS|SHACL|SPARQL)\b.{0,50}\b(?:ontology|ontologies|vocabulary|vocabularies|schema|graph|graphs|data|tool|suite|store|database|endpoint)\b',re.I)


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
    if NEGATIVE.search(quote) or NEGATIVE.search(fields.get(field,'')):return 'mention-negative-or-different-relationship'
    if not (CAPABILITY.search(quote) or REPRESENTATION.search(quote)):
        return 'excerpt-does-not-establish-use-or-support'
    return 'supported'


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
