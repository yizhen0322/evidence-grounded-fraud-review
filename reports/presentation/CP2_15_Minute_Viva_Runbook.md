# CP2 15-Minute Viva Runbook

Project: **Evidence-Grounded Local-LLM Explanations for Credit Card Fraud Alert Review**  
Student: **Ng Yi Zhen (23076003)**  
Format: **12 slides + live system demonstration within 15 minutes**

## 1. Hard timing rule

- Target finish: **14:20**.
- Absolute stop: **15:00**.
- Slides: approximately **10 minutes 20 seconds**.
- Live demonstration: approximately **3 minutes 20 seconds**.
- Transition and contingency reserve: approximately **1 minute 20 seconds**.
- Do not read every bullet. State one conclusion per slide and use the visual as evidence.
- If delayed by more than 45 seconds, skip the detailed detector-group explanation on Slide 6 and the individual human-pilot percentages on Slide 11.

## 2. Timed presentation sequence

| Clock | Duration | Screen | Main point to say |
|---|---:|---|---|
| 0:00-0:35 | 0:35 | Slide 1 | The detector and SHAP provide evidence; the local LLM is optional; deterministic checks decide what reaches the analyst. |
| 0:35-1:20 | 0:45 | Slide 2 | Readability is not faithfulness. The research problem is safe explanation delivery, not unrestricted text generation. |
| 1:20-2:10 | 0:50 | Slide 3 | The gap is the evaluated combination of local execution, deterministic validation, fail-closed fallback, and separate raw-versus-delivered measurement. |
| 2:10-2:55 | 0:45 | Slide 4 | ULB and S0 have different evidence roles but test the same delivery boundary; their detector scores are not compared. |
| 2:55-3:45 | 0:50 | Slide 5 | Evidence is frozen before generation: split, train, select, persist SHAP reason codes, minimise the LLM payload, then validate or fall back. |
| 3:45-4:45 | 1:00 | Slide 6 | No detector dominates. G6 supports the explanation chain because of its AP, precision, and false-positive profile; it is not an algorithmic novelty claim. |
| 4:45-5:45 | 1:00 | Slide 7 | The same raw candidate is measured under OFF policy and gated under ON policy. Rejection is visible; it is not hidden by a normaliser. |
| 5:45-6:55 | 1:10 | Slide 8 | Strict prompting reduced raw violations, deterministic checks caught recorded failures, and fallback controlled delivery. State the manual-audit bound honestly. |
| 6:55-7:20 | 0:25 | Slide 9 | The application is operational proof that the evidence boundary survives analyst workflow. Transition immediately into the demo. |
| 7:20-10:40 | 3:20 | Live demo | Queue -> recorded fallback case -> controlled direction-flip test -> deterministic fallback. |
| 10:40-11:35 | 0:55 | Slide 10 | The LLM shortened articulation but reduced evidence coverage; it did not create new fraud knowledge. |
| 11:35-12:30 | 0:55 | Slide 11 | Preference did not guarantee comprehension or trust. The pilot supports a bounded usability discussion only. |
| 12:30-13:35 | 1:05 | Slide 12 | Generated text remains untrusted until checked. Summarise detector, guardrail, LLM role, workbench, and limitations. |
| 13:35-14:20 | 0:45 | Closing reserve | Finish the final sentence, recover from any transition delay, and return to the title or conclusion slide. |
| 14:20-15:00 | 0:40 | Safety reserve | Do not add new content. Use only if the live page or slide switching was slow. |

## 3. Exact live-demo route

Keep the app open at:

`http://127.0.0.1:8000/queue?source=operational`

Use the recorded fallback transaction:

- Case ID: `3069170327433504`
- Display ID: `TX00045057`
- Direct case URL: `http://127.0.0.1:8000/operational/cases/3069170327433504`
- Assurance URL: `http://127.0.0.1:8000/assurance/narratives?mode=operational&case_id=3069170327433504`

Do **not** use the legacy `/cases/3069170327433504` URL. That route is for the ULB research evidence lane and will not load the S0 operational case correctly.

## 4. Live-demo script and clicks

### 7:20-7:50 — Queue (30 seconds)

Action:

1. Switch from Slide 9 to the browser.
2. Show the source-labelled queue.
3. Point to the S0 operational cases, ULB supporting benchmark, and fallback count.

Say:

> This is one analyst-facing system, but the evidence sources remain labelled. S0 is the primary readable explanation queue, while ULB remains supporting real-data benchmark evidence. Their rankings are never merged. I will open a recorded S0 case where the generated candidate failed the delivery contract.

