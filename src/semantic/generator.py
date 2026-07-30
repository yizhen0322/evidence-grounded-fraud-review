"""Deterministic synthetic card-transaction stream generator."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class GeneratorConfig:
    seed: int = 42
    n_transactions: int = 5000
    n_customers: int = 350
    n_terminals: int = 120
    start: str = "2024-01-01T00:00:00"
    days: int = 90
    terminal_compromise_rate: float = 0.08
    burst_fraud_rate: float = 0.012


def _stable_transaction_id(index: int, timestamp: pd.Timestamp, customer: int) -> int:
    payload = f"{index}|{timestamp.isoformat()}|{customer}".encode()
    return int(hashlib.sha256(payload).hexdigest()[:13], 16)


def generate_transactions(config: GeneratorConfig) -> pd.DataFrame:
    """Generate an independently implemented deterministic transaction stream."""
    rng = np.random.default_rng(config.seed)
    start = pd.Timestamp(config.start)
    offsets = np.sort(
        rng.integers(
            0,
            config.days * 24 * 60 * 60,
            size=config.n_transactions,
            endpoint=False,
        )
    )
    timestamps = start + pd.to_timedelta(offsets, unit="s")

    customer_xy = rng.uniform(0, 100, size=(config.n_customers, 2))
    terminal_xy = rng.uniform(0, 100, size=(config.n_terminals, 2))
    customer_base_amount = rng.lognormal(mean=3.55, sigma=0.45, size=config.n_customers)
    customer_activity = rng.gamma(shape=2.0, scale=1.0, size=config.n_customers)
    customer_prob = customer_activity / customer_activity.sum()

    distances = np.linalg.norm(customer_xy[:, None, :] - terminal_xy[None, :, :], axis=2)
    nearby_terminals = np.argsort(distances, axis=1)[:, :12]

    compromised_terminals = set(
        rng.choice(
            config.n_terminals,
            size=max(1, int(config.n_terminals * config.terminal_compromise_rate)),
            replace=False,
        ).tolist()
    )
    compromise_windows = {
        terminal: (
            start
            + pd.to_timedelta(int(rng.integers(10, max(11, config.days - 20))), unit="D"),
            int(rng.integers(10, 21)),
        )
        for terminal in compromised_terminals
    }

    rows: list[dict[str, object]] = []
    recent_burst_customers: dict[int, pd.Timestamp] = {}
    for index, timestamp in enumerate(timestamps):
        customer = int(rng.choice(config.n_customers, p=customer_prob))
        hour = int(timestamp.hour)
        use_far_terminal = rng.random() < 0.08
        if use_far_terminal:
            terminal = int(rng.integers(0, config.n_terminals))
        else:
            terminal = int(rng.choice(nearby_terminals[customer]))

        amount = float(
            rng.lognormal(
                mean=np.log(customer_base_amount[customer]),
                sigma=0.55,
            )
        )
        fraud_scenario = 0
        terminal_start, terminal_days = compromise_windows.get(
            terminal,
            (pd.Timestamp.min, 0),
        )
        in_compromise = terminal_start <= timestamp < terminal_start + pd.Timedelta(days=terminal_days)
        if in_compromise and rng.random() < 0.26:
            fraud_scenario = 2
            amount *= float(rng.uniform(1.4, 3.2))
        elif (
            use_far_terminal
            and (hour <= 6 or hour >= 22)
            and rng.random() < config.burst_fraud_rate * 12
        ):
            fraud_scenario = 1
            amount *= float(rng.uniform(2.0, 5.0))
            recent_burst_customers[customer] = timestamp
        elif (
            customer in recent_burst_customers
            and timestamp - recent_burst_customers[customer] < pd.Timedelta(hours=12)
            and rng.random() < 0.18
        ):
            fraud_scenario = 1
            amount *= float(rng.uniform(1.8, 4.0))

        rows.append(
            {
                "case_id": _stable_transaction_id(index, timestamp, customer),
                "transaction_id": f"TX{index:08d}",
                "timestamp": timestamp,
                "customer_id": f"C{customer:05d}",
                "terminal_id": f"T{terminal:05d}",
                "amount": round(max(amount, 0.5), 2),
                "customer_profile_x": round(float(customer_xy[customer, 0]), 4),
                "customer_profile_y": round(float(customer_xy[customer, 1]), 4),
                "terminal_profile_x": round(float(terminal_xy[terminal, 0]), 4),
                "terminal_profile_y": round(float(terminal_xy[terminal, 1]), 4),
                "fraud_scenario": fraud_scenario,
                "Class": int(fraud_scenario != 0),
            }
        )
    frame = pd.DataFrame(rows).sort_values(["timestamp", "transaction_id"]).reset_index(drop=True)
    return frame


def generator_config_from_dict(raw: dict | None) -> GeneratorConfig:
    values = dict(raw or {})
    return GeneratorConfig(**values)


def dataset_summary(frame: pd.DataFrame, config: GeneratorConfig) -> dict[str, object]:
    return {
        "generator": "independent_fdh_inspired_synthetic_stream",
        "generator_config": asdict(config),
        "n": int(len(frame)),
        "frauds": int(frame["Class"].sum()),
        "fraud_ratio": float(frame["Class"].mean()),
        "start": str(frame["timestamp"].min()),
        "end": str(frame["timestamp"].max()),
        "customers": int(frame["customer_id"].nunique()),
        "terminals": int(frame["terminal_id"].nunique()),
        "fraud_scenarios": {
            str(key): int(value)
            for key, value in frame["fraud_scenario"].value_counts().sort_index().items()
        },
    }


def dataframe_sha256(frame: pd.DataFrame) -> str:
    normalized = frame.copy()
    normalized["timestamp"] = pd.to_datetime(normalized["timestamp"]).dt.strftime(
        "%Y-%m-%dT%H:%M:%S"
    )
    payload = normalized.to_json(orient="records", date_format="iso").encode()
    return hashlib.sha256(payload).hexdigest()


def write_dataset_json(path: str | Path, frame: pd.DataFrame) -> None:
    serializable = frame.copy()
    serializable["timestamp"] = pd.to_datetime(serializable["timestamp"]).dt.strftime(
        "%Y-%m-%dT%H:%M:%S"
    )
    Path(path).write_text(json.dumps(serializable.to_dict("records"), indent=2) + "\n")
