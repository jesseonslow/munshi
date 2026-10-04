"""Docproc Ingestion & OCR Workbench."""
from __future__ import annotations

import streamlit as st
from munshi_admin.client import MunshiApiClient

st.set_page_config(page_title="Docproc Ingest", page_icon="📥", layout="wide")
api = MunshiApiClient()

st.title("📥 Docproc Ingestion & OCR Hub")
st.markdown("Upload raw PDF issues or monographs to extract reading orders, bounding boxes, and `<span id=\"page-N\">` Markdown.")

uploaded_files = st.file_uploader("Upload Scanned PDF(s)", type=["pdf"], accept_multiple_files=True)
if uploaded_files:
    st.info(f"Staged {len(uploaded_files)} document(s) for ingestion.")
    if st.button("Begin OCR & Stitching Pass", type="primary"):
        st.warning("Worker dispatch endpoint ready in `apps/api`: `POST /api/docproc/upload`.")

st.markdown("---")
st.subheader("Running Extraction Workers")
st.caption("Active PyMuPDF and OpenRouter VLM jobs will stream here via Server-Sent Events (SSE).")