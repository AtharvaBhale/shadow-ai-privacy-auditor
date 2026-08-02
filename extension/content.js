// content.js
//
// Injected into chatgpt.com / chat.openai.com. Watches the message composer,
// runs PrivacyDetectors (detectors.js) on the current draft text, shows a
// live findings panel, and intercepts Send when risky content is present so
// the user gets one confirmation step before sending.
//
// Scope note: this extension only covers the regex/validation-backed
// categories (see detectors.js header). NAME detection is not available
// here — it requires the Python/spaCy NER model, which only runs in the
// Streamlit app. This is a disclosed limitation, not an oversight.

(function () {
  const SEVERITY_COLORS = { high: "#E4572E", medium: "#F2A541", low: "#4FB0A5" };
  const CATEGORY_LABELS = {
    CONTACT_INFO: "Contact Info",
    GOVT_IDENTIFIER: "Government ID",
    FINANCIAL_IDENTIFIER: "Financial ID",
    CREDENTIALS: "Credential / Secret",
    MEDICAL_INFO: "Medical Info",
    EMPLOYEE_INFO: "Employee / Client Info",
    CONFIDENTIAL_INFO: "Confidential Info",
  };

  let panel = null;
  let lastFindings = [];
  let debounceTimer = null;

  function buildPanel() {
    if (panel) return panel;
    panel = document.createElement("div");
    panel.id = "shadow-ai-auditor-panel";
    panel.innerHTML = `
      <div id="saa-header">🛡️ Shadow AI Privacy Auditor <span id="saa-toggle">▾</span></div>
      <div id="saa-body"><div id="saa-empty">No sensitive patterns detected in your draft.</div></div>
    `;
    document.body.appendChild(panel);
    panel.querySelector("#saa-header").addEventListener("click", () => {
      const body = panel.querySelector("#saa-body");
      body.style.display = body.style.display === "none" ? "block" : "none";
    });
    return panel;
  }

  function renderFindings(findings) {
    buildPanel();
    const body = panel.querySelector("#saa-body");
    if (findings.length === 0) {
      body.innerHTML = `<div id="saa-empty">No sensitive patterns detected in your draft.</div>`;
      panel.dataset.risky = "false";
      return;
    }
    panel.dataset.risky = "true";
    const rows = findings.map((f) => {
      const color = SEVERITY_COLORS[f.severity] || "#8A8F98";
      const label = CATEGORY_LABELS[f.category] || f.category;
      return `<div class="saa-finding" style="border-left-color:${color}">
        <span class="saa-cat" style="color:${color}">${label}</span>
        <span class="saa-sev" style="color:${color};border-color:${color}">${f.severity}</span>
        <div class="saa-reason">${f.reason}</div>
      </div>`;
    }).join("");
    body.innerHTML = rows + `<div class="saa-note">Note: name detection is not available in the browser extension — see the full app for complete coverage.</div>`;
  }

  function findComposer() {
    // ChatGPT's composer has used a few different selectors over time;
    // check the common ones and fall back to any visible contenteditable
    // or textarea near the bottom of the page.
    return (
      document.querySelector("#prompt-textarea") ||
      document.querySelector('div[contenteditable="true"][id*="prompt"]') ||
      document.querySelector('textarea[data-id]') ||
      document.querySelector('main form textarea') ||
      document.querySelector('main form [contenteditable="true"]')
    );
  }

  function getComposerText(el) {
    if (!el) return "";
    return el.innerText !== undefined && el.tagName !== "TEXTAREA" ? el.innerText : el.value || "";
  }

  function runAudit() {
    const el = findComposer();
    const text = getComposerText(el);
    if (!text || !text.trim()) {
      renderFindings([]);
      lastFindings = [];
      return;
    }
    const findings = PrivacyDetectors.auditText(text);
    lastFindings = findings;
    renderFindings(findings);
  }

  function debouncedAudit() {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(runAudit, 400);
  }

  function interceptSend(e) {
    if (lastFindings.length === 0) return; // nothing risky, let it through
    const highSeverity = lastFindings.filter((f) => f.severity === "high").length;
    const summary = lastFindings
      .map((f) => CATEGORY_LABELS[f.category] || f.category)
      .join(", ");
    const proceed = window.confirm(
      `⚠️ Shadow AI Privacy Auditor found ${lastFindings.length} sensitive item(s) ` +
      `(${summary}) in your message${highSeverity ? ", including high-severity findings" : ""}.\n\n` +
      `Send anyway?`
    );
    if (!proceed) {
      e.preventDefault();
      e.stopPropagation();
      e.stopImmediatePropagation();
    }
  }

  function attachSendInterception() {
    // Capture-phase listeners on the whole document so this fires before
    // ChatGPT's own handlers, regardless of exactly which element the
    // click/keypress lands on (send button vs. Enter key in the composer).
    document.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        const el = findComposer();
        if (el && (el === document.activeElement || el.contains(document.activeElement))) {
          interceptSend(e);
        }
      }
    }, true);

    document.addEventListener("click", (e) => {
      const btn = e.target.closest('button[data-testid="send-button"], button[aria-label*="Send" i]');
      if (btn) interceptSend(e);
    }, true);
  }

  function observeComposer() {
    const observer = new MutationObserver(debouncedAudit);
    observer.observe(document.body, { childList: true, subtree: true, characterData: true });
    document.addEventListener("input", debouncedAudit, true);
  }

  function init() {
    buildPanel();
    attachSendInterception();
    observeComposer();
    debouncedAudit();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
