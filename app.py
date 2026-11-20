"""ClauseWise Streamlit dashboard."""
import json

import streamlit as st

from config import MAX_UPLOAD_MB
from modules.pdf_extractor import DocumentInputError, extract_pdf
from modules.pipeline import analyze_document

st.set_page_config(page_title="ClauseWise", page_icon="🌸", layout="wide")
st.markdown("""
<style>
  :root { --rose: #c34d78; --ink: #382a33; --muted: #806d78; --line: #f0dce5; }
  .stApp { background: linear-gradient(180deg,#fff8fb 0%,#fff 52%); color: var(--ink); }
  [data-testid="stHeader"] { background: rgba(255,248,251,.94); }
  [data-testid="stAppViewContainer"] > .main .block-container { max-width: 1120px; padding-top: 2rem; }
  .hero { background: linear-gradient(125deg,#fae5ee 0%,#fff1f6 58%,#fcecf1 100%); color: #492d3a; padding: 2rem 2.2rem; border: 1px solid #f4d8e4; border-radius: 24px; margin-bottom: 1rem; box-shadow: 0 12px 32px rgba(168,85,120,.08); }
  .hero .eyebrow { color: #a24d70; text-transform: uppercase; letter-spacing: .16em; font-size: .72rem; font-weight: 700; margin: 0 0 .55rem; }
  .hero h1 { font-family: Georgia,serif; font-size: 2.8rem; letter-spacing: -.04em; margin: 0; color: #492d3a; }
  .hero p { color: #715966; margin: .35rem 0 0; font-size: 1.04rem; }
  [data-testid="stVerticalBlockBorderWrapper"] { border-color: var(--line); border-radius: 20px; background: rgba(255,255,255,.9); }
  h2, h3 { color: #492d3a; font-family: Georgia,serif; }
  .stCaption, [data-testid="stCaptionContainer"] { color: var(--muted); }
  .stButton > button, [data-testid="stDownloadButton"] button { border-radius: 12px; border: 1px solid #c34d78; color: white; background: #c34d78; font-weight: 650; transition: all .15s ease; }
  .stButton > button:hover, [data-testid="stDownloadButton"] button:hover { background: #a93c65; border-color: #a93c65; color: white; }
  [data-testid="stFileUploader"] section { background: #fff8fb; border: 1px dashed #e6a8c0; border-radius: 16px; }
  [data-testid="stMetric"] { background: white; border: 1px solid var(--line); border-radius: 16px; padding: .85rem 1rem; box-shadow: 0 5px 16px rgba(168,85,120,.05); }
  [data-testid="stMetricLabel"] { color: #806d78; }
  [data-baseweb="tab-list"] { gap: .35rem; }
  [data-baseweb="tab"] { background: #fff4f8; border-radius: 10px 10px 0 0; color: #725867; }
  [aria-selected="true"] { color: #a93c65 !important; }
  .risk-card { background: white; border: 1px solid #f0dce5; border-radius: 14px; padding: 1rem 1.2rem; margin: .7rem 0; box-shadow: 0 4px 14px rgba(168,85,120,.05); }
  .risk-high { border-left: 5px solid #c64f62; } .risk-medium { border-left: 5px solid #d79542; } .risk-low { border-left: 5px solid #6e9c83; }
  .muted { color: var(--muted); font-size: .9rem; }
  [data-testid="stAlert"] { border-radius: 13px; }
  @media (max-width: 700px) { [data-testid="stAppViewContainer"] > .main .block-container { padding: 1rem .8rem; } .hero { padding: 1.4rem; border-radius: 18px; } .hero h1 { font-size: 2.2rem; } }
</style>
<div class="hero"><p class="eyebrow">Your fine-print companion</p><h1>ClauseWise</h1><p>Make sense of the details, know what to look for, and feel more confident before you agree.</p></div>
""", unsafe_allow_html=True)
st.caption("Educational document analysis. ClauseWise is not a law firm and does not provide legal advice.")

