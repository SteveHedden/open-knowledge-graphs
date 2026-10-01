"""Exercise UI publication with real Git checkouts and checksum-verified datasets."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from test_catalog_snapshot import ROOT, make_catalog, finalize, write
import catalog_snapshot as catalog
import ui_release


class UIReleaseTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.repo = self.root / 'repository'
        self.baseline = self.root / 'baseline'
        self.destination = self.root / 'candidate'
        make_catalog(self.repo)
        for path in catalog.STAGING_SUPPORT_FILES:
            target = self.repo / path
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / path, target)
        write(self.repo / 'data/jobs/jobs.json', '{"items": []}\n')
        self.git('init', '-q')
        self.git('add', '.')
        catalog.write_jobs_manifest(self.repo, '2026-08-14T11:00:00Z', '2026-08-14T11:00:00Z', '2026-08-14T12:00:00Z')
        self.original = finalize(self.repo)
        self.commit()
        self.git('clone', '-q', str(self.repo), str(self.baseline))

    def git(self, *args):
        return subprocess.check_output(['git', *args], cwd=self.repo, stderr=subprocess.STDOUT, text=True).strip()

    def commit(self):
        self.git('add', '.')
        self.git('-c', 'user.name=Test', '-c', 'user.email=test@example.test', 'commit', '-qm', 'fixture')

    def stage(self):
        return ui_release.stage(self.repo, self.baseline, self.destination, '2026-08-15T00:00:00Z')

    def test_ui_release_preserves_every_dataset_and_jobs_manifest(self):
        write(self.repo / 'site/index.html', '<html>Search first</html>')
        write(self.repo / 'site/theme.css', 'body { color: navy; }')
        (self.repo / 'site/app.js').unlink()
        self.commit()
        result = self.stage()
        self.assertTrue(result['changed'])
        self.assertNotEqual(result['generation_id'], self.original['generationId'])
        self.assertEqual(ui_release.protected_hashes(self.destination), ui_release.protected_hashes(self.baseline))
        self.assertEqual((self.destination / 'site/index.html').read_text(), '<html>Search first</html>')
        self.assertFalse((self.destination / 'site/app.js').exists())
        self.assertEqual(catalog.verify_all_manifests(self.destination)['sourceRetrievedAt'], self.original['sourceRetrievedAt'])

    def test_no_change_retains_generation(self):
        result = self.stage()
        self.assertFalse(result['changed'])
        self.assertEqual(result['generation_id'], self.original['generationId'])

    def test_unpublished_data_is_rejected(self):
        write(self.repo / 'data/jobs/jobs.json', '{"items": [{"title": "new job"}]}')
        with self.assertRaisesRegex(ValueError, 'protected artifacts'):
            self.stage()
        self.assertFalse(self.destination.exists())

    def test_generator_change_requires_full_publication(self):
        write(self.repo / 'scripts/detail_metadata.py', '# changed generator')
        self.commit()
        with self.assertRaisesRegex(ValueError, 'runtime changes'):
            self.stage()

    def test_corrupted_baseline_is_rejected(self):
        write(self.baseline / 'site/index.html', 'tampered')
        with self.assertRaises(catalog.SnapshotError):
            self.stage()

    def test_candidate_data_tampering_is_rejected_even_with_new_manifest(self):
        self.stage()
        write(self.destination / 'data/software.json', '{"items": []}')
        finalize(self.destination)
        with self.assertRaisesRegex(ValueError, 'protected artifacts'):
            ui_release.verify(self.destination, self.baseline)

    def test_symlink_does_not_qualify_for_fast_ci(self):
        (self.repo / 'site/link.js').symlink_to('app.js')
        self.commit()
        self.assertFalse(ui_release.classify_repository(self.repo, 'HEAD~1'))

    def test_classification_requires_only_presentation_changes(self):
        self.assertTrue(ui_release.classify(['site/index.html', 'site/app.js', 'data/manifest.json']))
        for extra in ['data/jobs/jobs.json', 'api/src/index.ts', 'scripts/ui_release.py',
                      '.github/workflows/validate.yml', 'site/resource/example/index.html']:
            with self.subTest(extra=extra):
                self.assertFalse(ui_release.classify(['site/index.html', extra]))
        self.assertFalse(ui_release.classify(['README.md']))


if __name__ == '__main__':
    unittest.main()
