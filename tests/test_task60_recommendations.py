"""Task 60 contracts: source evidence, direction, cross-catalog pages and ranking."""
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from rdflib import Graph, URIRef, Literal
from rdflib.namespace import RDF, DCTERMS

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import related_resources as r
import fetch_data
import generate_pages
from test_task25_related_resources import add_resource

O=r.OKG


def software(graph,slug,qid,**kw):
    old=add_resource(graph,slug,qid,**kw)
    new=URIRef(str(old).replace('/resource/','/software/'))
    for p,o in list(graph.predicate_objects(old)):
        graph.remove((old,p,o));graph.add((new,p,O.Software if p==RDF.type else o))
    return new


def run_pair(resources,tools,eligible=None):
    corpus=resources+tools;ctx=r.build_similarity_context((resources,tools))
    for kind,graph in [('resource',resources),('software',tools)]:
        r.add_related_resources(graph,kind,context=ctx,candidate_graph=corpus,eligible_urls=eligible)
    return corpus


class RecommendationContracts(unittest.TestCase):
    def test_spec_library_uses_is_not_implements_in_either_direction(self):
        resources,tools=Graph(),Graph()
        spec=add_resource(resources,'spec','Q9001')
        library=software(tools,'library','Q9002',uses=['http://www.wikidata.org/entity/Q9001'])
        run_pair(resources,tools)
        forward=r.project_recommendations(tools,library)[0]
        reverse=r.project_recommendations(resources,spec)[0]
        self.assertEqual((forward['canonicalUrl'],forward['reason']['text']),(str(spec),'Uses'))
        self.assertEqual((reverse['canonicalUrl'],reverse['reason']['text']),(str(library),'Used by'))
        self.assertEqual(forward['reason']['direction'],'forward')
        self.assertEqual(reverse['reason']['direction'],'reverse')
        self.assertEqual(forward['reason']['path'],reverse['reason']['path'])
        corpus=resources+tools
        r.validate_recommendations(resources,corpus);r.validate_recommendations(tools,corpus)
        self.assertNotIn('implement',json.dumps([forward,reverse]).lower())
        # No external-catalog resource records copied into the source graph.
        self.assertFalse(list(tools.objects(spec,O.wikidataId)))

    def test_part_relationship_preserves_actual_source_direction(self):
        graph=Graph();parent=add_resource(graph,'parent','Q1')
        child=add_resource(graph,'child','Q2',parents=['http://www.wikidata.org/entity/Q1'])
        r.add_related_resources(graph,'resource')
        self.assertEqual(r.project_recommendations(graph,child)[0]['reason']['text'],'Part of')
        self.assertEqual(r.project_recommendations(graph,parent)[0]['reason']['text'],'Has part')

    def test_vendor_name_and_unknown_rare_class_are_not_evidence(self):
        graph=Graph()
        a=software(graph,'acme-tool','Q1',source_types=['http://www.wikidata.org/entity/Q987654321'])
        software(graph,'acme-database','Q2',source_types=['http://www.wikidata.org/entity/Q987654321'])
        r.add_related_resources(graph,'software')
        self.assertEqual(r.project_recommendations(graph,a),[])

    def test_data_format_trap_and_independent_positive(self):
        graph=Graph();broad='http://www.wikidata.org/entity/Q494823'
        a=add_resource(graph,'spec','Q1',source_types=[broad])
        b=add_resource(graph,'catalog-vocabulary','Q2',source_types=[broad])
        c=add_resource(graph,'museum-format','Q3',source_types=[broad])
        r.add_related_resources(graph,'resource')
        self.assertFalse(list(graph.triples((None,O.relatedTo,None))))
        graph.add((a,O.uses,URIRef('http://www.wikidata.org/entity/Q2')))
        r.add_related_resources(graph,'resource')
        self.assertEqual(set(graph.objects(a,O.relatedTo)),{b})
        self.assertNotIn((a,O.relatedTo,c),graph)

    def test_same_creator_is_honest_and_not_compatibility(self):
        graph=Graph();creator=URIRef('https://example.test/acme')
        a=software(graph,'tool','Q1',creators=[str(creator)])
        software(graph,'other','Q2',creators=[str(creator)])
        graph.add((creator,O.name,Literal('Acme')))
        r.add_related_resources(graph,'software')
        entry=r.project_recommendations(graph,a)[0]
        self.assertEqual(entry['reason']['text'],'Same creator: Acme')
        self.assertEqual(entry['reason']['direction'],'shared')
        self.assertEqual({e['predicate'] for e in entry['reason']['path']},{str(O.creator)})

    def test_functional_class_is_explicit_classification_not_interchangeability(self):
        graph=Graph();kind='http://www.wikidata.org/entity/Q3539533'
        a=software(graph,'first','Q1',source_types=[kind]);software(graph,'second','Q2',source_types=[kind])
        r.add_related_resources(graph,'software')
        self.assertEqual(r.project_recommendations(graph,a)[0]['reason']['text'],'Both classified as: triplestore')

    def test_direct_evidence_first_top_five_dedup_and_repeatability(self):
        graph=Graph();kind='http://www.wikidata.org/entity/Q3539533';repo='https://example.test/repo'
        source=software(graph,'source','Q1',source_types=[kind],repository=repo,creators=['https://example.test/dev'])
        direct=software(graph,'z-direct','Q2');graph.add((source,O.uses,URIRef('http://www.wikidata.org/entity/Q2')))
        for i in range(8):software(graph,f'peer-{i}',f'Q{10+i}',source_types=[kind],repository=repo,creators=['https://example.test/dev'])
        software(graph,'peer-duplicate','Q10',source_types=[kind],repository=repo)
        diagnostics=r.add_related_resources(graph,'software');first=r.project_recommendations(graph,source)
        self.assertEqual(len(first),5);self.assertEqual(first[0]['canonicalUrl'],str(direct))
        self.assertEqual([e['rank'] for e in first],[1,2,3,4,5])
        self.assertEqual(len({str(graph.value(URIRef(e['canonicalUrl']),O.wikidataId)) for e in first}),5)
        before=set(graph);again=r.add_related_resources(graph,'software')
        self.assertEqual(before,set(graph));self.assertEqual(diagnostics,again)
        self.assertEqual(first,r.project_recommendations(graph,source))
        # Strongest primary path wins over creator/class reasons.
        self.assertEqual(first[1]['reason']['code'],'same_repository')

    def test_non_surviving_target_does_not_consume_slot_or_leave_evidence(self):
        resources,tools=Graph(),Graph();a=add_resource(resources,'spec','Q1')
        b=software(tools,'library','Q2',uses=['http://www.wikidata.org/entity/Q1'])
        run_pair(resources,tools);self.assertTrue(list(resources.objects(a,O.recommendation)))
        run_pair(resources,tools,{str(a)})
        self.assertEqual(r.project_recommendations(resources,a),[])
        self.assertFalse(list(resources.subjects(RDF.type,O.Recommendation)))
        self.assertFalse(list(tools.subjects(RDF.type,O.Recommendation)))

    def test_rdf_json_html_jsonld_preserve_evidence_rank_and_direction(self):
        graph=Graph();a=software(graph,'tool','Q1',uses=['http://www.wikidata.org/entity/Q2']);add_resource(graph,'spec','Q2')
        r.add_related_resources(graph,'software');entries=fetch_data.related_tools_for_resource(graph,a)
        item=dict(title='Tool',canonicalUrl=str(a),wikidataId='https://www.wikidata.org/wiki/Q1',description='Tool description.',homepage='https://example.test/tool',types=['Software'],relatedTools=entries)
        ld=json.loads(generate_pages.make_json_ld(item,'software'))
        page=generate_pages.make_page(item,'software','tool')
        self.assertEqual(page.count('<h2 class="detail-related-heading">Related resources</h2>'),1)
        self.assertIn('<span class="detail-related-reason">Uses</span>',page)
        node=ld[str(O.recommendation)][0]
        self.assertEqual(node[str(O.reasonDirection)],'forward')
        self.assertEqual(json.loads(node[str(O.evidencePath)]),entries[0]['reason']['path'])
        # Parse just the absolute-IRI extension without fetching Schema.org.
        parsed=Graph().parse(data=json.dumps({'@id':str(a),str(O.recommendation):ld[str(O.recommendation)]}),format='json-ld')
        rec=URIRef(entries[0]['recommendationId'])
        self.assertEqual(set(parsed.predicate_objects(rec)),set(graph.predicate_objects(rec)))
        self.assertIn((a,O.recommendation,rec),parsed)

    def test_validator_rejects_fabricated_or_relabelled_evidence(self):
        graph=Graph();a=add_resource(graph,'a','Q1',uses=['http://www.wikidata.org/entity/Q2']);add_resource(graph,'b','Q2')
        r.add_related_resources(graph,'resource');r.validate_recommendations(graph)
        node=graph.value(a,O.recommendation);graph.set((node,O.reasonText,Literal('Implements')))
        with self.assertRaises(AssertionError):r.validate_recommendations(graph)

    def test_same_wikidata_entity_is_not_its_own_cross_catalog_neighbor(self):
        resources,tools=Graph(),Graph();a=add_resource(resources,'model','Q1',repository='https://example.test/repo')
        software(tools,'model','Q1',repository='https://example.test/repo')
        run_pair(resources,tools);self.assertEqual(r.project_recommendations(resources,a),[])

    def test_final_refresh_backfills_slots_and_preserves_source_records(self):
        resources,tools=Graph(),Graph()
        a=add_resource(resources,'a','Q1')
        for i in range(6):
            software(tools,f'library-{i}',f'Q{10+i}',uses=['http://www.wikidata.org/entity/Q1'])
        originals={k:set(g) for k,g in [('resource',resources),('software',tools)]}
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);(root/'data').mkdir()
            for kind,stem,graph in [('resource','ontologies',resources),('software','software',tools)]:
                graph.serialize(root/f'data/{stem}.ttl',format='turtle')
                rows=[{'canonicalUrl':str(owner),'description':'Preserve this field','sharedTags':{'sentinel':True}}
                      for owner in sorted(set(graph.subjects(O.wikidataId,None)),key=str)]
                (root/f'data/{stem}.json').write_text(json.dumps({'generatedAt':'2026-11-14T00:00:00Z','items':rows}))
            eligible={str(a)}|{str(s) for s in tools.subjects(O.wikidataId,None) if not str(s).endswith('library-0/')}
            r.refresh_recommendations(root,eligible)
            saved=json.loads((root/'data/ontologies.json').read_text())['items'][0]
            self.assertEqual(saved['description'],'Preserve this field')
            self.assertEqual(saved['sharedTags'],{'sentinel':True})
            self.assertEqual(len(saved['relatedTools']),5)
            self.assertTrue(saved['relatedTools'][-1]['canonicalUrl'].endswith('library-5/'))
            for kind,stem in [('resource','ontologies'),('software','software')]:
                graph=Graph().parse(root/f'data/{stem}.ttl')
                r.clear_recommendations(graph)
                self.assertEqual(set(graph),originals[kind])

    def test_jobs_cannot_enter_candidate_pool(self):
        resources,tools=Graph(),Graph();a=add_resource(resources,'a','Q1')
        job=URIRef('https://openknowledgegraphs.com/job/test')
        tools.add((job,O.wikidataId,URIRef('https://www.wikidata.org/wiki/Q2')))
        tools.add((job,O.homepage,URIRef('https://example.test/job')))
        tools.add((job,O.title,Literal('Job')))
        tools.add((job,O.uses,URIRef('http://www.wikidata.org/entity/Q1')))
        run_pair(resources,tools)
        self.assertEqual(r.project_recommendations(resources,a),[])

    def test_declared_recommendation_shape_rejects_out_of_range_rank(self):
        from pyshacl import validate
        from rdflib.namespace import XSD
        graph=Graph();a=add_resource(graph,'a','Q1',uses=['http://www.wikidata.org/entity/Q2']);add_resource(graph,'b','Q2')
        r.add_related_resources(graph,'resource')
        ontology=Graph().parse(Path(__file__).resolve().parents[1]/'ontology.ttl')
        conforms,_,report=validate(graph,shacl_graph=ontology,ont_graph=ontology)
        self.assertTrue(conforms,report)
        node=graph.value(a,O.recommendation)
        graph.set((node,O.recommendationRank,Literal(6,datatype=XSD.integer)))
        self.assertFalse(validate(graph,shacl_graph=ontology,ont_graph=ontology)[0])

    def test_independent_snapshot_defers_foreign_evidence_until_assembly(self):
        resources,tools=Graph(),Graph();a=add_resource(resources,'spec','Q1')
        software(tools,'library','Q2',uses=['http://www.wikidata.org/entity/Q1'])
        run_pair(resources,tools)
        r.validate_recommendations(resources,complete=False)
        r.validate_recommendations(resources,resources+tools)
        with self.assertRaises(AssertionError):r.validate_recommendations(resources)
        # Local source evidence is still mandatory in the independent snapshot.
        resources.remove((a,O.wikidataId,None))
        with self.assertRaises(AssertionError):r.validate_recommendations(resources,complete=False)


if __name__=='__main__':unittest.main()
