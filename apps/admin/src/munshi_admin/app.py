"""Mat Munshi Administrative Cockpit - Executive Overview & Status."""
from __future__ import annotations

import streamlit as st
from munshi_admin.client import MunshiApiClient

st.set_page_config(
    page_title="Mat Munshi Cockpit",
    page_icon="📜",
    layout="wide",
    initial_sidebar_state="expanded",
)

pg = st.navigation([
    st.Page("pages/1_📚_Wiki_Catalog.py", title="Wiki Catalog", icon=":material/menu_book:"),
    st.Page("pages/2_🧹_Janitor.py", title="Janitor & Reconciliation", icon=":material/build:"),
    st.Page("pages/3_📥_Docproc.py", title="Docproc Pipeline", icon=":material/upload_file:"),
    st.Page("pages/4_🗄️_Ledger.py", title="Entity Ledger", icon=":material/database:"),
    st.Page("pages/5_✍🏻_Summarizer.py", title="Publication Summarizer", icon=":material/summarize:"),
    st.Page("pages/6_⚡_Synthesizer.py", title="Topic Synthesizer", icon=":material/auto_stories:"),
])
pg.run()

api = MunshiApiClient()

# Global Sidebar
with st.sidebar:
    st.title("📜 Mat Munshi")
    st.caption("Archival Administration & Integrity Cockpit")

    if api.ping():
        st.success("API Control Plane: Online")
    else:
        st.error("API Control Plane: Offline")
        st.code("uv run uvicorn munshi_api.app:app --port 8000")
        st.stop()

    st.markdown("---")
    st.info("Use the navigation links in the sidebar to jump between modules.")

# Executive Overview Dashboard
st.title("🏛️ Mat Munshi Pipeline Overview")
st.markdown(
    "Control plane and health monitor for historical document extraction, "
    "occurrence indexing, and Open Knowledge Format (OKF) synthesis."
)

health = api.get_graph_health()
conflicts = api.get_attribution_conflicts()
source_issues = api.get_source_mismatches()

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Total Wiki Entities", health.get("total_entities", 0))
with col2:
    st.metric("Broken Outbound Links", health.get("broken_link_count", 0))
with col3:
    st.metric("Attribution Conflicts", len(conflicts), delta_color="inverse")
with col4:
    st.metric("Source Path Issues", len(source_issues), delta_color="inverse")

st.markdown("---")

c_left, c_right = st.columns(2)

with c_left:
    st.subheader("⚠️ Priority Janitorial Backlog")
    if conflicts:
        st.warning(f"**{len(conflicts)} author discrepancies** require reassignment.")
        for c in conflicts[:3]:
            st.markdown(
                f"- `{c['publication_slug']}`: Stated as **{c.get('article_stated_authors', [])}**, "
                f"claimed by **{c.get('claimed_by_author_profiles', [])}**"
            )
    else:
        st.success("Author attributions are completely aligned across the graph.")

    if source_issues:
        st.error(f"**{len(source_issues)} source path anomalies** detected.")
        for s in source_issues[:3]:
            st.markdown(f"- `{s['wiki_slug']}`: {s['detail']}")
    else:
        st.success("All wiki stubs resolve cleanly to source documents.")

with c_right:
    st.subheader("⚡ Quick Actions")
    st.markdown("Direct pipeline triggers:")
    if st.button("🔄 Refresh Graph Health Audit", use_container_width=True):
        st.rerun()

    st.markdown("##### Subsystem Run Status")
    st.markdown(
        "- **Docproc (Tier 1 & 2):** Ready (Processes PDFs $\\rightarrow$ JSONL $\\rightarrow$ `<span id=\"page-N\">` Markdown)\n"
        "- **Ledger (Tier 3 & 4):** Ready (Tracks occurrences in `entity_ledger.db`)\n"
        "- **Synthesizer (Tier 5):** Ready (Open Knowledge Format dual-RAG generator)"
    )