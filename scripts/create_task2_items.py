#!/usr/bin/env python3
"""Create Wikidata items for 5 W3C vocabularies missing from OKG (Issue #16 Task 2).

Items:
  - Linked Data Platform (LDP)
  - vCard Ontology
  - Basic Geo (WGS84 lat/long) Vocabulary
  - Vehicle Sales Ontology (VSO)
  - VSSo (Vehicle Signal Specification Ontology)

Usage:
  WIKI_USER="Lemoncheddar@okg-updater" WIKI_PASS="botpassword" python3 scripts/create_task2_items.py
  WIKI_USER="Lemoncheddar@okg-updater" WIKI_PASS="botpassword" python3 scripts/create_task2_items.py --dry-run
"""

from __future__ import annotations

import json
import os
import sys
import time

import requests

API_URL = "https://www.wikidata.org/w/api.php"

# Property IDs
P_INSTANCE_OF   = "P31"
P_WEBSITE       = "P856"
P_NAMESPACE_URI = "P7510"
P_LICENSE       = "P275"
P_SOURCE_REPO   = "P1324"

# Value QIDs
Q_ONTOLOGY              = "Q324254"
Q_CONTROLLED_VOCABULARY = "Q1469824"
Q_W3C_LICENSE           = "Q3564577"
Q_CC_BY_30              = "Q14947546"

EDIT_SUMMARY = "Creating item for W3C vocabulary missing from OKG catalog (Issue #16, via OKG catalog bot)"
PAUSE = 1.0

ITEMS = [
    {
        "label": "Linked Data Platform",
        "description": "W3C Recommendation defining HTTP operations for read/write Linked Data on the web",
        "claims": [
            ("item",   P_INSTANCE_OF,   Q_ONTOLOGY),
            ("string", P_WEBSITE,       "https://www.w3.org/TR/ldp/"),
            ("string", P_NAMESPACE_URI, "http://www.w3.org/ns/ldp#"),
            ("item",   P_LICENSE,       Q_W3C_LICENSE),
        ],
    },
    {
        "label": "vCard Ontology",
        "description": "W3C RDF/OWL mapping of the vCard specification for describing people and organizations",
        "claims": [
            ("item",   P_INSTANCE_OF,   Q_ONTOLOGY),
            ("string", P_WEBSITE,       "https://www.w3.org/TR/vcard-rdf/"),
            ("string", P_NAMESPACE_URI, "http://www.w3.org/2006/vcard/ns#"),
            ("item",   P_LICENSE,       Q_W3C_LICENSE),
        ],
    },
    {
        "label": "Basic Geo (WGS84 lat/long) Vocabulary",
        "description": "W3C RDF vocabulary for representing latitude, longitude and altitude using the WGS84 geodetic reference datum",
        "claims": [
            ("item",   P_INSTANCE_OF,   Q_CONTROLLED_VOCABULARY),
            ("string", P_WEBSITE,       "https://www.w3.org/2003/01/geo/"),
            ("string", P_NAMESPACE_URI, "http://www.w3.org/2003/01/geo/wgs84_pos#"),
            # No license stated — P275 omitted
        ],
    },
    {
        "label": "Vehicle Sales Ontology",
        "description": "Web vocabulary for describing vehicles for e-commerce, based on GoodRelations",
        "claims": [
            ("item",   P_INSTANCE_OF,   Q_ONTOLOGY),
            ("string", P_WEBSITE,       "https://www.heppnetz.de/ontologies/vso/ns"),
            ("string", P_NAMESPACE_URI, "http://purl.org/vso/ns#"),
            ("item",   P_LICENSE,       Q_CC_BY_30),
        ],
    },
    {
        "label": "VSSo",
        "description": "W3C OWL ontology representing vehicle signals and properties, based on SOSA/SSN (discontinued draft)",
        "claims": [
            ("item",   P_INSTANCE_OF,   Q_ONTOLOGY),
            ("string", P_WEBSITE,       "https://www.w3.org/TR/vsso/"),
            ("string", P_NAMESPACE_URI, "https://github.com/w3c/vsso#"),
            ("string", P_SOURCE_REPO,   "https://github.com/w3c/vsso"),
            ("item",   P_LICENSE,       Q_W3C_LICENSE),
        ],
    },
]


