# UI-only releases

For top-level `site/` HTML, CSS, JavaScript and image changes, use **Publish Catalog Generation → Run workflow → ui_only: true** on `main` after merging the UI change. Leave `initialize_semantic_search` unchecked. A push alone does not publish the site.

This mode reuses the live-verified `catalog-current` datasets and generated detail pages. It tests frontend behavior, verifies file hashes and manifest coverage, creates a new catalog manifest for changed UI assets, then uses the normal deployment, API compatibility, live smoke checks and rollback flow. It skips data assembly, page generation, full catalog validation and jobs reprocessing. The jobs manifest is preserved byte-for-byte and its checksums are still verified.

UI-only pull requests run frontend tests and candidate integrity checks instead of the full jobs/API/MCP suites. Classification uses the policy from the base branch. Workflow, generator, backend and data changes continue through full CI.

Use normal publication for detail-page generator/JSON-LD changes, backend changes, or refreshed datasets. UI-only publication refuses pending data changes relative to `catalog-current`, so it cannot overwrite an unpublished refresh. If there are no UI changes, it does not create or deploy a generation. Scheduled and refresh-triggered publications keep their existing behavior.

Files under `outputs/mockups/` are not published by this path.