### 7:50-9:05 — Recorded fallback case (75 seconds)

Action:

1. Open transaction `TX00045057`, or use the direct operational case URL.
2. Show the four adjacent panels: raw SHAP reason codes, deterministic brief, guarded local-LLM candidate, and delivered analyst brief.
3. Point to `Structured evidence retained: 1/3` and the failed validation status.
4. Point to the deterministic fallback that actually reached the analyst.
5. Briefly show the minimised payload; do not scroll through every field.

Say:

> The left side is the frozen model evidence. Ollama receives only the risk bucket and structured reason-code fields, not the raw transaction, fraud label, probability, or SHAP magnitude. The generated candidate is kept for measurement. In this case it retained only one of three evidence items and failed the contract. The candidate remains visible as a failure record, but it does not become the official brief. The analyst receives the deterministic evidence-derived fallback instead.

### 9:05-10:20 — Controlled assurance test (75 seconds)

Action:

1. Click **Open Explanation Assurance**.
2. Keep **Direction flip** selected.
3. Click **Run assurance test**.
4. Point to the modified direction, the failed Direction check, and `Rejected -> fallback active`.

Say:

> This page calls the same validator used in the recorded experiment. I am reversing one contribution direction. The modified candidate still looks structurally plausible, but the direction check compares it with the stored evidence, rejects it, and activates fallback. The controlled mutation is temporary and does not alter the recorded case artifacts.

### 10:20-10:40 — Return to slides (20 seconds)

Say:

> This is the practical value of the local LLM layer: it may provide a shorter articulation, but it never receives authority to create or replace evidence. I will now return to the measured benefits and limitations.

Return to Slide 10.

## 5. What not to demonstrate

- Do not train a model during the viva.
- Do not open source code unless an examiner asks.
- Do not spend presentation time on the full Results page; Slides 6, 8, 10, and 11 already report the results more clearly.
- Do not compare S0 and ULB risk scores or ranks.
- Do not use a random case; the recorded fallback case gives a deterministic, rehearsable outcome.
- Do not make live Ollama regeneration the critical path. The recorded candidate and validator path are sufficient to demonstrate the contribution.
- Do not edit analyst workflow state during the main demo. It adds time but does not strengthen the research claim.

## 6. Demo preflight

Run from the repository root:

```bash
uv run python tools/validate_dashboard.py --config configs/dashboard.yaml
uv run python -m app.backend.server --config configs/dashboard.yaml
```

Before presenting, verify:

- `http://127.0.0.1:8000/api/v1/health` reports `status: ready`.
- `artifact_ready` is `true`.
- Ollama shows `available` with `llama3:8b` if live generation may be discussed.
- The queue and direct operational case URL both load.
- The direction-flip assurance test returns a Direction failure and deterministic fallback.
- Browser zoom is suitable for the projector.
- Notifications are disabled and unrelated tabs are closed.

## 7. Failure-safe presentation plan

### If Ollama is unavailable

Continue normally. Say:

> The generation service is currently unavailable, so the system preserves the verified evidence and uses deterministic fallback. This is the intended fail-closed availability behaviour, not a loss of the detector evidence.

### If the server is unavailable

Use the slide screenshots and explain the same three states: stored evidence, rejected candidate, delivered fallback. Keep a PDF copy of the slides and a screenshot of the fallback case locally.

### If time is running out

- End the demo immediately after the Direction check fails.
- Give only the headline on Slide 10.
- On Slide 11 say only: `Preference improved, but comprehension did not.`
- Finish Slide 12 with the final policy sentence.

## 8. Final closing sentence

> The safest conclusion from this project is that generated fraud-alert text should remain untrusted until deterministic checks confirm that it matches the approved model evidence; otherwise, the system should fail closed and deliver an evidence-derived fallback.

## 9. Slide-review actions before the final viva

1. Use the detector-results visual that includes F1 standard-deviation error bars, grouped precision-recall bars, and false-positive/false-negative bars. The verified local PPT deck already contains these; the Canva version should not use a simpler F1 chart without error bars.
2. Treat Slide 9 as a transition into the live demonstration rather than describing every application feature.
3. On Slide 10, prefer the precise headline `The LLM shortened articulation but reduced evidence coverage` over wording that could imply a general improvement.
4. Check body text from the back of a classroom. Slides 6 and 8 should be explained from the headline metrics rather than read line by line.
