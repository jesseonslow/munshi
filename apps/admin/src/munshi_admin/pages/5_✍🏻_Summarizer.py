"""Operational workbench for monitoring and triggering publication summaries."""
from __future__ import annotations

import streamlit as st
from munshi_admin.client import MunshiApiClient

st.set_page_config(
    page_title="Publication Summarizer",
    page_icon="📝",
    layout="wide",
)

api = MunshiApiClient()

st.title("📝 Publication Summarizer Workbench")
st.caption(
    "Orchestrates grounded primary-source syntheses, abstracts, and keyword hoisting "
    "for substantive scholarly papers (article_type: article)."
)

tab_queue, tab_single, tab_batch = st.tabs([
    "Pending Summaries Queue",
    "Single Article Runner",
    "Batch Execution",
])

# --- TAB 1: Pending Summaries Queue ---
with tab_queue:
    st.subheader("Corpus Summarization Status")

    c1, c2, c3 = st.columns([2, 1, 1])
    with c1:
        search_filter = st.text_input("Filter Title / Slug", placeholder="e.g. Laderman or Balan")
    with c2:
        article_type_select = st.selectbox("Article Subtype", ["article", "note", "All"])
    with c3:
        status_filter = st.selectbox("Status", ["Unsummarized Only", "Summarized Only", "All"])

    at_param = None if article_type_select == "All" else article_type_select
    sum_param = False if status_filter == "Unsummarized Only" else (True if status_filter == "Summarized Only" else None)

    articles_resp = api.list_wiki_articles(
        doc_type="article",
        article_type=at_param,
        summarized=sum_param,
        search=search_filter or None,
    )

    items = articles_resp.get("items", [])
    total_found = articles_resp.get("total", 0)

    st.info(f"Displaying **{len(items)}** candidate articles (Total matching: {total_found})")

    if items:
        grid_data = [
            {
                "Slug": a["slug"],
                "Title": a["title"],
                "Authors": ", ".join(a["authors"]),
                "Year": a["year"],
                "Subtype": a["article_type"],
                "Summarized": "✅ Done" if a["summarized"] else "⏳ Pending",
                "Source Document": a["source_doc"] or "❌ Missing",
            }
            for a in items
        ]
        st.dataframe(grid_data, use_container_width=True)
    else:
        st.success("No articles found matching the selected criteria.")

# --- TAB 2: Single Article Runner & Live Preview ---
with tab_single:
    st.subheader("Interactive Single-Article Summarizer")

    candidate_resp = api.list_wiki_articles(
        doc_type="article",
        article_type="article",
        summarized=False,
    )
    candidate_slugs = [a["slug"] for a in candidate_resp.get("items", [])]

    selected_target = st.selectbox(
        "Select an unsummarized article:",
        candidate_slugs if candidate_slugs else ["No unsummarized articles found"],
    )

    override_slug = st.text_input(
        "Or enter explicit article slug (overrides dropdown above):",
        placeholder="e.g. main-peteri-synopses-of-three-shamanistic-performances",
    )

    target_slug = override_slug.strip() if override_slug.strip() else selected_target

    if target_slug and target_slug != "No unsummarized articles found":
        col_meta, col_actions = st.columns([2, 1])

        with col_meta:
            doc_detail = api.get_wiki_detail(target_slug)
            fm = doc_detail.get("frontmatter", {})
            st.markdown(f"**Title:** {fm.get('title', target_slug)}")
            st.markdown(f"**Author(s):** {', '.join(fm.get('authors', [])) or 'Unknown'}")
            st.markdown(f"**Source Document:** `{fm.get('source_doc', 'None')}`")
            st.markdown(f"**Source Path:** `{fm.get('source_path', 'None')}`")

        with col_actions:
            force_resummarize = st.checkbox("Force Re-summarize (overwrite existing)", value=False)
            model_override = st.selectbox(
                "Model Slug",
                ["qwen/qwen3.8-27b", "qwen/qwen3.5-flash-02-23", "google/gemini-2.5-flash"],
            )
            trigger_button = st.button("Generate & Inject Summary", type="primary", use_container_width=True)

        if trigger_button:
            with st.status("Executing Summarizer Pipeline...", expanded=True) as status:
                st.write("Resolving source documents and verifying coordinates...")
                try:
                    result = api.trigger_summarizer(target_slug, force=force_resummarize, model_override=model_override)
                    status.update(label="Summary Injected Successfully!", state="complete", expanded=False)
                    st.success(f"Article `{target_slug}.md` updated on disk!")
                except Exception as e:
                    status.update(label="Summarization Failed", state="error", expanded=True)
                    st.error(f"Error during execution: {e}")

        st.markdown("---")
        st.subheader("Current Article Body on Disk")
        st.text_area("Markdown Preview", doc_detail.get("body", ""), height=400)

# --- TAB 3: Batch Execution ---
with tab_batch:
    st.subheader("Batch Queue Processor")
    st.write(
        "Safely iterates across unsummarized `article_type: article` records. "
        "Articles lacking primary sources on disk are skipped automatically."
    )

    unsummarized_count = len(candidate_slugs)
    st.metric("Pending Articles in Queue", unsummarized_count)

    batch_limit = st.slider("Batch Size Limit", min_value=1, max_value=50, value=5)

    if st.button("Start Batch Run", type="primary"):
        if unsummarized_count == 0:
            st.info("Queue is already empty!")
        else:
            progress_bar = st.progress(0)
            status_text = st.empty()

            processed = 0
            targets = candidate_slugs[:batch_limit]

            for idx, slug in enumerate(targets):
                status_text.text(f"Processing ({idx+1}/{len(targets)}): {slug}...")
                try:
                    api.trigger_summarizer(slug, force=False)
                except Exception as e:
                    st.warning(f"Failed to process {slug}: {e}")
                processed += 1
                progress_bar.progress(processed / len(targets))

            st.success(f"Batch completed! Processed {processed} articles.")