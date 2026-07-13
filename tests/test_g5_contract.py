import datetime
import json

import pytest

from tools.run_g5_narratives import (
    assert_calibration_gate,
    g5_output_dir,
    load_g4_context,
    parse_arms,
    summarize_arm,
    validate_g5_rows,
)


def test_g5_inherits_seed_and_full_detector_feature_list(tmp_path, monkeypatch):
    g4 = tmp_path / "g4"
    g4.mkdir()
    (g4 / "reason_codes.jsonl").write_text(
        json.dumps(
            {
                "case_id": 9,
                "risk_bucket": "High",
                "codes": [
                    {"feature": "V1", "direction": "increases_risk", "rank": 1}
                ],
            }
        )
        + "\n"
    )
    manifest = {
        "seed": 46,
        "feature_names": ["V1", "recon_error", "latent_0"],
    }
    monkeypatch.setattr(
        "tools.run_g5_narratives.validate_run_manifest",
        lambda path, expected_group=None: manifest
        if expected_group == "g4"
        else pytest.fail("G4 group was not enforced"),
    )
    _, records, seed, known_features = load_g4_context(g4)
    assert [row["case_id"] for row in records] == [9]
    assert seed == 46
    assert known_features == ["V1", "recon_error", "latent_0"]


def test_duplicate_g4_case_ids_are_rejected(tmp_path, monkeypatch):
    g4 = tmp_path / "g4"
    g4.mkdir()
    row = json.dumps({"case_id": 9, "codes": []})
    (g4 / "reason_codes.jsonl").write_text(f"{row}\n{row}\n")
    monkeypatch.setattr(
        "tools.run_g5_narratives.validate_run_manifest",
        lambda *args, **kwargs: {"seed": 42, "feature_names": ["V1"]},
    )
    with pytest.raises(ValueError, match="case_id"):
        load_g4_context(g4)


def test_quick_and_final_paths_cannot_collide():
    day = datetime.date(2026, 7, 13)
    quick = g5_output_dir(46, 5, day)
    final = g5_output_dir(46, None, day)
    assert quick.parent.as_posix() == "experiments/tuning_runs"
    assert final.parent.as_posix() == "experiments/runs"
    assert "seed46" in quick.name and "seed46" in final.name
    assert quick != final


def test_arm_summary_has_detected_rates_denominators_ci_and_policy_label():
    rows = [
        {
            "checks": {
                "format": True,
                "completeness": True,
                "grounding": True,
                "direction": False,
            },
            "fallback": True,
            "latency_seconds": 1.0,
        },
        {"checks": None, "fallback": True, "latency_seconds": 3.0},
    ]
    result = summarize_arm(rows)
    direction = result["off_policy_prevalence"]["detected_direction_violation"]
    assert direction["rate"] == 1.0 and direction["n"] == 1
    assert len(direction["ci95"]) == 2
    assert result["on_policy_delivery"]["fallback"]["rate"] == 1.0
    residual = result["on_policy_delivery"][
        "residual_detected_violation_on_delivered"
    ]
    assert residual["by_construction"] is True and residual["n"] == 0


def test_rows_must_cover_each_case_once_per_arm():
    records = [{"case_id": 1}, {"case_id": 2}]
    rows = [
        {"case_id": case_id, "arm": arm}
        for arm in ["strict", "simple"]
        for case_id in [1, 2]
    ]
    validate_g5_rows(rows, records, ["strict", "simple"])
    with pytest.raises(ValueError, match="unique"):
        validate_g5_rows(rows + [rows[0]], records, ["strict", "simple"])


def test_arm_parser_rejects_unknown_and_duplicate_values():
    assert parse_arms("strict,simple") == ["strict", "simple"]
    with pytest.raises(ValueError):
        parse_arms("strict,strict")
    with pytest.raises(ValueError):
        parse_arms("creative")


def test_calibration_gate_rejects_stale_validator(tmp_path):
    corpus = tmp_path / "corpus.jsonl"
    corpus.write_text("{}\n")
    calibration = tmp_path / "calibration.json"
    calibration.write_text(
        json.dumps(
            {
                "overall": {"gate_passed": True, "failed_corpus_ids": []},
                "instrument_sha256": "stale",
                "corpus_sha256": "stale",
            }
        )
    )
    with pytest.raises(ValueError, match="validator changed"):
        assert_calibration_gate(calibration, corpus)
