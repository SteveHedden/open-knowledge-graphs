"""Behavioral contracts for independent refreshes and pinned publication."""
import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from rdflib import Graph, Literal, URIRef
from rdflib.namespace import RDF

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import dataset_snapshots as snapshots
import shared_tags as tags
import catalog_snapshot as catalog

TERM={'id':tags.BASE+'entities/python','label':'Python','dimension':'tools','definition':'A programming language',
      'aliases':[],'broader':[],'types':[],'catalogPages':[]}


def fixture(root):
    terms={TERM['id']:copy.deepcopy(TERM)}
    (root/'vocabularies').mkdir(parents=True,exist_ok=True)
    for name in ('categories.ttl','software-types.ttl'):
        shutil.copy2(ROOT/'vocabularies'/name,root/'vocabularies'/name)
    tags.write_json(root/'data/tag-vocabularies.json', {'terms':list(terms.values())})
    tags.write_json(root/'data/uri_registry.json', {'resource':{},'software':{}})
    (root/'curation').mkdir(parents=True,exist_ok=True)
    (root/'curation/classifications.ttl').write_text('')
    tags.write_json(root/'jobs/catalog-mention-policy.json',{})
    for kind in snapshots.KINDS:
        row={'title':'Engineer','description':'Python expertise required.'}
        if kind=='jobs':row.update(id='fixture',classification='qualified',active=True,validThrough='2020-01-01',lastSeenAt='2020-01-01T00:00:00Z')
        else:row.update(canonicalUrl=tags.BASE+kind+'/fixture/',wikidataId='https://www.wikidata.org/wiki/Q1',aliases=[],types=['Ontology' if kind=='resource' else 'Software'])
        record={'subject':tags.subject(row,kind),'kind':kind,'key':'fixture-'+kind,'fields':tags.fields(row,kind),'candidates':[TERM['id']]}
        assignment={'target':TERM['id'],'field':'description','quote':row['description'],'state':'accepted','relation':'supports','requirementStatus':'required','requirementGroup':''}
        graph,projection=tags.assessment_graph(record,[assignment],terms,{})
        if kind!='jobs':
            owner=URIRef(record['subject'])
            graph.add((owner,RDF.type,tags.OKG.Ontology if kind=='resource' else tags.OKG.Software))
            graph.add((owner,tags.OKG.title,Literal(row['title'])))
            graph.add((owner,tags.OKG.description,Literal(row['description'])))
            graph.add((owner,tags.OKG.wikidataId,URIRef(row['wikidataId'])))

        row=tags.apply_projection(row,projection,kind)
        stem=snapshots.STEMS[kind]
        tags.write_json(root/f'data/{stem}.json',[row] if kind=='jobs' else {'generatedAt':'2026-09-19T00:00:00Z','items':[row]})
        tags.write_rdf(root/f'data/{stem}.ttl',graph)
    tags.write_json(root/'data/jobs/run.json',{'sourceRefreshes':{'fixture':'2026-09-19T00:00:00Z'}})
    return terms


class DatasetSnapshotTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.base=Path(self.tmp.name);self.root=self.base/'root';self.terms=fixture(self.root)

    def seal(self,kind='jobs',name='bundle'):
        destination=self.base/name
        snapshots.bundle(self.root,kind,destination,'abc123')
        return destination

    def test_complete_dataset_output_and_content_identity(self):
        for kind in snapshots.KINDS:
            destination=self.seal(kind,kind)
            m=snapshots.verify(destination,kind)
            self.assertEqual(m['dataset'],kind)
            self.assertNotIn('data/page_qids.json',m['files'])
            self.assertEqual(m['sourceRetrievedAt'],'2026-09-19T00:00:00Z')

    def test_partial_and_tampered_snapshots_are_rejected(self):
        destination=self.seal()
        (destination/'data/jobs/jobs.ttl').unlink()
        with self.assertRaisesRegex(ValueError,'Partial'):snapshots.verify(destination,'jobs')
        destination=self.seal(name='tampered')
        (destination/'data/jobs/jobs.json').write_text('[]')
        with self.assertRaisesRegex(ValueError,'checksum'):snapshots.verify(destination,'jobs')

    def test_stale_classification_evidence_is_rejected(self):
        path=self.root/'data/jobs/jobs.json';rows=tags.read(path);rows[0]['description']='Changed evidence';tags.write_json(path,rows)
        with self.assertRaisesRegex(ValueError,'evidence'):self.seal()

    def test_additive_and_label_link_changes_preserve_assignments_without_network(self):
        updated=copy.deepcopy(self.terms);updated[TERM['id']]['label']='Python language';updated[TERM['id']]['catalogPages']=[tags.BASE+'software/python/']
        updated['new']={**TERM,'id':'new','label':'New tool'}
        with patch.object(tags,'load_vocabulary',return_value=(updated,'new-version')),patch.object(tags.requests,'post',side_effect=AssertionError('network')):
            snapshots.reproject(self.root,{k:{'terms':list(self.terms.values())} for k in snapshots.KINDS})
        row=tags.read(self.root/'data/jobs/jobs.json')[0]
        resource=tags.read(self.root/'data/ontologies.json')['items'][0]
        self.assertEqual(resource['sharedTags']['tools'][0]['label'],'Python language')
        self.assertEqual(resource['sharedTags']['tools'][0]['catalogPages'],[tags.BASE+'software/python/'])
        self.assertFalse(row['active']);self.assertEqual(row['lastSeenAt'],'2020-01-01T00:00:00Z')
        graph=Graph().parse(self.root/'data/jobs/jobs.ttl')
        self.assertEqual(graph.value(URIRef(tags.subject(row,'jobs')),URIRef('https://openknowledgegraphs.com/jobs/ontology#active')),Literal(False))

    def test_semantic_removal_and_changed_meaning_require_review(self):
        for changed in ({},{TERM['id']:{**TERM,'definition':'Different meaning'}}):
            with patch.object(tags,'load_vocabulary',return_value=(changed,'changed')):
                snapshots.reproject(self.root,{k:{'terms':list(self.terms.values())} for k in snapshots.KINDS})
                row=tags.read(self.root/'data/ontologies.json')['items'][0]
                self.assertEqual(row['sharedTags']['tools'],[])
                self.assertEqual(row['sharedTags']['assessment']['status'],'pending')

    def test_registry_merge_keeps_concurrent_additions_and_blocks_url_changes(self):
        current={'resource':{'Q1':'one'},'software':{'Q2':'two'}}
        merged=snapshots.merge_registry(current,{'resource':{'Q3':'three'}},'resource')
        self.assertEqual(merged['resource'],{'Q1':'one','Q3':'three'});self.assertEqual(merged['software'],current['software'])
        for bad in ({'Q1':'renamed'},{'Q3':'one'}):
            with self.assertRaises(ValueError):snapshots.merge_registry(current,{'resource':bad},'resource')

    def test_unchanged_evidence_reuses_assessment_when_vocabulary_grows(self):
        updated=copy.deepcopy(self.terms);updated['new']={**TERM,'id':'new','label':'New tool'}
        with patch.object(tags,'ROOT',self.root),patch.object(tags,'load_vocabulary',return_value=(updated,'new-version')),patch.object(tags,'request_batch',side_effect=AssertionError('classification API called')) as request:
            tags.run(self.root,only={'jobs'})
            request.assert_not_called()

    def test_changed_evidence_never_reuses_stale_assessment(self):
        rows=tags.read(self.root/'data/jobs/jobs.json');rows[0]['description']='Changed Python evidence';tags.write_json(self.root/'data/jobs/jobs.json',rows)
        with patch.object(tags,'ROOT',self.root),patch.object(tags,'load_vocabulary',return_value=(self.terms,'version')),patch.object(tags,'request_batch') as request:
            tags.run(self.root,only={'jobs'})
            row=tags.read(self.root/'data/jobs/jobs.json')[0]
            self.assertEqual(row['sharedTags']['assessment']['status'],'pending')
            self.assertEqual(row['sharedTags']['tools'],[])
            request.assert_not_called()

    def test_meaning_change_cannot_be_silently_reclassified(self):
        changed={TERM['id']:{**TERM,'definition':'New meaning'}}
        with patch.object(tags,'ROOT',self.root),patch.object(tags,'load_vocabulary',return_value=(changed,'version')),patch.object(tags,'request_batch') as request:
            tags.run(self.root,only={'jobs'},allow_llm=True)
            row=tags.read(self.root/'data/jobs/jobs.json')[0]
            self.assertEqual(row['sharedTags']['assessment']['status'],'pending')
            self.assertEqual(row['sharedTags']['tools'],[])
            request.assert_not_called()

    def test_git_storage_deduplicates_and_pins_concurrent_arrivals(self):
        repo=self.base/'repo';remote=self.base/'remote.git';repo.mkdir()
        subprocess.run(['git','init','--bare',str(remote)],check=True,capture_output=True)
        subprocess.run(['git','init',str(repo)],check=True,capture_output=True)
        for key,value in [('user.name','Test'),('user.email','test@example.com')]:snapshots.git(repo,'config',key,value)
        (repo/'README').write_text('baseline');snapshots.git(repo,'add','README');snapshots.git(repo,'commit','-m','baseline')
        snapshots.git(repo,'remote','add','origin',str(remote))
        directory=self.seal();first=snapshots.store(repo,directory,'jobs')
        self.assertEqual(snapshots.store(repo,directory,'jobs'),first)
        pin_dir=self.base/'pinned';selection=snapshots.pin(repo,pin_dir)
        tags.write_json(self.root/'build/refresh-selection.json',selection)
        rows=tags.read(self.root/'data/jobs/jobs.json');rows[0]['salary']='100';tags.write_json(self.root/'data/jobs/jobs.json',rows)
        second=snapshots.store(repo,self.seal(name='newer'),'jobs')
        self.assertNotEqual(first,second)
        self.assertEqual(selection['jobs']['commit'],first)
        self.assertNotIn('salary',tags.read(pin_dir/'jobs/data/jobs/jobs.json')[0])
        followup=snapshots.pin(repo,self.base/'followup');self.assertEqual(followup['jobs']['commit'],second)
        # A late writer still based on the first acquisition cannot replace it.
        rows[0]['salary']='stale late writer';tags.write_json(self.root/'data/jobs/jobs.json',rows)
        with self.assertRaisesRegex(ValueError,'Newer dataset snapshot'):
            snapshots.store(repo,self.seal(name='late'),'jobs')
        self.assertEqual(snapshots.git(repo,'ls-remote','origin','refs/heads/dataset-snapshots/jobs').split()[0],second)
        self.assertEqual(snapshots.git(repo,'show',first+':snapshot.json'),(directory/'snapshot.json').read_text().strip())

    def test_reprojection_does_not_rewrite_unchanged_job_rdf(self):
        with patch.object(tags,'load_vocabulary',return_value=(self.terms,'version')):
            vocab={k:{'terms':list(self.terms.values())} for k in snapshots.KINDS}
            snapshots.reproject(self.root,vocab)
            path=self.root/'data/jobs/jobs.ttl';before=path.read_bytes();mtime=path.stat().st_mtime_ns
            snapshots.reproject(self.root,vocab)
            self.assertEqual(before,path.read_bytes());self.assertEqual(mtime,path.stat().st_mtime_ns)


