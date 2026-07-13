import json

import pandas as pd
import pytest

from src.provenance import sha256_file
from tools.make_audit_sample import (
    AUDIT_COLUMNS,
    IMMUTABLE_AUDIT_COLUMNS,
    build_blind_sample,
    immutable_rows_sha256,
    make_audit_sample,
)
from tools.score_audit import score_audit


def _accepted_rows():
    return [
        {
            "case_id": case_id,
            "arm": "strict",
            "evidence": f"evidence {case_id}",
            "final_text": f"delivered {case_id}",
            "raw_output": "hidden",
            "checks": {"format": True},
            "fallback": case_id == 3,
        }
        for case_id in [1, 2, 3]
    ]


def test_audit_sample_is_blind_bound_and_human_columns_are_blank(
    tmp_path,
    monkeypatch,
):
    run = tmp_path / "g5"
    run.mkdir()
    (run / "run_manifest.json").write_text("{}")
    monkeypatch.setattr(
        "tools.make_audit_sample.validate_reportable_g5_run",
        lambda _run: ({"extra": {"arms": ["strict", "simple"]}}, _accepted_rows()),
    )
    destination = make_audit_sample(
        run,
        n=50,
        output=tmp_path / "audit.csv",
    )
    frame = pd.read_csv(destination, keep_default_na=False)
    assert list(frame.columns) == AUDIT_COLUMNS
    assert set(frame["case_id"]) == {1, 2}
    assert not {"raw_output", "checks"}.intersection(frame.columns)
    assert (frame[["violation_found", "violation_category", "notes"]] == "").all().all()
    audit_manifest = json.loads(destination.with_suffix(".manifest.json").read_text())
    assert audit_manifest["source_g5_manifest_sha256"] == sha256_file(
        run / "run_manifest.json"
    )
    assert audit_manifest["immutable_rows_sha256"] == immutable_rows_sha256(frame)


def test_audit_sample_rejects_manifest_free_or_nonreportable_run(tmp_path):
    run = tmp_path / "g5"
    run.mkdir()
    with pytest.raises(ValueError, match="missing manifest"):
        make_audit_sample(run, output=tmp_path / "audit.csv")


def _write_filled_audit(tmp_path):
    g5_rows = [
        {
            "case_id": case_id,
            "arm": "strict",
            "evidence": f"evidence {case_id}",
            "final_text": f"delivered {case_id}",
            "fallback": False,
        }
        for case_id in [1, 2, 3]
    ]
    frame = build_blind_sample(g5_rows, arm="strict", n=3, seed=42)
    frame["violation_found"] = ["yes", "no", "NO"]
    frame["violation_category"] = ["grounding", "", ""]
    frame["notes"] = ["manual note", "", ""]
    sheet = tmp_path / "filled.csv"
    frame.to_csv(sheet, index=False)
    g5 = tmp_path / "g5"
    g5.mkdir()
    (g5 / "run_manifest.json").write_text("verified-g5")
    manifest = {
        "schema_version": 1,
        "source_g5_run": str(g5),
        "source_g5_manifest_sha256": sha256_file(g5 / "run_manifest.json"),
        "arm": "strict",
        "requested_n": 3,
        "actual_n": len(frame),
        "sampling_seed": 42,
        "columns": AUDIT_COLUMNS,
        "immutable_columns": IMMUTABLE_AUDIT_COLUMNS,
        "immutable_rows_sha256": immutable_rows_sha256(frame),
        "blank_human_columns": [
            "violation_found",
            "violation_category",
            "notes",
        ],
        "sample_csv": str(sheet),
        "sample_csv_sha256_at_creation": sha256_file(sheet),
        "source_code_sha256": {
            "tools/make_audit_sample.py": sha256_file(
                "tools/make_audit_sample.py"
            ),
            "tools/run_g5_narratives.py": sha256_file(
                "tools/run_g5_narratives.py"
            ),
        },
    }
    manifest_path = tmp_path / "sample.manifest.json"
    manifest_path.write_text(json.dumps(manifest))
    return frame, sheet, manifest_path, g5, g5_rows


def test_score_audit_requires_bound_schema_labels_and_human_attestation(
    tmp_path,
    monkeypatch,
):
    _frame, sheet, manifest, g5, g5_rows = _write_filled_audit(tmp_path)
    monkeypatch.setattr(
        "tools.score_audit.validate_reportable_g5_run",
        lambda path: ({}, g5_rows)
        if path == g5
        else pytest.fail("scorer did not validate the bound G5 run"),
    )
    output = score_audit(
        sheet,
        manifest,
        human_attestation="I completed these labels manually.",
        output=tmp_path / "result.json",
    )
    result = json.loads(output.read_text())
    assert result["undetected_violation_rate"]["rate"] == pytest.approx(1 / 3)
    assert result["undetected_violation_rate"]["n"] == 3
    assert result["annotation_source"] == "human_attested"

    with pytest.raises(ValueError, match="attestation"):
        score_audit(sheet, manifest, human_attestation="AI", output=tmp_path / "x")


def test_score_audit_rejects_forged_schema_empty_or_changed_rows(
    tmp_path,
    monkeypatch,
):
    frame, sheet, manifest, g5, g5_rows = _write_filled_audit(tmp_path)
    monkeypatch.setattr(
        "tools.score_audit.validate_reportable_g5_run",
        lambda path: ({}, g5_rows)
        if path == g5
        else pytest.fail("scorer did not validate the bound G5 run"),
    )
    one_column = tmp_path / "one.csv"
    pd.DataFrame({"violation_found": ["no"]}).to_csv(one_column, index=False)
    with pytest.raises(ValueError, match="exact blinded schema"):
        score_audit(
            one_column,
            manifest,
            human_attestation="I completed these labels manually.",
        )

    empty = tmp_path / "empty.csv"
    pd.DataFrame(columns=AUDIT_COLUMNS).to_csv(empty, index=False)
    with pytest.raises(ValueError, match="cannot be empty"):
        score_audit(
            empty,
            manifest,
            human_attestation="I completed these labels manually.",
        )

    frame.loc[0, "evidence"] = "changed"
    frame.to_csv(sheet, index=False)
    with pytest.raises(ValueError, match="immutable"):
        score_audit(
            sheet,
            manifest,
            human_attestation="I completed these labels manually.",
        )


def test_score_audit_rejects_manifest_not_bound_to_a_real_g5(tmp_path):
    _frame, sheet, manifest, _g5, _g5_rows = _write_filled_audit(tmp_path)
    payload = json.loads(manifest.read_text())
    payload["source_g5_run"] = str(tmp_path / "missing-g5")
    payload["source_g5_manifest_sha256"] = "not-a-real-g5-hash"
    manifest.write_text(json.dumps(payload))
    with pytest.raises(ValueError, match="missing manifest"):
        score_audit(
            sheet,
            manifest,
            human_attestation="I completed these labels manually.",
        )
