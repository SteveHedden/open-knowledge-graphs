# Jobs recovery — September 17, 2026

The September 17 nightly refresh completed source retrieval but timed out during shared tagging. The configured OpenAI account returned HTTP 429 with `type=insufficient_quota` and `code=credit_balance_exhausted`. The retry handler recognized only the older error code and retried a permanent billing failure.

Recovered the normalized snapshots for all 40 sources from the retained cache of Actions run 35199233267, exported by recovery run 35230667967. Applied the existing reconciliation, first-party admission, catalog mention and job-tag rules without changing source descriptions or eligibility. One failed source retained its last-good snapshot. No new crawl or paid classification requests were made for the recovery.

The recovered snapshot contains 952 stored records, including 523 qualifying jobs. The newest qualifying posting date is September 17. Of the uncached assessments, 27 distinct qualifying descriptions were reviewed directly by Codex using the approved vocabulary and exact source excerpts. Two short introductory excerpts supported no assignments. The attribution `entity-match+contextual-v2:codex-direct-review-2026-09-17:source-boundaries-4` identifies these automated assessments, including abstentions; it does not claim human review or an external GPT-5.4 API response. Identical descriptions can share a cached assessment.

Uncached `not_match` search results now receive the explicit status `excluded-not-match` and method `admission-exclusion-v1:none`, rather than requiring contextual classification before publication. Existing cached assessments remain reusable. Exclusions have separate cache keys, so admission as a qualifying job cannot reuse an exclusion as a completed assessment.

Existing public raw files retain their original timestamps. The recovered normalized records, not a newly downloaded raw response, supply this update. `data/jobs/run.json` records this provenance. The normal nightly workflow is restored; both refresh workflows allow reuse of the direct assessments. Future new qualifying descriptions still require funded classification or another direct review.

Validation: exact evidence and vocabulary checks, RDF/JSON parity, preservation of source fields and membership, classifier regression tests, jobs tests, manifest verification, and cache reconstruction from committed RDF without an API call.
