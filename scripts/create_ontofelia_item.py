#!/usr/bin/env python3
"""Create a Wikidata item for Ontofelia, missing from the OKG catalog.

Confirmed via five separate Wikidata search angles (label variants, GitHub
repo URL, maintainer org name, full-text search) that no existing item
covers this project.

Ontofelia is an early-stage (v0.0.1, "research preview") open-source AI
agent gateway giving LLM agents RDF/OWL-based semantic memory (queryable
via SPARQL, with OWL-DL reasoning) instead of vector embeddings.

Usage:
  WIKI_USER="Lemoncheddar@okg-updater" WIKI_PASS="botpassword" python3 scripts/create_ontofelia_item.py
  WIKI_USER="Lemoncheddar@okg-updater" WIKI_PASS="botpassword" python3 scripts/create_ontofelia_item.py --dry-run
"""

from __future__ import annotations

import json
import os
import sys
import time

import requests

API_URL = "https://www.wikidata.org/w/api.php"

# Property IDs
P_INSTANCE_OF = "P31"
P_WEBSITE     = "P856"
P_LICENSE     = "P275"
P_SOURCE_REPO = "P1324"
P_LANGUAGE    = "P277"
P_VERSION     = "P348"

# Value QIDs
Q_SEMANTIC_WEB_SOFTWARE = "Q124653107"
Q_APACHE_2              = "Q13785927"
Q_TYPESCRIPT            = "Q978185"

EDIT_SUMMARY = "Creating item for Ontofelia, missing from OKG catalog (via OKG catalog bot)"
PAUSE = 1.0

ITEM = {
    "label": "Ontofelia",
    "description": "Open-source self-hosted AI agent gateway giving LLM agents RDF/OWL-based semantic memory, queryable via SPARQL with OWL-DL reasoning",
    "claims": [
        ("item",   P_INSTANCE_OF, Q_SEMANTIC_WEB_SOFTWARE),
        ("item",   P_LICENSE,     Q_APACHE_2),
        ("item",   P_LANGUAGE,    Q_TYPESCRIPT),
        ("string", P_SOURCE_REPO, "https://github.com/semantification-org/Ontofelia"),
        ("string", P_WEBSITE,     "https://github.com/semantification-org/Ontofelia"),
        ("string", P_VERSION,     "0.0.1"),
    ],
}


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
    print(f"{'DRY RUN — ' if dry_run else ''}Creating Wikidata item for {ITEM['label']}\n")

    session = requests.Session()
    session.headers.update({
        "User-Agent": "OKG-ItemCreator/1.0 (https://openknowledgegraphs.com)"
    })

    token = "" if dry_run else login(session)

    errors = 0
    header, results = process_item(session, token, ITEM, dry_run)
    print(header)
    for line in results:
        print(line)
        if "ERROR" in line:
            errors += 1

    print(f"\nDone. {'No errors.' if errors == 0 else f'{errors} error(s).'}")
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
