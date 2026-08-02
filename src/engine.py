# src/engine.py
import re
import math

# ---------------------------------------------------------------------------
# ML model: spaCy en_core_web_sm (MIT license, free, no API key, no torch).
# Loaded lazily and cached so the app doesn't pay model-load cost on every
# audit call, and so importing this module doesn't require the model to be
# present (keeps unit tests fast / offline-safe).
# ---------------------------------------------------------------------------
_nlp_spacy = None


def _get_ner_pipeline():
    """Loads spaCy's small English model (en_core_web_sm), cached after first
    call. Swapped in from a larger transformer model (dslim/bert-base-NER)
    after evaluation on the deployed free-tier host showed the ~500MB
    transformer + PyTorch combination silently failed to load under the
    platform's memory limit (see docs/model_card.md for the full account).
    en_core_web_sm is ~12MB, has no torch dependency, and loads in well
    under a second, at the cost of using a shallower statistical/CNN model
    rather than a transformer."""
    global _nlp_spacy
    if _nlp_spacy is None:
        import spacy
        _nlp_spacy = spacy.load("en_core_web_sm")
    return _nlp_spacy


class PrivacyAuditorEngine:
    """
    Detection is ML-first for the NAME category: a pretrained NER model
    (spaCy en_core_web_sm) does the core work of finding person names (see
    model card in docs/model_card.md). Regex + validation logic SUPPORT the
    model for categories that are inherently structured/rule-based rather
    than linguistic — SSNs, credit card numbers (Luhn-validated), credentials
    (entropy-validated), employee/client IDs, and confidential-keyword
    triggers — exactly as the brief allows ("regular expressions may support
    it, but the model does the core work").

    Note: spaCy's ORG entity label is not mapped to CONFIDENTIAL_INFO. During
    evaluation it produced false positives (e.g. tagging "SSN" itself as an
    ORG), so CONFIDENTIAL_INFO is handled entirely by the keyword regex
    below instead, which is more precise for that category.
    """

    # NER entity labels this app treats as sensitive, and which internal
    # category each maps to.
    NER_CATEGORY_MAP = {
        "PERSON": "NAME",
    }

    # Tier 2: severity weight per category, for risk scoring. Credentials
    # and financial/government identifiers carry the highest real-world
    # harm (account takeover, identity theft, direct financial loss) so
    # they're weighted "high." Medical and confidential-org info are
    # "medium" (serious but usually not immediately exploitable on their
    # own). Name/contact info alone is "low" (identifying but not
    # inherently exploitable without other data).
    SEVERITY_MAP = {
        "CREDENTIALS": "high",
        "FINANCIAL_IDENTIFIER": "high",
        "GOVT_IDENTIFIER": "high",
        "MEDICAL_INFO": "medium",
        "EMPLOYEE_INFO": "medium",
        "CONFIDENTIAL_INFO": "medium",
        "NAME": "low",
        "CONTACT_INFO": "low",
    }
    SEVERITY_SCORE = {"high": 3, "medium": 2, "low": 1}

    def __init__(self, use_ml: bool = True):
        self.use_ml = use_ml
        # Tracks whether the ML model is actually available and working.
        # None = not checked yet, True = loaded fine, False = load failed.
        # This exists specifically so a broken/missing model produces a
        # VISIBLE warning in the UI instead of silently returning zero NAME
        # findings — this exact silent failure cost real debugging time
        # twice during development (once on a memory-constrained deploy
        # host, once from a missing local dependency).
        self.ml_available = None

        # --- Structured / rule-based detectors (support the ML model) ---
        self.email_regex = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
        self.phone_regex = re.compile(r'\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b')

        self.ssn_regex = re.compile(r'\b\d{3}-\d{2}-\d{4}\b')
        self.ssn_context_keywords = re.compile(r'\b(?:ssn|social security|social)\b', re.IGNORECASE)
        self.ssn_bare_regex = re.compile(r'\b\d{9}\b')
        self.credit_card_regex = re.compile(r'\b(?:\d{4}[-\s]?){3}\d{4}\b|\b\d{13,16}\b')

        self.credential_regex = re.compile(
            r'\b(?:password|passwd|api_key|secret|token|access_key)\b\s*[:=]\s*["\']?([A-Za-z0-9_\-+=!@#$%^&*./]{8,64})["\']?',
            re.IGNORECASE
        )

        self.medical_regex = re.compile(
            r'\b(?:diagnosed with|tested positive for|medical record|prescription for|patient suffers from)\b\s+([A-Za-z0-9\s]{3,30})\b',
            re.IGNORECASE
        )

        # Employee / client / volunteer IDs, matching the format shown in the
        # orientation deck: EMP-12345, VOL-4821, patient ID style codes.
        self.org_id_regex = re.compile(r'\b(?:EMP|VOL|CLIENT|PT)-\d{3,6}\b', re.IGNORECASE)

        # Confidential/organizational keyword triggers.
        self.confidential_keywords = re.compile(
            r'\b(?:strictly confidential|internal only|do not distribute|confidential|acquisition|roadmap)\b',
            re.IGNORECASE
        )

    def _luhn_checksum(self, card_number: str) -> bool:
        digits = [int(d) for d in re.sub(r'\D', '', card_number)]
        if not digits or len(digits) < 13:
            return False
        checksum = 0
        reverse_digits = digits[::-1]
        for i, digit in enumerate(reverse_digits):
            if i % 2 == 1:
                digit *= 2
                if digit > 9:
                    digit -= 9
            checksum += digit
        return checksum % 10 == 0

    def _calculate_entropy(self, text: str) -> float:
        if not text:
            return 0.0
        entropy = 0.0
        for x in set(text):
            p_x = text.count(x) / len(text)
            entropy -= p_x * math.log2(p_x)
        return entropy

    def _ml_findings(self, text: str):
        """Run the NER model and map its entities onto our category schema."""
        findings = []
        if not self.use_ml:
            self.ml_available = False
            return findings
        try:
            nlp = _get_ner_pipeline()
            self.ml_available = True
        except Exception as e:
            # Model unavailable — fail soft so regex detectors still run
            # rather than crashing the whole app, but record WHY so the UI
            # can surface a visible warning instead of silently returning
            # zero NAME findings.
            self.ml_available = False
            self.ml_error = str(e)
            return findings

        doc = nlp(text)
        for ent in doc.ents:
            category = self.NER_CATEGORY_MAP.get(ent.label_)
            if category is None:
                continue
            findings.append({
                'start': ent.start_char,
                'end': ent.end_char,
                'category': category,
                'value': ent.text,
                'reason': f'Detected by NER model (spaCy en_core_web_sm) as a {ent.label_} entity — '
                          f'may identify an individual.',
                'source': 'ml',
                'confidence': None,  # spaCy's small pipeline does not expose a calibrated confidence score
            })
        return findings

    def audit_text(self, text: str, custom_rules=None):
        """
        custom_rules (Tier 2): optional list of user-defined rule dicts,
        each shaped like {'pattern': <regex string>, 'category': <label>,
        'reason': <explanation>, 'severity': 'high'|'medium'|'low'}.
        Lets a user extend detection at runtime without touching source
        code. Invalid regex patterns are skipped rather than raising, so
        one bad custom rule can't break the whole audit.
        """
        findings = []

        # --- ML: names and organizations (core detection) ---
        findings.extend(self._ml_findings(text))

        # --- Regex/validation: contact info ---
        for match in self.email_regex.finditer(text):
            findings.append({'start': match.start(), 'end': match.end(), 'category': 'CONTACT_INFO', 'value': match.group(), 'reason': 'Exposes direct personal communication endpoints.', 'source': 'regex'})
        for match in self.phone_regex.finditer(text):
            findings.append({'start': match.start(), 'end': match.end(), 'category': 'CONTACT_INFO', 'value': match.group(), 'reason': 'Exposes direct phone details.', 'source': 'regex'})

        # --- Regex/validation: government & financial identifiers ---
        for match in self.ssn_regex.finditer(text):
            findings.append({'start': match.start(), 'end': match.end(), 'category': 'GOVT_IDENTIFIER', 'value': match.group(), 'reason': 'Social Security Numbers can lead to extreme identity theft threats.', 'source': 'regex'})
        for match in self.ssn_bare_regex.finditer(text):
            window_start = max(0, match.start() - 30)
            window = text[window_start:match.start()]
            if self.ssn_context_keywords.search(window):
                findings.append({'start': match.start(), 'end': match.end(), 'category': 'GOVT_IDENTIFIER', 'value': match.group(), 'reason': 'Social Security Number (unformatted) found near an SSN-signaling keyword.', 'source': 'regex'})
        for match in self.credit_card_regex.finditer(text):
            val = match.group()
            if self._luhn_checksum(val):
                findings.append({'start': match.start(), 'end': match.end(), 'category': 'FINANCIAL_IDENTIFIER', 'value': val, 'reason': 'Valid financial payment card detected via Luhn checksum verification.', 'source': 'regex'})

        # --- Regex/validation: credentials ---
        for match in self.credential_regex.finditer(text):
            val = match.group(1)
            if self._calculate_entropy(val) > 3.0:
                findings.append({'start': match.start(1), 'end': match.end(1), 'category': 'CREDENTIALS', 'value': val, 'reason': 'High-entropy secret key or operational password footprint.', 'source': 'regex'})

        # --- Regex/validation: medical info ---
        for match in self.medical_regex.finditer(text):
            findings.append({'start': match.start(1), 'end': match.end(1), 'category': 'MEDICAL_INFO', 'value': match.group(1), 'reason': 'Contains protected health data tied directly to an active context.', 'source': 'regex'})

        # --- Regex: employee/client/volunteer IDs ---
        for match in self.org_id_regex.finditer(text):
            findings.append({'start': match.start(), 'end': match.end(), 'category': 'EMPLOYEE_INFO', 'value': match.group(), 'reason': 'Internal employee, volunteer, or client identifier.', 'source': 'regex'})

        # --- Regex: confidential organizational info ---
        for match in self.confidential_keywords.finditer(text):
            findings.append({'start': match.start(), 'end': match.end(), 'category': 'CONFIDENTIAL_INFO', 'value': match.group(), 'reason': 'Signals confidential or pre-announcement organizational information.', 'source': 'regex'})

        # --- Tier 2: user-defined custom rules ---
        for rule in (custom_rules or []):
            pattern = rule.get('pattern', '')
            category = rule.get('category', 'CUSTOM')
            reason = rule.get('reason', 'Matches a user-defined custom rule.')
            try:
                compiled = re.compile(pattern, re.IGNORECASE)
            except re.error:
                # Invalid regex from the user — skip this rule rather than
                # crash the whole audit.
                continue
            for match in compiled.finditer(text):
                findings.append({
                    'start': match.start(),
                    'end': match.end(),
                    'category': category,
                    'value': match.group(),
                    'reason': reason,
                    'source': 'custom',
                    'custom_severity': rule.get('severity'),
                })

        # Sort and resolve overlaps: longest match wins; ML and regex findings
        # compete on equal footing at this stage.
        findings = sorted(findings, key=lambda x: (x['start'], -(x['end'] - x['start'])))
        cleaned_findings = []
        last_end = -1
        for f in findings:
            if f['start'] >= last_end:
                cleaned_findings.append(f)
                last_end = f['end']

        # Tier 2: tag every finding with a severity level, one place, applied
        # uniformly regardless of whether it came from the ML model, regex,
        # or a user-defined custom rule. Custom rules may specify their own
        # severity; otherwise default to 'medium' for unknown categories.
        for f in cleaned_findings:
            if f.get('source') == 'custom' and f.get('custom_severity') in self.SEVERITY_SCORE:
                f['severity'] = f['custom_severity']
            else:
                f['severity'] = self.SEVERITY_MAP.get(f['category'], 'medium')

        return cleaned_findings

    def risk_score(self, findings):
        """
        Tier 2: an overall risk summary for a whole audited text. Returns a
        dict with counts per severity level, a total weighted score, and a
        simple label (Low/Medium/High/Critical) derived from that score.
        Weighted rather than a plain count so a handful of low-severity
        findings (e.g. a name and an email) doesn't read the same as a
        single leaked credential.
        """
        counts = {"high": 0, "medium": 0, "low": 0}
        for f in findings:
            counts[f.get('severity', 'low')] += 1

        weighted_total = sum(self.SEVERITY_SCORE[level] * n for level, n in counts.items())

        if counts["high"] >= 1:
            label = "Critical" if counts["high"] >= 2 else "High"
        elif counts["medium"] >= 1:
            label = "Medium"
        elif counts["low"] >= 1:
            label = "Low"
        else:
            label = "Clean"

        return {
            "label": label,
            "weighted_score": weighted_total,
            "counts": counts,
            "total_findings": len(findings),
        }

    def highlight_html(self, text: str, findings) -> str:
        import html as _html
        sorted_findings = sorted(findings, key=lambda x: x['start'])
        out = []
        cursor = 0
        for f in sorted_findings:
            out.append(_html.escape(text[cursor:f['start']]))
            span_text = _html.escape(text[f['start']:f['end']])
            out.append(
                f'<mark class="finding finding-{f["category"]}" title="{_html.escape(f["reason"])}">'
                f'{span_text}</mark>'
            )
            cursor = f['end']
        out.append(_html.escape(text[cursor:]))
        return "".join(out)

    def redact_text(self, text: str, findings) -> str:
        sorted_findings = sorted(findings, key=lambda x: x['start'], reverse=True)
        redacted = text
        for f in sorted_findings:
            placeholder = f"[{f['category']}]"
            redacted = redacted[:f['start']] + placeholder + redacted[f['end']:]
        return redacted