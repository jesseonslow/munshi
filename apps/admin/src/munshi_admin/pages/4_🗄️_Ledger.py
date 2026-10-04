"""Entity Ledger & Curation Manager."""
from __future__ import annotations

import streamlit as st
from munshi_admin.client import MunshiApiClient

st.set_page_config(page_title="Entity Ledger", page_icon="🧠", layout="wide")
api = MunshiApiClient()

st.title("🧠 Entity Ledger & Authority Curator")
st.markdown("Browse entities extracted from `entity_ledger.db`, manage historical aliases, and maintain the ignore list.")

c1, c2 = st.columns(2)
with c1:
    tier = st.selectbox("Tier", ["All", "A", "B", "C"])
with c2:
    category = st.selectbox("Category", ["All", "person", "place", "event", "concept", "group"])

t_param = None if tier == "All" else tier
c_param = None if category == "All" else category

entities = api.list_ledger_entities(tier=t_param, category=c_param)

if entities:
    st.dataframe(entities, use_container_width=True)
else:
    st.info("No entities returned from ledger query.")