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
UNKNOWN_FEATURE_TOKEN_RE = re.compile(r"\b(?:V\d+|[A-Za-z]+_[A-Za-z0-9_]+)\b", re.I)
RISK_LEVEL_RE = re.compile(r"\b(?P<level>High|Medium|Low)\s+risk\b", re.I)
CALIBRATED_KNOWN_FEATURES = [
    "Time",
    *[f"V{index}" for index in range(1, 29)],
    "Amount",
]
DIRECTION_PHRASES = {
    "increases_risk": (
        "increases risk",
        "increases the risk",
        "increase risk",
        "increase the risk",
        "raises risk",
        "raises the risk",
        "raise risk",
        "raise the risk",
        "increasing risk",
        "increasing the risk",
        "raising risk",
        "raising the risk",
    ),
    "decreases_risk": (
        "decreases risk",
        "decreases the risk",
        "decrease risk",
        "decrease the risk",
        "lowers risk",
        "lowers the risk",
        "lower risk",
        "lower the risk",
        "decreasing risk",
        "decreasing the risk",
        "lowering risk",
        "lowering the risk",
    ),
}


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
        len(sentences) == 2
        and all(sentence[-1] in ".!?" for sentence in sentences)
        and not _has_unauthorized_number(text, known_features)
    )


def _parse_narrative_clauses(
    narrative: str,
    known_features: list[str],
) -> list[tuple[str, str]] | None:
    """Parse a closed grammar so free-text reasons cannot accompany evidence."""
    sentences = [
        sentence.strip()
        for sentence in re.split(r"(?<=[.!?])\s+", narrative.strip())
        if sentence.strip()
    ]
    if len(sentences) != 2:
        return None
    body = sentences[1][:-1].strip()
    feature_alt = "|".join(
        re.escape(feature) for feature in sorted(known_features, key=len, reverse=True)
    )
    phrase_to_direction = {
        phrase: direction
        for direction, phrases in DIRECTION_PHRASES.items()
        for phrase in phrases
    }
    direction_alt = "|".join(
        re.escape(phrase)
        for phrase in sorted(phrase_to_direction, key=len, reverse=True)
    )
    clause_re = re.compile(
        rf"\b(?P<features>(?:{feature_alt})(?:(?:\s*,\s*(?:and\s+)?|\s+and\s+)(?:{feature_alt}))*)\b\s+"
        rf"(?:also\s+)?"
        rf"(?P<direction>{direction_alt})"
        rf"(?:\s+for this transaction)?",
        re.I,
    )
    matches = list(clause_re.finditer(body))
    if not matches:
        return None
    rows: list[tuple[str, str]] = []
    cursor = 0
    canonical_features = {feature.lower(): feature for feature in known_features}
    for index, match in enumerate(matches):
        separator = body[cursor : match.start()]
        if index == 0:
            if separator.strip().lower() not in {
                "",
                "both",
                "this case is rated high risk due to",
                "this case is rated medium risk due to",
                "this case is rated low risk due to",
            }:
                return None
        elif re.fullmatch(
            r"\s*(?:,\s*(?:(?:and|while)\s+)?|(?:and|while)\s+)",
            separator,
            re.I,
        ) is None:
            return None
        phrase = re.sub(r"\s+", " ", match.group("direction").lower())
        for raw_feature in re.split(
            r"\s*(?:,\s*(?:and\s+)?|\s+and\s+)\s*",
            match.group("features"),
            flags=re.I,
        ):
            rows.append(
                (
                    canonical_features[raw_feature.lower()],
                    phrase_to_direction[phrase],
                )
            )
        cursor = match.end()
    if body[cursor:].strip():
        return None
    return rows


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
    narrative_rows = _parse_narrative_clauses(
        match.group("narrative"),
        known_features,
    )
    if narrative_rows is None:
        return False
    if {feature for feature, _ in narrative_rows} - allowed:
        return False
    unknown = {
        token
        for token in UNKNOWN_FEATURE_TOKEN_RE.findall(text)
        if token.lower() not in allowed_lower
    }
    if unknown:
        return False
    first_sentence = re.split(
        r"(?<=[.!?])\s+",
        match.group("narrative").strip(),
        maxsplit=1,
    )[0]
    if re.fullmatch(
        r"This case is rated (High|Medium|Low) risk\.",
        first_sentence,
        re.I,
    ) is None:
        return False
    stated_levels = {
        found.group("level").lower()
        for found in RISK_LEVEL_RE.finditer(match.group("narrative"))
    }
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

    expected = dict(expected_rows)
    narrative_rows = _parse_narrative_clauses(
        match.group("narrative"),
        known_features,
    )
    if narrative_rows is None:
        return False
    return (
        len(narrative_rows) == len(expected)
        and all(expected.get(feature) == direction for feature, direction in narrative_rows)
    )


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
