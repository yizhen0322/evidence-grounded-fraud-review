import pandas as pd

from src.semantic.features import engineer_past_only_features
from src.semantic.generator import GeneratorConfig, dataframe_sha256, generate_transactions


def test_generator_is_deterministic_for_fixed_seed():
    config = GeneratorConfig(seed=7, n_transactions=200, n_customers=30, n_terminals=12)
    first = generate_transactions(config)
    second = generate_transactions(config)

    assert dataframe_sha256(first) == dataframe_sha256(second)
    assert first.equals(second)
    assert int(first["case_id"].max()) <= 2**53 - 1


def test_future_row_mutation_cannot_change_prior_features():
    frame = generate_transactions(
        GeneratorConfig(seed=8, n_transactions=220, n_customers=25, n_terminals=10)
    )
    baseline = engineer_past_only_features(frame)

    mutated = frame.copy()
    cutoff = len(mutated) // 2
    mutated.loc[cutoff:, "amount"] = mutated.loc[cutoff:, "amount"] * 100
    mutated.loc[cutoff:, "Class"] = 1 - mutated.loc[cutoff:, "Class"]
    mutated.loc[cutoff:, "terminal_id"] = "T99999"
    changed = engineer_past_only_features(mutated)

    feature_columns = [
        "TransactionAmount",
        "AmountVsCustomer30Day",
        "CustomerTxCount1Day",
        "CustomerTxCount7Day",
        "MinutesSinceCustomerTx",
        "NewTerminalForCustomer30Day",
        "TerminalDistanceFromCustomerHome",
        "TerminalTxCount7Day",
        "TerminalFraudRisk7Day",
        "DuringNight",
        "DuringWeekend",
    ]
    pd.testing.assert_frame_equal(
        baseline.loc[: cutoff - 1, feature_columns],
        changed.loc[: cutoff - 1, feature_columns],
    )


def test_terminal_fraud_risk_uses_seven_day_delayed_labels():
    frame = pd.DataFrame(
        [
            {
                "case_id": 1,
                "transaction_id": "TX1",
                "timestamp": pd.Timestamp("2024-01-01"),
                "customer_id": "C1",
                "terminal_id": "T1",
                "amount": 10.0,
                "Class": 1,
                "fraud_scenario": 2,
            },
            {
                "case_id": 2,
                "transaction_id": "TX2",
                "timestamp": pd.Timestamp("2024-01-06"),
                "customer_id": "C2",
                "terminal_id": "T1",
                "amount": 10.0,
                "Class": 0,
                "fraud_scenario": 0,
            },
            {
                "case_id": 3,
                "transaction_id": "TX3",
                "timestamp": pd.Timestamp("2024-01-09"),
                "customer_id": "C3",
                "terminal_id": "T1",
                "amount": 10.0,
                "Class": 0,
                "fraud_scenario": 0,
            },
        ]
    )

    engineered = engineer_past_only_features(frame)

    assert engineered.loc[1, "TerminalFraudRisk7Day"] == 0.0
    assert engineered.loc[2, "TerminalFraudRisk7Day"] == 1.0
