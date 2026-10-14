import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from generate_pages import passes_content_filter


class PageTitleFilterTests(unittest.TestCase):
    def test_named_resources_starting_with_q_are_eligible(self):
        for title in ("QUDT - Quantities, Units, Dimensions and Data Types Ontologies", "Quantities ontology", "Q123 ontology"):
            with self.subTest(title=title):
                self.assertTrue(passes_content_filter({
                    "title": title,
                    "description": "ontologies for Units of Measure, Quantity Kinds, Dimensions and Types",
                    "homepage": "https://qudt.org/",
                }))

    def test_unresolved_ids_and_empty_titles_are_ineligible(self):
        for title in ("Q25917172", " Q123 ", "", "   "):
            with self.subTest(title=title):
                self.assertFalse(passes_content_filter({
                    "title": title,
                    "description": "A meaningful description of this resource",
                    "homepage": "https://qudt.org/",
                }))
