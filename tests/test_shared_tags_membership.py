import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import shared_tags as tags

class MembershipMetadataTests(unittest.TestCase):
    def test_health_metadata_preserves_resource_and_software_links(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'data').mkdir()
            (root / 'vocabularies').mkdir()
            for name in ('categories', 'activities', 'supplementary-entities'):
                (root / 'vocabularies' / (name + '.ttl')).write_text('')
            membership = {'resource': {'Q1': 'example-resource'}, 'software': {'Q2': 'example-tool'}}
            for dataset, kind, qid, slug in [('ontologies', 'resource', 'Q1', 'example-resource'), ('software', 'software', 'Q2', 'example-tool')]:
                (root / 'data' / (dataset + '.ttl')).write_text(
                    f'<{tags.BASE}{kind}/{slug}/> <{tags.OKG.wikidataId}> <http://www.wikidata.org/entity/{qid}>; <{tags.OKG.title}> "{slug}" .')
            registry = root / 'data/page_qids.json'
            registry.write_text(json.dumps(membership))
            before, digest = tags.load_vocabulary(root)
            membership['homepageHealth'] = {'https://example.com': {'status': 'unavailable', 'reason': 'timeout'}}
            registry.write_text(json.dumps(membership))
            after, new_digest = tags.load_vocabulary(root)
            self.assertEqual(before, after)
            self.assertEqual(digest, new_digest)
            self.assertEqual(sum(len(t['catalogPages']) for t in after.values()), 2)

if __name__ == '__main__':
    unittest.main()
