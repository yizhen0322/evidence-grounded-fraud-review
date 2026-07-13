import datetime
import json

import pytest

from src.narratives.llm_client import LLMUnavailable, NarrativeGeneration
from tools.run_g5_narratives import (
    assert_calibration_gate,
    G5_SOURCE_FILES,
    g5_output_dir,
    load_g4_context,
    parse_arms,
    run_g5,
    summarize_arm,
    validate_g5_rows,
    validate_reportable_g5_run,
)


RECORD = {
    "case_id": 1,
    "risk_bucket": "High",
    "codes": [
        {"feature": "V1", "direction": "increases_risk", "rank": 1}
    ],
}
RUNTIME = {
    "host": "http://localhost:11434",
    "version": "0.31.1",
    "model": "llama3:8b",
    "digest": "abc123",
}


def _write_reason_codes(path, rows):
    path.mkdir()
    (path / "reason_codes.jsonl").write_text(
        "".join(json.dumps(row) + "\n" for row in rows)
    )


def test_g5_inherits_seed_and_full_detector_feature_list(tmp_path, monkeypatch):
    g4 = tmp_path / "g4"
    _write_reason_codes(g4, [RECORD])
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
    assert [row["case_id"] for row in records] == [1]
    assert seed == 46
    assert known_features == ["V1", "recon_error", "latent_0"]


@pytest.mark.parametrize(
    ("mutator", "message"),
    [
        (lambda row: {**row, "risk_bucket": "Extreme"}, "risk bucket"),
        (
            lambda row: {
                **row,
                "codes": [{**row["codes"][0], "direction": "sideways"}],
            },
            "direction",
        ),
        (
            lambda row: {**row, "codes": [row["codes"][0], {**row["codes"][0], "rank": 2}]},
            "unique features",
        ),
    ],
)
def test_malformed_g4_enums_and_duplicate_features_are_rejected(
    tmp_path,
    monkeypatch,
    mutator,
    message,
):
    g4 = tmp_path / "g4"
    _write_reason_codes(g4, [mutator(RECORD)])
    monkeypatch.setattr(
        "tools.run_g5_narratives.validate_run_manifest",
        lambda *args, **kwargs: {"seed": 42, "feature_names": ["V1"]},
    )
    with pytest.raises(ValueError, match=message):
        load_g4_context(g4)


def test_duplicate_g4_case_ids_are_rejected(tmp_path, monkeypatch):
    g4 = tmp_path / "g4"
    _write_reason_codes(g4, [RECORD, RECORD])
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
    assert result["llm_transport_unavailable"]["rate"] == 0.5
    residual = result["on_policy_delivery"][
        "residual_detected_violation_on_delivered"
    ]
    assert residual["by_construction"] is True and residual["n"] == 0
    assert residual["rate"] is None and residual["estimable"] is False


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


def test_reported_invariants_cannot_be_overridden(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "tools.run_g5_narratives.load_g4_context",
        lambda _path: ({}, [RECORD], 42, ["V1"]),
    )
    with pytest.raises(ValueError, match="strict,simple"):
        run_g5(tmp_path / "g4", arms=["strict"])
    with pytest.raises(ValueError, match="output path"):
        run_g5(tmp_path / "g4", output=tmp_path / "reported")
    with pytest.raises(TypeError):
        run_g5(tmp_path / "g4", require_clean=False)  # type: ignore[call-arg]


def test_nonreportable_manifest_is_rejected_before_audit_use(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "tools.run_g5_narratives.validate_run_manifest",
        lambda *args, **kwargs: {
            "git_dirty": False,
            "source_code_sha256": {},
            "extra": {"reported": False},
        },
    )
    with pytest.raises(ValueError, match="not a clean reportable"):
        validate_reportable_g5_run(tmp_path / "quick")


