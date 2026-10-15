"""Unknown Wikidata values must not abort a whole catalog refresh."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import fetch_data as fetch

class UnknownEntityTests(unittest.TestCase):
    def test_unknown_values_do_not_abort_catalog_or_invent_claims(self):
        item = 'http://www.wikidata.org/entity/Q123'
        license = 'http://www.wikidata.org/entity/Q334661'
        for unknown in [
            {'type': 'uri', 'value': 'http://www.wikidata.org/.well-known/genid/abc'},
            {'type': 'uri', 'value': 'https://www.wikidata.org/.well-known/genid/abc'},
            {'type': 'bnode', 'value': 'unknown-license'},
        ]:
            with self.subTest(unknown=unknown):
                rows = [{'item': {'value': item}, 'license': unknown, 'creator': unknown,
                         'partOfEntity': unknown, 'programmingLanguage': unknown},
                        {'item': {'value': item}, 'license': {'type': 'uri', 'value': license}}]
                self.assertEqual(fetch.collect_entity_iris(rows, 'license'), {license})
                for parser, extra in [(fetch.parse_software_rows, ()), (fetch.parse_ontology_rows, ({},))]:
                    records = parser(rows, {item: 'Example'}, {}, {}, *extra)[0]
                    self.assertEqual(records[item].licenses, {license})
                    self.assertEqual(records[item].creators, set())
                    self.assertEqual(records[item].part_of_entities, set())
                    self.assertEqual(records[item].programming_languages, set())

    def test_unexpected_entity_iri_still_fails_validation(self):
        with self.assertRaises(ValueError):
            fetch.collect_entity_iris([{'license': {'type': 'uri', 'value': 'https://example.org/bad'}}], 'license')

if __name__ == '__main__':
    unittest.main()
