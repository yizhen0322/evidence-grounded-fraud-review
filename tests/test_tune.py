import json

from tools import tune as tune_module


def test_tuning_is_validation_only_and_ranked(tmp_path, monkeypatch):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        "group: g6\nfeatures: original\nimbalance: scale_pos_weight\nseed: 42\n"
    )
    validation_scores = [0.6, 0.9, 0.7]
    calls = []

    def fake_run(config, **kwargs):
        calls.append(kwargs)
        run_dir = tmp_path / config["group"]
        run_dir.mkdir()
        score = validation_scores[len(calls) - 1]
        (run_dir / "metrics.json").write_text(
            json.dumps({"val": {"auc_pr": score, "f1": score - 0.1}})
        )
        return run_dir

    monkeypatch.setattr(tune_module, "run", fake_run)
    output = tune_module.tune(
        config_path,
        n_trials=3,
        data_path=tmp_path / "data.csv",
        out_root=tmp_path / "runs",
        results_root=tmp_path / "results",
        require_clean=False,
    )

    trials = json.loads(output.read_text())
    assert [trial["val_auc_pr"] for trial in trials] == [0.9, 0.7, 0.6]
    assert all(call["evaluate_test"] is False for call in calls)
    assert all("validate_data" not in call for call in calls)
