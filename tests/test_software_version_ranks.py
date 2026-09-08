import sys
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from rdflib import Graph

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import fetch_data


def row(version, rank='NormalRank', published=None, qid='Q141112433'):
    result = {'item': {'value': 'http://www.wikidata.org/entity/' + qid},
              'version': {'value': version},
              'versionRank': {'value': 'http://wikiba.se/ontology#' + rank}}
    if published:
        result['pubDate'] = {'value': published + 'T00:00:00Z'}
    return result


class SoftwareVersionRanks(unittest.TestCase):
    def test_query_projects_ranks_and_excludes_deprecated_claims(self):
        graph = Graph().parse(data='''
            @prefix wd: <http://www.wikidata.org/entity/> .
            @prefix p: <http://www.wikidata.org/prop/> .
            @prefix ps: <http://www.wikidata.org/prop/statement/> .
            @prefix wb: <http://wikiba.se/ontology#> .
            wd:Q141112433 p:P348 [ ps:P348 "2.0.16"; wb:rank wb:PreferredRank ],
                [ ps:P348 "2.2.0.16"; wb:rank wb:NormalRank ],
                [ ps:P348 "99"; wb:rank wb:DeprecatedRank ] .
        ''', format='turtle')
        with patch.object(fetch_data, 'wikidata_property', side_effect=['P348', 'P577']), \
             patch.object(fetch_data, 'class_union_clause', return_value='VALUES ?item { wd:Q141112433 }'):
            query = fetch_data.build_software_version_query(None)
        results = graph.query(query)
        bindings = [{'item': {'value': str(r.item)}, 'version': {'value': str(r.version)},
                     'versionRank': {'value': str(r.versionRank)}} for r in results]
        self.assertEqual({r['version']['value'] for r in bindings}, {'2.0.16', '2.2.0.16'})
        self.assertEqual(self.select(bindings), ('2.0.16', None))

    def select(self, rows):
        return fetch_data.pick_latest_version_rows(rows)['http://www.wikidata.org/entity/Q141112433']

    def test_raptor_preferred_release_beats_imported_tag_on_same_date(self):
        rows = [row('2.0.16', 'PreferredRank', '2023-03-01'),
                row('2.2.0.16', published='2023-03-01')]
        for ordered in (rows, list(reversed(rows))):
            self.assertEqual(self.select(ordered), ('2.0.16', date(2023, 3, 1)))

    def test_preferred_without_date_beats_newer_normal_and_deprecated(self):
        self.assertEqual(self.select([row('1', 'PreferredRank'),
                                      row('2', published='2026-01-01'),
                                      row('3', 'DeprecatedRank', '2027-01-01')]), ('1', None))

    def test_multiple_preferred_preserve_version_date_pair(self):
        self.assertEqual(self.select([row('1', 'PreferredRank', '2024-01-01'),
                                      row('2', 'PreferredRank', '2025-01-01')]),
                         ('2', date(2025, 1, 1)))

    def test_normal_fallback_and_per_item_rank_selection(self):
        rows = [row('1', published='2024-01-01'), row('2', published='2025-01-01'),
                row('99', 'DeprecatedRank', '2026-01-01'),
                row('4', 'PreferredRank', qid='Q1')]
        self.assertEqual(self.select(rows), ('2', date(2025, 1, 1)))
        self.assertEqual(fetch_data.pick_latest_version_rows([row('1', 'DeprecatedRank')]), {})

    def test_undated_and_legacy_rows_keep_existing_fallback(self):
        legacy = row('2')
        del legacy['versionRank']
        self.assertEqual(self.select([row('1'), legacy]), ('2', None))


if __name__ == '__main__':
    unittest.main()
