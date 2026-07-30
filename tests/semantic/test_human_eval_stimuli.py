from pathlib import Path

from tools.build_human_eval_stimuli import apps_script_source, build_stimuli, form_payload


RUN_DIR = Path("experiments/runs/2026-07-26_s0_seed42")


def test_human_eval_stimuli_are_balanced_and_use_accepted_briefs():
    stimuli = build_stimuli(RUN_DIR)
    assert len(stimuli) == 9
    assert {row["risk_bucket"] for row in stimuli} == {"High", "Medium", "Low"}
    assert all(row["guarded_llm_brief"] for row in stimuli)


def test_single_form_has_three_tasks_per_condition_and_no_raw_case_id():
    stimuli = build_stimuli(RUN_DIR)
    payload = form_payload(stimuli)
    conditions = [task["condition"] for task in payload["tasks"]]
    assert len(payload["tasks"]) == 9
    assert {condition: conditions.count(condition) for condition in set(conditions)} == {
        "raw_reason_codes": 3,
        "deterministic_brief": 3,
        "guarded_llm_brief": 3,
    }
    assert conditions == [
        "raw_reason_codes",
        "deterministic_brief",
        "guarded_llm_brief",
    ] * 3
    serialized = str(payload)
    assert all(row["source_case_id"] not in serialized for row in stimuli)
    assert [task["participant_label"] for task in payload["tasks"]] == [
        f"Case {index:02d}" for index in range(1, 10)
    ]


def test_apps_script_is_one_private_closed_form_for_all_participants():
    stimuli = build_stimuli(RUN_DIR)
    source = apps_script_source(form_payload(stimuli))
    assert ".setCollectEmail(false)" in source
    assert ".setAcceptingResponses(false)" in source
    assert "No, I do not agree', FormApp.PageNavigationType.SUBMIT" in source
    assert "Practice case" in source
    assert "FormApp.create('Synthetic Fraud Alert Explanation Study'" in source
    assert "SpreadsheetApp.create('FYP Human Evaluation Responses')" in source
    assert "FORM_ID_V1" not in source
    assert "function doGet()" not in source
    assert "function assignParticipant()" not in source
    assert "Assigned study path" not in source
    assert "const TARGET_COMPLETED = 30" in source
    assert "openStudyAfterApproval('SUPERVISOR_APPROVED')" in source
