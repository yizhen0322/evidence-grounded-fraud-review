"""Analyse the frozen single-form human evaluation without exposing raw responses.

The input snapshot is intentionally stored under ``data/private`` and ignored by
git.  This script writes aggregate tables, a machine-readable summary, and one
publication-ready figure.  Optional free-text responses are counted but are not
read, coded, or reproduced.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.evaluation.stats import wilson_ci


DEFAULT_RAW = Path(
    "data/private/human_eval/2026-07-28-google-forms-responses-snapshot.json"
)
DEFAULT_FORM = Path("experiments/human_eval/draft_v1/form.json")
DEFAULT_TABLES = Path("reports/tables")
DEFAULT_FIGURES = Path("reports/figures")
DEFAULT_SUMMARY = Path("reports/human_eval_results.json")

CONDITION_LABELS = {
    "raw_reason_codes": "Raw reason codes",
    "deterministic_brief": "Deterministic brief",
    "guarded_llm_brief": "Guarded LLM brief",
}

RATING_FIELDS = {
    "confidence": "How confident are you in that routing action?",
    "clarity": "The explanation was easy to understand.",
    "enough_evidence": (
        "The explanation gave enough evidence for a provisional routing action."
    ),
    "mental_effort": "The explanation felt mentally effortful to use.",
}


def _answer_map(snapshot: dict[str, Any], response: dict[str, Any]) -> dict[str, Any]:
    schema = snapshot["schema"]
    answers = response["answers"]
    if len(schema) != len(answers):
        raise ValueError(
            f"Response {response['response_number']} has {len(answers)} answers for "
            f"{len(schema)} schema items."
        )
    return {item["question"]: answer for item, answer in zip(schema, answers, strict=True)}


def _case_question(case_label: str, suffix: str) -> str:
    return f"{case_label} — {suffix}"


def _likert_summary(values: pd.Series) -> dict[str, float | int]:
    numeric = pd.to_numeric(values, errors="raise")
    return {
        "n": int(numeric.size),
        "median": float(numeric.median()),
        "q1": float(numeric.quantile(0.25)),
        "q3": float(numeric.quantile(0.75)),
        "mean": float(numeric.mean()),
        "sd": float(numeric.std(ddof=1)) if numeric.size > 1 else 0.0,
    }


def _accuracy_summary(frame: pd.DataFrame, column: str) -> dict[str, float | int]:
    successes = int(frame[column].sum())
    n = int(frame[column].size)
    lower, upper = wilson_ci(successes, n)
    return {
        "successes": successes,
        "n": n,
        "rate": successes / n if n else 0.0,
        "ci95_lower": lower,
        "ci95_upper": upper,
    }


def build_analysis(
    snapshot: dict[str, Any], form: dict[str, Any]
) -> tuple[pd.DataFrame, dict[str, Any]]:
    tasks = {task["participant_label"]: task for task in form["tasks"]}
    expected_cases = {f"Case {index:02d}" for index in range(1, 10)}
    if set(tasks) != expected_cases:
        raise ValueError("The frozen form must contain Case 01 through Case 09 exactly once.")

    task_rows: list[dict[str, Any]] = []
    participant_rows: list[dict[str, Any]] = []
    included_response_numbers: list[int] = []
    excluded: list[dict[str, Any]] = []

    for response in snapshot["responses"]:
        answers = _answer_map(snapshot, response)
        consent = answers[
            "I confirm that I am at least 18 years old, have read the information "
            "above, and voluntarily agree to participate."
        ]
        required_task_answers = []
        for case_label in sorted(expected_cases):
            required_task_answers.extend(
                [
                    answers[_case_question(case_label, "Which evidence item was ranked first?")],
                    answers[
                        _case_question(
                            case_label,
                            "Did the first-ranked evidence raise or reduce risk?",
                        )
                    ],
                    answers[
                        _case_question(
                            case_label,
                            "How many distinct evidence items were explicitly named in the explanation?",
                        )
                    ],
                    answers[
                        _case_question(
                            case_label,
                            "What provisional routing action would you choose?",
                        )
                    ],
                    *[
                        answers[_case_question(case_label, suffix)]
                        for suffix in RATING_FIELDS.values()
                    ],
                ]
            )
        completion_rate = sum(value not in (None, "") for value in required_task_answers) / len(
            required_task_answers
        )

        exclusion_reason = None
        if consent != "Yes, I agree":
            exclusion_reason = "consent_or_age_confirmation_failed"
        elif completion_rate < 0.70:
            exclusion_reason = "less_than_70_percent_task_completion"

        if exclusion_reason:
            excluded.append(
                {
                    "response_number": response["response_number"],
                    "reason": exclusion_reason,
                }
            )
            continue

        included_response_numbers.append(int(response["response_number"]))
        participant_rows.append(
            {
                "participant_code": f"P{int(response['response_number']):03d}",
                "background_area": answers[
                    "Which area best describes your current study or work background?"
                ],
                "ml_familiarity": answers["How familiar are you with machine learning?"],
                "fraud_familiarity": answers[
                    "How familiar are you with fraud detection?"
                ],
                "shap_familiarity": answers[
                    "Have you used SHAP or feature-attribution explanations before?"
                ],
                "completion_rate": completion_rate,
                "overall_clearest": answers[
                    "Which explanation format was clearest overall?"
                ],
                "overall_preferred": answers[
                    "Which format would you prefer for a first-pass synthetic alert review?"
                ],
                "overall_trustworthy": answers[
                    "Which explanation format felt most trustworthy?"
                ],
                "has_overall_free_text": bool(answers["Briefly explain your preference."]),
            }
        )

        for case_label, task in tasks.items():
            direction_expected = (
                "Raised risk" if task["top_direction_expected"] == "up" else "Reduced risk"
            )
            top_answer = answers[
                _case_question(case_label, "Which evidence item was ranked first?")
            ]
            direction_answer = answers[
                _case_question(
                    case_label, "Did the first-ranked evidence raise or reduce risk?"
                )
            ]
            count_answer = answers[
                _case_question(
                    case_label,
                    "How many distinct evidence items were explicitly named in the explanation?",
                )
            ]
            optional_comment = answers[
                _case_question(case_label, "Optional: What, if anything, was unclear?")
            ]

            task_rows.append(
                {
                    "participant_code": f"P{int(response['response_number']):03d}",
                    "case_label": case_label,
                    "condition": task["condition"],
                    "condition_label": CONDITION_LABELS[task["condition"]],
                    "risk_bucket": task["risk_bucket"],
                    "top_evidence_correct": top_answer == task["top_evidence_expected"],
                    "direction_correct": direction_answer == direction_expected,
                    "evidence_count_correct": str(count_answer)
                    == str(task["named_evidence_count_expected"]),
                    "routing_action": answers[
                        _case_question(
                            case_label, "What provisional routing action would you choose?"
                        )
                    ],
                    "confidence": int(
                        answers[
                            _case_question(case_label, RATING_FIELDS["confidence"])
                        ]
                    ),
                    "clarity": int(
                        answers[_case_question(case_label, RATING_FIELDS["clarity"])]
                    ),
                    "enough_evidence": int(
                        answers[
                            _case_question(case_label, RATING_FIELDS["enough_evidence"])
                        ]
                    ),
                    "mental_effort": int(
                        answers[
                            _case_question(case_label, RATING_FIELDS["mental_effort"])
                        ]
                    ),
                    "has_optional_comment": bool(optional_comment),
                }
            )

    tasks_frame = pd.DataFrame(task_rows)
    participants_frame = pd.DataFrame(participant_rows)
    if tasks_frame.empty:
        raise ValueError("No responses passed the pre-specified inclusion rules.")

    condition_summaries: dict[str, Any] = {}
    for condition in CONDITION_LABELS:
        condition_frame = tasks_frame[tasks_frame["condition"] == condition]
        condition_summaries[condition] = {
            "label": CONDITION_LABELS[condition],
            "participants": int(condition_frame["participant_code"].nunique()),
            "task_responses": int(len(condition_frame)),
            "accuracy": {
                "top_evidence": _accuracy_summary(
                    condition_frame, "top_evidence_correct"
                ),
                "direction": _accuracy_summary(condition_frame, "direction_correct"),
                "evidence_count": _accuracy_summary(
                    condition_frame, "evidence_count_correct"
                ),
            },
            "ratings": {
                field: _likert_summary(condition_frame[field]) for field in RATING_FIELDS
            },
            "routing_action_counts": dict(
                Counter(condition_frame["routing_action"].tolist())
            ),
        }

    preference_fields = ["overall_clearest", "overall_preferred", "overall_trustworthy"]
    preferences = {
        field: {
            value: {
                "count": int(count),
                "rate": float(count / len(participants_frame)),
            }
            for value, count in participants_frame[field].value_counts(dropna=False).items()
        }
        for field in preference_fields
    }

    participant_profile = {
        field: {
            str(value): int(count)
            for value, count in participants_frame[field].value_counts(dropna=False).items()
        }
        for field in [
            "background_area",
            "ml_familiarity",
            "fraud_familiarity",
            "shap_familiarity",
        ]
    }

    summary = {
        "status": "interim_pilot_below_pre_specified_minimum",
        "target_completed_participants": 30,
        "pre_specified_minimum_if_recruitment_interrupted": 18,
        "responses_observed": int(len(snapshot["responses"])),
        "participants_included": int(len(participants_frame)),
        "participants_excluded": int(len(excluded)),
        "included_response_numbers": included_response_numbers,
        "excluded_responses": excluded,
        "completed_case_reviews": int(len(tasks_frame)),
        "condition_summaries": condition_summaries,
        "preferences": preferences,
        "participant_profile": participant_profile,
        "free_text": {
            "case_comments_nonempty": int(tasks_frame["has_optional_comment"].sum()),
            "overall_comments_nonempty": int(
                participants_frame["has_overall_free_text"].sum()
            ),
            "analysis": "not coded or reproduced",
        },
        "inferential_tests": {
            "performed": False,
            "reason": (
                "The interim n=11 sample is below the pre-specified minimum of 18; "
                "the registered analysis therefore remains descriptive."
            ),
        },
        "limitations": [
            "interim sample below the pre-specified minimum",
            "proxy reviewers rather than professional fraud analysts",
            "synthetic alerts and a fixed nine-case order",
            "three cases per explanation condition",
            "task responses are clustered within participants",
            "no real banking deployment or fraud-loss outcome",
        ],
    }
    return tasks_frame, {"summary": summary, "participants": participants_frame}


def write_outputs(
    tasks_frame: pd.DataFrame,
    analysis: dict[str, Any],
    tables_dir: Path,
    figures_dir: Path,
    summary_path: Path,
) -> None:
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)
    summary_path.parent.mkdir(parents=True, exist_ok=True)

    summary = analysis["summary"]
    participants: pd.DataFrame = analysis["participants"]

    accuracy_rows: list[dict[str, Any]] = []
    likert_rows: list[dict[str, Any]] = []
    routing_rows: list[dict[str, Any]] = []
    for condition, condition_summary in summary["condition_summaries"].items():
        for metric, values in condition_summary["accuracy"].items():
            accuracy_rows.append(
                {
                    "condition": condition,
                    "condition_label": condition_summary["label"],
                    "metric": metric,
                    **values,
                }
            )
        for metric, values in condition_summary["ratings"].items():
            likert_rows.append(
                {
                    "condition": condition,
                    "condition_label": condition_summary["label"],
                    "metric": metric,
                    **values,
                }
            )
        for action, count in condition_summary["routing_action_counts"].items():
            routing_rows.append(
                {
                    "condition": condition,
                    "condition_label": condition_summary["label"],
                    "routing_action": action,
                    "count": count,
                    "n": condition_summary["task_responses"],
                    "rate": count / condition_summary["task_responses"],
                }
            )

    preference_rows: list[dict[str, Any]] = []
    for question, values in summary["preferences"].items():
        for choice, result in values.items():
            preference_rows.append({"question": question, "choice": choice, **result})

    profile_rows: list[dict[str, Any]] = []
    for field, values in summary["participant_profile"].items():
        for category, count in values.items():
            profile_rows.append(
                {
                    "field": field,
                    "category": category,
                    "count": count,
                    "n": len(participants),
                    "rate": count / len(participants),
                }
            )

    pd.DataFrame(accuracy_rows).to_csv(
        tables_dir / "human_eval_accuracy.csv", index=False
    )
    pd.DataFrame(likert_rows).to_csv(
        tables_dir / "human_eval_likert.csv", index=False
    )
    pd.DataFrame(preference_rows).to_csv(
        tables_dir / "human_eval_preferences.csv", index=False
    )
    pd.DataFrame(profile_rows).to_csv(
        tables_dir / "human_eval_participant_profile.csv", index=False
    )
    pd.DataFrame(routing_rows).to_csv(
        tables_dir / "human_eval_routing.csv", index=False
    )

    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    _write_figure(pd.DataFrame(accuracy_rows), pd.DataFrame(likert_rows), figures_dir)
    _write_preference_figure(pd.DataFrame(preference_rows), figures_dir)


def _write_figure(
    accuracy: pd.DataFrame, likert: pd.DataFrame, figures_dir: Path
) -> None:
    condition_order = list(CONDITION_LABELS)
    labels = [CONDITION_LABELS[key] for key in condition_order]
    colours = ["#475569", "#2563EB", "#0F766E"]

    figure, axes = plt.subplots(1, 2, figsize=(12.8, 5.2), constrained_layout=True)

    accuracy_metrics = ["top_evidence", "direction", "evidence_count"]
    accuracy_labels = ["Top evidence", "Direction", "Evidence count"]
    x = np.arange(len(accuracy_metrics))
    width = 0.24
    for index, condition in enumerate(condition_order):
        values = (
            accuracy[accuracy["condition"] == condition]
            .set_index("metric")
            .loc[accuracy_metrics]
        )
        rate = values["rate"].to_numpy(dtype=float)
        yerr = np.vstack(
            [
                rate - values["ci95_lower"].to_numpy(dtype=float),
                values["ci95_upper"].to_numpy(dtype=float) - rate,
            ]
        )
        axes[0].bar(
            x + (index - 1) * width,
            rate,
            width,
            yerr=yerr,
            capsize=3,
            label=labels[index],
            color=colours[index],
        )
    axes[0].set_title("Evidence comprehension accuracy")
    axes[0].set_ylabel("Observed proportion")
    axes[0].set_ylim(0, 1.08)
    axes[0].set_xticks(x, accuracy_labels)
    axes[0].grid(axis="y", alpha=0.22)

    rating_metrics = ["clarity", "confidence", "enough_evidence", "mental_effort"]
    rating_labels = ["Clarity", "Confidence", "Enough evidence", "Mental effort"]
    x2 = np.arange(len(rating_metrics))
    for index, condition in enumerate(condition_order):
        values = (
            likert[likert["condition"] == condition]
            .set_index("metric")
            .loc[rating_metrics]
        )
        median = values["median"].to_numpy(dtype=float)
        yerr = np.vstack(
            [
                median - values["q1"].to_numpy(dtype=float),
                values["q3"].to_numpy(dtype=float) - median,
            ]
        )
        axes[1].bar(
            x2 + (index - 1) * width,
            median,
            width,
            yerr=yerr,
            capsize=3,
            label=labels[index],
            color=colours[index],
        )
    axes[1].set_title("Perceived explanation quality")
    axes[1].set_ylabel("Median Likert rating (1–5); IQR error bars")
    axes[1].set_ylim(0, 5.4)
    axes[1].set_xticks(x2, rating_labels)
    axes[1].grid(axis="y", alpha=0.22)

    handles, legend_labels = axes[0].get_legend_handles_labels()
    figure.legend(handles, legend_labels, loc="outside lower center", ncol=3, frameon=False)
    figure.suptitle("Interim human evaluation (n = 11 proxy reviewers; 99 case reviews)")
    figure.savefig(figures_dir / "human_eval_outcomes.png", dpi=220, bbox_inches="tight")
    plt.close(figure)


def _write_preference_figure(preferences: pd.DataFrame, figures_dir: Path) -> None:
    question_order = ["overall_clearest", "overall_preferred", "overall_trustworthy"]
    question_labels = ["Clearest overall", "Preferred first pass", "Most trustworthy"]
    choice_order = [
        "Raw reason codes",
        "Deterministic brief",
        "Guarded LLM brief",
        "No preference",
    ]
    colours = ["#475569", "#2563EB", "#0F766E", "#CBD5E1"]
    x = np.arange(len(question_order))
    width = 0.19

    figure, axis = plt.subplots(figsize=(9.8, 5.0), constrained_layout=True)
    for index, choice in enumerate(choice_order):
        subset = preferences[preferences["choice"] == choice].set_index("question")
        values = np.array(
            [float(subset.loc[q, "rate"]) if q in subset.index else 0.0 for q in question_order]
        )
        bars = axis.bar(
            x + (index - 1.5) * width,
            values,
            width,
            label=choice,
            color=colours[index],
        )
        axis.bar_label(
            bars,
            labels=[f"{round(value * 11):.0f}" if value else "" for value in values],
            padding=3,
            fontsize=9,
        )

    axis.set_title("Overall explanation-format preferences")
    axis.set_ylabel("Participant proportion (n = 11)")
    axis.set_ylim(0, 0.82)
    axis.set_xticks(x, question_labels)
    axis.grid(axis="y", alpha=0.22)
    axis.legend(loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=2, frameon=False)
    figure.savefig(
        figures_dir / "human_eval_preferences.png", dpi=220, bbox_inches="tight"
    )
    plt.close(figure)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", type=Path, default=DEFAULT_RAW)
    parser.add_argument("--form", type=Path, default=DEFAULT_FORM)
    parser.add_argument("--tables-dir", type=Path, default=DEFAULT_TABLES)
    parser.add_argument("--figures-dir", type=Path, default=DEFAULT_FIGURES)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    snapshot = json.loads(args.raw.read_text(encoding="utf-8"))
    form = json.loads(args.form.read_text(encoding="utf-8"))
    tasks_frame, analysis = build_analysis(snapshot, form)
    write_outputs(
        tasks_frame,
        analysis,
        tables_dir=args.tables_dir,
        figures_dir=args.figures_dir,
        summary_path=args.summary,
    )
    summary = analysis["summary"]
    print(
        "Human evaluation analysed: "
        f"{summary['participants_included']} included participants, "
        f"{summary['completed_case_reviews']} completed case reviews."
    )


if __name__ == "__main__":
    main()
