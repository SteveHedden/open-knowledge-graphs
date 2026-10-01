"""Resource-page presentation and Schema.org regressions."""
import json
from pathlib import Path
import re
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import generate_pages as pages
import detail_metadata as details


def fixture(**extra):
    return dict(canonicalUrl='https://openknowledgegraphs.com/resource/example/',
                title='Example ontology', description='An ontology of examples.',
                homepage='https://example.org/', wikidataId='https://www.wikidata.org/wiki/Q123',
                **extra)


def statement(prop, value, label, qualifiers=()):
    return {'property': 'http://www.wikidata.org/entity/' + prop,
            'propertyLabel': prop, 'value': {'type': 'uri', 'value': value},
            'label': label, 'qualifiers': list(qualifiers), 'rank': details.WB + 'NormalRank',
            'statement': 'http://www.wikidata.org/entity/statement/Q123-' + prop}


class ResourceDetailDesignTests(unittest.TestCase):
    def test_download_release_and_repository_have_appropriate_nodes(self):
        item = fixture(downloads=['https://example.org/file.owl', 'javascript:bad'],
                       documentation=['https://example.org/docs'], sourceRepo='https://example.org/repo',
                       latestVersion='1.6.0', releaseDate='2026-09-01')
        ld = json.loads(pages.make_json_ld(item, 'resource'))
        self.assertEqual(ld['encoding'], [{'@type': 'MediaObject', 'contentUrl': 'https://example.org/file.owl'}])
        self.assertNotIn('datePublished', ld)
        self.assertEqual(ld['releasedEvent']['startDate'], '2026-09-01')
        self.assertNotIn('codeRepository', ld)
        self.assertEqual(ld['mainEntityOfPage']['mainEntity']['@id'], item['canonicalUrl'])
        self.assertEqual(len(ld['subjectOf']), 2)
        software = json.loads(pages.make_json_ld(item, 'software'))
        self.assertEqual(software['hasPart'][0]['codeRepository'], item['sourceRepo'])
        self.assertEqual(software['softwareHelp'][0]['url'], item['documentation'][0])

    def test_qualified_licenses_and_site_language_keep_their_scope(self):
        qualifier = {'property': 'http://www.wikidata.org/entity/P407', 'propertyLabel': 'language',
                     'value': {'type': 'uri', 'value': 'http://www.wikidata.org/entity/Q1860'}, 'label': 'English'}
        entries = [statement('P275', 'http://www.wikidata.org/entity/Q1', 'Scoped license', [qualifier]),
                   statement('P856', 'https://example.org/', 'Homepage', [qualifier]),
                   statement('P6216', 'http://www.wikidata.org/entity/Q2', 'Copyrighted')]
        item = fixture(detailStatements=entries, licenses=['Scoped license'])
        ld = json.loads(pages.make_json_ld(item, 'resource'))
        self.assertNotIn('license', ld)
        self.assertNotIn('inLanguage', ld)
        self.assertEqual(ld['subjectOf'][0]['inLanguage'][0]['name'], 'English')
        self.assertEqual(ld['copyrightNotice'], 'Copyrighted')
        self.assertIn('language: English', ld['mainEntityOfPage']['citation'][0]['description'])
        html = pages.make_page(item, 'resource', 'example')
        facts = html.split('<dl class="detail-facts">')[1].split('</dl>')[0]
        self.assertNotIn('Scoped license', facts)
        self.assertIn('See Sources and details', facts)

    def test_multiple_unqualified_licenses_remain_structured(self):
        ld = json.loads(pages.make_json_ld(fixture(licenses=['MIT', 'Apache 2.0']), 'resource'))
        self.assertEqual([v['name'] for v in ld['license']], ['MIT', 'Apache 2.0'])

    def test_action_order_download_section_jobs_link_and_safe_json(self):
        item = fixture(sourceRepo='https://example.org/repo', downloads=['https://example.org/file.owl'],
                       licenses=['MIT'], aliases=['</script><script>alert(1)</script>'],
                       latestVersion='1', releaseDate='2026-09-01', detailStatements=[
                           statement('P6216', 'http://www.wikidata.org/entity/Q2', 'Copyrighted')])
        html = pages.make_page(item, 'resource', 'example')
        actions = html.split('<div class="detail-links">')[1].split('</div>')[0]
        self.assertLess(actions.index('Homepage'), actions.index('Wikidata'))
        self.assertLess(actions.index('Wikidata'), actions.index('Source'))
        self.assertNotIn('Download', actions)
        self.assertIn('<h2>Downloads</h2>', html)
        self.assertIn('Download OWL', html)
        self.assertIn('See job postings mentioning Example ontology', html)
        self.assertIn('<details class="detail-sources"><summary>Sources and details</summary>', html)
        script = re.search(r'<script type="application/ld\+json">(.*?)</script>', html, re.S).group(1)
        self.assertEqual(json.loads(script)['alternateName'], item['aliases'][0])
        self.assertNotIn('</script><script>', html)


if __name__ == '__main__':
    unittest.main()
