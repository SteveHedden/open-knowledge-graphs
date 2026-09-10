"""Reviewed canonical URL migrations with permanent reservations for old slugs."""
import html
import json
import re
from pathlib import Path

BASE_URL = "https://openknowledgegraphs.com"


def load_migrations(root):
    path = Path(root) / "validation/uri-migrations.json"
    if not path.exists():
        return []
    rows = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(rows, list):
        raise ValueError("URI migrations must be a list")
    identities, sources, targets = set(), set(), set()
    for row in rows:
        if (not isinstance(row, dict) or row.get("dataset") not in {"resource", "software"}
                or not re.fullmatch(r"Q[1-9][0-9]*", row.get("qid", ""))
                or not all(re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", row.get(k, ""))
                           for k in ("from", "to"))
                or row["from"] == row["to"]):
            raise ValueError("Invalid URI migration")
        identity = (row["dataset"], row["qid"])
        source = (row["dataset"], row["from"])
        target = (row["dataset"], row["to"])
        if identity in identities or source in sources or target in targets:
            raise ValueError("Duplicate URI migration")
        identities.add(identity)
        sources.add(source)
        targets.add(target)
    if sources & targets:
        raise ValueError("Chained or cyclic URI migrations are not supported")
    return rows


def permits(rows, dataset, qid, old, new):
    return any(r["dataset"] == dataset and r["qid"] == qid
               and r["from"] == old and r["to"] == new for r in rows)


def apply_migrations(registry, rows):
    for row in rows:
        entries = registry.setdefault(row["dataset"], {})
        for qid, slug in entries.items():
            if qid != row["qid"] and slug in {row["from"], row["to"]}:
                raise ValueError("URI migration conflicts with another identity")
        current = entries.get(row["qid"])
        if current is not None and current not in {row["from"], row["to"]}:
            raise ValueError("URI migration does not match the reserved identity")
        entries[row["qid"]] = row["to"]
    return registry


def redirect_document(target):
    url = html.escape(target, quote=True)
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8">'
            f'<title>Resource moved</title><meta name="robots" content="noindex">'
            f'<link rel="canonical" href="{url}">'
            f'<meta http-equiv="refresh" content="0; url={url}"></head>'
            f'<body><p>This resource has moved. <a href="{url}">Continue to its page</a>.</p>'
            f'</body></html>\n')


def active_redirects(rows, registry, page_qids):
    active = []
    for row in rows:
        # A migration is pending until a normal catalog fetch changes the registry.
        if registry.get(row["dataset"], {}).get(row["qid"]) != row["to"]:
            continue
        if page_qids.get(row["dataset"], {}).get(row["qid"]) != row["to"]:
            raise ValueError("Migrated resource must have a verified destination page")
        active.append(row)
    return active


def write_redirects(site, rows):
    for row in rows:
        page = Path(site) / row["dataset"] / row["from"] / "index.html"
        page.parent.mkdir(parents=True, exist_ok=True)
        page.write_text(redirect_document(
            f'{BASE_URL}/{row["dataset"]}/{row["to"]}/'), encoding="utf-8")
