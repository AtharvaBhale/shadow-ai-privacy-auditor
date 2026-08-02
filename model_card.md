# Model Card — Shadow AI Privacy Auditor

## Model

**`dslim/bert-base-NER`** — a BERT-base model fine-tuned for Named Entity Recognition on the CoNLL-2003 dataset, hosted on Hugging Face. Apache 2.0 licensed, freely downloadable, no API key or paid service required.

## Why this model

- **Free and local.** Runs entirely on-device via the `transformers` library's CPU inference pipeline. The text a user pastes never leaves the machine running the app — which matters specifically because this is a *privacy* tool; sending user text to a third-party inference API to check whether it's sensitive would undermine the tool's own purpose.
- **Right-sized for the task.** BERT-base (~110M parameters) is small enough to load and run in a Streamlit app on CPU with acceptable latency, unlike larger general-purpose LLMs that would need a GPU or a paid hosted endpoint.
- **Entity types match our categories directly.** The model's four entity groups — `PER` (person), `ORG` (organization), `LOC` (location), `MISC` — map cleanly onto this app's needs: `PER` → our `NAME` category, `ORG` → contributes to `CONFIDENTIAL_INFO` (an organization name appearing in casual text can leak a business relationship, deal, or affiliation).
- **Pretrained, not fine-tuned.** Training a custom model was explicitly optional per the brief; a pretrained general-purpose NER model is adequate for identifying names and organizations in everyday text without requiring our own labeled training corpus.

## What the model does vs. what regex does

The ML model handles **linguistic entity recognition** — the part of the problem that pattern matching is genuinely bad at (recognizing "Alice Smith" as a name requires understanding context and structure, not just a fixed pattern).

Regex + validation logic (Luhn checksum, Shannon entropy, keyword proximity) handle **structured/rule-based categories** where the data has a fixed, well-defined shape: SSNs, credit card numbers, API keys/passwords, employee/volunteer ID codes, and confidential-keyword triggers. This split follows the brief's explicit guidance: *"Regular expressions may support it, but the model does the core work."* The model is the only detector for the NAME category and contributes to CONFIDENTIAL_INFO; every other category is regex/validation-driven because it is inherently structured, not linguistic.

## Accuracy

See `test_cases.py` → `evaluate_metrics()` for the precision/recall/F1 computation over the labeled test set in the same file. Run with:

```bash
python test_cases.py
```

This prints per-case pass/fail plus aggregate precision, recall, and F1 across all labeled categories in the set.

**Known false positive, documented rather than papered over.** On `"Volunteer ID VOL-4821 (Maria) missed her shift; SSN 123-45-6789."`, the model tags an extra low-confidence `ORG` entity that isn't a real organization. A confidence threshold (0.85) was tried to filter this out; it also suppressed the correct `NAME` detection for "Maria" in the same sentence, trading recall for no net precision gain. The threshold was reverted. With the hackathon deadline close, this is disclosed as a known limitation rather than chased further — see `docs/reflection.md`.

## Limitations

- `dslim/bert-base-NER` was trained on CoNLL-2003 (Reuters news text from the 1990s). Its accuracy on informal chat-style text, unusual names, or non-Western names is weaker than on the news-style text it was trained on — a known limitation, not something this integration works around.
- `ORG` detection is a proxy for "confidential info," not a precise category — it will also flag organization names in completely benign, non-confidential sentences (e.g., "I had lunch near Acme Corp's office"). This is a deliberate precision/recall tradeoff disclosed here rather than hidden.
- Model load time adds a few seconds of latency on first use in a session; the app caches the loaded pipeline after that.