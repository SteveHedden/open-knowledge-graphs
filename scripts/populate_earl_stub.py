#!/usr/bin/env python3
"""Populate the Wikidata stub for EARL (Q3061304) — Evaluation and Report Language.

Sets:
  - English label
  - English description
  - P31 (instance of) → Q1469824 (controlled vocabulary)
  - P856 (official website) → https://www.w3.org/WAI/standards-guidelines/earl/
  - P275 (copyright license) → Q3564577 (W3C Software License)

Usage:
  WIKI_USER="Lemoncheddar@okg-updater" WIKI_PASS="botpassword" python3 scripts/populate_earl_stub.py
  WIKI_USER="Lemoncheddar@okg-updater" WIKI_PASS="botpassword" python3 scripts/populate_earl_stub.py --dry-run
"""

from __future__ import annotations

import json
import os
import sys
import time

import requests

API_URL = "https://www.wikidata.org/w/api.php"
QID = "Q3061304"

LABEL = "Evaluation and Report Language"
DESCRIPTION = "W3C RDF vocabulary for expressing web accessibility test results"

# Property IDs
P_INSTANCE_OF = "P31"
P_OFFICIAL_WEBSITE = "P856"
P_LICENSE = "P275"

# Value QIDs
Q_CONTROLLED_VOCABULARY = "Q1469824"
Q_W3C_SOFTWARE_LICENSE = "Q3564577"

OFFICIAL_WEBSITE = "https://www.w3.org/WAI/standards-guidelines/earl/"

EDIT_SUMMARY = "Populating stub for EARL (Evaluation and Report Language) (via OKG catalog bot)"
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

    r = session.get(API_URL, params={
        "action": "query", "meta": "tokens", "format": "json"
    })
    return r.json()["query"]["tokens"]["csrftoken"]


def get_current_state(session: requests.Session) -> dict:
    r = session.get(API_URL, params={
        "action": "wbgetentities", "ids": QID,
        "props": "labels|descriptions|claims",
        "languages": "en", "format": "json"
    })
    entity = r.json()["entities"][QID]
    label = entity.get("labels", {}).get("en", {}).get("value")
    description = entity.get("descriptions", {}).get("en", {}).get("value")
    claims = entity.get("claims", {})
    return {"label": label, "description": description, "claims": claims}


def set_label(session: requests.Session, token: str, dry_run: bool, current: str | None) -> str:
    if current:
        return f"SKIP label (already set: '{current}')"
    if dry_run:
        return f"DRY RUN: set label → '{LABEL}'"
    r = session.post(API_URL, data={
        "action": "wbsetlabel", "id": QID, "language": "en",
        "value": LABEL, "token": token, "format": "json", "summary": EDIT_SUMMARY,
    })
    if "error" in r.json():
        return f"ERROR: {r.json()['error']}"
    return f"OK: set label → '{LABEL}'"


def set_description(session: requests.Session, token: str, dry_run: bool, current: str | None) -> str:
    if current:
        return f"SKIP description (already set: '{current}')"
    if dry_run:
        return f"DRY RUN: set description → '{DESCRIPTION}'"
    r = session.post(API_URL, data={
        "action": "wbsetdescription", "id": QID, "language": "en",
        "value": DESCRIPTION, "token": token, "format": "json", "summary": EDIT_SUMMARY,
    })
    if "error" in r.json():
        return f"ERROR: {r.json()['error']}"
    return f"OK: set description → '{DESCRIPTION}'"


def add_item_claim(
    session: requests.Session, token: str, dry_run: bool,
    prop: str, target_qid: str, claims: dict, label: str
) -> str:
    existing = claims.get(prop, [])
    for c in existing:
        val = c.get("mainsnak", {}).get("datavalue", {}).get("value", {})
        if isinstance(val, dict) and str(val.get("numeric-id")) == target_qid.lstrip("Q"):
            return f"SKIP {label} (already set)"
    if existing:
        return f"SKIP {label} (already has {prop} claim, not overwriting)"
    if dry_run:
        return f"DRY RUN: add {prop} → {target_qid} ({label})"
    numeric_id = int(target_qid.lstrip("Q"))
    r = session.post(API_URL, data={
        "action": "wbcreateclaim", "entity": QID,
        "property": prop, "snaktype": "value",
        "value": json.dumps({"entity-type": "item", "numeric-id": numeric_id}),
        "token": token, "format": "json", "summary": EDIT_SUMMARY,
    })
    if "error" in r.json():
        return f"ERROR {label}: {r.json()['error']}"
    return f"OK: added {prop} → {target_qid} ({label})"


def add_url_claim(
    session: requests.Session, token: str, dry_run: bool,
    prop: str, url: str, claims: dict, label: str
) -> str:
    existing = claims.get(prop, [])
    for c in existing:
        val = c.get("mainsnak", {}).get("datavalue", {}).get("value")
        if val and val.rstrip("/").lower() == url.rstrip("/").lower():
            return f"SKIP {label} (already set: '{val}')"
    if existing:
        return f"SKIP {label} (already has {prop} claim, not overwriting)"
    if dry_run:
        return f"DRY RUN: add {prop} → '{url}' ({label})"
    r = session.post(API_URL, data={
        "action": "wbcreateclaim", "entity": QID,
        "property": prop, "snaktype": "value",
        "value": json.dumps(url),
        "token": token, "format": "json", "summary": EDIT_SUMMARY,
    })
    if "error" in r.json():
        return f"ERROR {label}: {r.json()['error']}"
    return f"OK: added {prop} → '{url}' ({label})"


def main() -> int:
    dry_run = "--dry-run" in sys.argv
    prefix = "DRY RUN — " if dry_run else ""
    print(f"{prefix}Populating Wikidata stub for {QID} (EARL)\n")

    session = requests.Session()
    session.headers.update({
        "User-Agent": "OKG-StubPopulator/1.0 (https://openknowledgegraphs.com)"
    })

    state = get_current_state(session)
    print(f"Current state:")
    print(f"  label:       {state['label']!r}")
    print(f"  description: {state['description']!r}")
    print(f"  claims:      {list(state['claims'].keys()) or 'none'}\n")

    token = "" if dry_run else login(session)

    results = []

    results.append(("label", set_label(session, token, dry_run, state["label"])))
    if not dry_run:
        time.sleep(PAUSE)

    results.append(("description", set_description(session, token, dry_run, state["description"])))
    if not dry_run:
        time.sleep(PAUSE)

    results.append(("instance of", add_item_claim(
        session, token, dry_run, P_INSTANCE_OF, Q_CONTROLLED_VOCABULARY,
        state["claims"], "controlled vocabulary"
    )))
    if not dry_run:
        time.sleep(PAUSE)

    results.append(("official website", add_url_claim(
        session, token, dry_run, P_OFFICIAL_WEBSITE, OFFICIAL_WEBSITE,
        state["claims"], "official website"
    )))
    if not dry_run:
        time.sleep(PAUSE)

    results.append(("license", add_item_claim(
        session, token, dry_run, P_LICENSE, Q_W3C_SOFTWARE_LICENSE,
        state["claims"], "W3C Software License"
    )))

    print("Results:")
    errors = 0
    for name, status in results:
        print(f"  {name}: {status}")
        if status.startswith("ERROR"):
            errors += 1

    print(f"\nDone. {'No errors.' if errors == 0 else f'{errors} error(s).'}")
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
