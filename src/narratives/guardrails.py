"""Deterministic narrative checks. Any failed check triggers reason-code fallback."""

from __future__ import annotations

import re
from dataclasses import dataclass

SECTION_RE = re.compile(
    r"\ANARRATIVE:\s*(?P<narrative>.+?)\n"
    r"EVIDENCE:\n(?P<evidence>(?:-\s+[^\n]+\n)+)"
    r"ACTION:\s*Recommended for manual review\.\s*\Z",
    re.S,
)
BULLET_RE = re.compile(
    r"-\s+(?P<feature>[A-Za-z_][A-Za-z0-9_]*)\s+-\s+"
    r"(?P<direction>increases risk|decreases risk)",
    re.I,
)
NUMBER_RE = re.compile(r"(?<![A-Za-z_])[-+]?\d+(?:\.\d+)?%?")
NEGATED_DIRECTION_RE = re.compile(
    r"\b(?:not|never|no|doesn't|does not|isn't|is not)\b"
    r".{0,30}\b(?:increase|increases|increasing|decrease|decreases|decreasing)\s+risk\b",
    re.I,
)
UNKNOWN_FEATURE_TOKEN_RE = re.compile(r"\b(?:V\d+|[A-Za-z]+_[A-Za-z0-9_]+)\b", re.I)
RISK_LEVEL_RE = re.compile(r"\b(?P<level>High|Medium|Low)\s+risk\b", re.I)


@dataclass(frozen=True)
class GuardrailResult:
    ok: bool
    checks: dict[str, bool]
    final_text: str
    fallback: bool


def fallback_text(record: dict) -> str:
    """Produce a deterministic output that does not depend on the LLM."""
    lines = [f"Risk level: {record['risk_bucket']}. Standardized reason codes:"]
    for code in sorted(record["codes"], key=lambda item: item["rank"]):
        direction = (
            "increases risk"
            if code["direction"] == "increases_risk"
            else "decreases risk"
        )
        lines.append(f"{code['rank']}. {code['feature']} - {direction}")
    return "\n".join(lines)


def _sections(text: str) -> re.Match[str] | None:
    return SECTION_RE.fullmatch(text.strip())


def _parse_bullets(evidence: str) -> list[tuple[str, str]] | None:
    rows: list[tuple[str, str]] = []
    for line in evidence.strip().splitlines():
        match = BULLET_RE.fullmatch(line.strip())
        if match is None:
            return None
        direction = (
            "increases_risk"
            if match.group("direction").lower() == "increases risk"
            else "decreases_risk"
        )
        rows.append((match.group("feature"), direction))
    return rows


def _mentioned_features(text: str, features: list[str]) -> set[str]:
    return {
        feature
        for feature in features
        if re.search(rf"\b{re.escape(feature)}\b", text, re.I)
    }


def _has_unauthorized_number(text: str, known_features: list[str]) -> bool:
    scrubbed = text
    for feature in sorted(known_features, key=len, reverse=True):
        scrubbed = re.sub(
            rf"\b{re.escape(feature)}\b",
            "FEATURE",
            scrubbed,
            flags=re.I,
        )
    return NUMBER_RE.search(scrubbed) is not None


def _format_ok(text: str, known_features: list[str]) -> bool:
    match = _sections(text)
    if match is None or _parse_bullets(match.group("evidence")) is None:
        return False
    narrative = match.group("narrative").strip()
    sentences = [
        sentence.strip()
        for sentence in re.split(r"(?<=[.!?])\s+", narrative)
        if sentence.strip()
    ]
    return (
        2 <= len(sentences) <= 3
        and all(sentence[-1] in ".!?" for sentence in sentences)
        and not _has_unauthorized_number(text, known_features)
    )


def _completeness_ok(text: str, record: dict) -> bool:
    match = _sections(text)
    if match is None:
        return False
    bullets = _parse_bullets(match.group("evidence"))
    if bullets is None:
        return False
    expected_order = [
        code["feature"]
        for code in sorted(record["codes"], key=lambda item: item["rank"])
    ]
    return (
        [feature for feature, _ in bullets] == expected_order
        and _mentioned_features(match.group("narrative"), expected_order)
        == set(expected_order)
    )


def _grounding_ok(text: str, record: dict, known_features: list[str]) -> bool:
    match = _sections(text)
    if match is None:
        return False
    allowed = {code["feature"] for code in record["codes"]}
    allowed_lower = {feature.lower() for feature in allowed}
    if _mentioned_features(text, known_features) - allowed:
        return False
    unknown = {
        token
        for token in UNKNOWN_FEATURE_TOKEN_RE.findall(text)
        if token.lower() not in allowed_lower
    }
    if unknown:
        return False
    stated_levels = {match.group("level").lower() for match in RISK_LEVEL_RE.finditer(match.group("narrative"))}
    return stated_levels == {str(record["risk_bucket"]).lower()}


def _direction_ok(text: str, record: dict, known_features: list[str]) -> bool:
    match = _sections(text)
    if match is None:
        return False
    bullets = _parse_bullets(match.group("evidence"))
    if bullets is None:
        return False
    ordered_codes = sorted(record["codes"], key=lambda item: item["rank"])
    expected_rows = [(code["feature"], code["direction"]) for code in ordered_codes]
    if bullets != expected_rows:
        return False

    narrative = match.group("narrative")
    feature_alt = "|".join(
        re.escape(feature) for feature in sorted(known_features, key=len, reverse=True)
    )
    expected = dict(expected_rows)
    for feature, expected_direction in expected.items():
        pattern = re.compile(
            rf"\b{re.escape(feature)}\b(?P<span>.{{0,120}}?)"
            rf"(?=\b(?:{feature_alt})\b|[.!?;\n]|$)",
            re.I,
        )
        spans = [found.group("span") for found in pattern.finditer(narrative)]
        if not spans:
            return False
        for span in spans:
            if NEGATED_DIRECTION_RE.search(span):
                return False
            stated: set[str] = set()
            if re.search(r"\bincreases\s+risk\b", span, re.I):
                stated.add("increases_risk")
            if re.search(r"\bdecreases\s+risk\b", span, re.I):
                stated.add("decreases_risk")
            if stated != {expected_direction}:
                return False
    return True


def validate_narrative(
    text: str,
    record: dict,
    known_features: list[str],
) -> GuardrailResult:
    """Apply four independent checks and fail closed to reason codes."""
    checks = {
        "format": _format_ok(text, known_features),
        "completeness": _completeness_ok(text, record),
        "grounding": _grounding_ok(text, record, known_features),
        "direction": _direction_ok(text, record, known_features),
    }
    ok = all(checks.values())
    return GuardrailResult(
        ok=ok,
        checks=checks,
        final_text=text if ok else fallback_text(record),
        fallback=not ok,
    )
