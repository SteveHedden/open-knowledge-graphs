"""Every eligible refresh requests assembly; effective-input comparison deduplicates."""
import importlib.util
from pathlib import Path
import sys
import unittest

path=Path(__file__).resolve().parents[1]/'.github/workflows/scripts/catalog_publication_gate.py'
spec=importlib.util.spec_from_file_location('catalog_publication_gate',path)
gate=importlib.util.module_from_spec(spec);sys.modules[spec.name]=gate;spec.loader.exec_module(gate)

class PublicationGateTests(unittest.TestCase):
    def test_manual_and_recovery_requests(self):
        for event in ('workflow_dispatch','schedule'):
            self.assertTrue(gate.decide(event_name=event,default_branch='main').should_publish)

    def test_failed_and_manual_refreshes_can_publish_last_good_mix(self):
        for status in ('success','failure','cancelled'):
            for event in ('schedule','workflow_dispatch'):
                self.assertTrue(gate.decide(event_name='workflow_run',default_branch='main',upstream_branch='main',upstream_event=event,upstream_conclusion=status).should_publish)

    def test_untrusted_branch_and_unknown_triggers_are_rejected(self):
        for branch in ('feature',''):
            self.assertFalse(gate.decide(event_name='workflow_run',default_branch='main',upstream_branch=branch).should_publish)
        self.assertFalse(gate.decide(event_name='push',default_branch='main').should_publish)
