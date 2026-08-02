# app.py
import streamlit as st
from src.engine import PrivacyAuditorEngine

st.set_page_config(page_title="Shadow AI Privacy Auditor", layout="wide", page_icon="■")

# ---------------------------------------------------------------------------
# Visual identity: a "classified document" aesthetic — dark slate background,
# monospace headers evoking a terminal/redaction stamp, and findings rendered
# as colored underline-marks by category (not a generic yellow highlight).
# ---------------------------------------------------------------------------
CATEGORY_COLORS = {
    "NAME":                 "#4FB0A5",  # teal   - identity
    "CONTACT_INFO":         "#4FB0A5",  # teal   - identity
    "GOVT_IDENTIFIER":      "#F2A541",  # amber  - regulated ID
    "FINANCIAL_IDENTIFIER": "#E4572E",  # red    - high risk
    "CREDENTIALS":          "#E4572E",  # red    - high risk
    "MEDICAL_INFO":         "#F2A541",  # amber  - regulated ID
    "EMPLOYEE_INFO":        "#8B7FD1",  # violet - org data
    "CONFIDENTIAL_INFO":    "#8B7FD1",  # violet - org data
}
CATEGORY_LABELS = {
    "NAME": "Name",
    "CONTACT_INFO": "Contact Info",
    "GOVT_IDENTIFIER": "Government ID",
    "FINANCIAL_IDENTIFIER": "Financial ID",
    "CREDENTIALS": "Credential / Secret",
    "MEDICAL_INFO": "Medical Info",
    "EMPLOYEE_INFO": "Employee / Client Info",
    "CONFIDENTIAL_INFO": "Confidential Info",
}

mark_css = "\n".join(
    f'.finding-{cat} {{ background: {color}22; border-bottom: 2px solid {color}; '
    f'color: {color}; }}'
    for cat, color in CATEGORY_COLORS.items()
)

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;700&family=IBM+Plex+Sans:wght@400;500&display=swap');

html, body, [class*="css"]  {{
    font-family: 'IBM Plex Sans', sans-serif;
}}

.stApp {{
    background-color: #14171C;
    color: #E8E6E1;
}}

.sa-header {{
    font-family: 'IBM Plex Mono', monospace;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    font-size: 0.78rem;
    color: #8A8F98;
    border-bottom: 1px solid #2A2E36;
    padding-bottom: 0.6rem;
    margin-bottom: 0.4rem;
}}

.sa-title {{
    font-family: 'IBM Plex Mono', monospace;
    font-size: 2.1rem;
    font-weight: 700;
    color: #E8E6E1;
    margin: 0.1rem 0 0.2rem 0;
}}

.sa-title span {{
    background: #E4572E;
    color: #14171C;
    padding: 0 0.4rem;
}}

.sa-sub {{
    color: #8A8F98;
    font-size: 0.95rem;
    margin-bottom: 1.6rem;
}}

.sa-panel-label {{
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.75rem;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: #8A8F98;
    margin-bottom: 0.5rem;
}}

.sa-doc {{
    background: #1B1F26;
    border: 1px solid #2A2E36;
    border-radius: 4px;
    padding: 1.1rem 1.2rem;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.92rem;
    line-height: 1.7;
    white-space: pre-wrap;
    min-height: 220px;
}}

mark.finding {{
    padding: 0.05rem 0.15rem;
    border-radius: 2px;
    font-weight: 500;
    cursor: help;
}}

.sa-legend {{
    display: flex;
    flex-wrap: wrap;
    gap: 0.9rem;
    margin-top: 0.9rem;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.75rem;
    color: #8A8F98;
}}

.sa-legend-item {{ display: flex; align-items: center; gap: 0.4rem; }}
.sa-dot {{ width: 9px; height: 9px; border-radius: 50%; display: inline-block; }}

.sa-finding-row {{
    border-left: 3px solid #2A2E36;
    padding: 0.5rem 0.8rem;
    margin-bottom: 0.5rem;
    background: #1B1F26;
    border-radius: 0 4px 4px 0;
}}

.sa-finding-cat {{
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    font-weight: 700;
}}

.sa-finding-reason {{
    color: #B8BCC4;
    font-size: 0.85rem;
    margin-top: 0.15rem;
}}

{mark_css}

div.stButton > button {{
    background: #E4572E;
    color: #14171C;
    border: none;
    font-family: 'IBM Plex Mono', monospace;
    font-weight: 700;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    border-radius: 3px;
}}
div.stButton > button:hover {{
    background: #F2723F;
    color: #14171C;
}}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="sa-header">Community Dreams Foundation // Shadow AI Hackathon</div>', unsafe_allow_html=True)
st.markdown('<div class="sa-title">PRIVACY <span>AUDITOR</span></div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sa-sub">Scan text for sensitive information before it leaves your hands for a public AI tool. '
    'Nothing here is sent anywhere — a local NER model and pattern/validation rules run entirely on this machine, in this session.</div>',
    unsafe_allow_html=True,
)

if 'engine' not in st.session_state:
    st.session_state.engine = PrivacyAuditorEngine()
