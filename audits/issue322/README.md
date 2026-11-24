# ohi admission — issue 322

Reviewed November 23, 2026 against docs/adding-resources-through-wikidata.md.

Decision: approve ohi as semantic web software using existing Q142266807. It is an ontology package manager and registry with a CLI and SDKs; official documentation describes immutable ontology publications, dependency management, exact-file locking, and OWL/RDFS/SHACL/LinkML/Apache Ossie artifacts. Public code, substantive documentation and releases support an identifiable software entity. No new item, class, merge or admission exception is needed.

Identity: preserve Q140621056 as ohi LinkML, formerly LinkML-Scala. The independently packaged schema engine remains distinct from the registry/package manager. Official documentation identifies it as part of ohi. Existing Wikidata P527/P361 relationships and the component's renamed label, old-name alias, repository and release history already reflect this. Existing catalog classifications on the component are preserved.

Sources:
- https://ohi.dev/docs/
- https://ohi.dev/docs/guides/projects/
- https://github.com/NeverBlink-OSS/ohi
- https://github.com/NeverBlink-OSS/ohi/blob/main/LICENSE
- https://linkml.ohi.dev/

Verified Wikidata changes:
- Q142266807: added sourced P31 semantic web software and P973 documentation; added references to existing homepage, repository, Apache-2.0 license, supported-resource uses and has-part statements. Preserved other claims and language fields. https://www.wikidata.org/w/index.php?title=Q142266807&diff=2574250579&oldid=2574172267
- Q140621056: updated homepage to https://linkml.ohi.dev/ and referenced its existing part-of relationship. Preserved aliases, classifications, releases and unrelated metadata. https://www.wikidata.org/w/index.php?title=Q140621056&diff=2574250581&oldid=2574172436

License scope: Apache-2.0 applies to the software; registry ontologies have their own licenses. The website footer version is not assigned as the CLI version. No employer or full-name claim about the submitter is inferred.

Classification: prepare an immutable review against the verified ohi title and description in isolated staging. Technology & Web describes its ontology tooling subject; Ontology Engineering covers ontology publication/management as documented in the official contribution and project workflows. All dimensions reviewed. No inferred tool tags or unsupported activities are added from the short description; direct uses relationships come from sourced Wikidata claims. The existing ohi LinkML Developer Library classification is preserved.

The publisher must revalidate the exact source and vocabulary evidence when ohi is first imported. No staging software JSON is committed or published. Keep #322 open until both live pages, identity, homepage, license and classifications are verified after the normal refresh. No Actions were manually dispatched.