class AcquisitionIsolationTests(unittest.TestCase):
    def test_single_dataset_queries_never_acquire_the_other_dataset(self):
        import fetch_data as fetch
        for kind in ('resource','software'):
            contexts=[]
            def query(session, sparql, context):
                contexts.append(context)
                return []
            with patch.object(fetch,'run_wdqs_query',side_effect=query),patch.object(fetch,'fetch_direct_iri_edges',return_value=[]),patch.object(fetch,'fetch_entity_labels',return_value=({},{},{})),patch.object(fetch,'fetch_human_creators',return_value=set()),patch.object(fetch,'fetch_person_identifiers',return_value={}),patch.object(fetch.time,'sleep'),patch.object(fetch.requests.Session,'request',side_effect=AssertionError('network')):
                self.assertEqual(fetch.run(kind),1)  # Empty source results must retain last good.
            self.assertTrue(contexts)
            if kind=='resource':self.assertFalse(any('software' in context for context in contexts))
            else:self.assertTrue(all('software' in context for context in contexts))

    def test_publisher_has_no_acquisition_or_classification_step(self):
        workflow=(ROOT/'.github/workflows/update-data.yml').read_text()
        self.assertNotIn('run: python scripts/fetch_data.py',workflow)
        self.assertNotIn('--classify',workflow)
        self.assertNotIn('secrets.OPENAI_API_KEY',workflow)
        self.assertNotIn('secrets.ANTHROPIC_API_KEY',workflow)
        for name in ('resource','software','jobs'):
            refresh=(ROOT/f'.github/workflows/update-{name}.yml').read_text()
            self.assertIn('group: dataset-refresh-'+name,refresh)
            self.assertIn('dataset_snapshots.py store',refresh)
            self.assertNotIn('git commit',refresh)

class SemanticReviewTests(unittest.TestCase):
    def test_approval_is_specific_to_subject_target_and_semantic_transition(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);old={TERM['id']:TERM};new={TERM['id']:{**TERM,'definition':'Reviewed new meaning'}}
            owner='https://example.test/job'
            row={'subject':owner,'target':TERM['id'],'fromSemantics':tags.digest(tags.term_semantics(TERM)),
                 'toSemantics':tags.digest(tags.term_semantics(new[TERM['id']])),
                 'state':'approved','reviewedBy':'fixture reviewer','reviewedAt':'2026-09-20'}
            tags.write_json(root/'curation/tag-semantic-reviews.json',[row])
            self.assertTrue(tags.semantic_reviewed(root,owner,TERM['id'],old,new))
            self.assertFalse(tags.semantic_reviewed(root,'other',TERM['id'],old,new))
            self.assertFalse(tags.semantic_reviewed(root,owner,TERM['id'],old,{TERM['id']:{**TERM,'definition':'Later meaning'}}))
            self.assertFalse(tags.semantic_reviewed(root,owner,TERM['id'],old,{}))

if __name__=='__main__':unittest.main()
