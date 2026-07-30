# Design System — Fraud Review Workbench

## Product context

- **What this is:** A local analyst decision-support prototype backed by immutable, provenance-verified fraud-model evidence.
- **Who it is for:** A single fraud analyst, with model-risk reviewers and FYP examiners as secondary users.
- **Project type:** Dense desktop operational workbench with a separate assurance area.
- **Memorable quality:** This feels like a system an analyst works in every day, not a model demonstration page.
- **Default experience:** S0 operational simulation cases with readable evidence and a visible deterministic-versus-local-LLM comparison. ULB remains available as the real-data detector benchmark in the same application.

## Aesthetic direction

- **Direction:** Industrial/utilitarian.
- **Decoration:** Minimal and functional.
- **Mood:** Calm, exact, evidence-led, and operational. The interface should look trustworthy because states and boundaries are explicit, not because it imitates enterprise marketing.

## Typography

- **UI/body:** `Avenir Next`, `Avenir`, `Segoe UI`, sans-serif.
- **Data/code:** `SFMono-Regular`, `Consolas`, `Liberation Mono`, monospace.
- **Scale:** 12px metadata, 13px table/body, 15–16px section headings, 22–26px page headings.
- **Numbers:** Use tabular numerals for scores, metrics, revisions, and case IDs.

## Colour

- **Navigation:** `#111A23`.
- **Canvas:** `#F1F3F4`.
- **Surface:** `#FFFFFF`.
- **Primary ink:** `#17212B`.
- **Muted ink:** `#64717D`.
- **Border:** `#D5DBE0`.
- **Action blue:** `#1F67D2`.
- **Success:** `#267A55`.
- **Warning:** `#A66A16`.
- **Danger/high risk:** `#B83A36`.
- **Informational decrease:** `#2E6FA3`.

Colour is semantic. No gradients or decorative multi-colour surfaces.

## Spacing and density

- **Base unit:** 4px.
- **Density:** Compact but readable.
- **Scale:** 4, 8, 12, 16, 20, 24, 32, 40px.
- Queue at 1440×900 should show at least 10 rows without shrinking text below 12px.

## Layout

- **Shell:** 232px side rail, compact top command bar, full-width work canvas.
- **Operations:** table-first queue and evidence-first investigation workspace.
- **Investigation:** flexible evidence column plus 340–380px sticky decision rail.
- **Assurance:** controlled two-column test workspace and recorded metric tables.
- **Radius:** 3px controls, 4px panels, full radius only for tiny status dots.
- **Borders/shadows:** 1px borders; shadows only for drawers and elevated overlays.

## Motion

- **Approach:** Minimal-functional.
- 120–180ms state and route transitions.
- Drawer slide and row/selection feedback only.
- Respect `prefers-reduced-motion`.

## Component rules

- Cards exist only when the region is independently interactive.
- Operational counts use a ledger/strip, not a card mosaic.
- Page headings are compact and task-oriented.
- Risk and workflow state always have text labels.
- No fake alerts, avatars, merchants, maps, monetary savings, or SLA counters.
- Guardrail checks collapse to a concise assurance summary in the analyst workspace; detailed checks remain available on demand.

## Decisions log

| Date | Decision | Rationale |
|---|---|---|
| 2026-07-14 | Split immutable evidence from mutable local workflow metadata | Makes the prototype operational without contaminating experiment artifacts. |
| 2026-07-14 | Operations and Model Assurance are separate navigation groups | Keeps analyst work primary while preserving the research contribution. |
| 2026-07-14 | Historical ground truth is excluded from operational APIs and screens | Prevents hindsight leakage and makes the workflow credible. Aggregate retrospective results remain in Model Assurance. |
| 2026-07-26 | S0 is the default operational and semantic evaluation context; ULB remains the detector benchmark | Readable S0 evidence makes the local-LLM contract observable without weakening the real-data detector evidence or comparing incompatible score scales. |
