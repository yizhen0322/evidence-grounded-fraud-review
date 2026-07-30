"""Past-only semantic feature engineering for chronological streams."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

import numpy as np
import pandas as pd

from src.semantic.catalog import FEATURE_NAMES


@dataclass(frozen=True)
class ChronologicalSplits:
    train: pd.DataFrame
    val: pd.DataFrame
    test: pd.DataFrame


def chronological_split(frame: pd.DataFrame) -> ChronologicalSplits:
    ordered = frame.sort_values(["timestamp", "transaction_id"]).reset_index(drop=True)
    n = len(ordered)
    train_end = int(n * 0.70)
    val_end = int(n * 0.85)
    if train_end == 0 or val_end <= train_end or val_end >= n:
        raise ValueError("not enough rows for chronological 70/15/15 split")
    return ChronologicalSplits(
        train=ordered.iloc[:train_end].copy(),
        val=ordered.iloc[train_end:val_end].copy(),
        test=ordered.iloc[val_end:].copy(),
    )


def split_summary(splits: ChronologicalSplits) -> dict[str, dict[str, object]]:
    summary = {}
    for name in ("train", "val", "test"):
        frame = getattr(splits, name)
        summary[name] = {
            "n": int(len(frame)),
            "frauds": int(frame["Class"].sum()),
            "fraud_ratio": float(frame["Class"].mean()) if len(frame) else 0.0,
            "start": str(frame["timestamp"].min()),
            "end": str(frame["timestamp"].max()),
        }
    return summary


def split_assignments(splits: ChronologicalSplits) -> pd.DataFrame:
    return pd.concat(
        [
            pd.DataFrame({"case_id": getattr(splits, name)["case_id"].to_numpy(), "split": name})
            for name in ("train", "val", "test")
        ],
        ignore_index=True,
    )


def engineer_past_only_features(
    frame: pd.DataFrame,
    *,
    feedback_delay_days: int = 7,
    terminal_window_days: int = 7,
) -> pd.DataFrame:
    """Compute features using rows strictly before each current transaction."""
    ordered = frame.sort_values(["timestamp", "transaction_id"]).reset_index(drop=True)
    customer_history: dict[str, list[dict[str, object]]] = defaultdict(list)
    terminal_history: dict[str, list[dict[str, object]]] = defaultdict(list)
    rows: list[dict[str, object]] = []

    for raw in ordered.to_dict("records"):
        now = pd.Timestamp(raw["timestamp"])
        customer = str(raw["customer_id"])
        terminal = str(raw["terminal_id"])
        amount = float(raw["amount"])

        cust_past = customer_history[customer]
        term_past = terminal_history[terminal]
        cust_1d = [item for item in cust_past if now - pd.Timestamp(item["timestamp"]) <= pd.Timedelta(days=1)]
        cust_7d = [item for item in cust_past if now - pd.Timestamp(item["timestamp"]) <= pd.Timedelta(days=7)]
        cust_30d = [item for item in cust_past if now - pd.Timestamp(item["timestamp"]) <= pd.Timedelta(days=30)]
        mean_30d = (
            sum(float(item["amount"]) for item in cust_30d) / len(cust_30d)
            if cust_30d
            else amount
        )
        prior_time = pd.Timestamp(cust_past[-1]["timestamp"]) if cust_past else None
        terminal_cutoff = now - pd.Timedelta(days=feedback_delay_days)
        terminal_start = terminal_cutoff - pd.Timedelta(days=terminal_window_days)
        terminal_label_window = [
            item
            for item in term_past
            if terminal_start <= pd.Timestamp(item["timestamp"]) < terminal_cutoff
        ]
        term_7d = [item for item in term_past if now - pd.Timestamp(item["timestamp"]) <= pd.Timedelta(days=7)]

        features = {
            "TransactionAmount": amount,
            "AmountVsCustomer30Day": amount / max(mean_30d, 0.01),
            "CustomerTxCount1Day": float(len(cust_1d)),
            "CustomerTxCount7Day": float(len(cust_7d)),
            "MinutesSinceCustomerTx": (
                float((now - prior_time).total_seconds() / 60.0)
                if prior_time is not None
                else 30.0 * 24.0 * 60.0
            ),
            "NewTerminalForCustomer30Day": float(
                not any(str(item["terminal_id"]) == terminal for item in cust_30d)
            ),
            "TerminalDistanceFromCustomerHome": float(
                np.hypot(
                    float(raw.get("customer_profile_x", 0.0))
                    - float(raw.get("terminal_profile_x", 0.0)),
                    float(raw.get("customer_profile_y", 0.0))
                    - float(raw.get("terminal_profile_y", 0.0)),
                )
            ),
            "TerminalTxCount7Day": float(len(term_7d)),
            "TerminalFraudRisk7Day": (
                float(sum(int(item["Class"]) for item in terminal_label_window) / len(terminal_label_window))
                if terminal_label_window
                else 0.0
            ),
            "DuringNight": float(0 <= now.hour <= 6),
            "DuringWeekend": float(now.weekday() >= 5),
        }
        rows.append({**raw, **features})
        history_row = {
            "timestamp": now,
            "amount": amount,
            "terminal_id": terminal,
            "Class": int(raw["Class"]),
        }
        customer_history[customer].append(history_row)
        terminal_history[terminal].append(history_row)

    return pd.DataFrame(rows)


def feature_matrix(frame: pd.DataFrame) -> pd.DataFrame:
    return frame[FEATURE_NAMES].astype(float).copy()