engine = st.session_state.engine

col1, col2 = st.columns(2, gap="large")

with col1:
    st.markdown('<div class="sa-panel-label">01 / Source text</div>', unsafe_allow_html=True)
    raw_input = st.text_area(
        "source_text",
        height=280,
        placeholder="Dear John Doe, the password to database alpha is 'k9#mPq2_zL' and my contact is test@company.com...",
        label_visibility="collapsed",
    )
    run_audit = st.button("Run audit", type="primary", use_container_width=True)

    if run_audit and raw_input.strip():
        findings = engine.audit_text(raw_input)
        st.session_state.last_findings = findings
        st.session_state.last_text = raw_input
        st.session_state.ml_available = engine.ml_available
    elif run_audit:
        st.session_state.last_findings = None

    if st.session_state.get("ml_available") is False:
        st.warning(
            "⚠️ NAME detection is unavailable right now — the ML model (spaCy) failed to load. "
            "All other categories (contact info, government/financial IDs, credentials, medical, "
            "employee/client, confidential org info) are still fully active. "
            "See docs/model_card.md for troubleshooting.",
            icon="⚠️",
        )

    if st.session_state.get("last_findings") is not None:
        st.markdown('<div class="sa-panel-label" style="margin-top:1.4rem;">Marked original</div>', unsafe_allow_html=True)
        findings = st.session_state.last_findings
        text = st.session_state.last_text
        if findings:
            html = engine.highlight_html(text, findings)
        else:
            import html as _html
            html = _html.escape(text)
        st.markdown(f'<div class="sa-doc">{html}</div>', unsafe_allow_html=True)

        present_cats = sorted(set(f['category'] for f in findings))
        if present_cats:
            legend_items = "".join(
                f'<span class="sa-legend-item"><span class="sa-dot" style="background:{CATEGORY_COLORS.get(c, "#8A8F98")}"></span>{CATEGORY_LABELS.get(c, c)}</span>'
                for c in present_cats
            )
            st.markdown(f'<div class="sa-legend">{legend_items}</div>', unsafe_allow_html=True)

with col2:
    st.markdown('<div class="sa-panel-label">02 / Findings & safe output</div>', unsafe_allow_html=True)

    if st.session_state.get("last_findings") is None:
        st.markdown(
            '<div class="sa-doc" style="color:#565C66;">Run an audit to see findings here.</div>',
            unsafe_allow_html=True,
        )
    else:
        findings = st.session_state.last_findings
        text = st.session_state.last_text

        if not findings:
            st.markdown(
                '<div class="sa-doc" style="border-color:#2F7A5F; color:#7FD4AE;">'
                'No sensitive patterns detected. Text appears safe to share.</div>',
                unsafe_allow_html=True,
            )
        else:
            risk = engine.risk_score(findings)
            risk_colors = {
                "Critical": "#E4572E",
                "High": "#E4572E",
                "Medium": "#F2A541",
                "Low": "#4FB0A5",
                "Clean": "#4FB0A5",
            }
            risk_color = risk_colors.get(risk["label"], "#8A8F98")
            st.markdown(
                f'<div class="sa-finding-row" style="border-left-color:{risk_color}; margin-bottom:1rem;">'
                f'<span class="sa-finding-cat" style="color:{risk_color}; font-size:0.95rem;">'
                f'Overall risk: {risk["label"]} (score {risk["weighted_score"]})</span>'
                f'<div class="sa-finding-reason">'
                f'{risk["counts"]["high"]} high · {risk["counts"]["medium"]} medium · {risk["counts"]["low"]} low severity finding(s)'
                f'</div></div>',
                unsafe_allow_html=True,
            )

            st.markdown(f'<div class="sa-panel-label">{len(findings)} finding(s)</div>', unsafe_allow_html=True)
            severity_badge_colors = {"high": "#E4572E", "medium": "#F2A541", "low": "#4FB0A5"}
            for f in findings:
                color = CATEGORY_COLORS.get(f["category"], "#8A8F98")
                label = CATEGORY_LABELS.get(f["category"], f["category"])
                sev = f.get("severity", "low")
                sev_color = severity_badge_colors.get(sev, "#8A8F98")
                st.markdown(
                    f'<div class="sa-finding-row" style="border-left-color:{color};">'
                    f'<span class="sa-finding-cat" style="color:{color};">{label}</span>'
                    f'<span style="float:right; font-family:\'IBM Plex Mono\',monospace; font-size:0.7rem; '
                    f'text-transform:uppercase; color:{sev_color}; border:1px solid {sev_color}; '
                    f'padding:0.1rem 0.4rem; border-radius:2px;">{sev}</span>'
                    f'<div class="sa-finding-reason">{f["reason"]}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

            st.markdown('<div class="sa-panel-label" style="margin-top:1.2rem;">Redacted — safe to share</div>', unsafe_allow_html=True)
            redacted = engine.redact_text(text, findings)
            st.text_area("redacted_output", value=redacted, height=180, label_visibility="collapsed")
            st.download_button("Copy / download safe text", data=redacted, file_name="redacted_output.txt", use_container_width=True)