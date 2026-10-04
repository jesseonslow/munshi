"""Janitorial Re-attribution & Source Alignment Module."""
from __future__ import annotations

from collections import defaultdict
import streamlit as st
from munshi_admin.client import MunshiApiClient

st.set_page_config(page_title="Janitorial Desk", page_icon="⚖️", layout="wide")
api = MunshiApiClient()

st.title("⚖️ Janitorial Mutation Desk")

tab_author, tab_sources = st.tabs(["Author Reconciliation", "Source Path Integrity"])

# --- TAB 1: Author Discrepancies ---
with tab_author:
    st.subheader("Author Attribution Discrepancies")
    conflicts = api.get_attribution_conflicts()

    if not conflicts:
        st.success("No author attribution conflicts detected!")
    else:
        st.warning(f"Found **{len(conflicts)}** pending attribution conflicts.")

        # Group conflicts by (old_name, can_slug, can_name) for Bulk Actions
        groups = defaultdict(list)
        for conf in conflicts:
            old_name = conf["article_stated_authors"][0] if conf.get("article_stated_authors") else "Unknown"
            can_slug = conf.get("claiming_author_slug") or (
                conf["claimed_by_author_profiles"][0] if conf.get("claimed_by_author_profiles") else ""
            )
            can_name = conf.get("claiming_author_name") or can_slug.replace("-", " ").title()
            groups[(old_name, can_slug, can_name)].append(conf)

        bulk_eligible = {k: v for k, v in groups.items() if len(v) > 1}
        if bulk_eligible:
            st.subheader("⚡ Bulk Reassignments")
            for (old_name, can_slug, can_name), items in bulk_eligible.items():
                with st.container(border=True):
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.markdown(
                            f"**Pattern:** Reassign all **`{len(items)}`** articles from "
                            f"**`{old_name}`** to **`{can_name}`** (`{can_slug}`)"
                        )
                        st.caption(", ".join(x["publication_slug"] for x in items[:4]) + ("..." if len(items) > 4 else ""))
                    with col2:
                        if st.button(f"Fix All {len(items)}", key=f"bulk_{old_name}_{can_slug}", type="primary"):
                            with st.spinner(f"Reassigning {len(items)} articles across wiki graph..."):
                                res = api.batch_reassign_author(
                                    old_author_name=old_name,
                                    new_author_name=can_name,
                                    new_author_slug=can_slug,
                                )
                                st.success(res.get("detail", "Batch completed successfully!"))
                                st.rerun()

        st.markdown("---")
        st.subheader("Individual Conflict Queue")
        for idx, conf in enumerate(conflicts):
            with st.expander(f"Conflict #{idx+1}: {conf['publication_slug']}", expanded=(idx < 2)):
                col_a, col_b = st.columns(2)
                with col_a:
                    st.write(f"**Publication Slug:** `{conf['publication_slug']}`")
                    st.write(f"**Frontmatter Authors:** `{conf.get('article_stated_authors', [])}`")
                with col_b:
                    st.write(f"**Claimed By Profile:** `{conf.get('claimed_by_author_profiles', [])}`")
                    st.write(f"**Discrepancy:** `{conf.get('discrepancy_type', 'mismatch')}`")

                default_old_name = conf["article_stated_authors"][0] if conf.get("article_stated_authors") else ""
                default_can_slug = conf.get("claiming_author_slug") or (
                    conf["claimed_by_author_profiles"][0] if conf.get("claimed_by_author_profiles") else ""
                )
                default_can_name = conf.get("claiming_author_name") or default_can_slug.replace("-", " ").title()

                with st.form(f"resolve_author_form_{idx}"):
                    f1, f2 = st.columns(2)
                    with f1:
                        old_auth = st.text_input("Old Author Name", value=default_old_name)
                        old_slug = st.text_input("Old Author Slug (Optional)", value="")
                    with f2:
                        new_auth = st.text_input("Canonical Author Name", value=default_can_name)
                        new_slug = st.text_input("Canonical Author Slug", value=default_can_slug)

                    if st.form_submit_button("Reassign Across Wiki Graph", type="primary"):
                        try:
                            res = api.reassign_author(
                                publication_slug=conf["publication_slug"],
                                old_author_name=old_auth,
                                new_author_name=new_auth,
                                new_author_slug=new_slug,
                                old_author_slug=old_slug.strip() or None,
                            )
                            st.success(f"Patched {len(res['modified_files'])} file(s): {', '.join(res['modified_files'][:3])}")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")

# --- TAB 2: Source Path Mismatches ---
with tab_sources:
    st.subheader("Source Path Alignment")
    mismatches = api.get_source_mismatches()

    if not mismatches:
        st.success("All articles resolve cleanly to authentic sources!")
    else:
        st.error(f"Found **{len(mismatches)}** articles with source path anomalies.")
        for idx, m in enumerate(mismatches):
            with st.expander(f"⚠️ {m['wiki_slug']} — [{m['error_type']}]", expanded=False):
                st.write(f"**Detail:** {m['detail']}")
                st.write(f"**Current:** `{m['current_source_path']}`")
                if m.get("suggested_source_path"):
                    st.info(f"Remedy: `{m['suggested_source_path']}`")
                    if st.button("Apply Suggested Fix", key=f"fix_btn_{idx}"):
                        try:
                            api.fix_source_path(
                                m["wiki_slug"],
                                m["suggested_source_path"],
                                m.get("suggested_doc_id"),
                            )
                            st.success("Updated!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed: {e}")