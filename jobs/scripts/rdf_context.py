"""Occurrence-level handling of the observed Robotics Data Foundation homonym.

Only explicit team-name spans and supported team references are rejected.
Independently supported semantic RDF is retained; unresolved uses are recorded
as ambiguous, not silently assigned the meaning of another occurrence.
"""
from __future__ import annotations
import re

FIELDS = ('title', 'description', 'qualifications', 'responsibilities')
ROBOTICS = re.compile(r'(?i)\bRobotics\s+Data\s+Foundation\b')
RDF = re.compile(r'\bRDF\b')
STANDARD = r'Resource\s+Description\s+Framework'
EXPANSIONS = (
    ('robotics', re.compile(r'(?i)\bRobotics\s+Data\s+Foundation\s*\(\s*(RDF)\s*\)')),
    ('robotics', re.compile(r'(?i)\b(RDF)\s*\(\s*Robotics\s+Data\s+Foundation\s*\)')),
    ('semantic', re.compile(r'(?i)\b' + STANDARD + r'\s*\(\s*(RDF)\s*\)')),
    ('semantic', re.compile(r'(?i)\b(RDF)\s*\(\s*' + STANDARD + r'\s*\)')),
)
SEMANTIC = re.compile(r'(?i)\b(?:Resource\s+Description\s+Framework|SPARQL|RDFS|SHACL|'
                      r'knowledge\s+graphs?|semantic\s+(?:web|data)|triplestores?|triples?|'
                      r'RDF\s*/\s*XML|RDF\s+seriali[sz]ation)\b')
SKILL_CONTEXT = re.compile(r'(?i)\b(?:skills?|experience|proficien\w*|knowledge|'
                           r'require\w*|using|use|engineers?)\b')
BOUNDARY = re.compile(r'[.!?;\n\r]')
TEAM = re.compile(r'(?i)^\s*(?:team|group)\b')


def _clause(text: str, start: int, end: int) -> str:
    left, right = 0, len(text)
    # A line wrap inside a recognized multiword marker ("semantic\n data")
    # is not a new evidence clause. Other bullet/line boundaries remain intact.
    markers = [match.span() for match in SEMANTIC.finditer(text)]
    for boundary in BOUNDARY.finditer(text):
        if any(left < boundary.start() and boundary.end() < right for left, right in markers):
            continue
        if boundary.end() <= start:
            left = boundary.end()
        elif boundary.start() >= end:
            right = boundary.start()
            break
    return text[left:right]


def analyze_rdf(record: dict) -> list[dict]:
    """Return separate decisions for RDF occurrences only in collision records."""
    fields = {f: record[f] for f in FIELDS if isinstance(record.get(f), str)}
    if not any(ROBOTICS.search(text) for text in fields.values()):
        return []
    semantic_fields = {f for f, text in fields.items() if SEMANTIC.search(text)}
    decisions = []
    for field, text in fields.items():
        explicit = {m.span(1): sense for sense, pattern in EXPANSIONS
                    for m in pattern.finditer(text)}
        for match in RDF.finditer(text):
            span = match.span(); clause = _clause(text, *span)
            sense = explicit.get(span)
            reason = 'explicit expansion'
            if sense is None:
                team_reference = bool(TEAM.match(text[match.end():]))
                local_semantics = bool(SEMANTIC.search(clause))
                if team_reference:
                    sense = 'ambiguous' if local_semantics else 'robotics'
                    reason = 'team reference with conflicting senses' if local_semantics else 'reference to the named robotics team'
                elif local_semantics:
                    sense, reason = 'semantic', 'semantic technology context in the same clause'
                elif (semantic_fields - {field}) and SKILL_CONTEXT.search(clause):
                    sense, reason = 'semantic', 'role or skill context supported by semantic evidence in another field'
                else:
                    sense, reason = 'ambiguous', 'no occurrence-specific evidence resolves the acronym'
            decisions.append({'field': field, 'start': span[0], 'end': span[1],
                              'sense': sense, 'reason': reason})
    return decisions


def matching_projection(record: dict, *, mask_ambiguous: bool = True) -> dict:
    """Return a same-offset matching view; never mutate source fields."""
    decisions = analyze_rdf(record)
    fields = {f: record[f] for f in FIELDS if isinstance(record.get(f), str)}
    if not any(ROBOTICS.search(text) for text in fields.values()):
        return record
    result = dict(record)
    for field, text in fields.items():
        spans = [m.span() for m in ROBOTICS.finditer(text)]
        spans += [(d['start'], d['end']) for d in decisions if d['field'] == field
                  and (d['sense'] == 'robotics' or (mask_ambiguous and d['sense'] == 'ambiguous'))]
        chars = list(text)
        for start, end in spans:
            chars[start:end] = ' ' * (end - start)
        result[field] = ''.join(chars)
    return result
