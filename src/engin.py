# src/engine.py
import re
import math

class PrivacyAuditorEngine:
    def __init__(self):
        # 1. Names & Contact Info
        self.email_regex = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
        self.phone_regex = re.compile(r'\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b')
        # Simple structural context name matching (e.g., Dear John Doe, Regards, Jane Smith)
        self.name_context_regex = re.compile(r'\b(?:Hi|Dear|Regards|Sincerely|Attn|From|To),\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b')

        # 2. Government & Financial Identifiers
        self.ssn_regex = re.compile(r'\b\d{3}-\d{2}-\d{4}\b')
        self.credit_card_regex = re.compile(r'\b(?:\d{4}[-\s]?){3}\d{4}\b|\b\d{13,16}\b')

        # 3. Credentials & API Keys
        # Captures keys/passwords followed by alphanumeric/special strings, excluding short placeholders
        self.credential_regex = re.compile(
            r'\b(?:password|passwd|api_key|secret|token|access_key)\b\s*[:=]\s*["\']?([A-Za-z0-9_\-+=]{8,64})["\']?', 
            re.IGNORECASE
        )

        # 4. Medical / Sensitive Personal Info
        # Strict context-based medical phrases to avoid flagging "wellness meeting"
        self.medical_regex = re.compile(
            r'\b(?:diagnosed with|tested positive for|medical record|prescription for|patient suffers from)\b\s+([A-Za-z0-9\s]{3,30})\b', 
            re.IGNORECASE
        )

    def _luhn_checksum(self, card_number: str) -> bool:
        """Validates card strings using the Luhn Algorithm to eliminate false positives."""
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
        """Calculates Shannon Entropy to verify if a string looks like a random cryptographic key."""
        if not text:
            return 0.0
        entropy = 0.0
        for x in set(text):
            p_x = text.count(x) / len(text)
            entropy -= p_x * math.log2(p_x)
        return entropy

    def audit_text(self, text: str):
        findings = []

        # Category 1: Contact/Names
        for match in self.email_regex.finditer(text):
            findings.append({'start': match.start(), 'end': match.end(), 'category': 'CONTACT_INFO', 'value': match.group(), 'reason': 'Exposes direct personal communication endpoints.'})
        for match in self.phone_regex.finditer(text):
            findings.append({'start': match.start(), 'end': match.end(), 'category': 'CONTACT_INFO', 'value': match.group(), 'reason': 'Exposes direct phone details.'})
        for match in self.name_context_regex.finditer(text):
            findings.append({'start': match.start(1), 'end': match.end(1), 'category': 'NAME', 'value': match.group(1), 'reason': 'Identified individual identifier via surrounding conversational cues.'})

        # Category 2: Gov/Financial
        for match in self.ssn_regex.finditer(text):
            findings.append({'start': match.start(), 'end': match.end(), 'category': 'GOVT_IDENTIFIER', 'value': match.group(), 'reason': 'Social Security Numbers can lead to extreme identity theft threats.'})
        for match in self.credit_card_regex.finditer(text):
            val = match.group()
            if self._luhn_checksum(val):
                findings.append({'start': match.start(), 'end': match.end(), 'category': 'FINANCIAL_IDENTIFIER', 'value': val, 'reason': 'Valid financial payment card detected via Luhn checksum verification.'})

        # Category 3: Credentials
        for match in self.credential_regex.finditer(text):
            val = match.group(1)
            # Ensure the captured value has enough character diversity (entropy) to look like a real credential
            if self._calculate_entropy(val) > 3.0:
                findings.append({'start': match.start(1), 'end': match.end(1), 'category': 'CREDENTIALS', 'value': val, 'reason': 'High-entropy secret key or operational password footprint.'})

        # Category 4: Medical Info
        for match in self.medical_regex.finditer(text):
            findings.append({'start': match.start(1), 'end': match.end(1), 'category': 'MEDICAL_INFO', 'value': match.group(1), 'reason': 'Contains protected health data tied directly to an active context.'})

        # Sort matches and resolve overlaps (Keep the longest match)
        findings = sorted(findings, key=lambda x: (x['start'], -(x['end'] - x['start'])))
        cleaned_findings = []
        last_end = -1
        
        for f in findings:
            if f['start'] >= last_end:
                cleaned_findings.append(f)
                last_end = f['end']
                
        return cleaned_findings

    def redact_text(self, text: str, findings) -> str:
        """Applies smart placeholders onto sensitive regions safely without over-redacting."""
        # Reverse sort by start index to prevent shifting character positions while editing
        sorted_findings = sorted(findings, key=lambda x: x['start'], reverse=True)
        redacted = text
        for f in sorted_findings:
            placeholder = f"[{f['category']}]"
            redacted = redacted[:f['start']] + placeholder + redacted[f['end']:]
        return redacted