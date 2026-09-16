import json
from pathlib import Path
import sys
import unittest
import tempfile
import shutil
from unittest.mock import patch
from rdflib import Graph, URIRef
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import shared_tags as tags

class SharedTagTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.terms,cls.version=tags.load_vocabulary(ROOT)
    def record(self):
        target=tags.BASE+'entities/python'
        return {'subject':tags.BASE+'jobs/live/job/test','kind':'jobs','key':'fixture','fields':{'description':'Python or Java experience preferred.'},'source':'https://example.com/job','candidates':[target]}
    def assignment(self):
        return {'target':tags.BASE+'entities/python','field':'description','quote':'Python or Java experience preferred.','relation':'requested-skill','requirementStatus':'preferred','requirementGroup':'Python or Java','state':'accepted'}
    def test_public_projection_excludes_internal_requirement_metadata(self):
        g,p=tags.assessment_graph(self.record(),[self.assignment()],self.terms,{})
        self.assertTrue(list(g.objects(None,tags.OKG.requirementStatus)))
        self.assertTrue(list(g.objects(None,tags.OKG.requirementGroup)))
        self.assertNotIn('requirementStatus',json.dumps(p));self.assertNotIn('requirementGroup',json.dumps(p))
        self.assertEqual(p['tools'][0]['evidence']['reviewState'],'automated')
    def test_reused_model_attribution_is_preserved(self):
        r={**self.record(),'model':'claude-sonnet-4-6'}
        with patch.object(tags,'MODEL','gpt-5.4-2026-03-05'):
            g,p=tags.assessment_graph(r,[self.assignment()],self.terms,{})
        methods=list(map(str,g.objects(None,tags.OKG.classificationMethod)))
        self.assertTrue(methods)
        self.assertTrue(all('claude-sonnet-4-6' in method for method in methods))

    def test_openai_response_adapter_and_quota_failure(self):
        response=unittest.mock.Mock(status_code=200)
        response.json.return_value={'choices':[{'finish_reason':'stop','message':{'content':json.dumps({'records':[{'key':'fixture','assignments':[self.assignment()]}]})}}],'usage':{}}
        with patch.object(tags,'PROVIDER','openai'),patch.object(tags.requests,'post',return_value=response) as post:
            result,_=tags.request_batch([self.record()],self.terms,'fixture-key',model='gpt-5.4-2026-03-05')
            self.assertEqual(result['fixture'][0]['target'],self.assignment()['target'])
            self.assertEqual(post.call_args.args[0],'https://api.openai.com/v1/chat/completions')
            self.assertEqual(post.call_args.kwargs['json']['reasoning_effort'],'medium')
            response.status_code=429;response.json.return_value={'error':{'code':'insufficient_quota'}}
            with self.assertRaises(tags.ClassificationUnavailable):tags.request_batch([self.record()],self.terms,'fixture-key')

    def test_human_rejection_survives_new_automatic_assignment(self):
        r=self.record();a=self.assignment();override={(r['subject'],a['target']):{'reviewState':'rejected'}}
        g,p=tags.assessment_graph(r,[a],self.terms,override)
        self.assertEqual(p['tools'],[]);self.assertFalse(list(g.triples((None,tags.OKG.usesResource,None))))
    def test_ambiguous_assignments_not_materialized(self):
        a={**self.assignment(),'state':'suggested'}
        g,p=tags.assessment_graph(self.record(),[a],self.terms,{})
        self.assertEqual(p['tools'],[])
    def test_invented_quote_and_unknown_target_rejected(self):
        for change in [{'quote':'Required Python'}, {'target':'https://example.com/unapproved'}]:
            with self.subTest(change=change),self.assertRaises(ValueError):tags.validate_response([{**self.assignment(),**change}],self.record(),self.terms)
    def test_multi_domain_projection_and_determinism(self):
        r=self.record();r['fields']={'description':'Healthcare and banking applications.'}
        assignments=[{'target':str(tags.OKG[x]),'field':'description','quote':r['fields']['description'],'relation':'subject-domain','state':'accepted'} for x in ['Healthcare','FinancialServices']]
        g,p=tags.assessment_graph(r,assignments,self.terms,{})
        self.assertEqual(len(p['domains']),2)
        again,p2=tags.assessment_graph(r,assignments,self.terms,{})
        self.assertEqual(set(g),set(again));self.assertEqual(p,p2)
    def test_registry_reuses_catalog_identities_and_blocks_self_use(self):
        neo=tags.BASE+'software/neo4j/';r=self.record();r['kind']='software';r['subject']=neo
        a={**self.assignment(),'target':neo}
        _,p=tags.assessment_graph(r,[a],self.terms,{})
        self.assertEqual(p['tools'],[])
        self.assertIn(neo,self.terms)
    def test_matching_handles_boundaries_and_alias_collisions(self):
        terms={'one':{'id':'one','dimension':'tools','label':'Python','aliases':[],'catalogPages':[]},'two':{'id':'two','dimension':'tools','label':'RDF','aliases':[],'catalogPages':[]}}
        index=tags.entity_index(terms,{})
        self.assertEqual(tags.candidates({'description':'CPython and RDFish'},index,terms,'job'),[])
        self.assertEqual(tags.candidates({'description':'Python / RDF'},index,terms,'job'),['one','two'])
    def test_content_and_vocabulary_changes_invalidate_key(self):
        a=tags.digest([tags.fields({'title':'Engineer','description':'Python  skills'},'jobs'),self.version,tags.METHOD])
        same=tags.digest([tags.fields({'title':'Engineer','description':'Python skills'},'jobs'),self.version,tags.METHOD])
        changed=tags.digest([tags.fields({'title':'Engineer','description':'Java skills'},'jobs'),self.version,tags.METHOD])
        self.assertEqual(a,same);self.assertNotEqual(a,changed)
        self.assertNotEqual(a,tags.digest([tags.fields({'title':'Engineer','description':'Python skills'},'jobs'),'new-version',tags.METHOD]))
    def test_alternative_requirements_keep_both_public_tool_tags(self):
        r=self.record();r['fields']={'description':'Experience with Neo4j, Stardog, or equivalent.'}
        assignments=[{**self.assignment(),'target':tags.BASE+'software/'+name+'/', 'quote':r['fields']['description'],'requirementGroup':''} for name in ('neo4j','stardog')]
        g,p=tags.assessment_graph(r,assignments,self.terms,{})
        self.assertEqual({t['label'] for t in p['tools']},{'Neo4j','Stardog'})
        self.assertEqual(len(list(g.objects(None,tags.OKG.requirementGroup))),2)
        self.assertNotIn('requirementGroup',json.dumps(p))

    def test_alternative_group_is_grounded_even_when_model_omits_it(self):
        a={**self.assignment(),'requirementGroup':''}
        result=tags.evidence_boundaries(self.record(),[a],self.terms)[0]
        self.assertEqual(result['requirementGroup'],a['quote'])
        a['requirementGroup']='Invented alternative wording'
        result=tags.evidence_boundaries(self.record(),[a],self.terms)[0]
        self.assertEqual(result['requirementStatus'],'unspecified')
        self.assertEqual(result['requirementGroup'],a['quote'])

    def test_company_capability_is_not_job_activity(self):
        r=self.record();r['fields']={'description':'The company specializes in integrating complex data from disparate sources into unified intelligence systems.'}
        a={**self.assignment(),'target':tags.BASE+'jobs/vocab/activity-semantic-integration','quote':'integrating complex data from disparate sources into unified intelligence systems'}
        _,p=tags.assessment_graph(r,[a],self.terms,{})
        self.assertEqual(p['activities'],[])

    def test_catalog_title_is_not_an_activity_assertion(self):
        r=self.record();r['kind']='resource';r['fields']={'title':'Botryllus anatomy and development ontology'}
        a={**self.assignment(),'field':'title','target':tags.BASE+'vocabularies/activities/ontology-engineering','quote':r['fields']['title']}
        _,p=tags.assessment_graph(r,[a],self.terms,{})
        self.assertEqual(p['activities'],[])

    def test_bare_ontology_identity_is_not_engineering_evidence(self):
        r=self.record();r['kind']='resource';r['fields']={'description':'Brucellosis Ontology is a biomedical ontology.'}
        a={**self.assignment(),'target':tags.BASE+'vocabularies/activities/ontology-engineering','quote':r['fields']['description']}
        g,p=tags.assessment_graph(r,[a],self.terms,{})
        self.assertEqual(p['activities'],[])

    def test_refresh_reuses_cache_and_preserves_original_job_and_catalog(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            for relative in ['vocabularies/categories.ttl','vocabularies/activities.ttl','vocabularies/supplementary-entities.ttl','data/ontologies.ttl','data/software.ttl','data/ontologies.json','data/software.json','data/page_qids.json','curation/tag-decisions.ttl']:
                dest=root/relative;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/relative,dest)
            raw={'id':'fixture','title':'Engineer','description':'Python or Java experience preferred.','hiringOrganization':'Fixture employer','canonicalUrl':'https://example.com/job','sourceUrl':'https://example.com/job','classification':'review','active':True,'evidence':[]}
            jobs=root/'data/jobs';jobs.mkdir();tags.write_json(jobs/'jobs.json',[raw])
            graph=Graph();uri=URIRef(tags.subject(raw,'jobs'));graph.add((uri,tags.SCHEMA.description,tags.Literal(raw['description'])));tags.write_rdf(jobs/'jobs.ttl',graph)
            before=(root/'data/ontologies.ttl').read_bytes()
            def model(batch,*args):return {r['key']:[self.assignment()] for r in batch},{}
            with patch.dict('os.environ',{'ANTHROPIC_API_KEY':'fixture-only','OPENAI_API_KEY':'fixture-only'}),patch.object(tags,'request_batch',side_effect=model) as mocked:
                tags.run(root,allow_llm=True,only={'jobs'},workers=1)
                self.assertEqual(mocked.call_count,1)
            first=(jobs/'jobs.json').read_bytes()
            with patch.object(tags,'request_batch',side_effect=AssertionError('Unchanged content must use its cache')):
                tags.run(root,allow_llm=False,only={'jobs'})
            self.assertEqual(first,(jobs/'jobs.json').read_bytes())
            # An unrelated automatic catalog admission must not invalidate jobs.
            catalog=Graph().parse(root/'data/software.ttl');new=URIRef(tags.BASE+'software/unrelated-new-tool/')
            catalog.add((new,tags.OKG.wikidataId,URIRef('http://www.wikidata.org/entity/Q999999999')))
            catalog.add((new,tags.OKG.title,tags.Literal('Unrelated New Tool')))
            tags.write_rdf(root/'data/software.ttl',catalog)
            with patch.object(tags,'request_batch',side_effect=AssertionError('Unrelated entity changed')):
                tags.run(root,allow_llm=False,only={'jobs'})
            self.assertEqual(first,(jobs/'jobs.json').read_bytes())
            self.assertEqual(before,(root/'data/ontologies.ttl').read_bytes())
            output=json.loads(first)[0]
            for key,value in raw.items():self.assertEqual(output[key],value)

if __name__=='__main__':unittest.main()
