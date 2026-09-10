import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import uri_migrations as migrations
import validate_catalog

ROW = {'dataset':'resource','qid':'Q123','from':'old-name','to':'new-name'}


class UriMigrationTests(unittest.TestCase):
    def test_migration_is_idempotent_and_rejects_collisions(self):
        registry={'resource':{'Q123':'old-name'}}
        migrations.apply_migrations(registry,[ROW])
        migrations.apply_migrations(registry,[ROW])
        self.assertEqual(registry['resource']['Q123'],'new-name')
        for slug in ['old-name','new-name']:
            with self.assertRaises(ValueError):
                migrations.apply_migrations({'resource':{'Q123':'old-name','Q456':slug}},[ROW])
        with self.assertRaises(ValueError):
            migrations.apply_migrations({'resource':{'Q123':'unexpected'}},[ROW])

    def test_unapproved_changes_still_fail_registry_validation(self):
        baseline={'resource':{'Q123':'old-name'},'software':{}}
        current={'resource':{'Q123':'new-name'},'software':{}}
        payloads={'resource':{'items':[{'wikidataId':'https://www.wikidata.org/wiki/Q123','canonicalUrl':'https://openknowledgegraphs.com/resource/new-name/'}]},'software':{'items':[]}}
        report=validate_catalog.ValidationReport()
        validate_catalog.validate_registry(current,baseline,payloads,report)
        self.assertTrue(any(e.code=='uri-stability' for e in report.errors))
        report=validate_catalog.ValidationReport()
        validate_catalog.validate_registry(current,baseline,payloads,report,[ROW])
        self.assertFalse(report.errors)
        self.assertFalse(migrations.permits([ROW],'resource','Q456','old-name','new-name'))
        self.assertFalse(migrations.permits([ROW],'resource','Q123','new-name','old-name'))

    def test_redirect_requires_verified_destination_and_is_not_a_second_item(self):
        registry={'resource':{'Q123':'new-name'}}
        with self.assertRaises(ValueError):migrations.active_redirects([ROW],registry,{'resource':{}})
        pages={'resource':{'Q123':'new-name'}}
        rows=migrations.active_redirects([ROW],registry,pages)
        with tempfile.TemporaryDirectory() as directory:
            migrations.write_redirects(directory,rows)
            html=(Path(directory)/'resource/old-name/index.html').read_text()
            self.assertIn('http-equiv="refresh"',html)
            self.assertIn('rel="canonical" href="https://openknowledgegraphs.com/resource/new-name/"',html)
            self.assertIn('content="noindex"',html)
        self.assertEqual(pages,{'resource':{'Q123':'new-name'}})
        self.assertEqual(migrations.active_redirects([ROW],{'resource':{'Q123':'old-name'}},{}),[])

    def test_invalid_paths_and_chains_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'validation').mkdir()
            for rows in [[{**ROW,'from':'../escape'}], [ROW,{**ROW,'qid':'Q456','from':'new-name','to':'next'}], [ROW,ROW]]:
                (root/'validation/uri-migrations.json').write_text(json.dumps(rows))
                with self.assertRaises(ValueError):migrations.load_migrations(root)
