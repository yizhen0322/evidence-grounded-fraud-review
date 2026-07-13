import json

import pandas as pd
import pytest

from tools.make_audit_sample import AUDIT_COLUMNS, make_audit_sample
from tools.score_audit import score_audit


def test_audit_sample_is_blind_and_human_columns_are_blank(tmp_path):
    run = tmp_path / "g5"
    run.mkdir()
    rows = [
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
    (run / "narratives.jsonl").write_text(
        "".join(json.dumps(row) + "\n" for row in rows)
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


def test_score_audit_requires_complete_yes_no_human_labels(tmp_path):
    sheet = tmp_path / "filled.csv"
    pd.DataFrame({"violation_found": ["yes", "no", "NO"]}).to_csv(
        sheet,
        index=False,
    )
    output = score_audit(sheet, tmp_path / "result.json")
    result = json.loads(output.read_text())
    assert result["undetected_violation_rate"]["rate"] == pytest.approx(1 / 3)
    assert result["undetected_violation_rate"]["n"] == 3
    assert result["annotation_source"] == "human"

    pd.DataFrame({"violation_found": ["yes", ""]}).to_csv(sheet, index=False)
    with pytest.raises(ValueError, match="yes/no"):
        score_audit(sheet, tmp_path / "invalid.json")
