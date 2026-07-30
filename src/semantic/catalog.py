"""Semantic feature catalogue and coarse bucket rendering."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SemanticFeature:
    key: str
    label: str
    meaning: str
    bucket: str


FEATURE_CATALOG: dict[str, SemanticFeature] = {
    "TransactionAmount": SemanticFeature(
        "TransactionAmount",
        "Transaction amount",
        "Current synthetic transaction amount",
        "amount",
    ),
    "AmountVsCustomer30Day": SemanticFeature(
        "AmountVsCustomer30Day",
        "Amount vs customer 30-day average",
        "Ratio to the customer's past-only 30-day mean",
        "ratio",
    ),
    "CustomerTxCount1Day": SemanticFeature(
        "CustomerTxCount1Day",
        "Customer activity in 24 hours",
        "Past-only transaction count in the previous day",
        "count",
    ),
    "CustomerTxCount7Day": SemanticFeature(
        "CustomerTxCount7Day",
        "Customer activity in 7 days",
        "Past-only transaction count in the previous week",
        "count",
    ),
    "MinutesSinceCustomerTx": SemanticFeature(
        "MinutesSinceCustomerTx",
        "Time since customer's prior transaction",
        "Short gaps indicate a burst",
        "time_gap",
    ),
    "NewTerminalForCustomer30Day": SemanticFeature(
        "NewTerminalForCustomer30Day",
        "New terminal for customer",
        "Terminal absent from the customer's prior 30-day history",
        "binary",
    ),
    "TerminalDistanceFromCustomerHome": SemanticFeature(
        "TerminalDistanceFromCustomerHome",
        "Terminal distance from customer home",
        "Distance between synthetic customer and terminal profile locations",
        "distance",
    ),
    "TerminalTxCount7Day": SemanticFeature(
        "TerminalTxCount7Day",
        "Terminal activity in 7 days",
        "Past-only terminal transaction count",
        "count",
    ),
    "TerminalFraudRisk7Day": SemanticFeature(
        "TerminalFraudRisk7Day",
        "Delayed terminal fraud rate",
        "Seven-day risk window using labels delayed by seven days",
        "risk_rate",
    ),
    "DuringNight": SemanticFeature(
        "DuringNight",
        "Night-time transaction",
        "Transaction occurred from midnight through 06:00",
        "binary",
    ),
    "DuringWeekend": SemanticFeature(
        "DuringWeekend",
        "Weekend transaction",
        "Transaction occurred on Saturday or Sunday",
        "binary",
    ),
}

FEATURE_NAMES = list(FEATURE_CATALOG)


def catalogue_records() -> list[dict[str, str]]:
    """Return a serializable ordered feature catalogue."""
    return [
        {
            "key": item.key,
            "label": item.label,
            "meaning": item.meaning,
            "bucket": item.bucket,
        }
        for item in FEATURE_CATALOG.values()
    ]


def coarse_bucket(feature: str, value: float) -> str:
    """Map exact detector values to a coarse LLM-safe bucket."""
    kind = FEATURE_CATALOG[feature].bucket
    if kind == "amount":
        if value < 40:
            return "low"
        if value < 160:
            return "typical"
        return "high"
    if kind == "ratio":
        if value < 0.8:
            return "below_customer_pattern"
        if value <= 1.5:
            return "near_customer_pattern"
        return "above_customer_pattern"
    if kind == "count":
        if value <= 0:
            return "none"
        if value <= 3:
            return "low"
        if value <= 10:
            return "elevated"
        return "high"
    if kind == "time_gap":
        if value < 30:
            return "short_gap"
        if value < 24 * 60:
            return "same_day"
        return "long_gap"
    if kind == "distance":
        if value < 10:
            return "near_home"
        if value < 35:
            return "regional"
        return "far_from_home"
    if kind == "binary":
        return "yes" if value >= 0.5 else "no"
    if kind == "risk_rate":
        if value <= 0:
            return "none"
        if value < 0.05:
            return "low"
        if value < 0.2:
            return "elevated"
        return "high"
    raise ValueError(f"unknown bucket type for feature: {feature}")
