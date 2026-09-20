"""Formatting-only evidence changes must not invalidate preserved citations."""
import copy
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import shared_tags as tags

class EvidenceFormattingTests(unittest.TestCase):
    def test_legacy_quotes_match_normalized_fields(self):
        examples = [
            'ontology for phenotypes of the slime-mould <i>Dictyostelium discoideum</i>',
            'Research &amp; development with Python',
            '<p>Python</p><p>experience required</p>',
            'Python\u00a0 experience\nrequired',
            'Cafe\u0301 research',
        ]
        for raw in examples:
            with self.subTest(raw=raw):
                source = tags.fields({'description': raw}, 'resource')['description']
                self.assertTrue(tags.evidence_matches(raw, source))
                self.assertTrue(tags.evidence_matches(source, source))

    def test_empty_and_changed_evidence_rejected(self):
        for quote in ('', '  ', '<i></i>', '&nbsp;', '<br>', None,
                      '<i>Python required</i>', 'Python not required'):
            with self.subTest(quote=quote):
                self.assertFalse(tags.evidence_matches(quote, 'Python preferred'))

    def test_literal_escaped_markup_is_not_decoded_twice(self):
        source = tags.fields({'description': 'Use &lt;custom&gt; syntax'}, 'resource')['description']
        self.assertEqual(source, 'Use <custom> syntax')
        self.assertTrue(tags.evidence_matches('Use &lt;custom&gt; syntax', source))
        self.assertTrue(tags.evidence_matches('Use <custom> syntax', source))
        self.assertFalse(tags.evidence_matches('Use syntax', source))

    def test_response_validation_preserves_quote_and_rejects_wrong_field(self):
        target = tags.BASE + 'ontology#LifeSciences'
        quote = 'slime-mould <i>Dictyostelium discoideum</i>'
        row = {'target': target, 'field': 'description', 'quote': quote,
               'relation': 'subject-domain', 'state': 'accepted'}
        record = {'fields': tags.fields({'description': quote, 'title': 'Ontology'}, 'resource'),
                  'candidates': []}
        terms = {target: {'dimension': 'domains'}}
        original = copy.deepcopy(row)
        self.assertEqual(tags.validate_response([row], record, terms)[0]['quote'], quote)
        self.assertEqual(row, original)
        with self.assertRaisesRegex(ValueError, 'Unsupported evidence'):
            tags.validate_response([{**row, 'field': 'title'}], record, terms)

if __name__ == '__main__':
    unittest.main()
