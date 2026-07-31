# Architecture Overview

## Final Tech Stack

Python + Streamlit, exactly as planned in `planning.md`. No deviation. `requirements.txt` was trimmed to just `streamlit` — the starting scaffold pulled in `plotly` and `pandas`, neither of which the code imports.

## Folder Structure

```
src/
├── engine.py       # PrivacyAuditorEngine: all detectors, overlap resolution,
│                   # inline highlight rendering, and redaction
app.py              # Streamlit UI: input, highlighted preview, findings panel, redacted output
test_cases.py        # 14 fictional test cases (5 safe, 9 risky) with strict category assertions
```

Simpler than the folder layout sketched in `planning.md` (which proposed a `detectors/` package with one module per category). In practice, four detectors plus shared helpers (Luhn, entropy, proximity windows) fit comfortably in a single `engine.py`. Splitting into separate files would have added import overhead without a real readability gain at this size. Worth revisiting only if Tier 2 pushes the file past ~300 lines.

## Detection Design

`PrivacyAuditorEngine.audit_text()` runs every detector over the input and returns a list of finding dicts: `{start, end, category, value, reason}`.

**Names & contact info** — email and phone via regex. Names are only flagged when they follow a salutation cue (`Dear`, `Regards`, `Hi`, `Sincerely`, `Attn`, `From`, `To`, followed by a comma and a capitalized word or two). This is a deliberate precision-over-recall tradeoff: a plain wordlist of first/last names would flag common words used as names elsewhere in a sentence ("May", "Grace", "Mark"). The tradeoff is documented, not hidden — bare names with no salutation context are a known miss (see Limitations).

**Government & financial identifiers** — SSNs match the standard `XXX-XX-XXXX` format directly. A second pattern also catches unformatted 9-digit SSNs, but only when a keyword (`SSN`, `social security`, `social`) appears within a 30-character window before the number — this avoids flagging unrelated 9-digit numbers like tracking codes or order IDs. Credit cards match a 13–16 digit pattern and are then validated with a **Luhn checksum**; only checksum-valid numbers are flagged, which eliminates the majority of false positives that a naive digit-count regex would produce.

**Credentials & API keys** — a keyword-anchored regex (`password`, `api_key`, `secret`, `token`, `access_key` followed by `:` or `=`) captures the value, which must then pass a **Shannon entropy check** (`> 3.0`). This is what stops `password: please` or `password='password'` from being flagged as a leaked secret — low-entropy, dictionary-like values are excluded even though they match the keyword pattern.

**Medical info** — phrase-anchored regex (`diagnosed with`, `tested positive for`, `prescription for`, etc.) rather than a bare keyword list, so a sentence like "the clinic newsletter covers general asthma awareness" doesn't trigger just because "asthma" appears — the phrase itself has to imply an active personal medical context.

**Overlap resolution** — all findings are sorted by start position (ties broken by longest match first), then a single pass keeps a finding only if it starts at or after the previous finding's end. This guarantees no two highlighted spans overlap in the UI or in redaction.

**From match to UI** — three consumers read the same finding list:
1. `highlight_html()` walks the original text and wraps each finding in a `<mark>` span colored and labeled by category, so the *original* text is shown with in-place highlights (not just a before/after diff).
2. The findings panel renders each finding's category and `reason` as a card.
3. `redact_text()` applies `[CATEGORY]` placeholders back-to-front (reverse-sorted by start index) so replacing one span doesn't shift the character offsets of the others.

## AI Integration Design

No AI model runs inside the app. Detection is 100% deterministic regex/keyword/validation logic, which was a deliberate choice: it avoids any paid API, keeps the tool auditable (you can point at the exact rule that fired), and avoids the irony of a privacy tool sending the user's sensitive text to a third-party LLM to check if it's sensitive.

AI (Claude) was used only during development — to draft synthetic test sentences and review regex edge cases — never at runtime. Detailed in `reflection.md`.

## What Changed From the Plan

- **Folder structure simplified** from a `detectors/` package to a single `engine.py`, as noted above.
- **Inline highlighting (`highlight_html`) was added mid-build**, not in the original plan — the first UI draft only showed a redacted-text box and a separate findings list, which didn't satisfy the brief's explicit "visually highlighted" requirement. Caught during review, fixed before Tier 2 work started.
- **Bare/unformatted SSN detection was added** after edge-case testing showed dashed-format-only detection missed a realistic input shape. Gated on nearby context rather than a bare 9-digit regex, to avoid false-positiving on unrelated numeric IDs.
- **Test suite strengthened mid-build**: the original test runner only checked finding *count*, which meant a finding with the wrong category label would still show as "passed." Rewritten to assert exact expected categories per case.