# Dashboard Visual Direction

## Visual thesis

A projector-safe fraud investigation console: pale slate canvas, crisp white evidence surfaces, dark navy typography, one cobalt interaction accent, and restrained red/blue semantic signals that make the evidence chain feel auditable rather than promotional.

## Content plan

1. **Global shell:** show Recorded or Live Replay mode, artifact readiness, Ollama state, current case, navigation, and provenance access without competing with the investigation content.
2. **Case Queue:** start directly with curated scenarios, deterministic filters, and the flagged-case table; the dominant action is opening a case.
3. **Investigation:** connect detector outcome, top recorded SHAP contributions, reason codes, narrative checks, fallback, and the exact minimized LLM payload in a single 60/40 workspace.
4. **Guardrail Lab:** make one controlled mutation at a time, compare original and tampered text, then reveal the real validator result and deterministic fallback.
5. **Results:** separate detector performance from explanation/faithfulness evidence and keep provenance visible beside every recorded source.
6. **Provenance drawer:** provide run IDs, manifest hashes, source compatibility, and recorded/live wording without exposing local filesystem paths.

## Interaction thesis

1. Route changes and selected rows use a short shared-position highlight so the examiner never loses orientation.
2. Recorded-to-live transitions replace only the narrative workspace, with a restrained fade/slide and a persistent `Demo-only; not a reported G5 result` banner.
3. Guardrail demonstrations reveal the mutation, failed checks, and fallback in a short ordered sequence; reduced-motion mode removes movement while preserving the same state order and announcements.

## Restraint rules

- Use layout, dividers, tables, and typography before cards or shadows.
- Use one interaction accent; red, blue, green, and amber remain semantic only.
- Never use colour as the sole status cue.
- Avoid hero copy, marketing claims, decorative gradients, external assets, and non-functional animation.
- Optimize first for a 1280×720 projector view and keyboard-driven demo flow.
