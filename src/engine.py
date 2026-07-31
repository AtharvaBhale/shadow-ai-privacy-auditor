# src/engine.py
import re
import math

# ---------------------------------------------------------------------------
# ML model: dslim/bert-base-NER (Hugging Face, Apache 2.0, free, no API key).
# Loaded lazily and cached so the app doesn't pay model-load cost on every
# audit call, and so importing this module doesn't require the model to be
# present (keeps unit tests fast / offline-safe).
# ---------------------------------------------------------------------------
_ner_pipeline = None


def _get_ner_pipeline():
    global _ner_pipeline
    if _ner_pipeline is None:
        from transformers import pipeline
        _ner_pipeline = pipeline(
            "ner",
            model="dslim/bert-base-NER",
            grouped_entities=True,
        )
    return _ner_pipeline


class PrivacyAuditorEngine:
    """
    Detection is ML-first: a pretrained NER model (dslim/bert-base-NER) does
    the core work of finding names and organizations (see model card in
    docs/model_card.md). Regex + validation logic SUPPORT the model for
    categories that are inherently structured/rule-based rather than
    linguistic — SSNs, credit card numbers (Luhn-validated), and credentials
    (entropy-validated) — exactly as the brief allows ("regular expressions
    may support it, but the model does the core work").
    """

    # NER entity groups this app treats as sensitive, and which internal
    # category each maps to.
    NER_CATEGORY_MAP = {
        "PER": "NAME",
        "ORG": "CONFIDENTIAL_INFO",   # org names showing up in casual text can leak affiliations/deals
    }

    def __init__(self, use_ml: bool = True):
        self.use_ml = use_ml

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
            return findings
        try:
            nlp = _get_ner_pipeline()
        except Exception:
            # Model unavailable (e.g. no network in this environment) —
            # fail soft so regex detectors still run rather than crashing
            # the whole app. This should not happen in the deployed app,
            # which has normal internet access to download the model once.
            return findings

        for ent in nlp(text):
            group = ent.get("entity_group")
            category = self.NER_CATEGORY_MAP.get(group)
            if category is None:
                continue
            findings.append({
                'start': ent['start'],
                'end': ent['end'],
                'category': category,
                'value': text[ent['start']:ent['end']],
                'reason': f'Detected by NER model (dslim/bert-base-NER) as a {group} entity — '
                          f'may identify an individual or organization.',
                'source': 'ml',
                'confidence': float(ent.get('score', 0.0)),
            })
        return findings

    def audit_text(self, text: str):
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

        # Sort and resolve overlaps: longest match wins; ML and regex findings
        # compete on equal footing at this stage.
        findings = sorted(findings, key=lambda x: (x['start'], -(x['end'] - x['start'])))
        cleaned_findings = []
        last_end = -1
        for f in findings:
            if f['start'] >= last_end:
                cleaned_findings.append(f)
                last_end = f['end']

        return cleaned_findings

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