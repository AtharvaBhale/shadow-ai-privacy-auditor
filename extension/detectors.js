// detectors.js
//
// A JavaScript port of the regex/validation detectors from src/engine.py.
// Browser extensions run JavaScript, not Python, so this intentionally
// mirrors only the categories that don't require the NER model:
// CONTACT_INFO, GOVT_IDENTIFIER, FINANCIAL_IDENTIFIER, CREDENTIALS,
// MEDICAL_INFO, EMPLOYEE_INFO, CONFIDENTIAL_INFO.
//
// NAME detection is NOT available here — it depends on the spaCy NER model
// (src/engine.py), which only runs in the Python/Streamlit app. This is a
// disclosed, intentional scope limit for the extension, not an oversight.
// See docs/architecture.md for the full explanation.

const PrivacyDetectors = (() => {
  const EMAIL_RE = /\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b/g;
  const PHONE_RE = /\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b/g;

  const SSN_RE = /\b\d{3}-\d{2}-\d{4}\b/g;
  const SSN_CONTEXT_RE = /\b(?:ssn|social security|social)\b/i;
  const SSN_BARE_RE = /\b\d{9}\b/g;

  const CREDIT_CARD_RE = /\b(?:\d{4}[-\s]?){3}\d{4}\b|\b\d{13,16}\b/g;

  const CREDENTIAL_RE = /\b(?:password|passwd|api_key|secret|token|access_key|contraseña|clave de acceso)\b\s*[:=]\s*["']?([A-Za-z0-9_\-+=!@#$%^&*./]{8,64})["']?/gi;

  const MEDICAL_RE = /\b(?:diagnosed with|tested positive for|medical record|prescription for|patient suffers from|diagnosticado con|dio positivo por|expediente médico|receta para)\b\s+([A-Za-z0-9\sÀ-ÿ]{3,30})\b/gi;

  const ORG_ID_RE = /\b(?:EMP|VOL|CLIENT|PT)-\d{3,6}\b/gi;

  const CONFIDENTIAL_RE = /\b(?:strictly confidential|internal only|do not distribute|confidential|acquisition|roadmap|estrictamente confidencial|no distribuir|confidencial|adquisición)\b/gi;

  function luhnCheck(cardNumber) {
    const digits = cardNumber.replace(/\D/g, "").split("").map(Number);
    if (digits.length < 13) return false;
    let checksum = 0;
    const reversed = digits.slice().reverse();
    for (let i = 0; i < reversed.length; i++) {
      let d = reversed[i];
      if (i % 2 === 1) {
        d *= 2;
        if (d > 9) d -= 9;
      }
      checksum += d;
    }
    return checksum % 10 === 0;
  }

  function shannonEntropy(str) {
    if (!str) return 0;
    const freq = {};
    for (const ch of str) freq[ch] = (freq[ch] || 0) + 1;
    let entropy = 0;
    for (const ch in freq) {
      const p = freq[ch] / str.length;
      entropy -= p * Math.log2(p);
    }
    return entropy;
  }

  const SEVERITY_MAP = {
    CREDENTIALS: "high",
    FINANCIAL_IDENTIFIER: "high",
    GOVT_IDENTIFIER: "high",
    MEDICAL_INFO: "medium",
    EMPLOYEE_INFO: "medium",
    CONFIDENTIAL_INFO: "medium",
    CONTACT_INFO: "low",
  };

  function findAll(regex, text, mapFn) {
    const results = [];
    let m;
    const re = new RegExp(regex.source, regex.flags.includes("g") ? regex.flags : regex.flags + "g");
    while ((m = re.exec(text)) !== null) {
      results.push(mapFn(m));
      if (m.index === re.lastIndex) re.lastIndex++; // avoid infinite loop on zero-width match
    }
    return results;
  }

  function auditText(text) {
    let findings = [];

    findings.push(...findAll(EMAIL_RE, text, (m) => ({
      start: m.index, end: m.index + m[0].length, category: "CONTACT_INFO",
      value: m[0], reason: "Exposes direct personal communication endpoints.",
    })));
    findings.push(...findAll(PHONE_RE, text, (m) => ({
      start: m.index, end: m.index + m[0].length, category: "CONTACT_INFO",
      value: m[0], reason: "Exposes direct phone details.",
    })));

    findings.push(...findAll(SSN_RE, text, (m) => ({
      start: m.index, end: m.index + m[0].length, category: "GOVT_IDENTIFIER",
      value: m[0], reason: "Social Security Numbers can lead to extreme identity theft threats.",
    })));

    // Bare 9-digit SSN, gated on nearby context keyword (same design as engine.py)
    findAll(SSN_BARE_RE, text, (m) => ({
      start: m.index, end: m.index + m[0].length, value: m[0],
    })).forEach((m) => {
      const windowStart = Math.max(0, m.start - 30);
      const window = text.slice(windowStart, m.start);
      if (SSN_CONTEXT_RE.test(window)) {
        findings.push({
          start: m.start, end: m.end, category: "GOVT_IDENTIFIER",
          value: m.value, reason: "Social Security Number (unformatted) found near an SSN-signaling keyword.",
        });
      }
    });

    findAll(CREDIT_CARD_RE, text, (m) => ({
      start: m.index, end: m.index + m[0].length, value: m[0],
    })).forEach((m) => {
      if (luhnCheck(m.value)) {
        findings.push({
          start: m.start, end: m.end, category: "FINANCIAL_IDENTIFIER",
          value: m.value, reason: "Valid financial payment card detected via Luhn checksum verification.",
        });
      }
    });

    findAll(CREDENTIAL_RE, text, (m) => ({
      start: m.index + m[0].indexOf(m[1]), end: m.index + m[0].indexOf(m[1]) + m[1].length,
      value: m[1],
    })).forEach((m) => {
      if (shannonEntropy(m.value) > 3.0) {
        findings.push({
          start: m.start, end: m.end, category: "CREDENTIALS",
          value: m.value, reason: "High-entropy secret key or operational password footprint.",
        });
      }
    });

    findings.push(...findAll(MEDICAL_RE, text, (m) => {
      const capStart = m.index + m[0].indexOf(m[1]);
      return {
        start: capStart, end: capStart + m[1].length, category: "MEDICAL_INFO",
        value: m[1], reason: "Contains protected health data tied directly to an active context.",
      };
    }));

    findings.push(...findAll(ORG_ID_RE, text, (m) => ({
      start: m.index, end: m.index + m[0].length, category: "EMPLOYEE_INFO",
      value: m[0], reason: "Internal employee, volunteer, or client identifier.",
    })));

    findings.push(...findAll(CONFIDENTIAL_RE, text, (m) => ({
      start: m.index, end: m.index + m[0].length, category: "CONFIDENTIAL_INFO",
      value: m[0], reason: "Signals confidential or pre-announcement organizational information.",
    })));

    // Overlap resolution: sort by start, longest match wins ties, drop overlaps.
    findings.sort((a, b) => a.start - b.start || (b.end - b.start) - (a.end - a.start));
    const cleaned = [];
    let lastEnd = -1;
    for (const f of findings) {
      if (f.start >= lastEnd) {
        f.severity = SEVERITY_MAP[f.category] || "medium";
        cleaned.push(f);
        lastEnd = f.end;
      }
    }
    return cleaned;
  }

  return { auditText };
})();
