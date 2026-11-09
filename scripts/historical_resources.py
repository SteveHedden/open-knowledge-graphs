"""Explicitly reviewed historical-page exceptions; never substitute a homepage.

Read from the code checkout, including when rendering a staged catalog. The
policy participates in dataset_snapshots.code_digest through validation/.
A changed homepage requires fresh review and follows ordinary link checking.
"""
import json
import re
from pathlib import Path
from urllib.parse import urlsplit


def load_policy():
    policy = json.loads((Path(__file__).resolve().parents[1] /
                         "validation/historical-resources.json").read_text())
    for qid, entry in policy.items():
        if (not re.fullmatch(r"Q[1-9][0-9]*", qid)
                or not isinstance(entry.get("homepage"), str)
                or not entry.get("notice") or not entry.get("reviewedAt")
                or not entry.get("links")):
            raise ValueError(f"Invalid historical-resource policy: {qid}")
        for link in entry["links"]:
            parsed = urlsplit(link["url"])
            if parsed.scheme != "https" or not parsed.netloc or not link.get("label"):
                raise ValueError(f"Invalid historical-resource evidence: {qid}")
    return policy


POLICY = load_policy()


def historical_record(item):
    qid = (item.get("wikidataId") or "").rstrip("/").rsplit("/", 1)[-1]
    record = POLICY.get(qid)
    if record and (item.get("homepage") or "").strip() == record["homepage"]:
        return record
    return None
