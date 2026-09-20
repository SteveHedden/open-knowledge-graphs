import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from datetime import date
from rdflib import Graph, Literal, URIRef
from rdflib.namespace import RDF
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import release_metadata as releases
import catalog_events as events
import fetch_data as fetch
from semantic_config import OKG,load_source_mappings,ONTOLOGIES_DATASET

ITEM='http://www.wikidata.org/entity/Q1'
STMT='http://www.wikidata.org/entity/statement/Q1-version'
def row(version='1',dt='2026-07-05T00:00:00Z',precision=11,rank='NormalRank',statement=STMT):
 d={k:{'value':v} for k,v in {'item':ITEM,'version':version,'verStmt':statement,'versionRank':releases.WB+rank}.items()}
 if dt:d.update({k:{'value':str(v)} for k,v in {'pubDate':dt,'precision':precision,'calendar':releases.GREGORIAN}.items()})
 return d

def item(kind='resource',version='1',dt='2026-07-05T00:00:00Z'):
 return {'wikidataId':'https://www.wikidata.org/wiki/Q1','title':'Example','types':['Ontology' if kind=='resource' else 'Software'],
         'canonicalUrl':releases.BASE+kind+'/example/','latestRelease':releases.select([row(version,dt)])[ITEM]}

class ReleaseTests(unittest.TestCase):
 def test_query_pairs_qualifier_value_and_preserves_references(self):
  g=Graph().parse(data='''@prefix wd: <http://www.wikidata.org/entity/> .
@prefix p: <http://www.wikidata.org/prop/> . @prefix ps: <http://www.wikidata.org/prop/statement/> .
@prefix pq: <http://www.wikidata.org/prop/qualifier/> . @prefix pqv: <http://www.wikidata.org/prop/qualifier/value/> .
@prefix wdt: <http://www.wikidata.org/prop/direct/> . @prefix wb: <http://wikiba.se/ontology#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> . @prefix prov: <http://www.w3.org/ns/prov#> .
@prefix pr: <http://www.wikidata.org/prop/reference/> .
wd:Q1 wdt:P577 "1990-01-01T00:00:00Z"^^xsd:dateTime ; p:P348 <urn:statement> .
<urn:statement> ps:P348 "1" ; wb:rank wb:PreferredRank ; pq:P577 "2026-07-05T00:00:00Z"^^xsd:dateTime ; pqv:P577 <urn:date> ; prov:wasDerivedFrom <urn:reference> .
<urn:date> wb:timeValue "2026-07-05T00:00:00Z"^^xsd:dateTime ; wb:timePrecision 11 ; wb:timeCalendarModel wd:Q1985727 .
<urn:reference> pr:P854 <https://example.com/release> .
''',format='turtle')
  bindings=json.loads(g.query(releases.query('VALUES ?item { wd:Q1 }')).serialize(format='json'))['results']['bindings']
  selected=releases.select(bindings)[ITEM]
  self.assertEqual(selected['date'],'2026-07-05');self.assertIn('urn:reference',selected['references'])
  self.assertIn('http://www.wikidata.org/prop/qualifier/P577',selected['qualifiers'])
  g.remove((URIRef('urn:statement'),URIRef('http://www.wikidata.org/prop/qualifier/P577'),None))
  g.remove((URIRef('urn:statement'),URIRef('http://www.wikidata.org/prop/qualifier/value/P577'),None))
  bindings=json.loads(g.query(releases.query('VALUES ?item { wd:Q1 }')).serialize(format='json'))['results']['bindings']
  self.assertNotIn('date',releases.select(bindings)[ITEM])
 def test_rank_and_same_statement(self):
  rows=[row('1',None,rank='PreferredRank'),row('2',statement='urn:2'),row('99',rank='DeprecatedRank',statement='urn:99')]
  self.assertEqual(releases.select(rows)[ITEM]['version'],'1');self.assertNotIn('date',releases.select(rows)[ITEM])
 def test_unknown_version_is_not_a_literal_identifier(self):
  unknown=row();unknown['version']={'type':'bnode','value':'unknown-value-node'}
  self.assertEqual(releases.select([unknown]),{})
  self.assertEqual(releases.select([row(version=' ')]),{})
 def test_precision_and_unsupported_dates(self):
  for precision,expected in [(9,'2026'),(10,'2026-07'),(11,'2026-07-05')]:
   self.assertEqual(releases.select([row(precision=precision)])[ITEM]['date'],expected)
  for r in [row(precision=8),{**row(),'calendar':{'value':'http://www.wikidata.org/entity/Q1985786'}}]:
   self.assertNotIn('date',releases.select([r])[ITEM])
 def test_conflicting_statement_dates_are_unknown(self):
  selected=releases.select([row(),row(dt='2026-07-06T00:00:00Z')])[ITEM]
  self.assertNotIn('date',selected);self.assertEqual(selected['dateIssue'],'conflicting-or-unsupported-date')
 def test_ties_explicit_and_deterministic(self):
  rows=[row('1'),row('2',statement='urn:2')]
  self.assertEqual(releases.select(rows),releases.select(list(reversed(rows))))
  self.assertIn('selectionIssue',releases.select(rows)[ITEM])
 def test_overlapping_coarse_dates_are_ambiguous(self):
  selected=releases.select([row('1',precision=9),row('2',statement='urn:2')])[ITEM]
  self.assertEqual(selected['selectionIssue'],'overlapping-release-dates')
 def test_resource_projection_and_date_datatype(self):
  for kind,typ in [('resource',OKG.Ontology),('software',OKG.Software)]:
   r=fetch.ResourceRecord(ITEM,'Example',types={typ},release=releases.select([row(precision=10)])[ITEM])
   g=fetch.build_graph({ITEM:r},{},{},set(),{},kind=='software',kind,{'Q1':'example'})
   result=fetch.extract_items_from_graph(g,{typ},kind=='software',{typ:'Example'})[0]
   self.assertEqual(result['releaseDate'],'2026-07');self.assertEqual(result['releaseDatePrecision'],'month')
   self.assertEqual(result['latestRelease']['statement'],STMT)
   releases.validate_graph(g)
   g.set((URIRef(result['canonicalUrl']),OKG.releaseDate,Literal('2026-07-01')))
   with self.assertRaisesRegex(ValueError,'Release'):releases.validate_graph(g)
 def test_resource_detail_page_and_structured_version(self):
  import generate_pages
  from test_semantic_metadata import page_fixture
  record=page_fixture(canonicalUrl=releases.BASE+'resource/example/',latestVersion='3',releaseDate='2026-07')
  ld=json.loads(generate_pages.make_json_ld(record,'resource'))
  self.assertEqual(ld['version'],'3');self.assertNotIn('softwareVersion',ld)
  html=generate_pages.make_page(record,'resource','example')
  self.assertIn('Latest version:</strong> 3 (2026-07)',html)
  self.assertNotIn('2026-07-01',html)
  record.pop('releaseDate');record.pop('latestVersion')
  self.assertNotIn('Latest version:',generate_pages.make_page(record,'resource','example'))
 def test_actual_wikidata_examples(self):
  sys.path.insert(0,str(ROOT/'tests/fixtures/releases'))
  from entity_bindings import bindings
  examples=json.loads((ROOT/'tests/fixtures/releases/wikidata-examples.json').read_text())
  selected=releases.select([row for q,e in examples.items() for row in bindings(q,e)])
  self.assertEqual(selected['http://www.wikidata.org/entity/Q3475322']['version'],'30.1')
  self.assertEqual(selected['http://www.wikidata.org/entity/Q3475322']['date'],'2026-09-15')
  self.assertTrue(selected['http://www.wikidata.org/entity/Q3475322']['references'])
  self.assertEqual(selected['http://www.wikidata.org/entity/Q141112433']['version'],'2.0.16')
  self.assertNotIn('http://www.wikidata.org/entity/Q4866972',selected)
  from jsonschema import Draft202012Validator, FormatChecker
  schema=json.loads((ROOT/'validation/catalog-events-v1/events.schema.json').read_text())
  payload=json.loads((ROOT/'tests/fixtures/releases/event-feed.json').read_text())
  Draft202012Validator(schema,format_checker=FormatChecker()).validate(payload)
  self.assertEqual(payload['events'][0]['date'],'2026-09-15')
 def test_source_mappings_include_resources(self):
  m=load_source_mappings(ROOT/'sources.ttl');self.assertEqual(m.property_id_for('version',ONTOLOGIES_DATASET,'string'),'P348')