def test_reportable_validation_recomputes_forged_row_fields(tmp_path, monkeypatch):
    run = tmp_path / "g5"
    run.mkdir()
    source = tmp_path / "g4"
    (run / "source_g4_run.txt").write_text(str(source))
    forged_rows = []
    for arm in ["strict", "simple"]:
        forged_rows.append(
            {
                "case_id": 1,
                "arm": arm,
                "evidence": "forged evidence",
                "raw_output": "not a valid narrative",
                "candidate_text": "not a valid narrative",
                "checks": {
                    "format": True,
                    "completeness": True,
                    "grounding": True,
                    "direction": True,
                },
                "fallback": False,
                "fallback_reason": None,
                "final_text": "FORGED DELIVERED TEXT",
                "latency_seconds": 1.0,
            }
        )
    (run / "narratives.jsonl").write_text(
        "".join(json.dumps(row) + "\n" for row in forged_rows)
    )
    (run / "faithfulness.json").write_text(
        json.dumps(
            {
                "model": "llama3:8b",
                "ollama_runtime": RUNTIME,
                "generation": {
                    "seed": 42,
                    "options": {"temperature": 0.1, "seed": 42},
                    "prompt_sha256": {},
                },
                "llm_transport_unavailable_count": 0,
                "arms": {
                    arm: summarize_arm([row])
                    for arm, row in zip(["strict", "simple"], forged_rows)
                },
            }
        )
    )
    manifest = {
        "git_dirty": False,
        "seed": 42,
        "source_runs": [{"run_id": "g4", "manifest_sha256": "source"}],
        "source_code_sha256": {path: "hash" for path in G5_SOURCE_FILES},
        "extra": {
            "reported": True,
            "arms": ["strict", "simple"],
            "llm_transport_unavailable_count": 0,
            "ollama_runtime": RUNTIME,
            "model": "llama3:8b",
            "generation_seed": 42,
            "generation_options": {"temperature": 0.1, "seed": 42},
            "prompt_sha256": {},
        },
    }
    monkeypatch.setattr(
        "tools.run_g5_narratives.validate_run_manifest",
        lambda *args, **kwargs: manifest,
    )
    monkeypatch.setattr(
        "tools.run_g5_narratives.load_g4_context",
        lambda _path: ({"seed": 42}, [RECORD], 42, ["V1"]),
    )
    monkeypatch.setattr(
        "tools.run_g5_narratives.source_run_ref",
        lambda _path: {"run_id": "g4", "manifest_sha256": "source"},
    )
    monkeypatch.setattr(
        "tools.run_g5_narratives.assert_source_hashes",
        lambda *args, **kwargs: None,
    )
    with pytest.raises(ValueError, match="serialized evidence|stored checks"):
        validate_reportable_g5_run(run)


def test_reported_run_enforces_clean_tree_before_generation(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "tools.run_g5_narratives.load_g4_context",
        lambda _path: ({}, [RECORD], 42, ["V1"]),
    )
    monkeypatch.setattr(
        "tools.run_g5_narratives.assert_clean_repository",
        lambda: (_ for _ in ()).throw(ValueError("dirty")),
    )
    with pytest.raises(ValueError, match="dirty"):
        run_g5(tmp_path / "g4")


def test_reported_run_aborts_without_writing_on_transport_failure(
    tmp_path,
    monkeypatch,
):
    destination = tmp_path / "reported-g5"
    monkeypatch.setattr(
        "tools.run_g5_narratives.load_g4_context",
        lambda _path: ({}, [RECORD], 42, ["V1"]),
    )
    monkeypatch.setattr("tools.run_g5_narratives.assert_clean_repository", lambda: None)
    monkeypatch.setattr(
        "tools.run_g5_narratives.assert_calibration_gate",
        lambda **_kwargs: {"overall": {"gate_passed": True}, "n_items": 1},
    )
    monkeypatch.setattr(
        "tools.run_g5_narratives.get_ollama_runtime",
        lambda *args, **kwargs: RUNTIME,
    )
    monkeypatch.setattr(
        "tools.run_g5_narratives.g5_output_dir",
        lambda *_args, **_kwargs: destination,
    )
    monkeypatch.setattr(
        "tools.run_g5_narratives.generate_narrative_response",
        lambda *args, **kwargs: (_ for _ in ()).throw(LLMUnavailable("offline")),
    )
    with pytest.raises(RuntimeError, match="transport_unavailable"):
        run_g5(tmp_path / "g4")
    assert not destination.exists()


def test_malformed_raw_text_is_judged_and_not_counted_as_unavailable(
    tmp_path,
    monkeypatch,
):
    destination = tmp_path / "quick-g5"
    captured_seeds = []
    monkeypatch.setattr(
        "tools.run_g5_narratives.load_g4_context",
        lambda _path: ({}, [RECORD], 46, ["V1"]),
    )
    monkeypatch.setattr(
        "tools.run_g5_narratives.assert_calibration_gate",
        lambda **_kwargs: {"overall": {"gate_passed": True}, "n_items": 1},
    )
    monkeypatch.setattr(
        "tools.run_g5_narratives.get_ollama_runtime",
        lambda *args, **kwargs: RUNTIME,
    )

    def generate(*args, **kwargs):
        captured_seeds.append(kwargs["generation_seed"])
        return NarrativeGeneration(raw_response="", text="")

    monkeypatch.setattr(
        "tools.run_g5_narratives.generate_narrative_response",
        generate,
    )
    monkeypatch.setattr(
        "tools.run_g5_narratives.write_run_manifest",
        lambda **kwargs: {},
    )
    result = run_g5(
        tmp_path / "g4",
        arms=["strict"],
        limit=1,
        output=destination,
    )
    row = json.loads((result / "narratives.jsonl").read_text())
    faithfulness = json.loads((result / "faithfulness.json").read_text())
    assert row["raw_output"] == row["candidate_text"] == ""
    assert row["checks"]["format"] is False
    assert row["fallback_reason"].startswith("guardrail_failed:")
    assert faithfulness["llm_transport_unavailable_count"] == 0
    assert captured_seeds == [46]
