# Model Card — Shadow AI Privacy Auditor

## Model

**`en_core_web_sm`** (spaCy) — a small English pipeline including a statistical/CNN-based Named Entity Recognition component, distributed by spaCy/Explosion AI under the MIT license. Free, no API key, no paid service, no GPU required.

### Why this replaced the original model choice

The first version of this app used `dslim/bert-base-NER` (a BERT-base transformer) via Hugging Face `transformers` + PyTorch. That worked correctly in local testing, but **on the deployed Streamlit Community Cloud free tier, the model silently failed to load** — most likely due to the platform's memory ceiling being too tight for a ~500MB transformer plus the PyTorch runtime. Because the app is designed to fail soft (a broken ML component shouldn't crash the whole tool), this produced a live app that looked fully functional but was quietly missing every NAME finding, with no visible error.

Rather than fighting the resource limit of a free hosting tier close to the deadline, the model was swapped for `en_core_web_sm`: ~12MB, no `torch` dependency, loads in well under a second, and is bundled directly via `requirements.txt` (as a wheel URL) so no runtime download is needed on cold start. This is a deliberate reliability-over-sophistication tradeoff, made explicitly because a model that doesn't load provides zero value regardless of its accuracy ceiling.

## Why this model (general)

- **Free and local.** Runs entirely on-device; the text a user pastes never leaves the machine running the app.
- **Right-sized for a free-tier deployment.** Small enough to load reliably within Streamlit Community Cloud's resource limits.
- **Entity types map to our categories.** spaCy's `PERSON` label maps to this app's `NAME` category.

## What the model does vs. what regex does

The ML model handles **linguistic entity recognition** — specifically, the `NAME` category, which pattern matching alone can't reliably do (recognizing "Alice Smith" as a name requires understanding sentence structure, not just a fixed pattern).

Regex + validation logic (Luhn checksum, Shannon entropy, keyword proximity) handle every other category: contact info, SSNs, credit cards, credentials, medical info, employee/client IDs, and confidential-organization keywords. This follows the brief's guidance that "regular expressions may support it, but the model does the core work" — the model owns the one category (names) that is genuinely linguistic rather than structured.

**Note on spaCy's `ORG` label:** an earlier version of this engine also mapped `ORG` entities to the `CONFIDENTIAL_INFO` category. Evaluation showed this produced a false positive — spaCy tagged the literal word "SSN" as an `ORG` entity in one test case. `ORG` mapping was removed; `CONFIDENTIAL_INFO` is handled entirely by keyword-trigger regex instead, which proved more precise for that category.

## Accuracy

See `test_cases.py` → `evaluate_metrics()`. Run with:

```bash
python test_cases.py
```

Current result on the 16-case labeled set: **Precision 1.000, Recall 0.933, F1 0.966** (15/16 cases fully correct).

**Known limitation, disclosed rather than hidden:** on `"Volunteer ID VOL-4821 (Maria) missed her shift; SSN 123-45-6789."`, the model does not detect "Maria" as a `PERSON` — a single first name inside a parenthetical mid-sentence is a harder case for a small statistical NER model than a full name after a salutation (which it detects correctly, per test #15). This is the one false negative in the current suite.

## Limitations

- `en_core_web_sm`'s NER is shallower than a transformer model like BERT — it is more likely to miss names in unusual sentence structures or short/isolated name fragments (see above).
- It was trained on general English text; performance on informal chat-style text or non-Western names is not independently verified here.
- Model load adds negligible latency (well under a second), unlike the original transformer approach, which was part of why it was chosen for this deployment.