# Architecture Overview

## Final Tech Stack

Python + Streamlit, as planned. Detection is a hybrid of one ML model and several regex/validation detectors — not the original all-regex plan.

**Key libraries:** `streamlit`, `spacy` (+ its `en_core_web_sm` model, installed directly from a wheel URL in `requirements.txt`). No `pandas`/`plotly` (unused, removed early). No `transformers`/`torch` — see below for why that combination was tried and dropped.

## Folder Structure

```
src/
├── engine.py         # PrivacyAuditorEngine: NER-based NAME detection,
│                     # regex/validation detectors for every other category,
│                     # overlap resolution, inline highlight rendering, redaction
app.py                # Streamlit UI: input, highlighted preview, findings panel, redacted output
test_cases.py         # 16 labeled fictional test cases; strict category assertions
                      # plus precision/recall/F1 computation (evaluate_metrics())
model_card.md         # Model choice, rationale, and the BERT→spaCy swap story
```

Simpler than the `detectors/` package sketched in `planning.md` — one file was sufficient at this size.

## Detection Design

`PrivacyAuditorEngine.audit_text()` runs every detector and returns finding dicts: `{start, end, category, value, reason, source}`.

**Names (ML-driven, the core linguistic category)** — spaCy's `en_core_web_sm` NER pipeline detects `PERSON` entities, mapped to the `NAME` category. This is the one category assigned to the model rather than regex, because recognizing a name requires understanding sentence structure, not matching a fixed pattern.

**Everything else (regex + validation, supporting the model per the brief's own guidance):**
- **Contact info** — email/phone regex.
- **Government/financial identifiers** — SSN via the standard dashed format, plus a bare 9-digit pattern gated on a nearby keyword (`SSN`, `social security`) within a 30-character window, to avoid flagging unrelated 9-digit numbers. Credit cards match a 13–16 digit pattern and are validated with a **Luhn checksum**; only checksum-valid numbers are flagged.
- **Credentials** — keyword-anchored regex (`password`, `api_key`, `secret`, `token`, `access_key`) whose captured value must pass a **Shannon entropy check** (`> 3.0`), so low-entropy placeholders like `password='password'` don't false-positive.
- **Medical info** — phrase-anchored regex (`diagnosed with`, `tested positive for`, etc.) rather than bare keywords, so incidental mentions ("clinic newsletter covers asthma awareness") don't trigger.
- **Employee/client/volunteer info** — ID-code regex (`EMP-#####`, `VOL-#####`, etc.), matching the format shown in the hackathon orientation materials.
- **Confidential organizational info** — keyword triggers (`confidential`, `internal only`, `acquisition`, `roadmap`, etc.).

**Overlap resolution** — all findings, ML and regex alike, are sorted by start position (longest match wins ties), then kept only if they don't overlap a previously accepted finding.

**From match to UI** — the same finding list feeds three things: `highlight_html()` (in-place colored `<mark>` spans over the original text), the findings panel (category + reason cards), and `redact_text()` (back-to-front placeholder substitution so earlier redactions don't shift later offsets).

## AI Integration Design — including a real production issue and how it was resolved

**Original choice: `dslim/bert-base-NER`.** A BERT-base transformer via Hugging Face `transformers` + PyTorch, chosen for accuracy and for entity types (`PER`, `ORG`) that mapped onto both the NAME and CONFIDENTIAL_INFO categories. It ran correctly in local development and passed the full test suite there.

**What broke on deployment.** After deploying to Streamlit Community Cloud, the live app returned zero NAME findings on every input — including cases that worked locally. Because the engine is designed to fail soft (an ML load failure shouldn't crash the whole tool), this produced no visible error to the user; the app just silently behaved as if the model wasn't there. The most likely cause: `bert-base-NER` plus PyTorch's runtime is roughly 500MB+, which is tight against Streamlit Community Cloud's free-tier memory ceiling — the model most likely failed to load during the app's cold start.

**The fix.** Swapped to spaCy's `en_core_web_sm` — a ~12MB pipeline with no `torch` dependency, installed directly as a wheel in `requirements.txt` so it doesn't need a runtime download call. Local re-testing after the swap: 15/16 labeled cases correct, precision 1.000, recall 0.933, F1 0.966. Redeployed and manually verified live: the NAME category now correctly appears in the deployed app's findings.

**A design decision that came out of this swap:** the original engine also mapped BERT's `ORG` entity type to `CONFIDENTIAL_INFO`. Evaluation surfaced a false positive — the model tagging the literal word "SSN" as an organization. Rather than keep chasing that mapping (e.g., with a confidence threshold, which was tried and reverted because it also suppressed a correct NAME detection in the same test case, trading recall for no clean precision gain), the `ORG→CONFIDENTIAL_INFO` mapping was dropped entirely. `CONFIDENTIAL_INFO` is handled solely by keyword regex now, which turned out to be more precise for that category anyway.

**Privacy tradeoff.** No text is sent to any external API at inference time — both the original and replacement models run locally/on-device. This was a deliberate constraint from the start: a privacy tool that phones a third-party AI service to check whether text is sensitive would undermine its own purpose, beyond also being a paid-service dependency this project intentionally avoided.

## What Changed From the Plan

- **`planning.md` originally proposed a fully regex/keyword-based engine** with no ML model. Partway through, hackathon orientation materials clarified that ML-driven detection was a hard requirement, not optional — the engine was restructured so NER does the core work for the NAME category, with regex supporting every structured category, matching the brief's explicit guidance.
- **Model choice changed mid-build, in production, not in the plan.** `dslim/bert-base-NER` → `en_core_web_sm` after the free-tier deployment revealed a real memory-constraint failure that local testing hadn't caught. This is arguably the most important lesson from the build: passing tests locally doesn't guarantee correct behavior once deployed under a hosting platform's real resource limits, and a fail-soft design without visible error surfacing can hide exactly this kind of bug until it's manually checked live.
- **Bare/unformatted SSN detection and the employee-ID/confidential-keyword categories** were added after the initial four-category build, once time allowed pushing past the Tier 1 minimum.
- **Test suite evolved from pass/fail counting to strict per-category assertion plus precision/recall/F1**, after an early version of the suite was found to consider a wrong-category finding a "pass" as long as the count matched.