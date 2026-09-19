"""Supplementary tags retain their identity when catalog resources return."""
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from rdflib import Graph, Literal, URIRef
from rdflib.namespace import RDF
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import shared_tags as tags

class SupplementaryCatalogIdentityTests(unittest.TestCase):
    def test_returning_catalog_resources_reuse_tag_uris_and_suppress_self_tags(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            shutil.copytree(ROOT/'vocabularies',root/'vocabularies')
            (root/'data').mkdir()
            for f in ('ontologies.ttl','software.ttl','page_qids.json'):
                shutil.copy(ROOT/'data'/f,root/'data'/f)
            graph=Graph().parse(root/'data/ontologies.ttl')
            membership=json.loads((root/'data/page_qids.json').read_text())
            for name,qid in [('shacl','Q29377821'),('skos','Q2288360')]:
                page=URIRef(tags.BASE+'resource/'+name+'/')
                graph.add((page,RDF.type,tags.OKG.Ontology))
                graph.add((page,tags.OKG.title,Literal(name.upper())))
                graph.add((page,tags.OKG.wikidataId,URIRef('https://www.wikidata.org/wiki/'+qid)))
                membership['resource'][qid]=name
            graph.serialize(root/'data/ontologies.ttl',format='turtle')
            (root/'data/page_qids.json').write_text(json.dumps(membership))
            terms,_=tags.load_vocabulary(root)
            for name in ('shacl','skos'):
                ident=tags.BASE+'entities/'+name
                page=tags.BASE+'resource/'+name+'/'
                self.assertNotIn(page,terms)
                self.assertEqual(terms[ident]['catalogPages'],[page])
                self.assertEqual(terms[ident]['catalogIdentities'],[page])
                index=tags.entity_index(terms,{})
                self.assertNotIn(ident,tags.candidates({'title':name.upper()},index,terms,page))
                registry=tags.registry_graph(terms)
                self.assertIn((URIRef(ident),tags.OKG.catalogPage,URIRef(page)),registry)
            # An unreviewed same-name collision must still fail.
            sg=Graph().parse(root/'vocabularies/supplementary-entities.ttl')
            sg.remove((URIRef(tags.BASE+'entities/shacl'),tags.OKG.wikidataId,None))
            sg.serialize(root/'vocabularies/supplementary-entities.ttl',format='turtle')
            with self.assertRaisesRegex(ValueError,'duplicates a catalog entity: SHACL'):
                tags.load_vocabulary(root)