class EventsTests(unittest.TestCase):
 def setUp(self):
  t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup);self.root=Path(t.name);(self.root/'data').mkdir()
 def save(self,items,kind='resource'):
  (self.root/f'data/{events.KINDS[kind]}.json').write_text(json.dumps({'items':items}))
 def seed(self):
  g=Graph();events.record_identity(g,'resource','Q99',uncertain=True);events.write_graph(self.root/events.LEDGER,g)
 def sync(self):return events.synchronize(self.root,'2026-09-20T12:00:00Z')['events']
 def test_no_migration_additions_and_old_release_uses_actual_date(self):
  self.save([item()]);out=self.sync();self.assertEqual(len(out),1)
  self.assertEqual(out[0]['type'],'release');self.assertEqual(out[0]['date'],'2026-07-05')
  self.assertEqual(out[0]['discoveredAt'],'2026-09-20T12:00:00Z')
 def test_refresh_rename_restore_are_idempotent(self):
  self.seed();self.save([item()]);out=self.sync();self.assertEqual(len(out),2)
  data=(self.root/events.LEDGER).read_bytes();self.assertEqual(out,self.sync());self.assertEqual(data,(self.root/events.LEDGER).read_bytes())
  self.save([]);self.assertTrue(all(not r['eligible'] for r in self.sync()))
  renamed=item();renamed['title']='Renamed';renamed['canonicalUrl']=releases.BASE+'resource/renamed/'
  self.save([renamed]);restored=self.sync();self.assertEqual({r['id'] for r in out},{r['id'] for r in restored})
  self.assertTrue(all(r['title']=='Renamed' for r in restored));events.validate(self.root)
 def test_date_correction_retains_revision_without_duplicate_event(self):
  self.save([item()]);first=self.sync()[0]
  self.save([item(dt='2026-07-06T00:00:00Z')]);second=self.sync()[0]
  self.assertEqual(first['id'],second['id']);self.assertEqual(len(second['history']),2)
 def test_undated_ambiguous_future_and_metadata_only(self):
  self.save([item(dt=None)]);self.assertEqual(self.sync(),[])
  x=item();x['latestRelease']['selectionIssue']='tied';self.save([x]);self.assertFalse(self.sync()[0]['eligible'])
  x=item(dt='2027-01-01T00:00:00Z');self.save([x]);self.assertFalse(self.sync()[0]['eligible'])
  x=item();x.pop('latestRelease');x['updatedAt']='2026-09-20';self.save([x]);self.assertFalse(self.sync()[0]['eligible'])
 def test_shared_contract_across_catalogs(self):
  self.seed();self.save([item()]);self.save([item('software')],'software');out=self.sync()
  self.assertEqual(len(out),4);self.assertEqual({e['kind'] for e in out},{'resource','software'})
 def test_coarse_date_end_not_invented(self):
  self.assertFalse(events.date_ended('2026',date(2026,9,20)));self.assertTrue(events.date_ended('2026-07',date(2026,9,20)))
 def test_dataset_snapshot_carries_release_but_cannot_overwrite_event_ledger(self):
  from test_dataset_snapshots import fixture
  import dataset_snapshots as snapshots
  import shared_tags as tags
  fixture(self.root)
  path=self.root/'data/ontologies.ttl';g=Graph().parse(path)
  subject=URIRef(releases.BASE+'resource/fixture/')
  releases.add_to_graph(g,subject,releases.select([row()])[ITEM]);tags.write_rdf(path,g)
  payload=tags.read(self.root/'data/ontologies.json')
  payload['items']=fetch.extract_items_from_graph(g,{OKG.Ontology},False,{OKG.Ontology:'Ontology'})
  tags.write_json(self.root/'data/ontologies.json',payload)
  events.synchronize(self.root,'2026-09-20T12:00:00Z')
  history=(self.root/events.LEDGER).read_bytes()
  destination=self.root/'snapshot'
  manifest=snapshots.bundle(self.root,'resource',destination,'fixture')
  self.assertNotIn(events.LEDGER,manifest['files'])
  snapshots.copy_dataset(destination,self.root,'resource')
  self.assertEqual(history,(self.root/events.LEDGER).read_bytes())
  events.synchronize(self.root,'2026-09-21T12:00:00Z')
  self.assertEqual(history,(self.root/events.LEDGER).read_bytes())
  events.validate(self.root)
 def test_history_backfill_baseline_rename_removal_and_new(self):
  subprocess.run(['git','init','-q'],cwd=self.root,check=True)
  def commit(message):
   subprocess.run(['git','add','.'],cwd=self.root,check=True)
   subprocess.run(['git','-c','user.name=Fixture','-c','user.email=fixture@example.com','commit','-qm',message],cwd=self.root,check=True)
  self.save([item()]);commit('baseline')
  self.save([]);commit('removed')
  new=item();new['wikidataId']='https://www.wikidata.org/wiki/Q2';self.save([item(),new]);commit('restored and new')
  g=events.backfill(self.root,self.root)
  self.assertFalse(events.text(g,events.identity('resource','Q1'),OKG.firstSeenAt))
  self.assertTrue(events.text(g,events.identity('resource','Q2'),OKG.firstSeenAt))
  before=(self.root/events.LEDGER).read_bytes();events.backfill(self.root,self.root);self.assertEqual(before,(self.root/events.LEDGER).read_bytes())

if __name__=='__main__':unittest.main()
