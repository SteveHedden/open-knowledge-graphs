#!/usr/bin/env python3
"""Validate and stage presentation-only releases using an unchanged live dataset.

The allowlist is deliberately narrow. Generator/JSON-LD, API, jobs and data
changes use full publication. UI releases retain the normal manifest, API
compatibility, Pages smoke checks and rollback flow.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import subprocess

UI_SUFFIXES = {'.html', '.css', '.js', '.svg', '.png', '.jpg', '.jpeg', '.webp', '.ico'}
PR_COMPANIONS = {'data/manifest.json', 'tests/catalog_browser.test.js',
                 'tests/test_catalog_browser.py', 'docs/ui-releases.md', 'README.md'}


def is_ui_asset(path: str) -> bool:
    p = Path(path)
    return p.parent.as_posix() == 'site' and p.suffix.lower() in UI_SUFFIXES


def git_paths(repository: Path, base: str, head: str = 'HEAD') -> list[str]:
    output = subprocess.check_output(
        ['git', 'diff', '--name-only', '--no-renames', '-z', base, head, '--'], cwd=repository)
    return [p.decode('utf-8') for p in output.split(b'\0') if p]


def classify(paths: list[str]) -> bool:
    return any(is_ui_asset(p) for p in paths) and all(is_ui_asset(p) or p in PR_COMPANIONS for p in paths)


def classify_repository(repository: Path, base: str, head: str = 'HEAD') -> bool:
    paths = git_paths(repository, base, head)
    if not classify(paths):
        return False
    # Renames are treated as delete+add; symlink assets never enter the fast path.
    tree = subprocess.check_output(['git', 'ls-tree', '-r', '-z', head, '--', 'site'], cwd=repository)
    return not any(record.startswith(b'120000 ') for record in tree.split(b'\0') if record)


def check_runtime_changes(repository: Path, baseline: Path) -> None:
    base = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=baseline, text=True).strip()
    changed = git_paths(repository, base)
    blocked = [p for p in changed if (
        p.startswith(('api/', 'jobs/', 'mcp-server/'))
        or (p.startswith('scripts/') and p != 'scripts/ui_release.py')
        or p == 'requirements.txt'
        or p.startswith('validation/')
    )]
    if blocked:
        raise ValueError('Full publication required for runtime changes: ' + ', '.join(blocked[:12]))


def protected_hashes(root: Path) -> dict[str, str]:
    import catalog_snapshot as catalog
    return {p: catalog.sha256_file(root / p)
            for p in catalog.deployed_files(root, include_manifest=True)
            if not is_ui_asset(p) and p != catalog.MANIFEST_PATH}


def assert_same_data(candidate: Path, baseline: Path) -> None:
    before, after = protected_hashes(baseline), protected_hashes(candidate)
    changed = sorted(p for p in before.keys() | after.keys() if before.get(p) != after.get(p))
    if changed:
        raise ValueError('UI publication cannot change data or protected artifacts: ' + ', '.join(changed[:12]))


def verify(candidate: Path, baseline: Path) -> dict:
    import catalog_snapshot as catalog
    catalog.verify_all_manifests(baseline)
    assert_same_data(candidate, baseline)
    return catalog.verify_all_manifests(candidate)


def stage(repository: Path, baseline: Path, destination: Path, started_at: str) -> dict:
    import catalog_snapshot as catalog
    if destination.resolve() == repository.resolve() or repository.resolve() in destination.resolve().parents:
        raise ValueError("The staging directory must be outside the repository checkout.")
    # Verify the immutable baseline before trusting any of its files.
    old = catalog.verify_all_manifests(baseline)
    check_runtime_changes(repository, baseline)
    # Refuse to overwrite unpublished data in main during later promotion.
    assert_same_data(repository, baseline)
    catalog.prepare_staging(baseline, destination)
    source_ui = {p for p in catalog.deployed_files(repository) if is_ui_asset(p)}
    baseline_ui = {p for p in catalog.deployed_files(baseline) if is_ui_asset(p)}
    changed = sorted(p for p in source_ui | baseline_ui
                     if p not in source_ui or p not in baseline_ui
                     or catalog.sha256_file(repository / p) != catalog.sha256_file(baseline / p))
    for p in sorted(baseline_ui - source_ui):
        (destination / p).unlink()
    for p in sorted(source_ui):
        shutil.copy2(repository / p, destination / p)
    if changed:
        catalog.write_manifest(destination, started_at, old['sourceRetrievedAt'])
    manifest = verify(destination, baseline)
    return {'changed': bool(changed), 'generation_id': manifest['generationId'], 'paths': changed}


def outputs(path: Path | None, values: dict) -> None:
    if path:
        with path.open('a') as stream:
            for key, value in values.items():
                if isinstance(value, (str, bool)):
                    stream.write(f'{key}={str(value).lower() if isinstance(value, bool) else value}\n')
    print(json.dumps(values, indent=2))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['classify', 'stage', 'verify'])
    parser.add_argument('--repository', type=Path, default=Path('.'))
    parser.add_argument('--base')
    parser.add_argument('--head', default='HEAD')
    parser.add_argument('--baseline', type=Path)
    parser.add_argument('--destination', type=Path)
    parser.add_argument('--started-at')
    parser.add_argument('--output-file', type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == 'classify':
            if not args.base:
                parser.error('classify requires --base')
            result = {'ui_only': classify_repository(args.repository, args.base, args.head)}
        elif args.command == 'stage':
            if not all((args.baseline, args.destination, args.started_at)):
                parser.error('stage requires --baseline, --destination and --started-at')
            result = stage(args.repository.resolve(), args.baseline.resolve(), args.destination.resolve(), args.started_at)
        else:
            if not args.baseline or not args.destination:
                parser.error('verify requires --baseline and --destination')
            result = {'generation_id': verify(args.destination.resolve(), args.baseline.resolve())['generationId']}
        outputs(args.output_file, result)
        return 0
    except (ValueError, RuntimeError, OSError, subprocess.CalledProcessError) as exc:
        parser.exit(1, f'UI release rejected: {exc}\n')


if __name__ == '__main__':
    raise SystemExit(main())
