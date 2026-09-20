#!/usr/bin/env python3
"""Authorize refresh completion/recovery requests; deduplicate pinned data later."""
from dataclasses import dataclass
import os

@dataclass(frozen=True)
class Decision:
    should_publish: bool
    reason: str


def decide(*, event_name, default_branch, upstream_branch='', **_):
    if event_name == 'workflow_dispatch':
        return Decision(True, 'manual-dispatch')
    if event_name == 'workflow_run':
        if not default_branch or upstream_branch != default_branch:
            return Decision(False, 'upstream-not-default-branch')
        # A failed jobs run can still have sealed complete, validated output
        # retaining last-good data for failed sources. Verify the snapshot itself.
        return Decision(True, 'dataset-refresh-completed')
    if event_name == 'schedule':
        return Decision(True, 'snapshot-recovery-check')
    return Decision(False, 'unsupported-trigger')


def main():
    decision = decide(event_name=os.getenv('EVENT_NAME',''),
                      default_branch=os.getenv('DEFAULT_BRANCH',''),
                      upstream_branch=os.getenv('UPSTREAM_BRANCH',''))
    result = f'should_publish={str(decision.should_publish).lower()}\nreason={decision.reason}\n'
    if os.getenv('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'],'a') as stream: stream.write(result)
    print(result)
    return 0

if __name__ == '__main__': raise SystemExit(main())
