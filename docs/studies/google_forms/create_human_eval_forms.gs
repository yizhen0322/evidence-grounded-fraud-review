/**
 * Create one CLOSED Google Form for approximately 30 participants.
 * Every participant receives the same link and reviews the same nine cases.
 * The form remains closed until
 * openStudyAfterApproval('SUPERVISOR_APPROVED') is run by the project owner.
 */

const FORM_PAYLOAD = {
  "form_version": "single",
  "tasks": [
    {
      "slot": "S01",
      "participant_label": "Case 01",
      "source_case_id_sha256": "2536720a2dcdedf440c6ff3cc5b550ba5050f6e5463c51efeb2194ae1e5ab7aa",
      "condition": "raw_reason_codes",
      "risk_bucket": "High",
      "context": "Synthetic transaction alert. Relative review priority: High.",
      "explanation": "Ranked evidence:\n1. Terminal distance from customer home - raises risk - value bucket: far from home\n2. Amount vs customer 30-day average - raises risk - value bucket: above customer pattern\n3. Transaction amount - raises risk - value bucket: high",
      "evidence_options": [
        "Terminal distance from customer home",
        "Amount vs customer 30-day average",
        "Transaction amount"
      ],
      "top_evidence_expected": "Terminal distance from customer home",
      "top_direction_expected": "up",
      "named_evidence_count_expected": 3
    },
    {
      "slot": "S04",
      "participant_label": "Case 02",
      "source_case_id_sha256": "6fcc0adf929a69a919a25d7cf5a0c9e4957ca81455f0631441a98c330aec8e44",
      "condition": "deterministic_brief",
      "risk_bucket": "Medium",
      "context": "Synthetic transaction alert. Relative review priority: Medium.",
      "explanation": "This above-threshold synthetic alert has Medium relative review priority.\n1. Terminal distance from customer home raises risk; value bucket: far_from_home.\n2. Amount vs customer 30-day average raises risk; value bucket: above_customer_pattern.\n3. Transaction amount raises risk; value bucket: high.",
      "evidence_options": [
        "Terminal distance from customer home",
        "Amount vs customer 30-day average",
        "Transaction amount"
      ],
      "top_evidence_expected": "Terminal distance from customer home",
      "top_direction_expected": "up",
      "named_evidence_count_expected": 3
    },
    {
      "slot": "S07",
      "participant_label": "Case 03",
      "source_case_id_sha256": "370d7b9764d66f1dcf0c2e8ff07040b52680a389c583f8b6f0b9489963caf5cd",
      "condition": "guarded_llm_brief",
      "risk_bucket": "Low",
      "context": "Synthetic transaction alert. Relative review priority: Low.",
      "explanation": "All supplied signals raise risk, led by Terminal distance from customer home.",
      "evidence_options": [
        "Terminal distance from customer home",
        "Amount vs customer 30-day average",
        "Night-time transaction"
      ],
      "top_evidence_expected": "Terminal distance from customer home",
      "top_direction_expected": "up",
      "named_evidence_count_expected": 1
    },
    {
      "slot": "S02",
      "participant_label": "Case 04",
      "source_case_id_sha256": "edbd3f7bea3d520354d18c0e3e7931a4996a21e03f28dff360b3d75af820b2d3",
      "condition": "raw_reason_codes",
      "risk_bucket": "High",
      "context": "Synthetic transaction alert. Relative review priority: High.",
      "explanation": "Ranked evidence:\n1. Amount vs customer 30-day average - raises risk - value bucket: above customer pattern\n2. Terminal distance from customer home - raises risk - value bucket: far from home\n3. Transaction amount - raises risk - value bucket: high",
      "evidence_options": [
        "Amount vs customer 30-day average",
        "Terminal distance from customer home",
        "Transaction amount"
      ],
      "top_evidence_expected": "Amount vs customer 30-day average",
      "top_direction_expected": "up",
      "named_evidence_count_expected": 3
    },
    {
      "slot": "S05",
      "participant_label": "Case 05",
      "source_case_id_sha256": "2f336acf1986cba5a76102aaae5f3c6e117cb817b1a030b7f1de85860f49e324",
      "condition": "deterministic_brief",
      "risk_bucket": "Medium",
      "context": "Synthetic transaction alert. Relative review priority: Medium.",
      "explanation": "This above-threshold synthetic alert has Medium relative review priority.\n1. Amount vs customer 30-day average raises risk; value bucket: above_customer_pattern.\n2. Terminal distance from customer home raises risk; value bucket: regional.\n3. Transaction amount raises risk; value bucket: high.",
      "evidence_options": [
        "Amount vs customer 30-day average",
        "Terminal distance from customer home",
        "Transaction amount"
      ],
      "top_evidence_expected": "Amount vs customer 30-day average",
      "top_direction_expected": "up",
      "named_evidence_count_expected": 3
    },
    {
      "slot": "S08",
      "participant_label": "Case 06",
      "source_case_id_sha256": "d1f2c6db0f087cd4c1b18abe839e6a69bc133ddf722c6cfe2d8028e62204faf0",
      "condition": "guarded_llm_brief",
      "risk_bucket": "Low",
      "context": "Synthetic transaction alert. Relative review priority: Low.",
      "explanation": "All supplied signals raise risk, led by Amount vs customer 30-day average.",
      "evidence_options": [
        "Amount vs customer 30-day average",
        "Terminal distance from customer home",
        "Night-time transaction"
      ],
      "top_evidence_expected": "Amount vs customer 30-day average",
      "top_direction_expected": "up",
      "named_evidence_count_expected": 1
    },
    {
      "slot": "S03",
      "participant_label": "Case 07",
      "source_case_id_sha256": "7e0d40bc45672c4de7320f01c9699364614738664ea874e479b42d255c118997",
      "condition": "raw_reason_codes",
      "risk_bucket": "High",
      "context": "Synthetic transaction alert. Relative review priority: High.",
      "explanation": "Ranked evidence:\n1. Amount vs customer 30-day average - raises risk - value bucket: above customer pattern\n2. Terminal distance from customer home - raises risk - value bucket: regional\n3. Delayed terminal fraud rate - raises risk - value bucket: elevated",
      "evidence_options": [
        "Amount vs customer 30-day average",
        "Terminal distance from customer home",
        "Delayed terminal fraud rate"
      ],
      "top_evidence_expected": "Amount vs customer 30-day average",
      "top_direction_expected": "up",
      "named_evidence_count_expected": 3
    },
    {
      "slot": "S06",
      "participant_label": "Case 08",
      "source_case_id_sha256": "f1e643eca99a815d9d0b2449fcca3f988c1d9ef9690013328d845b46de90f479",
      "condition": "deterministic_brief",
      "risk_bucket": "Medium",
      "context": "Synthetic transaction alert. Relative review priority: Medium.",
      "explanation": "This above-threshold synthetic alert has Medium relative review priority.\n1. Terminal distance from customer home raises risk; value bucket: far_from_home.\n2. Amount vs customer 30-day average raises risk; value bucket: above_customer_pattern.\n3. Night-time transaction raises risk; value bucket: yes.",
      "evidence_options": [
        "Terminal distance from customer home",
        "Amount vs customer 30-day average",
        "Night-time transaction"
      ],
      "top_evidence_expected": "Terminal distance from customer home",
      "top_direction_expected": "up",
      "named_evidence_count_expected": 3
    },
    {
      "slot": "S09",
      "participant_label": "Case 09",
      "source_case_id_sha256": "ff1f36201bee2af76e8262347f439866de13c32b6f44502513214d473d657a1b",
      "condition": "guarded_llm_brief",
      "risk_bucket": "Low",
      "context": "Synthetic transaction alert. Relative review priority: Low.",
      "explanation": "All supplied signals raise risk, led by Terminal distance from customer home.",
      "evidence_options": [
        "Terminal distance from customer home",
        "Amount vs customer 30-day average",
        "Night-time transaction"
      ],
      "top_evidence_expected": "Terminal distance from customer home",
      "top_direction_expected": "up",
      "named_evidence_count_expected": 1
    }
  ]
};
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
