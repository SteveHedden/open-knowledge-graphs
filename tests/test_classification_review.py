"""Task 51 behavior: pending publication, validated review and inbox reconciliation."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from rdflib import Graph, Literal, URIRef
from rdflib.namespace import RDF
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import shared_tags as tags
import classification_review as review
import classification_issue as issue

TERM={'id':tags.BASE+'entities/python','label':'Python','dimension':'tools','definition':'Programming language',
      'aliases':[],'broader':[],'catalogPages':[],'types':[]}

class ReviewTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
  self.terms={TERM['id']:copy.deepcopy(TERM)}
  self.r={'subject':tags.BASE+'jobs/live/job/example','kind':'jobs','raw':{'active':True,'classification':'qualified'},
          'fields':{'title':'Engineer','description':'Python experience required.','qualifications':'Graph skills.'},'candidates':[TERM['id']], 'source':'https://example.com/job'}
  self.a={'target':TERM['id'],'field':'description','quote':'Python experience required.','relation':'requested-skill',
          'requirementStatus':'required','requirementGroup':'','state':'accepted'}
 def previous(self):
  r={**self.r,'key':'initial'};g,p=tags.assessment_graph(r,[self.a],self.terms,{})
  review.annotate(g,r,self.terms);ass=g.value(URIRef(r['subject']),tags.OKG.tagAssessment)
  return {r['subject']:(g,ass,self.terms)}
 def prepare(self, r=None, prior=None, results=None):
  r=copy.deepcopy(r or self.r)
  rows=review.prepare_record(self.root,r,self.terms,prior or {},results or [],{})
  return r,rows
 def result(self, outcome='accepted'):
  ctx=review.context(self.r,self.terms);h=tags.digest(self.r['fields'])
  value={'version':'1','id':tags.BASE+'reviews/test','subject':self.r['subject'],'kind':'jobs','inputHash':h,
     'outcome':outcome,'reviewer':'fixture-reviewer','method':'codex-direct','reviewedAt':'2026-09-20T00:00:00Z',
     'scope':list(tags.DIMS),'vocabularyContext':ctx,'correctionsHash':review.corrections_hash(self.root,self.r['subject']),
     'findings':[], 'assignments':[] if outcome=='reviewed-empty' else [dict(self.a,state='reviewed')]}
  value['digest']=tags.digest(value)
  sid=tags.digest([self.r['subject'],h,ctx]);review.atom_json(self.root/f'data/classification-evidence/jobs/{sid}.json',
       {'subject':self.r['subject'],'fields':self.r['fields'],'vocabularyContext':ctx})
  return value
 def test_untagged_is_pending_without_network(self):
  with patch.object(tags.requests,'post',side_effect=AssertionError('API used')):
   r,rows=self.prepare()
  self.assertEqual(r['assessment_status'],'pending');self.assertEqual(rows,[])
 def test_assignment_scoped_invalidation(self):
  prior=self.previous();changed=copy.deepcopy(self.r);changed['fields']['qualifications']='Different requirement'
  r,rows=self.prepare(changed,prior);self.assertEqual(len(rows),1);self.assertEqual(r['assessment_status'],'pending')
  changed['fields']['description']='No programming needed.'
  r,rows=self.prepare(changed,prior);self.assertEqual(rows,[])
 def test_unchanged_empty_is_explicit_not_pending(self):
  result=self.result('reviewed-empty');r,rows=self.prepare(results=[result])
  self.assertEqual(r['assessment_status'],'reviewed-empty');self.assertEqual(rows,[])
 def test_deferred_is_not_empty(self):
  result=self.result('reviewed-empty');result['outcome']='deferred'
  with self.assertRaisesRegex(ValueError,'finding'):review.validate_result(result,self.r,self.terms,self.root)
  result['findings']=['Ambiguous usage; user review needed.']
  r,rows=self.prepare(results=[result]);self.assertEqual(r['assessment_status'],'deferred')
 def test_stale_hash_quote_target_and_vocabulary_rejected(self):
  valid=self.result()
  for change in [{'inputHash':'stale'},{'vocabularyContext':{TERM['id']:'changed'}},
                 {'assignments':[{**self.a,'quote':'Invented quote'}]}, {'assignments':[{**self.a,'target':'https://example.com/new'}]}]:
   with self.subTest(change=change),self.assertRaises(ValueError):
    review.validate_result({**valid,**change},self.r,self.terms,self.root)
 def test_additive_vocabulary_is_compatible(self):
  result=self.result();terms={**self.terms,'new':{**TERM,'id':'new'}}
  review.validate_result(result,self.r,terms,self.root)
 def test_semantic_change_removes_only_affected_assignment(self):
  prior=self.previous();self.terms[TERM['id']]={**TERM,'definition':'A snake'}
  r,rows=self.prepare(prior=prior);self.assertEqual(rows,[]);self.assertEqual(r['assessment_status'],'pending')
 def test_formatting_and_metadata_do_not_change_evidence_hash(self):
  one={'title':'Engineer','description':'<p>Python <b>experience</b> required.</p>','latestVersion':'1','retrievedAt':'today'}
  two={**one,'description':'Python experience\n required.','latestVersion':'2','retrievedAt':'tomorrow'}
  self.assertEqual(tags.fields(one,'software'),tags.fields(two,'software'))
 def test_human_correction_preserved_until_relevant_change(self):
  previous=self.previous();key=(self.r['subject'],TERM['id']);decision={'reviewState':'rejected','sourceField':'description'}
  r=copy.deepcopy(self.r);r['fields']['qualifications']='New irrelevant field'
  review.prepare_record(self.root,r,self.terms,previous,[],{key:decision});self.assertIn(key,r['overrides'])
  r=copy.deepcopy(self.r);r['fields']['description']='Changed relevant evidence'
  review.prepare_record(self.root,r,self.terms,previous,[],{key:decision});self.assertNotIn(key,r['overrides'])
 def test_only_published_matching_review_completes_queue(self):
  row={'id':'one','inputHash':'hash','review':'result','status':'applied'}
  backlog={'records':[row]}
  self.assertEqual(len(issue.reconcile(backlog,{})),1)
  self.assertEqual(len(issue.reconcile(backlog,{'one':{'inputHash':'hash','review':'result','status':'complete'}})),0)
  row['status']='deferred';self.assertEqual(len(issue.reconcile(backlog,{'one':{'inputHash':'hash','review':'result','status':'complete'}})),1)
 def test_legacy_api_entry_points_are_disabled(self):
  import category_classifier
  with patch.object(tags.requests,'post',side_effect=AssertionError('API')):
   with self.assertRaises(tags.ClassificationUnavailable):tags.request_batch([],{},'unused')
   with self.assertRaises(category_classifier.CategoryClassificationError):category_classifier._request_classification_batch([],api_key='unused')

 def test_invalidated_human_correction_does_not_revive_on_second_refresh(self):
  prior=self.previous();key=(self.r['subject'],TERM['id']);decision={'reviewState':'rejected','sourceField':'description'}
  bindings={};r=copy.deepcopy(self.r)
  review.prepare_record(self.root,r,self.terms,prior,[],{key:decision},bindings)
  r['fields']['description']='Python expertise now optional.'
  review.prepare_record(self.root,r,self.terms,prior,[],{key:decision},bindings)
  self.assertNotIn(key,r['overrides'])
  g,_=tags.assessment_graph(r,[],self.terms,r['overrides']);review.annotate(g,r,self.terms)
  ass=g.value(URIRef(r['subject']),tags.OKG.tagAssessment)
  second={r['subject']:(g,ass,self.terms)}
  review.prepare_record(self.root,r,self.terms,second,[],{key:decision},bindings)
  self.assertNotIn(key,r['overrides']);self.assertEqual(r['assessment_status'],'pending')

class EndToEndTests(unittest.TestCase):
 def test_new_changed_import_apply_and_publication_recovery(self):
  from test_dataset_snapshots import fixture
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory);terms=fixture(root)
   jobs=tags.read(root/'data/jobs/jobs.json');jobs[0]['validThrough']='2099-01-01'
   jobs[0]['description']='Python experience preferred for building graph applications.'
   tags.write_json(root/'data/jobs/jobs.json',jobs)
   with patch.object(tags,'load_vocabulary',return_value=(terms,'fixture')),patch.object(tags.requests,'post',side_effect=AssertionError('Paid API')):
    tags.run(root,only={'jobs'})
    backlog=tags.read(root/review.BACKLOG);row=next(x for x in backlog['records'] if x['kind']=='jobs')
    self.assertEqual(row['status'],'pending')
    draft=root/'result.ttl';review.template(root,row['id'],draft)
    g=Graph().parse(draft);s=next(g.subjects(RDF.type,tags.OKG.ClassificationReview))
    g.set((s,tags.OKG.reviewedBy,Literal('fixture-reviewer')))
    g.set((s,tags.OKG.reviewOutcome,Literal('accepted')));g.remove((s,tags.OKG.unresolvedFinding,None))
    a=URIRef(str(s)+'/python');g.add((s,tags.OKG.tagAssignment,a))
    for p,v in [('tagTarget',URIRef(TERM['id'])),('sourceField',Literal('description')),
                ('supportingText',Literal('Python experience preferred')),
                ('relationContext',Literal('requested-skill')),('requirementStatus',Literal('preferred'))]:g.add((a,tags.OKG[p],v))
    g.serialize(draft,format='turtle')
    self.assertEqual(review.import_results(root,draft),1)
    before=(root/review.RESULTS).read_bytes();review.import_results(root,draft)
    self.assertEqual(before,(root/review.RESULTS).read_bytes())
    reviewed=review.build_backlog(root);self.assertEqual(next(x for x in reviewed['records'] if x['id']==row['id'])['status'],'reviewed')
    tags.run(root,only={'jobs'});current=tags.read(root/'data/jobs/jobs.json')[0]
    self.assertEqual(current['sharedTags']['tools'][0]['id'],TERM['id'])
    self.assertNotIn('requirementStatus',json.dumps(current['sharedTags']))
    applied=tags.read(root/review.BACKLOG);entry=next(x for x in applied['records'] if x['id']==row['id'])
    self.assertEqual(entry['status'],'applied');self.assertEqual(len(issue.reconcile({'records':[entry]},{})),1)
    live={row['id']:{'inputHash':row['inputHash'],'review':str(s),'status':'complete'}}
    self.assertEqual(issue.reconcile({'records':[entry]},live),[])
    current['description']='No programming experience needed.';tags.write_json(root/'data/jobs/jobs.json',[current])
    original=(root/review.RESULTS).read_bytes()
    with self.assertRaisesRegex(ValueError,'Stale'):review.import_results(root,draft)
    self.assertEqual(original,(root/review.RESULTS).read_bytes())
    tags.run(root,only={'jobs'});changed=tags.read(root/'data/jobs/jobs.json')[0]
    self.assertEqual(changed['sharedTags']['tools'],[])
    self.assertEqual(changed['sharedTags']['assessment']['status'],'pending')
    self.assertTrue((root/'data/classification-history/jobs.ttl').exists())


class InboxTests(unittest.TestCase):
 def test_idempotent_update_reopen_close_and_api_failure(self):
  class Client:
   def __init__(self):self.issue=None;self.calls=[]
   def find(self):return self.issue
   def call(self,m,p,v):
    self.calls.append((m,p,v));self.issue={**(self.issue or {'number':1,'state':'open'}),**v}
  c=Client();row={'id':'x','title':'Example','kind':'resource','reason':'new','status':'pending','publication':'published','evidence':'data/evidence.json'}
  self.assertEqual(issue.sync(c,[row],'owner/repo'),'created')
  self.assertEqual(issue.sync(c,[row],'owner/repo'),'unchanged')
  self.assertEqual(issue.sync(c,[],'owner/repo'),'updated');self.assertEqual(c.issue['state'],'closed')
  self.assertEqual(issue.sync(c,[row],'owner/repo'),'updated');self.assertEqual(c.issue['state'],'open')
  c.call=lambda *args:(_ for _ in ()).throw(RuntimeError('API failure'))
  with self.assertRaises(RuntimeError):issue.sync(c,[],'owner/repo')
  self.assertEqual(c.issue['state'],'open')

if __name__=='__main__':unittest.main()
