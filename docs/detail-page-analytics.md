# Detail-page analytics

Resource and software detail pages load the same Umami website tracker as the main catalog. Umami records the pageview automatically. `site/detail-analytics.js` records `outbound_link_click` for external HTTP(S) links, including middle clicks, with the catalog-compatible `tab`, `resourceTitle`, `linkType`, and `destinationHost` properties. Additional `sourcePage=detail` and `resourcePath` identify the detail-page context. Full destination URLs and their query strings are not sent as event properties.

Internal OKG navigation does not count as outbound. Homepage, Wikidata, and primary source links have explicit link types; other external evidence, download, and documentation links use `external`. The tracker is optional: blocked or failed analytics must not prevent navigation.

## Reporting

For a defined period, count distinct analytics visitor/session identifiers that viewed a resource path and compare their recorded outbound events on that same path. Report the remainder as **visitors with no recorded outbound click**, not people who definitively did not click. For vendor-site conversion specifically, filter the click destination host; a Wikidata or GitHub click is an outbound click but not necessarily a vendor-site visit. Do not subtract event counts from unique visitors. State whether matching is within a visit, a time-bounded funnel, or the whole reporting period.

The March 7, 2026 analytics commit (`fb3b62a21`) covered only `site/index.html` and `site/app.js`. Detail-page measurement starts when this template change is successfully published. Previously unrecorded detail-page activity cannot be reconstructed retroactively.
