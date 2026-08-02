# Reflection

## What I Built
A Shadow AI Privacy Auditor covering all 6 sensitive-information categories: names (via NER), 
contact info, government/financial identifiers (SSN + Luhn-validated credit cards), credentials 
(entropy-validated), medical info, and employee/client/confidential-org info. Detection is hybrid: 
spaCy's en_core_web_sm NER model handles names — the one category that's genuinely linguistic, not 
pattern-based — while regex and validation logic (Luhn checksum, Shannon entropy, keyword proximity) 
handle every structured category. The UI highlights findings inline on the original text with 
category-colored marks and explanations, then generates a redacted, safe-to-share version.

What works reliably: contact info, financial/government IDs, credentials, medical info, employee IDs, 
and confidential-keyword detection — all regex/validation-backed and consistently accurate across the 
test suite. NAME detection works but is the weakest link (see limitations below).

## What I'd Do Differently
I'd load-test the ML model against the actual deployment platform's resource limits before finalizing 
a model choice, not after. I built and fully tested the app locally using dslim/bert-base-NER (a BERT 
transformer), which worked correctly — but silently failed to load on Streamlit Community Cloud's free 
tier, almost certainly due to memory limits, and produced zero NAME detections in production with no 
visible error. I caught this only through manual testing of the live URL. I'd add explicit error 
surfacing for ML load failures (e.g., a visible banner) rather than relying on fail-soft behavior alone, 
so a broken model component is obvious rather than silently degrading the tool's core claim.

I'd also test spaCy's entity mappings more carefully before committing to them — an earlier version 
mapped ORG entities to CONFIDENTIAL_INFO, which produced a false positive (the model tagged the literal 
word "SSN" as an organization). I dropped that mapping rather than keep tuning it, given time constraints.

With more time, I'd improve NAME recall on short/embedded name fragments (e.g., a single first name in 
a parenthetical mid-sentence, which the current model misses) and add a second lightweight name-detection 
pass as a fallback.

## AI Tools Used
Claude was used throughout development: to review and debug regex patterns (especially the credential 
entropy check and SSN false-positive guarding), to diagnose why the deployed app's NAME detection was 
failing, to help design and implement the swap from BERT to spaCy after the memory issue was found, and 
to draft synthetic fictional test cases. No AI model is called at runtime by the deployed app itself — 
detection is fully local (spaCy NER + regex/validation), which matters specifically because this is a 
privacy tool.

Beyond the core web app, I also built a Tier 2 Chrome extension (`extension/`) that watches ChatGPT's message composer directly and warns before you send something sensitive — combining the "browser extension" and "direct AI platform integration" stretch goals into one working deliverable. It's a JavaScript port of the app's regex/validation detectors (not the NER model, which can't run in a browser without a separate backend — a scope limit I documented rather than worked around, since building a backend just to expose the NER model would mean sending draft text to an external service, which conflicts with the whole point of a privacy tool). It intercepts both the Send button and Enter key, and shows a confirmation dialog before letting a risky message through.