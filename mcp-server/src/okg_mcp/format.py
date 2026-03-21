"""Markdown formatting for OKG API responses."""

from typing import Any


def format_catalog(data: dict[str, Any]) -> str:
    """Format catalog metadata as markdown."""
    lines = [
        f"# {data['name']}",
        "",
        data.get("description", ""),
        "",
        f"**Ontologies**: {data.get('total_ontologies', '?')}  ",
        f"**Software tools**: {data.get('total_software', '?')}  ",
        f"**Source**: {data.get('source', '')}",
        "",
        "## Categories",
        "",
    ]
    for cat in data.get("categories", []):
        lines.append(f"- {cat}")

    lines.extend(["", "## Endpoints", ""])
    for endpoint, desc in data.get("endpoints", {}).items():
        lines.append(f"- `{endpoint}` — {desc}")

    return "\n".join(lines)


def format_search_results(data: dict[str, Any]) -> str:
    """Format search results as markdown."""
    query = data.get("query", "")
    total = data.get("total", 0)
    results = data.get("results", [])
    category = data.get("category")

    header = f"## Search: \"{query}\""
    if category:
        header += f" (category: {category})"
    header += f" — {total} result{'s' if total != 1 else ''}"

    if not results:
        return f"{header}\n\nNo results found."

    lines = [header, ""]

    for i, r in enumerate(results, 1):
        score = r.get("score")
        match_type = r.get("match")
        title = r.get("title", "Untitled")
        score_str = f" (score: {score:.2f})" if score is not None else ""
        if match_type == "text":
            score_str = " [text match]"
        lines.append(f"### {i}. {title}{score_str}")

        if r.get("description"):
            lines.append(f"> {r['description']}")
            lines.append("")

        if r.get("wikidataId"):
            lines.append(f"- **Wikidata**: {r['wikidataId']}")
        if r.get("types"):
            lines.append(f"- **Types**: {', '.join(r['types'])}")
        if r.get("category"):
            lines.append(f"- **Category**: {r['category']}")
        if r.get("homepage"):
            lines.append(f"- **Homepage**: {r['homepage']}")
        if r.get("licenses"):
            lines.append(f"- **Licenses**: {', '.join(r['licenses'])}")
        if r.get("latestVersion"):
            lines.append(f"- **Version**: {r['latestVersion']}")
        if r.get("releaseDate"):
            lines.append(f"- **Release date**: {r['releaseDate']}")
        if r.get("partOf"):
            lines.append(f"- **Part of**: {r['partOf']}")

        lines.append("")

    return "\n".join(lines)
