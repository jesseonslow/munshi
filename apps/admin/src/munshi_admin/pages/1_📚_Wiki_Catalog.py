"""Wiki Catalog & Inspection Module."""
from __future__ import annotations

import streamlit as st
from munshi_admin.client import MunshiApiClient

st.set_page_config(page_title="Wiki Catalog", page_icon="📚", layout="wide")
api = MunshiApiClient()

st.title("📚 Wiki Catalog & Document Inspector")

c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
with c1:
    search_query = st.text_input("Search Title or Slug", placeholder="e.g. Swettenham or Klang War")
with c2:
    type_filter = st.selectbox("Type", ["All", "article", "person", "journal_issue", "concept"])
with c3:
    art_type_filter = st.selectbox("Article Subtype", ["All", "article", "note", "obituary", "book_review"])
with c4:
    summary_filter = st.selectbox("Summarized", ["All", "Yes", "No"])

tf = None if type_filter == "All" else type_filter
atf = None if art_type_filter == "All" else art_type_filter
sf = None if summary_filter == "All" else (True if summary_filter == "Yes" else False)

articles_data = api.list_wiki_articles(
    doc_type=tf, article_type=atf, summarized=sf, search=search_query or None
)

st.info(f"Showing **{len(articles_data.get('items', []))}** of {articles_data.get('total', 0)} entities")

if articles_data.get("items"):
    table_rows = [
        {
            "Slug": a["slug"],
            "Title": a["title"],
            "Type": f"{a['type']} ({a['article_type'] or '-'})",
            "Authors": ", ".join(a["authors"]),
            "Year": a["year"],
            "Summarized": "✅" if a["summarized"] else "⏳",
            "Source Linked": "✅" if a["source_path"] or a["source_doc"] else "❌",
        }
        for a in articles_data["items"]
    ]
    st.dataframe(table_rows, use_container_width=True)

    st.markdown("---")
    st.subheader("🔍 Article Inspector")
    all_slugs = [a["slug"] for a in articles_data["items"]]
    selected_slug = st.selectbox("Select document to inspect:", all_slugs)

    if selected_slug:
        doc_detail = api.get_wiki_detail(selected_slug)
        left_col, right_col = st.columns([1, 1])

        with left_col:
            st.markdown("**YAML Frontmatter**")
            st.json(doc_detail["frontmatter"])

        with right_col:
            st.markdown("**Body Markdown**")
            st.text_area("Content", doc_detail["body"], height=480)