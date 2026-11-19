"""Purpose discovery must retain both the software and exact-use constraints."""
import json
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch
from rdflib import Graph
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import fetch_data as f
import semantic_config as sc

class PurposeAdmissionTests(unittest.TestCase):
    def test_discovery_requires_software_and_exact_construction_purpose(self):
        registry = sc.load_source_mappings()
        graph = Graph().parse(data='''
          @prefix wd: <http://www.wikidata.org/entity/> .
          @prefix wdt: <http://www.wikidata.org/prop/direct/> .
          wd:Q188860 wdt:P279 wd:Q7397 .
          wd:Q29642950 wdt:P279 wd:Q188860 .
          wd:Q1 wdt:P31 wd:Q188860; wdt:P366 wd:Q120971305 .
          wd:Q2 wdt:P31 wd:Q29642950; wdt:P366 wd:Q120971305 .
          wd:Q3 wdt:P31 wd:Q7397; wdt:P366 wd:Q120971305 .
          wd:Q4 wdt:P31 wd:Q7397; wdt:P366 wd:Q816826 .
          wd:Q5 wdt:P31 wd:Q7397; wdt:P366 wd:Q121362277 .
          wd:Q6 wdt:P31 wd:Q7397; wdt:P2283 wd:Q120971305 .
          wd:Q7 wdt:P31 wd:Q43229; wdt:P366 wd:Q120971305 .
          wd:Q8 wdt:P366 wd:Q120971305 .
          wd:Q9 wdt:P31 wd:Q7397; wdt:P366 wd:Q900 .
          wd:Q900 wdt:P279 wd:Q120971305 .
          wd:Q10 wdt:P31 wd:Q188860 .
          wd:Q11 wdt:P31 wd:Q140639670 .
          wd:Q1 wdt:P31 wd:Q124653107 .
        ''', format='turtle')
        def execute(session, query, label):
            return json.loads(graph.query(query).serialize(format='json'))['results']['bindings']
        with patch.object(f, 'run_wdqs_query', side_effect=execute), patch.object(f.time, 'sleep'):
            result = f.fetch_software_qids(None, replace(registry, source_inclusions=()))
        self.assertEqual(result, {'Q1', 'Q2', 'Q3', 'Q11'})
        # No per-item allowance is needed and removing the purpose route excludes Q1-3
        # except Q1, which independently qualifies through semantic-web software.
        without = replace(registry, source_inclusions=(), class_mappings=tuple(
            m for m in registry.class_mappings if not m.required_purpose_id))
        with patch.object(f, 'run_wdqs_query', side_effect=execute), patch.object(f.time, 'sleep'):
            self.assertEqual(f.fetch_software_qids(None, without), {'Q1', 'Q11'})

    def test_invalid_purpose_identifier_and_catalog_rejected(self):
        original = sc.SOURCES_PATH.read_text()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'sources.ttl'
            for value in ['invalid', 'Q0', 'Q120971305 . ?item ?p ?o']:
                path.write_text(original.replace('requiredPurposeId "Q120971305"', f'requiredPurposeId "{value}"'))
                with self.assertRaises(sc.SemanticConfigError):
                    sc.load_source_mappings(path)
            prefix, rule = original.split('src:class-Q7397', 1)
            for old, new in [
                ('okg:requiredPurposeId "Q120971305" ;', ''),
                ('okg:requiredSourcePropertyId "P366" ;', ''),
                ('okg:requiredPurposeId "Q120971305" ;',
                 'okg:requiredPurposeId "Q120971305" ; okg:requiredTargetType okg:Ontology ;'),
            ]:
                path.write_text(prefix + 'src:class-Q7397' + rule.replace(old, new))
                with self.assertRaises(sc.SemanticConfigError):
                    sc.load_source_mappings(path)
            path.write_text(prefix + 'src:class-Q7397' + rule.replace('/datasets/software', '/datasets/ontologies'))
            with self.assertRaises(sc.SemanticConfigError):
                sc.load_source_mappings(path)
