import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from rdflib import Graph

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import fetch_data


class SoftwareQueryBatches(unittest.TestCase):
    def setUp(self):
        self.mappings = fetch_data.load_source_mappings(fetch_data.SOURCES_PATH)
        self.graph = Graph().parse(data='''
            @prefix wd: <http://www.wikidata.org/entity/> .
            @prefix wdt: <http://www.wikidata.org/prop/direct/> .
            @prefix p: <http://www.wikidata.org/prop/> .
            @prefix ps: <http://www.wikidata.org/prop/statement/> .
            @prefix pq: <http://www.wikidata.org/prop/qualifier/> .
            @prefix wb: <http://wikiba.se/ontology#> .
            @prefix prov: <http://www.w3.org/ns/prov#> .
            @prefix pr: <http://www.wikidata.org/prop/reference/> .
            wd:Q1 wdt:P31 wd:Q124653107, wd:Q595971 ;
                wdt:P856 <https://example.org/one>, <https://example.org/two> ;
                wdt:P275 wd:Q334661, wd:Q1131681 ;
                wdt:P170 wd:Q101 ; wdt:P50 wd:Q102 ; wdt:P178 wd:Q103 ;
                p:P348 [ ps:P348 "1"; wb:rank wb:NormalRank ],
                       [ ps:P348 "2"; wb:rank wb:PreferredRank ; pq:P548 wd:Q2804309 ;
                         prov:wasDerivedFrom [ pr:P854 <https://example.org/release> ] ],
                       [ ps:P348 "99"; wb:rank wb:DeprecatedRank ] .
            wd:Q900 wdt:P279 wd:Q124653107 .
            wd:Q2 wdt:P31 wd:Q900 ;
                p:P348 [ ps:P348 "3"; wb:rank wb:PreferredRank ] .
            wd:Q3 wdt:P31 wd:Q140639670 .
            wd:Q4 wdt:P31 wd:Q137916409 .
            wd:Q5 wdt:P31 wd:Q595971 .
            wd:Q6 wdt:P31 wd:Q999 ;
                p:P348 [ ps:P348 "100"; wb:rank wb:PreferredRank ] .
        ''', format='turtle')
        self.queries = []

    def execute(self, session, query, label):
        self.queries.append((query, label))
        return json.loads(self.graph.query(query).serialize(format='json'))['results']['bindings']

    def test_discovery_and_batches_preserve_membership_multivalues_and_release_provenance(self):
        with patch.object(fetch_data, 'run_wdqs_query', side_effect=self.execute), \
             patch.object(fetch_data.time, 'sleep'), \
             patch.object(fetch_data, 'SOFTWARE_QUERY_BATCH_SIZE', 2):
            qids = fetch_data.fetch_software_qids(None, self.mappings)
            self.assertEqual(qids, {'Q1', 'Q2', 'Q3', 'Q4', 'Q5'})
            self.assertEqual(len(self.queries), 4)
            for query, _ in self.queries:
                self.assertNotIn('UNION', query)
                self.assertNotIn('OPTIONAL', query)
            base = fetch_data.fetch_software_batches(
                None, qids, self.mappings, fetch_data.build_software_base_query, 'base')
            releases = fetch_data.fetch_software_batches(
                None, qids, self.mappings, fetch_data.build_software_version_query, 'releases')
        self.assertEqual(len(self.queries), 10)  # Four classes plus three batches of each kind.
        for query, _ in self.queries[4:]:
            self.assertNotIn('wdt:P279', query)
        self.assertEqual({r['item']['value'].split('/')[-1] for r in base}, qids)
        one = [r for r in base if r['item']['value'].endswith('/Q1')]
        self.assertEqual(len(one), 12)  # Both homepages, both licenses, all three creator properties.
        self.assertEqual({r['creator']['value'].split('/')[-1] for r in one}, {'Q101','Q102','Q103'})
        candidates = fetch_data.release_metadata.candidates(releases)
        self.assertEqual(set(candidates), {'http://www.wikidata.org/entity/Q1','http://www.wikidata.org/entity/Q2'})
        self.assertEqual({r['version'] for r in candidates['http://www.wikidata.org/entity/Q1']}, {'1','2'})
        selected = fetch_data.release_metadata.select(releases)['http://www.wikidata.org/entity/Q1']
        self.assertEqual(selected['version'], '2')
        self.assertTrue(selected['qualifiers'])
        self.assertTrue(selected['references'])

    def test_empty_cohort_does_not_query_and_failed_batch_does_not_return_partial_data(self):
        with patch.object(fetch_data, 'run_wdqs_query') as run, patch.object(fetch_data.time, 'sleep'):
            self.assertEqual(fetch_data.fetch_software_batches(
                None, set(), self.mappings, fetch_data.build_software_base_query, 'base'), [])
            run.assert_not_called()
        with patch.object(fetch_data, 'SOFTWARE_QUERY_BATCH_SIZE', 1), \
             patch.object(fetch_data.time, 'sleep'), \
             patch.object(fetch_data, 'run_wdqs_query', side_effect=[[{'item': {'value':'Q1'}}], fetch_data.WDQSError('unavailable')]) as run:
            with self.assertRaises(fetch_data.WDQSError):
                fetch_data.fetch_software_batches(
                    None, {'Q1','Q2','Q3'}, self.mappings, fetch_data.build_software_base_query, 'base')
            self.assertEqual(run.call_count, 2)


if __name__ == '__main__':
    unittest.main()
