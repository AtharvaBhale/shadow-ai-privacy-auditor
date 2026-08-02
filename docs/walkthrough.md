# Walkthrough Video

**Video Link:** https://www.loom.com/share/c7851a0943204d99b4d5ed009aea4a71

**Live App:** https://ai-privacy-auditor.streamlit.app/

**Metrics (16 labeled fictional test cases):** Precision 1.000 | Recall 0.933 | F1 0.966 (15/16 exact-match)

The video covers:
- What the tool does and why (Shadow AI privacy auditing before pasting text into public AI tools)
- Detection approach: spaCy NER for names, regex + validation (Luhn, entropy, keyword proximity) for 
  the other 5 categories
- A risky example detected, explained, and redacted live
- A safe example correctly left unchanged (no over-redaction)
- The BERT → spaCy model swap, prompted by a deployment memory-limit failure caught via manual testing
- AI usage: Claude used for development (debugging, regex review, test case generation) — no AI called 
  at runtime
- Known limitations: NAME detection can miss short/embedded name fragments; details in model_card.md