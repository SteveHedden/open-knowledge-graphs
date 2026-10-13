"""Minimal history must preserve corrections without accumulating job evidence."""
import gzip
import sys
import tempfile
import unittest
from pathlib import Path
from rdflib import Graph, Literal, URIRef
from rdflib.namespace import RDF
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import classification_review as review
import dataset_snapshots as snapshots
import shared_tags as tags

class HistoryRetentionTests(unittest.TestCase):
    def test_archive_is_lossless_and_correction_bindings_survive(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            row={'owner':'https://example.org/job','target':'https://example.org/term',
                 'fields':{'description':'Original correction evidence'},'semantics':'abc'}
            review.save_bindings(root,'jobs',{'decision':row})
            path=root/'data/classification-history/jobs.ttl'
            g=Graph().parse(path)
            old=URIRef('https://example.org/old-assessment')
            g.add((old,RDF.type,tags.OKG.TagAssessment))
            g.add((old,tags.OKG.evidenceSnapshot,Literal('Long obsolete description')))
            tags.write_rdf(path,g);original=path.read_bytes()
            review.archive(root,'jobs',{'old':(g,old,{})})
            self.assertEqual(review.correction_bindings(root,'jobs'),{'decision':row})
            self.assertFalse(list(Graph().parse(path).subjects(RDF.type,tags.OKG.TagAssessment)))
            archives=list((root/'archive/classification-history').glob('*.gz'))
            self.assertEqual(len(archives),1)
            self.assertEqual(gzip.decompress(archives[0].read_bytes()),original)
            compact=path.read_bytes()
            review.archive(root,'jobs',{'old':(g,old,{})})
            self.assertEqual(path.read_bytes(),compact)
            self.assertEqual(len(list((root/'archive/classification-history').glob('*.gz'))),1)

    def test_old_dataset_snapshot_cannot_restore_archived_assessments(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)/'destination';source=Path(directory)/'source'
            row={'owner':'https://example.org/job','target':'https://example.org/term',
                 'fields':{'description':'Keep this'},'semantics':'abc'}
            review.save_bindings(root,'jobs',{'destination':row})
            review.save_bindings(source,'jobs',{'source':row})
            path=source/'data/classification-history/jobs.ttl';g=Graph().parse(path)
            g.add((URIRef('https://example.org/old'),RDF.type,tags.OKG.TagAssessment))
            tags.write_rdf(path,g)
            snapshots.copy_dataset(source,root,'jobs')
            self.assertEqual(set(review.correction_bindings(root,'jobs')),{'source','destination'})
            self.assertFalse(list(Graph().parse(root/'data/classification-history/jobs.ttl').subjects(RDF.type,tags.OKG.TagAssessment)))
            self.assertTrue(list(Graph().parse(path).subjects(RDF.type,tags.OKG.TagAssessment)))
