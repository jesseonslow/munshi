"""Docproc Ingestion & OCR Workbench."""
from __future__ import annotations

import streamlit as st
from munshi_admin.client import MunshiApiClient

st.set_page_config(page_title="Docproc Ingest", page_icon="📥", layout="wide")
api = MunshiApiClient()

st.title("📥 Docproc Ingestion & OCR Hub")
st.markdown(
    "Upload scanned PDF issues or monographs to extract reading orders, bounding boxes, "
    "and `<span id=\"page-N\">` anchored Markdown into the primary sources corpus."
)

col_upload, col_settings = st.columns([3, 1])

with col_upload:
    uploaded_files = st.file_uploader(
        "Upload Primary Source PDF(s)",
        type=["pdf"],
        accept_multiple_files=True,
    )

with col_settings:
    st.markdown("##### Pipeline Settings")
    engine_choice = st.selectbox(
        "VLM Extraction Engine",
        ["qwen-vl", "pymupdf-text", "gemini-2.5-flash"],
        help="Model used to resolve reading orders and multi-column tables.",
    )
    force_ocr = st.checkbox("Force VLM pass on text-layer pages", value=False)

if uploaded_files:
    st.info(f"Staged **{len(uploaded_files)}** document(s) for ingestion.")
    
    if st.button("🚀 Begin Ingestion & Extraction Pass", type="primary"):
        # Package files as byte payloads for transmission
        file_payload = [
            (f.name, f.getvalue())
            for f in uploaded_files
        ]

        with st.status("Executing Docproc Pipeline...", expanded=True) as status_box:
            log_container = st.empty()
            accumulated_logs: list[str] = []

            try:
                for line in api.stream_docproc_run(file_payload, engine_override=engine_choice):
                    accumulated_logs.append(line)
                    # Display the latest 25 lines in an active terminal box
                    log_container.code("\n".join(accumulated_logs[-25:]), language="log")

                status_box.update(
                    label="Ingestion and Stitching Completed Successfully!",
                    state="complete",
                    expanded=True,
                )
                st.success(f"Processed {len(uploaded_files)} documents into the `sources/` corpus.")
            except Exception as e:
                status_box.update(label="Docproc Worker Failed", state="error", expanded=True)
                st.error(f"Execution error: {e}")

st.markdown("---")
st.subheader("Inspection & Verification")
st.caption(
    "Once ingested, documents become accessible for coordinate audits in the **Janitor** "
    "and text summarization in the **Publication Summarizer**."
)