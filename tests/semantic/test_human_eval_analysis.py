from tools.analyze_human_eval import _accuracy_summary, _likert_summary

import pandas as pd


def test_accuracy_summary_includes_exact_count_and_wilson_interval():
    frame = pd.DataFrame({"correct": [True, True, False, True]})

    result = _accuracy_summary(frame, "correct")

    assert result["successes"] == 3
    assert result["n"] == 4
    assert result["rate"] == 0.75
    assert 0.30 < result["ci95_lower"] < result["rate"]
    assert result["rate"] < result["ci95_upper"] < 1.0


def test_likert_summary_reports_median_and_iqr():
    result = _likert_summary(pd.Series([1, 2, 3, 4, 5]))

    assert result["n"] == 5
    assert result["median"] == 3.0
    assert result["q1"] == 2.0
    assert result["q3"] == 4.0
