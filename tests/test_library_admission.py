"""Relationship-constrained library admission uses the pinned catalog."""
import json
import sys
from pathlib import Path
from dataclasses import replace
from unittest.mock import patch
import unittest
import tempfile
from rdflib import Graph
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import fetch_data as f
import semantic_config as sc

class LibraryAdmissionTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.snapshot = Path(directory.name)
        self.registry = sc.load_source_mappings()
        (self.snapshot / "ontologies.json").write_text(json.dumps({"items": [
            {"wikidataId": "https://www.wikidata.org/wiki/Q100", "types": ["OntologyLanguage"]},
            {"wikidataId": "https://www.wikidata.org/wiki/Q101", "types": ["KnowledgeGraph"]}
        ]}))

    def test_discovery_excludes_subclasses_incidental_consumers_and_missing_edges(self):
        registry, snapshot = self.registry, self.snapshot
        graph = Graph().parse(data="""
            @prefix wd: <http://www.wikidata.org/entity/> .
            @prefix wdt: <http://www.wikidata.org/prop/direct/> .
            wd:Q1 wdt:P31 wd:Q188860 ; wdt:P2283 wd:Q100 .
            wd:Q2 wdt:P31 wd:Q188860 ; wdt:P2283 wd:Q101 .
            wd:Q3 wdt:P31 wd:Q900 ; wdt:P2283 wd:Q100 .
            wd:Q900 wdt:P279 wd:Q188860 .
            wd:Q4 wdt:P31 wd:Q188860 .
            wd:Q5 wdt:P31 wd:Q188860 ; wdt:P2283 wd:Q999 .
            wd:Q1 wdt:P31 wd:Q124653107 .
            wd:Q6 wdt:P31 wd:Q124653107 .
        """, format="turtle")
        def execute(session, query, label):
            return json.loads(graph.query(query).serialize(format="json"))["results"]["bindings"]
        with patch.object(f, "DATA_DIR", snapshot), patch.object(f, "run_wdqs_query", side_effect=execute), patch.object(f.time, "sleep"):
            assert f.fetch_software_qids(None, replace(registry, source_inclusions=())) == {"Q1", "Q6"}

    def test_snapshot_fails_closed_and_empty_is_valid(self):
        registry, tmp_path = self.registry, self.snapshot
        mapping = next(m for m in registry.class_mappings if m.source_class_id == "Q188860")
        path = tmp_path / "resources.json"
        with self.assertRaises(FileNotFoundError):
            f.eligible_relationship_targets(mapping, registry, path)
        path.write_text('{"items": {}}')
        with self.assertRaises(ValueError):
            f.eligible_relationship_targets(mapping, registry, path)
        path.write_text('{"items": []}')
        assert f.eligible_relationship_targets(mapping, registry, path) == set()

    def test_malformed_records_fail_closed(self):
        mapping = next(m for m in self.registry.class_mappings if m.source_class_id == "Q188860")
        path = self.snapshot / "resources.json"
        for record in [None, {"types": "OntologyLanguage"},
                       {"types": ["OntologyLanguage"], "wikidataId": "https://example.org/Q100"},
                       {"types": ["OntologyLanguage"]}]:
            with self.subTest(record=record):
                path.write_text(json.dumps({"items": [record]}))
                with self.assertRaises(ValueError):
                    f.eligible_relationship_targets(mapping, self.registry, path)

    def test_invalid_constraints_rejected(self):
        changes = [
            ('okg:requiredSourcePropertyId "P2283"', 'okg:requiredSourcePropertyId "invalid"'),
            ('okg:requiredSourcePropertyId "P2283" ;', ''),
            ('okg:requiredTargetType okg:Ontology, okg:OntologyLanguage, okg:Schema, okg:Standard ;', ''),
            ('okg:requiredTargetType okg:Ontology, okg:OntologyLanguage, okg:Schema, okg:Standard', 'okg:requiredTargetType okg:Unknown'),
            ('okg:includeSubclasses false', 'okg:includeSubclasses true'),
        ]
        for old, new in changes:
            with self.subTest(old=old, new=new):
                text = sc.SOURCES_PATH.read_text()
                prefix, library = text.split('src:class-Q188860', 1)
                path = self.snapshot / "sources.ttl"
                path.write_text(prefix + 'src:class-Q188860' + library.replace(old, new))
                with self.assertRaises(sc.SemanticConfigError):
                    sc.load_source_mappings(path)
