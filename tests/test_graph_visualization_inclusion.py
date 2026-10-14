"""Software imports honor each source class's traversal policy."""
import sys
import unittest
from pathlib import Path

from rdflib import Graph, Namespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import fetch_data
import semantic_config


class GraphVisualizationInclusion(unittest.TestCase):
    def test_direct_visualization_members_and_existing_software_subclasses(self):
        mappings = semantic_config.load_source_mappings()
        wd = Namespace('http://www.wikidata.org/entity/')
        wdt = Namespace('http://www.wikidata.org/prop/direct/')
        graph = Graph()
        for mapping in mappings.class_mappings_for(semantic_config.SOFTWARE_DATASET):
            qid = mapping.source_class_id
            graph.add((wd[qid + 'Direct'], wdt.P31, wd[qid]))
            graph.add((wd[qid + 'Child'], wdt.P279, wd[qid]))
            graph.add((wd[qid + 'Indirect'], wdt.P31, wd[qid + 'Child']))
        for mapping in mappings.class_mappings_for(semantic_config.SOFTWARE_DATASET):
            qid = mapping.source_class_id
            with self.subTest(source_class=qid):
                found = {row.item for row in graph.query(fetch_data.build_software_class_query(qid, mappings))}
                expected = {wd[qid + 'Direct']}
                if qid != 'Q108810446':
                    expected.add(wd[qid + 'Indirect'])
                self.assertEqual(found, expected)
        self.assertIn('Q108810446', mappings.class_ids_for(semantic_config.SOFTWARE_DATASET))
        self.assertNotIn('Q108810446', mappings.class_ids_for(semantic_config.ONTOLOGIES_DATASET))


if __name__ == '__main__':
    unittest.main()
