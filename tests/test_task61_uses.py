"""Canonical use normalization, replay safety and one recommendation presentation."""
import json
import sys
import unittest
from pathlib import Path
from rdflib import Graph,URIRef,Literal
from rdflib.namespace import RDF,OWL,DCTERMS
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import catalog_uses as u
import related_resources as r
import shared_tags as tags
import generate_pages
from test_task25_related_resources import add_resource
from test_task60_recommendations import software
O=u.OKG


class UsesContracts(unittest.TestCase):
    def fixture(self, text='Tool validates RDF data with SHACL.'):
        g=Graph();tool=software(g,'tool','Q1',description=text)
        rdf=add_resource(g,'rdf','Q2');shacl=add_resource(g,'shacl','Q3')
        alias=URIRef(tags.BASE+'entities/shacl')
        g.add((alias,OWL.sameAs,URIRef('https://www.wikidata.org/wiki/Q3')))
        g.add((alias,O.catalogPage,shacl))
        terms={str(rdf):{'label':'RDF','aliases':[]},str(alias):{'label':'SHACL','aliases':[]}}
        return g,tool,rdf,shacl,alias,terms

    def tag(self,g,owner,target,quote,field='description',relation='supports',state='reviewed'):
        ass=URIRef(str(owner)+'#assessment');node=URIRef(str(owner)+'#assignment-'+str(target).split('/')[-1])
        g.add((owner,O.tagAssessment,ass));g.add((ass,O.tagAssignment,node))
        for p,v in [(O.tagTarget,target),(O.tagDimension,Literal('tools')),(O.sourceField,Literal(field)),(O.supportingText,Literal(quote)),(O.relationContext,Literal(relation)),(O.reviewState,Literal(state)),(DCTERMS.source,owner)]:g.add((node,p,v))
        g.add((owner,O.usesResource,target))
        return ass,node

    def test_identity_resolution_is_explicit_and_ambiguous_ids_fail_closed(self):
        g,owner,rdf,shacl,alias,terms=self.fixture();ids=u.Identities(g)
        expected='http://www.wikidata.org/entity/Q3'
        for value in ('Q3','https://www.wikidata.org/wiki/Q3','https://www.wikidata.org/entity/Q3',str(alias),str(shacl)):
            self.assertEqual(ids.canonical(value),expected)
        g.add((alias,OWL.sameAs,URIRef('http://www.wikidata.org/entity/Q4')))
        self.assertIsNone(u.Identities(g).canonical(alias))
        self.assertEqual(ids.canonical('https://example.test/SHACL'),'https://example.test/SHACL')

    def test_p2283_and_review_have_same_target_and_mixed_sources_score_once(self):
        scores=[]
        for mode in ('upstream','review','both'):
            g,owner,rdf,shacl,alias,terms=self.fixture()
            if mode!='review':g.add((owner,O.uses,URIRef('http://www.wikidata.org/entity/Q3')))
            if mode!='upstream':self.tag(g,owner,alias,'validates RDF data with SHACL')
            u.normalize(g,terms=terms)
            self.assertEqual(set(g.objects(owner,O.uses)),{URIRef('http://www.wikidata.org/entity/Q3')})
            pair=r.score_pair(r.features_for_resource(g,owner),r.features_for_resource(g,shacl),context=r.build_similarity_context([g]))
            scores.append(pair.score)
            r.add_related_resources(g,'software')
            entry=r.project_recommendations(g,owner)[0]
            self.assertEqual(entry['canonicalUrl'],str(shacl));self.assertEqual(entry['reason']['text'],'Uses')
            self.assertEqual(len(entry['reason']['sources']),2 if mode=='both' else 1)
            self.assertEqual(r.project_recommendations(g,shacl)[0]['reason']['text'],'Used by')
            r.validate_recommendations(g,g)
        self.assertEqual(len(set(scores)),1)

    def test_replay_removes_stale_review_edges_without_losing_upstream(self):
        g,owner,rdf,shacl,alias,terms=self.fixture()
        g.add((owner,O.uses,URIRef('http://www.wikidata.org/entity/Q2')))
        ass,node=self.tag(g,owner,alias,'validates RDF data with SHACL')
        before=set(g.triples((node,None,None)))
        u.normalize(g,terms=terms);first=set(g)
        u.normalize(g,terms=terms);self.assertEqual(first,set(g))
        g.set((owner,O.description,Literal('Other functionality.')))
        u.normalize(g,terms=terms)
        self.assertEqual(set(g.objects(owner,O.uses)),{URIRef('http://www.wikidata.org/entity/Q2')})
        self.assertIn((owner,O.mentionsResource,alias),g)
        self.assertEqual(before,set(g.triples((node,None,None))))
        g.remove((ass,O.tagAssignment,node));u.normalize(g,terms=terms)
        self.assertEqual(len(list(g.objects(owner,O.uses))),1)

    def test_mentions_titles_negations_and_non_use_relations_stay_metadata(self):
        cases=[('Mentions SHACL in a reading list.','Mentions SHACL','description','supports'),
               ('SHACL','SHACL','title','uses'),
               ('No longer uses SHACL.','uses SHACL','description','uses'),
               ('Tool validates RDF data with SHACL.','validates RDF data with SHACL','description','intended-use')]
        for description,quote,field,relation in cases:
            with self.subTest(description=description):
                g,owner,rdf,shacl,alias,terms=self.fixture(description)
                self.tag(g,owner,alias,quote,field,relation)
                u.normalize(g,terms=terms)
                self.assertFalse(list(g.objects(owner,O.uses)))
                self.assertIn((owner,O.mentionsResource,alias),g)

    def test_unknown_target_and_self_never_create_broken_recommendations(self):
        g,owner,rdf,shacl,alias,terms=self.fixture()
        for value in ('Q1','Q999'):g.add((owner,O.uses,URIRef(value)))
        u.normalize(g,terms=terms);r.add_related_resources(g,'software')
        self.assertEqual(set(g.objects(owner,O.uses)),{URIRef('http://www.wikidata.org/entity/Q999')})
        self.assertEqual(r.project_recommendations(g,owner),[])

    def test_stale_assessment_and_ambiguous_assignment_do_not_assert_use(self):
        g,owner,rdf,shacl,alias,terms=self.fixture()
        ass,node=self.tag(g,owner,alias,'validates RDF data with SHACL')
        g.add((ass,O.evidenceSnapshot,Literal(json.dumps({'description':'Old text validates RDF data with SHACL.'}))))
        audit=u.normalize(g,terms=terms)
        self.assertEqual(audit[0]['status'],'stale-assessment-field')
        self.assertFalse(list(g.objects(owner,O.uses)))
        g.remove((ass,O.evidenceSnapshot,None))
        g.add((alias,OWL.sameAs,URIRef('http://www.wikidata.org/entity/Q4')))
        audit=u.normalize(g,terms=terms)
        self.assertEqual(audit[0]['status'],'ambiguous-identity')
        self.assertFalse(list(g.objects(owner,O.uses)))

    def test_jobs_remain_unchanged_by_catalog_normalization(self):
        g,owner,rdf,shacl,alias,terms=self.fixture()
        job=URIRef('https://openknowledgegraphs.com/jobs/example/')
        ass,node=self.tag(g,job,alias,'SHACL experience required',relation='requested-skill')
        before=set(g)
        u.normalize(g,terms=terms)
        for subject in (job,ass,node):
            self.assertEqual({t for t in before if t[0]==subject},set(g.triples((subject,None,None))))
        self.assertIn((job,O.usesResource,alias),g)

    def test_presentation_and_schema_include_provenance_without_catalog_pills(self):
        g,owner,rdf,shacl,alias,terms=self.fixture()
        self.tag(g,owner,alias,'validates RDF data with SHACL')
        u.normalize(g,terms=terms);r.add_related_resources(g,'software')
        entries=r.project_recommendations(g,owner)
        item={'canonicalUrl':str(owner),'title':'Tool','description':'Tool validates RDF data with SHACL.','wikidataId':'https://www.wikidata.org/wiki/Q1','homepage':'https://example.test/tool','types':['Software'],'softwareType':'Data Validation','category':'Technology & Web','categories':['Technology & Web'],'sharedTags':{'tools':[{'label':'SHACL','catalogPages':[str(shacl)]}]},'relatedTools':entries,'uses':u.projection(g,owner)}
        page=generate_pages.make_page(item,'software','tool',page_urls={str(shacl)})
        self.assertNotIn('aria-label="Related tools and resources"',page)
        self.assertIn('Data Validation',page);self.assertIn('Technology &amp; Web',page)
        ld=json.loads(generate_pages.make_json_ld(item,'software'))
        self.assertEqual(ld[str(O.uses)],[{'@id':'http://www.wikidata.org/entity/Q3'}])
        self.assertEqual(json.loads(ld[str(O.recommendation)][0][str(O.evidenceSources)]),entries[0]['reason']['sources'])
        from pyshacl import validate
        conforms,_,report=validate(g,shacl_graph=Graph().parse(Path(__file__).resolve().parents[1]/'ontology.ttl'))
        self.assertTrue(conforms,report)
