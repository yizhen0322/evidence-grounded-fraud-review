import pandas as pd
import pytest

from src.data.load import CASE_ID, FEATURES, TARGET, dedupe, load_raw


def make_tiny_csv(tmp_path, rows=10):
    cols = ["Time", *[f"V{i}" for i in range(1, 29)], "Amount", "Class"]
    df = pd.DataFrame([[float(i)] * 30 + [i % 2] for i in range(rows)], columns=cols)
    path = tmp_path / "tiny.csv"
    df.to_csv(path, index=False)
    return path


def test_load_raw_reads_csv(tmp_path):
    df = load_raw(make_tiny_csv(tmp_path), validate=False)
    assert list(df.columns) == [CASE_ID, *FEATURES, TARGET]
    assert len(df) == 10
    assert df[CASE_ID].tolist() == list(range(10))


def test_load_raw_validate_rejects_wrong_shape(tmp_path):
    with pytest.raises(ValueError):
        load_raw(make_tiny_csv(tmp_path), validate=True)


def test_dedupe_drops_exact_duplicates():
    df = pd.DataFrame({CASE_ID: [10, 11, 12], "a": [1, 1, 2], "b": [3, 3, 4]})
    out, dropped = dedupe(df)
    assert len(out) == 2 and dropped == 1
    assert out[CASE_ID].tolist() == [10, 12]
