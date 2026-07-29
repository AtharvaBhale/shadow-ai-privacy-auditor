# Architecture Overview

> Fill this in **after building**, not before. This documents how your app was actually implemented.
> Compare this against your `planning/planning.md` to reflect on where your plan changed and why.

---

## Final Tech Stack

<!-- What framework, language, and key libraries did you end up using?
Did anything change from your original plan in planning.md? If so, why? -->

## Folder Structure

<!-- Paste your actual src/ folder structure and briefly describe what each part does.
Example:
src/
├── detectors/      # One module per detection category (regex + keyword rules)
├── ui/             # Input box, highlighted preview, findings list, redacted output
├── lib/            # Validation helpers (Luhn, ranges), redaction utilities
└── examples/       # Sample/test sentences
-->

## Detection Design

<!-- How does your detection pipeline actually work?
- Which categories do you detect, and with what technique (regex, keyword lists, validation, NER, LLM)?
- How do you reduce false positives and avoid over-redacting safe text?
- How does a detected match become a highlight, a category/explanation, and the redacted output? -->

## AI Integration Design

<!-- If you used an AI model for detection or explanations:
- What context do you pass to the model, and where does it run (local vs. hosted)?
- How do you handle the privacy trade-off of sending text to an AI to check it?
- What prompt engineering decisions did you make? -->

## What Changed From the Plan

<!-- Where did your implementation diverge from planning.md and why?
This is not a penalty - honest reflection here is valued. -->
