#!/usr/bin/env python3
"""Enrich Wikidata items for ontology language items pulled into OKG (Issue #17).

Adds missing P856 (website), P7510 (namespace URI), P1324 (source repo),
and descriptions where absent.

Usage:
  WIKI_USER="Lemoncheddar@okg-updater" WIKI_PASS="botpassword" python3 scripts/enrich_ontology_language_items.py
  WIKI_USER="Lemoncheddar@okg-updater" WIKI_PASS="botpassword" python3 scripts/enrich_ontology_language_items.py --dry-run
"""

from __future__ import annotations

import json
import os
import sys
import time

import requests

API_URL = "https://www.wikidata.org/w/api.php"

P_WEBSITE       = "P856"
P_NAMESPACE_URI = "P7510"
P_SOURCE_REPO   = "P1324"

EDIT_SUMMARY = "Adding missing website/namespace/repo for ontology language item in OKG catalog (Issue #17, via OKG catalog bot)"
PAUSE = 1.0

# Each entry: (QID, label, description_to_set_if_missing, [(type, prop, value), ...])
# type is "string" or "item"
ITEMS = [
    (
        "Q123414430", "OWL DL", None,
        [
            ("string", P_WEBSITE,       "https://www.w3.org/TR/owl2-profiles/"),
            ("string", P_NAMESPACE_URI, "http://www.w3.org/ns/owl-profile/DL"),
        ],
    ),
    (
        "Q120969821", "OWL RL", None,
        [
            ("string", P_WEBSITE,       "https://www.w3.org/TR/owl2-profiles/"),
            ("string", P_NAMESPACE_URI, "http://www.w3.org/ns/owl-profile/RL"),
        ],
    ),
    (
        "Q123414431", "OWL Full", None,
        [
            ("string", P_WEBSITE,       "https://www.w3.org/TR/owl2-profiles/"),
            ("string", P_NAMESPACE_URI, "http://www.w3.org/ns/owl-profile/Full"),
        ],
    ),
    (
        "Q123414421", "OWL Lite", None,
        [
            ("string", P_WEBSITE, "https://www.w3.org/TR/owl-ref/"),
            # No namespace URI — W3C explicitly states none exists for OWL Lite
        ],
    ),
    (
        "Q137178031", "Ontological Modeling Language",
        "ontology language for systems engineering vocabularies, based on OWL2 and SWRL",
        [
            ("string", P_NAMESPACE_URI, "http://opencaesar.io/oml#"),
        ],
    ),
    (
        "Q16889021", "Web Rule Language", None,
        [
            ("string", P_WEBSITE, "https://www.w3.org/submissions/WRL/"),
        ],
    ),
    (
        "Q354163", "Knowledge Interchange Format", None,
        [
            ("string", P_WEBSITE, "http://www-ksl.stanford.edu/knowledge-sharing/kif/"),
        ],
    ),
    (
        "Q7449106", "Semantics of Business Vocabulary and Business Rules", None,
        [
            ("string", P_WEBSITE, "https://www.omg.org/spec/SBVR/About-SBVR/"),
        ],
    ),
    (
        "Q2648698", "Gellish", None,
        [
            ("string", P_SOURCE_REPO, "https://github.com/AndriesSHP/Gellish"),
        ],
    ),
    (
        "Q7075046", "Object Process Methodology", None,
        [
            ("string", P_WEBSITE, "https://www.iso.org/standard/84612.html"),
        ],
    ),
    (
        "Q7274488", "R2ML", None,
        [
            ("string", P_WEBSITE, "https://milan.milanovic.org/project/r2ml/"),
        ],
    ),
]


def login(session: requests.Session) -> str:
    user = os.environ.get("WIKI_USER")
    password = os.environ.get("WIKI_PASS")
    if not user or not password:
        print("Error: Set WIKI_USER and WIKI_PASS environment variables.")
        sys.exit(1)

    r = session.get(API_URL, params={"action": "query", "meta": "tokens", "type": "login", "format": "json"})
    login_token = r.json()["query"]["tokens"]["logintoken"]
    r = session.post(API_URL, data={"action": "login", "lgname": user, "lgpassword": password, "lgtoken": login_token, "format": "json"})
    result = r.json()["login"]["result"]
    if result != "Success":
        print(f"Login failed: {result}")
        sys.exit(1)
    print(f"Logged in as {user}\n")

    r = session.get(API_URL, params={"action": "query", "meta": "tokens", "format": "json"})
    return r.json()["query"]["tokens"]["csrftoken"]


def get_entity(session: requests.Session, qid: str) -> dict:
    r = session.get(API_URL, params={
        "action": "wbgetentities", "ids": qid,
        "props": "claims|descriptions", "languages": "en", "format": "json"
    })
    return r.json()["entities"][qid]


def claim_values(entity: dict, prop: str) -> list[str]:
    claims = entity.get("claims", {}).get(prop, [])
    values = []
    for c in claims:
        dv = c.get("mainsnak", {}).get("datavalue", {})
        if dv.get("type") == "string":
            values.append(dv["value"])
    return values


def add_string_claim(session: requests.Session, token: str, qid: str, prop: str, value: str) -> str:
    r = session.post(API_URL, data={
        "action": "wbcreateclaim", "entity": qid,
        "property": prop, "snaktype": "value",
        "value": json.dumps(value),
        "token": token, "format": "json", "summary": EDIT_SUMMARY,
    })
    resp = r.json()
    if "error" in resp:
        return f"ERROR {prop}: {resp['error']}"
    return f"OK: {prop} → '{value}'"


def set_description(session: requests.Session, token: str, qid: str, description: str) -> str:
    r = session.post(API_URL, data={
        "action": "wbsetdescription", "id": qid, "language": "en",
        "value": description, "token": token, "format": "json", "summary": EDIT_SUMMARY,
    })
    resp = r.json()
    if "error" in resp:
        return f"ERROR description: {resp['error']}"
    return f"OK: description → '{description}'"


def main() -> int:
    dry_run = "--dry-run" in sys.argv
    print(f"{'DRY RUN — ' if dry_run else ''}Enriching {len(ITEMS)} ontology language items\n")

    session = requests.Session()
    session.headers.update({"User-Agent": "OKG-ItemEnricher/1.0 (https://openknowledgegraphs.com)"})

    token = "" if dry_run else login(session)

    errors = 0
    for qid, label, description, claims in ITEMS:
        print(f"{qid} — {label}")

        if dry_run:
            if description:
                print(f"  DRY RUN: set description → '{description}'")
            for _, prop, value in claims:
                print(f"  DRY RUN: {prop} → '{value}'")
            print()
            continue

        entity = get_entity(session, qid)

        # Description
        if description:
            current_desc = entity.get("descriptions", {}).get("en", {}).get("value")
            if current_desc:
                print(f"  SKIP description (already set: '{current_desc}')")
            else:
                status = set_description(session, token, qid, description)
                print(f"  {status}")
                if "ERROR" in status:
                    errors += 1
                time.sleep(PAUSE)

        # Claims
        for _, prop, value in claims:
            existing = claim_values(entity, prop)
            if existing:
                print(f"  SKIP {prop} (already set: '{existing[0]}')")
                continue
            status = add_string_claim(session, token, qid, prop, value)
            print(f"  {status}")
            if "ERROR" in status:
                errors += 1
            time.sleep(PAUSE)

        print()

    print(f"Done. {'No errors.' if errors == 0 else f'{errors} error(s).'}")
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
