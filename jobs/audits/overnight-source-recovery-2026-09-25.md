# Overnight source recovery — 2026-09-25

Run [36113265634](https://github.com/SteveHedden/open-knowledge-graphs/actions/runs/36113265634) retained last-good data for four sources. The errors were read from its retained `nightly-run.json` diagnostics.

## Repaired adapters

- **Microsoft Research:** a complete official API record used an `https://apply.careers.microsoft.com/careers/job/<numeric-id>` permalink without repeating it in `msr_opportunity_hta`. Normalize that exact reviewed URL as the application URL. External hosts, other paths, query strings, conflicting identities, and incomplete content remain rejected. Live fetch and normalization succeeded for 133 records in 14 requests.
- **Open University:** the official API returned 11 jobs over two pages rather than the formerly assumed single page. The `recent` ordering returned overlapping pages in live probes; the `date` order returned all 11 unique jobs in descending publication-date order. Fetch all bounded pages before hydrating any details; reject changed totals, duplicate IDs, empty/truncated pages and excess requests. Preserve page evidence and account for every listing request. The request cap is now 22, allowing two listing pages plus the existing maximum 20 details. Live fetch and normalization succeeded for 11 jobs in 13 requests.

## Provider-side blockers still present

- **SAP:** the reviewed [ontology search](https://jobs.sap.com/search/?createNewAlert=false&locale=en_US&q=ontology) returned HTTP 403 with `cf-mitigated: challenge`, both with curl's default identity and the actual OKG source-client identity. The overnight run had rejected a redirect. No challenge bypass or unreviewed replacement feed was attempted.
- **metaphacts:** the [reviewed careers endpoint](https://metaphacts.com/about/about-us/career) redirects to `https://metaphactory.com/about/about-us/career`, which returns HTTP 404. The new official [company page](https://metaphactory.com/about/metaphactory/company) did not expose a replacement careers link during inspection. Do not interpret the vanished endpoint as evidence of zero vacancies.

These two sources remain enabled and fail visibly while retaining last-good records. This change does not relabel their refreshes as successful, erase their evidence, or change source publication eligibility.
