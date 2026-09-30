import sys
import tempfile
import unittest
from pathlib import Path
from rdflib import Graph, Literal, URIRef, BNode
from rdflib.compare import isomorphic
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import shared_tags as tags

class HistorySerializationTests(unittest.TestCase):
    def test_compact_history_preserves_all_rdf_and_unicode(self):
        graph = Graph()
        for i in range(100):
            subject = URIRef("https://openknowledgegraphs.com/assessment/" + str(i))
            for j in range(8):
                graph.add((subject, tags.OKG["evidence" + str(j)], Literal("reviewed evidence " + str(j))))
        blank = BNode()
        graph.add((blank, tags.OKG.reviewReason, Literal("Überprüfung\nsecond line", lang="de")))
        original = graph.serialize(format="nt").encode()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "classification-history" / "jobs.ttl"
            tags.write_rdf(path, graph)
            self.assertTrue(isomorphic(graph, Graph().parse(path)))
            self.assertLess(path.stat().st_size, len(original))
            before = path.read_bytes()
            tags.write_rdf(path, graph)
            self.assertEqual(before, path.read_bytes())
