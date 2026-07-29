# Planning Document

> Completed before writing any code, per hackathon instructions.
> Scope: Tier 1 is the committed plan. Tier 2 is attempted only after Tier 1 is fully working and tested — not in parallel. A complete Tier 1 outweighs an incomplete attempt at both tiers per the problem statement.

---

## Tech Stack

**Framework / Language:** Python + Streamlit

*Why:* This is a single-page tool (input → detect → highlight → redact), not a multi-route app. Streamlit gives a working UI with minimal code and deploys free on Streamlit Community Cloud with no backend config. This keeps time budget on detection accuracy (30% of grade) instead of frontend plumbing.

**Key Libraries:** `re` (stdlib regex), `streamlit`. No ML/NER library and no external AI API — regex, keyword lists, and validation algorithms (Luhn checksum, entropy checks) fully satisfy Tier 1's detection requirement without any paid service.

**Detection Approach / AI Provider:** Regex + keyword lists + validation logic. No AI model at inference time — the brief explicitly states training a model isn't required, and using deterministic pattern matching is also more precise and auditable for structured data (SSNs, card numbers, API key formats) than an LLM call would be. AI (Claude) is used only as a *development* tool — generating synthetic test cases and reviewing regex patterns — disclosed in `reflection.md`, not called by the running app.

---

## Detection Categories

| Category | Detect? | Planned technique |
|---|---|---|
| Names & contact information | Yes (Tier 1 core) | Regex for email/phone; curated first/last-name wordlist for names, flagged as lower-confidence than the other categories |
| Government or financial identifiers | Yes (Tier 1 core) | Regex for SSN format + credit card regex validated with the Luhn algorithm to cut false positives |
| Passwords, API keys or credentials | Yes (Tier 1 core) | Keyword-anchored regex (`api_key=`, `token:`, `password:`) combined with a high-entropy string check on the value, so `password: please` doesn't false-positive |
| Medical or sensitive personal information | Yes (Tier 1 core) | Keyword list (diagnoses, medications, clinical terms) + proximity check to a name/ID to reduce false positives on incidental mentions |
| Employee, client or volunteer information | Tier 2 | `Employee ID:`, `Client:`, `Volunteer #:` label patterns |
| Confidential organizational or project information | Tier 2 | Keyword triggers ("confidential", "internal only", "do not distribute") + project-codename pattern |

Four categories (names/contact, gov/financial, credentials, medical) meet and exceed the "at least 4 of 6" Tier 1 minimum. The remaining two are explicitly deferred to Tier 2 so Tier 1 ships complete and well-tested first.

---

## Phases & Priorities

### Tier 1 (committed scope)

| Phase | Goals |
|---|---|
| 1 | Planning doc, repo scaffold, `engine.py` skeleton, contact-info detector, credentials detector |
| 2 | Financial/gov identifiers detector (with Luhn), medical detector, redaction engine, Streamlit UI wired to all four |
| 3 | 10+ fictional test cases including safe examples, fix over-redaction/false-positive bugs found by testing |
| 4 | Deploy to Streamlit Community Cloud, record walkthrough video, finish `architecture.md` and `reflection.md` |

### Tier 2 (only started once every Tier 1 box above is checked and tested)

| Priority | Stretch goal | Technique |
|---|---|---|
| 1 | Employee/client/volunteer detector | Label-pattern regex, adds a 5th category |
| 2 | Confidential org info detector | Keyword triggers, adds the 6th category (full 6/6 coverage) |
| 3 | Severity/risk scoring | Weight findings by category (credentials/financial = high, names = medium) |
| 4 | One-click "copy safe text" + undo/keep per-finding controls | UI-only addition on top of existing redaction engine |
| 5 | Configurable custom rules | Let user add their own regex/keyword rule at runtime |

Not planned: browser extension, direct platform integration, multilingual detection, real-time monitoring — these require more infrastructure than the remaining time likely supports. Revisit only if Tier 2 priorities 1–4 finish early.

---

## What I'll Cut If Time Is Short

**First to cut:** everything under Tier 2 — none of it affects the Tier 1 grading floor.
**Last to cut:** the 10 test cases and safe-example correctness. This is directly graded, required by the brief, and is where over-redaction bugs get caught — cutting it late is the highest-risk shortcut.

---

## Open Questions / Risks

- **Name detection without NER is the weakest link.** A wordlist will miss uncommon names and can false-positive on common words used as names (May, Grace, Mark). Mitigation: treat name matches as lower-confidence and require them to co-occur with an email/phone/title nearby before flagging, rather than matching the wordlist alone.
- **Medical keyword lists risk over-redaction** on sentences that mention health-adjacent words without being sensitive ("wellness meeting agenda"). Needs dedicated safe test cases, not just risky ones.
- **Credential regex needs an entropy/length check, not just keyword presence**, or short/placeholder values like `password: 123` or `password: please` will both false-positive and under-flag real secrets.
- **Overlap resolution:** a single span of text could trigger two detectors (e.g., a name inside a "Client:" line). Plan: `engine.py` sorts matches by position and start index, and on overlap keeps the longer/more specific match rather than double-highlighting.
