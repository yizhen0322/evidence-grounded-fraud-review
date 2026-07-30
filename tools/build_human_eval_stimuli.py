"""Build a frozen single-form human-evaluation survey from the sealed S0 run.

The generated Google Forms remain closed to responses. Recruitment is outside
this script and remains gated by supervisor or ethics approval.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Any


DEFAULT_RUN = Path("experiments/runs/2026-07-26_s0_seed42")
DEFAULT_OUTPUT = Path("experiments/human_eval/draft_v1")
DEFAULT_APPS_SCRIPT = Path("docs/studies/google_forms/create_human_eval_forms.gs")

SELECTED_CASE_IDS = (
    "2365335092145894",
    "398564556210690",
    "50813004217433",
    "940801767539837",
    "1353086321996688",
    "4272573758717631",
    "651018576137270",
    "251280897846142",
    "3008127019169509",
)

CONDITION_ASSIGNMENT = (
    ("raw_reason_codes",) * 3
    + ("deterministic_brief",) * 3
    + ("guarded_llm_brief",) * 3
)

# Interleave the three conditions so participants do not receive one long block
# of the same presentation format.
FORM_ORDER = (0, 3, 6, 1, 4, 7, 2, 5, 8)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines() if line]


def case_hash(case_id: str) -> str:
    return hashlib.sha256(case_id.encode("utf-8")).hexdigest()


def raw_reason_text(reasons: list[dict[str, Any]]) -> str:
    lines = ["Ranked evidence:"]
    for reason in reasons:
        direction = "raises risk" if reason["direction"] == "up" else "reduces risk"
        value = str(reason["value_bucket"]).replace("_", " ")
        lines.append(
            f'{reason["rank"]}. {reason["display_label"]} - {direction} - '
            f"value bucket: {value}"
        )
    return "\n".join(lines)


def build_stimuli(run_dir: Path) -> list[dict[str, Any]]:
    cases = {str(row["case_id"]): row for row in read_jsonl(run_dir / "semantic_cases.jsonl")}
    explanations = {
        str(row["case_id"]): row
        for row in read_jsonl(run_dir / "explanation_comparison.jsonl")
    }
    stimuli: list[dict[str, Any]] = []
    for index, case_id in enumerate(SELECTED_CASE_IDS, start=1):
        case = cases[case_id]
        explanation = explanations[case_id]
        if explanation["fallback"]:
            raise ValueError(f"selected main-study case uses fallback: {case_id}")
        reasons = case["reason_codes"]
        if len(reasons) != 3:
            raise ValueError(f"expected three reason codes: {case_id}")
        stimuli.append(
            {
                "slot": f"S{index:02d}",
                "participant_label": f"Case {index:02d}",
                "source_case_id": case_id,
                "source_case_id_sha256": case_hash(case_id),
                "risk_bucket": case["risk_bucket"],
                "context": (
                    "Synthetic transaction alert. Relative review priority: "
                    f'{case["risk_bucket"]}.'
                ),
                "top_evidence": reasons[0]["display_label"],
                "top_direction": reasons[0]["direction"],
                "evidence_options": [reason["display_label"] for reason in reasons],
                "raw_reason_codes": raw_reason_text(reasons),
                "deterministic_brief": explanation["deterministic_brief"],
                "guarded_llm_brief": explanation["guarded_llm_brief"],
            }
        )
    return stimuli


def form_payload(stimuli: list[dict[str, Any]]) -> dict[str, Any]:
    tasks = []
    for display_index, slot_index in enumerate(FORM_ORDER, start=1):
        source = stimuli[slot_index]
        condition = CONDITION_ASSIGNMENT[slot_index]
        tasks.append(
            {
                "slot": source["slot"],
                "participant_label": f"Case {display_index:02d}",
                "source_case_id_sha256": source["source_case_id_sha256"],
                "condition": condition,
                "risk_bucket": source["risk_bucket"],
                "context": source["context"],
                "explanation": source[condition],
                "evidence_options": source["evidence_options"],
                "top_evidence_expected": source["top_evidence"],
                "top_direction_expected": source["top_direction"],
                "named_evidence_count_expected": (
                    1 if condition == "guarded_llm_brief" else len(source["evidence_options"])
                ),
            }
        )
    return {"form_version": "single", "tasks": tasks}


def write_admin_manifest(path: Path, stimuli: list[dict[str, Any]]) -> None:
    fields = [
        "slot",
        "participant_label",
        "source_case_id",
        "source_case_id_sha256",
        "risk_bucket",
        "top_evidence",
        "top_direction",
    ]
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(stimuli)


def apps_script_source(payload: dict[str, Any]) -> str:
    embedded = json.dumps(payload, ensure_ascii=True, indent=2)
    return '''/**
 * Create one CLOSED Google Form for approximately 30 participants.
 * Every participant receives the same link and reviews the same nine cases.
 * The form remains closed until
 * openStudyAfterApproval('SUPERVISOR_APPROVED') is run by the project owner.
 */

const FORM_PAYLOAD = ''' + embedded + r''';
const STUDY_FOLDER_NAME = 'FYP Human Evaluation - 2026-07-27';
const TARGET_COMPLETED = 30;

function createHumanEvaluationDraft() {
  const properties = PropertiesService.getScriptProperties();
  if (properties.getProperty('FORM_ID')) {
    return getStudyStatus();
  }

  const folder = getOrCreateStudyFolder_();
  const consent = `You are invited to take part in a short undergraduate final-year project study at Sunway University. The study compares how people understand three explanation formats for synthetic fraud-alert cases. No real bank customers, cards, or live payment data are used. Participation is voluntary. You may stop before submission by closing the browser. Do not enter your name, student ID, email address, phone number, or another identifier. Responses will be reported only in aggregate. By selecting Yes, you confirm that you are at least 18 years old, have read this information, and voluntarily agree to participate.`;
  const form = FormApp.create('Synthetic Fraud Alert Explanation Study', false)
    .setDescription(consent)
    .setCollectEmail(false)
    .setLimitOneResponsePerUser(false)
    .setAllowResponseEdits(false)
    .setShowLinkToRespondAgain(false)
    .setShuffleQuestions(false)
    .setProgressBar(true)
    .setPublishingSummary(false)
    .setConfirmationMessage('Thank you. Your anonymous response has been recorded. All cases were synthetic and all explanation formats came from the same detector evidence.');
  form.setAcceptingResponses(false);

  addConsentAndBackground_(form);
  addPracticeCase_(form);
  form.addPageBreakItem()
    .setTitle('Study cases')
    .setHelpText('Review each synthetic alert using only the explanation shown. This is not a test of professional fraud-investigation ability.');
  FORM_PAYLOAD.tasks.forEach((task) => addTask_(form, task));
  addOverallComparison_(form);

  const responseSheet = SpreadsheetApp.create('FYP Human Evaluation Responses');
  form.setDestination(FormApp.DestinationType.SPREADSHEET, responseSheet.getId());
  DriveApp.getFileById(form.getId()).setName('FYP Human Evaluation Form').moveTo(folder);
  DriveApp.getFileById(responseSheet.getId()).moveTo(folder);

  properties.setProperties({
    FORM_ID: form.getId(),
    FORM_URL: form.getPublishedUrl(),
    FORM_EDIT_URL: form.getEditUrl(),
    RESPONSE_SHEET_ID: responseSheet.getId(),
  });

  properties.setProperties({
    STUDY_OPEN: 'false',
    TARGET_COMPLETED: String(TARGET_COMPLETED),
  });
  Logger.log(JSON.stringify(getStudyStatus(), null, 2));
  return getStudyStatus();
}

function openStudyAfterApproval(confirmation) {
  if (confirmation !== 'SUPERVISOR_APPROVED') {
    throw new Error("Approval confirmation required: openStudyAfterApproval('SUPERVISOR_APPROVED')");
  }
  getForm_().setAcceptingResponses(true);
  PropertiesService.getScriptProperties().setProperty('STUDY_OPEN', 'true');
  return getStudyStatus();
}

function closeStudy() {
  getForm_().setAcceptingResponses(false);
  PropertiesService.getScriptProperties().setProperty('STUDY_OPEN', 'false');
  return getStudyStatus();
}

function getStudyStatus() {
  const properties = PropertiesService.getScriptProperties();
  const id = properties.getProperty('FORM_ID');
  const form = id ? FormApp.openById(id) : null;
  const sheetId = properties.getProperty('RESPONSE_SHEET_ID');
  return {
    studyOpen: properties.getProperty('STUDY_OPEN') === 'true',
    targetCompleted: TARGET_COMPLETED,
    form: form ? {
      created: true,
      acceptingResponses: form.isAcceptingResponses(),
      responseCount: form.getResponses().length,
      editUrl: form.getEditUrl(),
      publishedUrl: form.getPublishedUrl(),
      responseSheetUrl: sheetId ? SpreadsheetApp.openById(sheetId).getUrl() : null,
    } : {created: false},
  };
}

function getOrCreateStudyFolder_() {
  const properties = PropertiesService.getScriptProperties();
  const existing = properties.getProperty('STUDY_FOLDER_ID');
  if (existing) return DriveApp.getFolderById(existing);
  const folder = DriveApp.createFolder(STUDY_FOLDER_NAME);
  properties.setProperty('STUDY_FOLDER_ID', folder.getId());
  return folder;
}

function getForm_() {
  const id = PropertiesService.getScriptProperties().getProperty('FORM_ID');
  if (!id) throw new Error('The study form has not been created.');
  return FormApp.openById(id);
}

function addConsentAndBackground_(form) {
  const consent = form.addMultipleChoiceItem()
    .setTitle('I confirm that I am at least 18 years old, have read the information above, and voluntarily agree to participate.')
    .setRequired(true);
  const background = form.addPageBreakItem().setTitle('Background');
  consent.setChoices([
    consent.createChoice('Yes, I agree', background),
    consent.createChoice('No, I do not agree', FormApp.PageNavigationType.SUBMIT),
  ]);
  addChoice_(form, 'Which area best describes your current study or work background?', ['Computing / IT', 'Business / finance / accounting', 'Other STEM', 'Other non-STEM', 'Prefer not to say']);
  addChoice_(form, 'How familiar are you with machine learning?', ['None', 'Basic', 'Intermediate', 'Advanced']);
  addChoice_(form, 'How familiar are you with fraud detection?', ['None', 'Basic', 'Intermediate', 'Advanced']);
  addChoice_(form, 'Have you used SHAP or feature-attribution explanations before?', ['Yes', 'No', 'Not sure']);
}

function addPracticeCase_(form) {
  form.addPageBreakItem().setTitle('Practice case').setHelpText(
    'Synthetic transaction alert. Relative review priority: Medium.\n\nRanked evidence:\n1. Example evidence A - raises risk\n2. Example evidence B - reduces risk\n3. Example evidence C - raises risk'
  );
  addChoice_(form, 'Practice — Which evidence item was ranked first?', ['Example evidence A', 'Example evidence B', 'Example evidence C', 'Not clear']);
  addChoice_(form, 'Practice — Did the first-ranked evidence raise or reduce risk?', ['Raised risk', 'Reduced risk', 'Not clear']);
  addScale_(form, 'Practice — The explanation was easy to understand.', 'Strongly disagree', 'Strongly agree');
}

function addOverallComparison_(form) {
  form.addPageBreakItem().setTitle('Overall comparison');
  const formats = ['Raw reason codes', 'Deterministic brief', 'Guarded LLM brief', 'No preference'];
  addChoice_(form, 'Which explanation format was clearest overall?', formats);
  addChoice_(form, 'Which format would you prefer for a first-pass synthetic alert review?', formats);
  addChoice_(form, 'Which explanation format felt most trustworthy?', formats);
  form.addParagraphTextItem().setTitle('Briefly explain your preference.').setRequired(false);
  form.addPageBreakItem().setTitle('Debrief').setHelpText('All cases were synthetic. All three formats came from the same ranked model evidence. The LLM was constrained and validated; invalid output falls back to deterministic text. This study does not evaluate real fraud-investigation skill.');
}

function addChoice_(form, title, choices) {
  return form.addMultipleChoiceItem().setTitle(title).setChoiceValues(choices).setRequired(true);
}

function addScale_(form, title, lowLabel, highLabel) {
  return form.addScaleItem().setTitle(title).setBounds(1, 5).setLabels(lowLabel, highLabel).setRequired(true);
}

function addTask_(form, task) {
  const prefix = `${task.participant_label} — `;
  form.addPageBreakItem()
    .setTitle(task.participant_label)
    .setHelpText(`${task.context}\n\n${task.explanation}`);
  addChoice_(form, prefix + 'Which evidence item was ranked first?', task.evidence_options.concat(['Not clear']));
  addChoice_(form, prefix + 'Did the first-ranked evidence raise or reduce risk?', ['Raised risk', 'Reduced risk', 'Not clear']);
  addChoice_(form, prefix + 'How many distinct evidence items were explicitly named in the explanation?', ['1', '2', '3', 'Not clear']);
  addChoice_(form, prefix + 'What provisional routing action would you choose?', ['Escalate for investigation', 'Close without escalation', 'Request more information']);
  addScale_(form, prefix + 'How confident are you in that routing action?', 'Very low', 'Very high');
  addScale_(form, prefix + 'The explanation was easy to understand.', 'Strongly disagree', 'Strongly agree');
  addScale_(form, prefix + 'The explanation gave enough evidence for a provisional routing action.', 'Strongly disagree', 'Strongly agree');
  addScale_(form, prefix + 'The explanation felt mentally effortful to use.', 'Strongly disagree', 'Strongly agree');
  form.addParagraphTextItem().setTitle(prefix + 'Optional: What, if anything, was unclear?').setRequired(false);
}
'''


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path, default=DEFAULT_RUN)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--apps-script", type=Path, default=DEFAULT_APPS_SCRIPT)
    args = parser.parse_args()

    stimuli = build_stimuli(args.run_dir)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_admin_manifest(args.output_dir / "stimuli_admin_manifest.csv", stimuli)
    for stale_path in args.output_dir.glob("form_v*.json"):
        stale_path.unlink()
    payload = form_payload(stimuli)
    (args.output_dir / "form.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    )
    args.apps_script.parent.mkdir(parents=True, exist_ok=True)
    args.apps_script.write_text(apps_script_source(payload))
    print(f"wrote {len(stimuli)} stimuli and one closed form payload")


if __name__ == "__main__":
    main()