with st.container(border=True):
    st.subheader("Add a document")
    method = st.radio("Choose an input", ["Upload PDF", "Paste text"], horizontal=True, label_visibility="collapsed")
    document_text = ""
    if method == "Upload PDF":
        uploaded = st.file_uploader("Upload a Terms & Conditions or Privacy Policy PDF", type=["pdf"], help=f"Maximum file size: {MAX_UPLOAD_MB} MB")
        if uploaded:
            if uploaded.size > MAX_UPLOAD_MB * 1024 * 1024:
                st.error(f"This PDF exceeds the {MAX_UPLOAD_MB} MB upload limit.")
            else:
                try:
                    document_text = extract_pdf(uploaded.getvalue())
                    st.success(f"PDF text extracted ({len(document_text):,} characters).")
                except DocumentInputError as exc:
                    st.error(str(exc))
    else:
        document_text = st.text_area("Paste the document text", height=220, placeholder="Paste the complete policy or terms here…")
    analyze = st.button("Analyse document", type="primary", disabled=not bool(document_text.strip()), use_container_width=True)

if analyze:
    progress_bar = st.progress(0, text="Starting analysis…")
    try:
        result = analyze_document(document_text, progress=lambda fraction, label: progress_bar.progress(fraction, text=label))
        st.session_state["analysis"] = result
        st.session_state["source_length"] = len(document_text)
        progress_bar.empty()
    except (DocumentInputError, Exception) as exc:
        progress_bar.empty()
        st.error(f"Analysis could not be completed. {exc}")

result = st.session_state.get("analysis")
if result:
    st.divider()
    st.header(result["title"] or "Document analysis")
    st.caption(f"{result['document_type']} · {st.session_state.get('source_length', 0):,} source characters")
    risks = result["risks"]
    high = sum(r["risk_level"] == "High" for r in risks)
    medium = sum(r["risk_level"] == "Medium" for r in risks)
    low = sum(r["risk_level"] == "Low" for r in risks)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Potentially concerning clauses", len(risks))
    c2.metric("High", high)
    c3.metric("Medium", medium)
    c4.metric("Low", low)

    tab_summary, tab_risks, tab_terms, tab_sections = st.tabs(["Plain-language summary", "Risk overview", "Your rights & obligations", "Sections"])
    with tab_summary:
        st.subheader("In simple English")
        st.write(result["summary"])
        if result["unclear_points"]:
            st.subheader("Points that may need clarification")
            for point in result["unclear_points"]:
                st.markdown(f"- {point}")
    with tab_risks:
        st.subheader("Potentially concerning clauses")
        st.caption("Risk levels help prioritise review; they are informational, not legal judgments.")
        if not risks:
            st.info("No supported clauses from the monitored categories were identified in this document.")
        for item in risks:
            level = item["risk_level"]
            css_level = level.lower()
            st.markdown(f'<div class="risk-card risk-{css_level}"><strong>{level} · {item["category"]}</strong><p class="muted">{item["source_location"] or "Location not specified"}</p></div>', unsafe_allow_html=True)
            left, right = st.columns(2)
            with left:
                st.markdown("**Original clause**")
                st.info(item["original_excerpt"])
            with right:
                st.markdown("**In plain language**")
                st.write(item["plain_language"])
                st.markdown("**Why pay attention**")
                st.write(item["why_attention"])
    with tab_terms:
        left, right = st.columns(2)
        with left:
            st.subheader("Your obligations")
            if result["important_obligations"]:
                for item in result["important_obligations"]: st.markdown(f"- {item}")
            else: st.write("No specific user obligations were extracted.")
        with right:
            st.subheader("Your rights")
            if result["user_rights"]:
                for item in result["user_rights"]: st.markdown(f"- {item}")
            else: st.write("No specific user rights were extracted.")
    with tab_sections:
        for section in result["sections"]:
            with st.expander(section["name"] or "Section"):
                st.write(section["description"])
                if section["source_excerpt"]: st.caption(section["source_excerpt"])
    report = {**result, "verification_note": "Risk items were checked against the supplied source text. Risk levels are informational and are not legal judgments."}
    st.download_button("Download analysis report (JSON)", json.dumps(report, ensure_ascii=False, indent=2), file_name="clausewise-analysis.json", mime="application/json")
    st.caption(result["disclaimer"])
