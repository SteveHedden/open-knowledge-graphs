# Homepage activity and project requests

The homepage retains the existing catalog styling and controls. Its three activity
columns show up to five distinct resources, software projects, or qualified active
jobs from the past 90 days. Resource/software entries show releases only. Dates
come from releases or job postings, never refresh/discovery timestamps. Coarse
dates qualify only after the full period ends. Missing or future dates are omitted.
Resource links use the published page registry, falling back to Wikidata.

Resource releases use Task 52's catalog-events.json. During the software metadata
migration, entries without either a ledger release event or structured latestRelease
may use the existing software catalog latestVersion/releaseDate projection, matching
the software listing. Explicit ineligible events are never overridden. This is a
presentation fallback; it does not create or change event history. Remove this
fallback once software releases are consistently represented in the shared feed.

The Add or update your project button opens a short project request form. Continue
to GitHub opens a new public issue draft with the project name, website/repository,
requested change and optional Wikidata link. A visitor must sign in and submit it;
no issue or Wikidata edit is sent automatically. Maintainers review requests before
making appropriate updates. A direct Wikidata search link remains optional.

Task 54 was narrowed to these features by user approval. Shared OKG–Universal
Evidence design exploration and an HTML style guide are separate future work.
