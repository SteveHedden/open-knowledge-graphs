import unittest
from rdflib import Graph, URIRef, Literal
from rdflib.namespace import RDF
from test_release_events import releases, fetch as fetch_data, row, ITEM
import generate_pages

class PrereleaseDisplay(unittest.TestCase):
 def test_selected_qualifier_survives_projection_and_display(self):
  source=row('0.8.1','2026-10-01T00:00:00Z')
  source.update(qualifierProperty={'type':'uri','value':'http://www.wikidata.org/prop/qualifier/P548'},qualifierValue={'type':'uri','value':'http://www.wikidata.org/entity/Q51930650'})
  release=releases.select([source])[ITEM]
  g=Graph();subject=URIRef('https://openknowledgegraphs.com/software/example/');kind=fetch_data.OKG.Software
  for p,o in [(RDF.type,kind),(fetch_data.OKG.wikidataId,URIRef(ITEM)),(fetch_data.OKG.title,Literal('Example'))]:g.add((subject,p,o))
  releases.add_to_graph(g,subject,release)
  result=fetch_data.extract_items_from_graph(g,{kind},True,{kind:'Software'})[0]
  self.assertEqual(result['releaseStatus'],'prerelease')
  result.update(canonicalUrl=str(subject),description='Example software',homepage='https://example.org/')
  self.assertIn('0.8.1 (prerelease)',generate_pages.make_page(result,'software','example'))
  release['qualifiers']={};g=Graph()
  for p,o in [(RDF.type,kind),(fetch_data.OKG.wikidataId,URIRef(ITEM)),(fetch_data.OKG.title,Literal('Example'))]:g.add((subject,p,o))
  releases.add_to_graph(g,subject,release)
  self.assertNotIn('releaseStatus',fetch_data.extract_items_from_graph(g,{kind},True,{kind:'Software'})[0])
