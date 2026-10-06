"""OKF Synthesis Studio."""
from __future__ import annotations

import streamlit as st
from munshi_admin.client import MunshiApiClient

st.set_page_config(page_title="Synthesis Studio", page_icon="⚡", layout="wide")
api = MunshiApiClient()

st.title("⚡ Open Knowledge Format (OKF) Synthesis Studio")
st.markdown("Generate grounded, dual-retrieval encyclopedia articles from primary evidence passages.")

col_a, col_b = st.columns([2, 1])
with col_a:
    entity_name = st.text_input("Target Entity / Subject", placeholder="e.g. Frank Swettenham, Klang War, Ban Hin Lee Bank")
with col_b:
    template = st.selectbox("Template Type", ["person", "place", "event", "concept", "group", "publication"])

if st.button("Synthesize Article", type="primary"):
    if entity_name:
        with st.spinner(f"Aggregating evidence and generating {entity_name}..."):
            st.warning("Synthesis worker trigger ready in `apps/api`: `POST /api/synthesizer/generate`.")
    else:
        st.error("Please specify a target entity.")