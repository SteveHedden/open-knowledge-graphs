#!/usr/bin/env python3
"""Create a new Wikidata item for POWDER-S (W3C OWL vocabulary).

Creates the item and sets:
  - English label + description
  - P31 (instance of) → Q324254 (ontology)
  - P856 (official website) → https://www.w3.org/TR/powder-dr/
  - P7510 (XML namespace URL) → http://www.w3.org/2007/05/powder-s#
  - P275 (copyright license) → Q3564577 (W3C Software License)

Usage:
  WIKI_USER="Lemoncheddar@okg-updater" WIKI_PASS="botpassword" python3 scripts/create_powder_s_item.py
  WIKI_USER="Lemoncheddar@okg-updater" WIKI_PASS="botpassword" python3 scripts/create_powder_s_item.py --dry-run
"""

from __future__ import annotations

import json
import os
import sys
import time

import requests

API_URL = "https://www.wikidata.org/w/api.php"

LABEL = "POWDER-S"
DESCRIPTION = "W3C OWL vocabulary for describing and grouping web resources"

P_INSTANCE_OF = "P31"
P_OFFICIAL_WEBSITE = "P856"
P_NAMESPACE_URI = "P7510"
P_LICENSE = "P275"

Q_ONTOLOGY = "Q324254"
Q_W3C_SOFTWARE_LICENSE = "Q3564577"

OFFICIAL_WEBSITE = "https://www.w3.org/TR/powder-dr/"
NAMESPACE_URI = "http://www.w3.org/2007/05/powder-s#"

EDIT_SUMMARY = "Creating item for POWDER-S W3C OWL vocabulary (via OKG catalog bot)"
PAUSE = 1.0


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
    print(f"Logged in as {user}")

    r = session.get(API_URL, params={"action": "query", "meta": "tokens", "format": "json"})
    return r.json()["query"]["tokens"]["csrftoken"]


def create_item(session: requests.Session, token: str) -> str:
    """Create the base item with label and description. Returns new QID."""
    data = {
        "labels": {"en": {"language": "en", "value": LABEL}},
        "descriptions": {"en": {"language": "en", "value": DESCRIPTION}},
    }
    r = session.post(API_URL, data={
        "action": "wbeditentity", "new": "item",
        "data": json.dumps(data),
        "token": token, "format": "json", "summary": EDIT_SUMMARY,
    })
    resp = r.json()
    if "error" in resp:
        raise RuntimeError(f"Failed to create item: {resp['error']}")
    qid = resp["entity"]["id"]
    return qid


def add_item_claim(session: requests.Session, token: str, qid: str, prop: str, target_qid: str, label: str) -> str:
    numeric_id = int(target_qid.lstrip("Q"))
    r = session.post(API_URL, data={
        "action": "wbcreateclaim", "entity": qid,
        "property": prop, "snaktype": "value",
        "value": json.dumps({"entity-type": "item", "numeric-id": numeric_id}),
        "token": token, "format": "json", "summary": EDIT_SUMMARY,
    })
    resp = r.json()
    if "error" in resp:
        return f"ERROR {label}: {resp['error']}"
    return f"OK: added {prop} → {target_qid} ({label})"


def add_string_claim(session: requests.Session, token: str, qid: str, prop: str, value: str, label: str) -> str:
    r = session.post(API_URL, data={
        "action": "wbcreateclaim", "entity": qid,
        "property": prop, "snaktype": "value",
        "value": json.dumps(value),
        "token": token, "format": "json", "summary": EDIT_SUMMARY,
    })
    resp = r.json()
    if "error" in resp:
        return f"ERROR {label}: {resp['error']}"
    return f"OK: added {prop} → '{value}' ({label})"


def main() -> int:
    dry_run = "--dry-run" in sys.argv
    prefix = "DRY RUN — " if dry_run else ""
    print(f"{prefix}Creating Wikidata item for POWDER-S\n")
    print(f"  Label:       {LABEL}")
    print(f"  Description: {DESCRIPTION}")
    print(f"  P31:         {Q_ONTOLOGY} (ontology)")
    print(f"  P856:        {OFFICIAL_WEBSITE}")
    print(f"  P7510:       {NAMESPACE_URI}")
    print(f"  P275:        {Q_W3C_SOFTWARE_LICENSE} (W3C Software License)\n")

    if dry_run:
        print("Dry run — no changes made.")
        return 0

    session = requests.Session()
    session.headers.update({
        "User-Agent": "OKG-ItemCreator/1.0 (https://openknowledgegraphs.com)"
    })

    token = login(session)

    print("Creating item...")
    qid = create_item(session, token)
    print(f"Created: {qid} (https://www.wikidata.org/wiki/{qid})\n")
    time.sleep(PAUSE)

    results = []

    results.append(add_item_claim(session, token, qid, P_INSTANCE_OF, Q_ONTOLOGY, "ontology"))
    time.sleep(PAUSE)

    results.append(add_string_claim(session, token, qid, P_OFFICIAL_WEBSITE, OFFICIAL_WEBSITE, "official website"))
    time.sleep(PAUSE)

    results.append(add_string_claim(session, token, qid, P_NAMESPACE_URI, NAMESPACE_URI, "XML namespace URL"))
    time.sleep(PAUSE)

    results.append(add_item_claim(session, token, qid, P_LICENSE, Q_W3C_SOFTWARE_LICENSE, "W3C Software License"))

    print("Results:")
    errors = 0
    for status in results:
        print(f"  {status}")
        if status.startswith("ERROR"):
            errors += 1

    print(f"\nDone. New item: https://www.wikidata.org/wiki/{qid}")
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