def login(session: requests.Session) -> str:
    user = os.environ.get("WIKI_USER")
    password = os.environ.get("WIKI_PASS")
    if not user or not password:
        print("Error: Set WIKI_USER and WIKI_PASS environment variables.")
        sys.exit(1)

    r = session.get(API_URL, params={
        "action": "query", "meta": "tokens", "type": "login", "format": "json"
    })
    login_token = r.json()["query"]["tokens"]["logintoken"]

    r = session.post(API_URL, data={
        "action": "login", "lgname": user, "lgpassword": password,
        "lgtoken": login_token, "format": "json"
    })
    result = r.json()["login"]["result"]
    if result != "Success":
        print(f"Login failed: {result}")
        sys.exit(1)
    print(f"Logged in as {user}\n")

    r = session.get(API_URL, params={"action": "query", "meta": "tokens", "format": "json"})
    return r.json()["query"]["tokens"]["csrftoken"]


def create_item(session: requests.Session, token: str, label: str, description: str) -> str:
    data = {
        "labels": {"en": {"language": "en", "value": label}},
        "descriptions": {"en": {"language": "en", "value": description}},
    }
    r = session.post(API_URL, data={
        "action": "wbeditentity", "new": "item",
        "data": json.dumps(data),
        "token": token, "format": "json", "summary": EDIT_SUMMARY,
    })
    resp = r.json()
    if "error" in resp:
        raise RuntimeError(f"Failed to create item: {resp['error']}")
    return resp["entity"]["id"]


def add_item_claim(session: requests.Session, token: str, qid: str, prop: str, target_qid: str) -> str:
    numeric_id = int(target_qid.lstrip("Q"))
    r = session.post(API_URL, data={
        "action": "wbcreateclaim", "entity": qid,
        "property": prop, "snaktype": "value",
        "value": json.dumps({"entity-type": "item", "numeric-id": numeric_id}),
        "token": token, "format": "json", "summary": EDIT_SUMMARY,
    })
    resp = r.json()
    if "error" in resp:
        return f"ERROR {prop} → {target_qid}: {resp['error']}"
    return f"OK: {prop} → {target_qid}"


def add_string_claim(session: requests.Session, token: str, qid: str, prop: str, value: str) -> str:
    r = session.post(API_URL, data={
        "action": "wbcreateclaim", "entity": qid,
        "property": prop, "snaktype": "value",
        "value": json.dumps(value),
        "token": token, "format": "json", "summary": EDIT_SUMMARY,
    })
    resp = r.json()
    if "error" in resp:
        return f"ERROR {prop} → '{value}': {resp['error']}"
    return f"OK: {prop} → '{value}'"


def process_item(session: requests.Session, token: str, item: dict, dry_run: bool) -> tuple[str, list[str]]:
    label = item["label"]
    description = item["description"]
    claims = item["claims"]

    if dry_run:
        results = [f"  DRY RUN: would add {ctype} {prop} → {val}" for ctype, prop, val in claims]
        return f"DRY RUN: {label}", results

    qid = create_item(session, token, label, description)
    time.sleep(PAUSE)

    results = []
    for ctype, prop, val in claims:
        if ctype == "item":
            status = add_item_claim(session, token, qid, prop, val)
        else:
            status = add_string_claim(session, token, qid, prop, val)
        results.append(f"  {status}")
        time.sleep(PAUSE)

    return f"Created {qid} — {label} (https://www.wikidata.org/wiki/{qid})", results


def main() -> int:
    dry_run = "--dry-run" in sys.argv
    print(f"{'DRY RUN — ' if dry_run else ''}Creating {len(ITEMS)} Wikidata items\n")

    session = requests.Session()
    session.headers.update({
        "User-Agent": "OKG-ItemCreator/1.0 (https://openknowledgegraphs.com)"
    })

    token = "" if dry_run else login(session)

    errors = 0
    for item in ITEMS:
        header, results = process_item(session, token, item, dry_run)
        print(header)
        for line in results:
            print(line)
            if "ERROR" in line:
                errors += 1
        print()

    print(f"Done. {'No errors.' if errors == 0 else f'{errors} error(s).'}")
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
