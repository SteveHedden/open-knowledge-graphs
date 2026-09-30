#!/usr/bin/env python3
"""Wait for the resource/software cohort before publication pins its snapshots."""
import json
import os
import subprocess
import time
from urllib.parse import urlencode

WORKFLOWS = ('update-resource.yml', 'update-software.yml', 'refresh-catalog-data.yml')


def active_runs(pages, branch):
    """Keep queued/waiting runs too; a completed failure is no longer a writer."""
    runs = {}
    for page in pages:
        for run in page['workflow_runs']:
            workflow = run['path'].split('@', 1)[0].rsplit('/', 1)[-1]
            if workflow in WORKFLOWS and run['head_branch'] == branch and run['status'] != 'completed':
                runs[run['id']] = run
    return sorted(runs.values(), key=lambda run: run['id'])


def fetch_active_runs(repository, branch):
    pages = []
    for status in ('queued', 'in_progress', 'waiting', 'pending', 'requested'):
        query = urlencode({'branch': branch, 'status': status, 'per_page': 100})
        result = subprocess.run(
            ['gh', 'api', '--paginate', '--slurp',
             f'repos/{repository}/actions/runs?{query}'],
            check=True, capture_output=True, text=True, timeout=60,
        )
        pages.extend(json.loads(result.stdout))
    return active_runs(pages, branch)


def wait_until_idle(fetch, *, timeout=5400, quiet_seconds=30, poll_seconds=15,
                    clock=time.monotonic, sleep=time.sleep, log=print):
    deadline = clock() + timeout
    idle_since = None
    previous = None
    while True:
        runs = fetch()  # API errors fail closed; do not pin stale data.
        current = clock()
        if current >= deadline:
            raise TimeoutError('Resource/software refreshes did not settle before the publication deadline.')
        ids = tuple(run['id'] for run in runs)
        if ids != previous:
            log('Waiting for refresh runs: ' + ', '.join(map(str, ids)) if ids else
                'Refreshes complete; confirming the batch is idle.')
            previous = ids
        if runs:
            idle_since = None
        elif idle_since is None:
            idle_since = current
        elif current - idle_since >= quiet_seconds:
            log('Resource and software outputs are ready to pin together.')
            return
        sleep(min(poll_seconds, max(0, deadline - current)))


def main():
    repository = os.environ['GH_REPO']
    branch = os.environ['DEFAULT_BRANCH']
    if not repository or not branch:
        raise ValueError('Repository and default branch are required.')
    wait_until_idle(lambda: fetch_active_runs(repository, branch))


if __name__ == '__main__':
    main()
