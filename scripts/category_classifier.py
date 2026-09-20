#!/usr/bin/env python3
"""Generic utilities for classifying records against an RDF-supplied vocabulary."""

from __future__ import annotations

import json
import logging
import os
import re
import time

import requests


ANTHROPIC_VERSION = "2023-06-01"
DEFAULT_MODEL = "claude-sonnet-4-6"
DEFAULT_BATCH_SIZE = int(os.getenv("CATEGORY_CLASSIFICATION_BATCH_SIZE", "25"))
DEFAULT_TIMEOUT_SECONDS = int(os.getenv("ANTHROPIC_TIMEOUT_SECONDS", "90"))
MAX_REQUEST_ATTEMPTS = 4
BASE_BACKOFF_SECONDS = 3

QID_RE = re.compile(r"(Q\d+)$")
CODE_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.IGNORECASE | re.DOTALL)


class CategoryClassificationError(RuntimeError):
    """Raised when category classification fails for a batch."""


def qid_from_wikidata_id(value: str | None) -> str | None:
    """Parse a bare QID from a bare QID string or Wikidata entity/page IRI."""
    if not isinstance(value, str):
        return None
    candidate = value.strip()
    if not candidate:
        return None
    if QID_RE.fullmatch(candidate):
        return candidate
    match = QID_RE.search(candidate)
    if not match:
        return None
    return match.group(1)


def _chunked(items: list[dict[str, str]], size: int) -> list[list[dict[str, str]]]:
    return [items[index : index + size] for index in range(0, len(items), size)]


def _build_prompt(
    items: list[dict[str, str]],
    category_options: tuple[str, ...],
    definitions: dict[str, str] | None = None,
    entity_label: str = "ontology resource",
    fallback_instruction: str = 'Use "General / Cross-domain" when unsure.',
) -> str:
    if definitions:
        category_lines = "\n".join(f"- {category}: {definitions[category]}" for category in category_options)
    else:
        category_lines = "\n".join(f"- {category}" for category in category_options)
    serialized_items = json.dumps(items, ensure_ascii=False, indent=2)
    return (
        f"Classify each {entity_label} into exactly one category from this list:\n"
        f"{category_lines}\n\n"
        "Return ONLY a JSON object mapping each qid to one category string.\n"
        f"Do not include explanations. {fallback_instruction}\n\n"
        "Items:\n"
        f"{serialized_items}"
    )


def _extract_response_text(payload: dict) -> str:
    content = payload.get("content")
    if not isinstance(content, list):
        raise CategoryClassificationError("Anthropic response is missing content array.")

    chunks: list[str] = []
    for part in content:
        if not isinstance(part, dict):
            continue
        if part.get("type") != "text":
            continue
        text = part.get("text")
        if isinstance(text, str):
            chunks.append(text)

    joined = "".join(chunks).strip()
    if not joined:
        raise CategoryClassificationError("Anthropic response did not contain text.")
    return joined


def _extract_json_object(text: str) -> dict[str, str]:
    candidate = text.strip()
    fence_match = CODE_FENCE_RE.search(candidate)
    if fence_match:
        candidate = fence_match.group(1).strip()

    try:
        loaded = json.loads(candidate)
    except json.JSONDecodeError as exc:
        raise CategoryClassificationError(f"Could not parse JSON from model output: {exc}") from exc

    if not isinstance(loaded, dict):
        raise CategoryClassificationError("Model output must be a JSON object.")

    normalized: dict[str, str] = {}
    for raw_qid, raw_category in loaded.items():
        qid = qid_from_wikidata_id(raw_qid if isinstance(raw_qid, str) else None)
        if not qid:
            continue
        if isinstance(raw_category, str):
            normalized[qid] = raw_category.strip()
    return normalized


def _request_classification_batch(*args, **kwargs):
    raise CategoryClassificationError('Paid classification disabled; use the Codex review backlog')


def classify_items(
    items: list[dict[str, str]],
    api_key: str,
    category_options: tuple[str, ...],
    category_set: set[str],
    model: str = DEFAULT_MODEL,
    batch_size: int = DEFAULT_BATCH_SIZE,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    definitions: dict[str, str] | None = None,
    entity_label: str = "ontology resource",
    fallback_instruction: str = 'Use "General / Cross-domain" when unsure.',
) -> tuple[dict[str, str], list[str]]:
    """Classify items and return (successful_mapping, failed_qids)."""
    if not items:
        return {}, []
    if batch_size <= 0:
        raise ValueError("batch_size must be positive.")
    if not api_key:
        raise ValueError("api_key must be provided.")

    normalized_items: list[dict[str, str]] = []
    seen_qids: set[str] = set()
    for item in items:
        qid = qid_from_wikidata_id(item.get("qid"))
        if not qid or qid in seen_qids:
            continue
        seen_qids.add(qid)
        normalized_items.append(
            {
                "qid": qid,
                "title": str(item.get("title", "")).strip(),
                "description": str(item.get("description", "")).strip(),
            }
        )

    if not normalized_items:
        return {}, []

    successful: dict[str, str] = {}
    failed_qids: list[str] = []
    session = requests.Session()

    for index, batch in enumerate(_chunked(normalized_items, batch_size), start=1):
        expected_qids = {item["qid"] for item in batch}
        logging.info(
            "Classifying category batch %d (%d items) with model %s",
            index,
            len(batch),
            model,
        )
        try:
            response_mapping = _request_classification_batch(
                session=session,
                api_key=api_key,
                items=batch,
                model=model,
                timeout_seconds=timeout_seconds,
                category_options=category_options,
                definitions=definitions,
                entity_label=entity_label,
                fallback_instruction=fallback_instruction,
            )
        except CategoryClassificationError as exc:
            logging.warning("Category classification batch failed: %s", exc)
            failed_qids.extend(sorted(expected_qids))
            continue

        batch_success: dict[str, str] = {}
        for qid, category in response_mapping.items():
            if qid not in expected_qids:
                continue
            if category not in category_set:
                continue
            batch_success[qid] = category

        missing = expected_qids - set(batch_success)
        if missing:
            failed_qids.extend(sorted(missing))
        successful.update(batch_success)

    return successful, sorted(set(failed_qids))
