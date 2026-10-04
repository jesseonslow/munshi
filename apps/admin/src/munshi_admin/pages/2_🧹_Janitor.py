"""Janitorial Re-attribution & Source Alignment Module."""
from __future__ import annotations

from collections import defaultdict
import streamlit as st
from munshi_admin.client import MunshiApiClient

st.set_page_config(page_title="Janitorial Desk", page_icon="⚖️", layout="wide")
api = MunshiApiClient()

# -----------------------------------------------------------------------------
# Cached Data Fetchers (Maintains sub-100ms UI responsiveness)
# -----------------------------------------------------------------------------
@st.cache_data(ttl=120, show_spinner="Loading author attribution discrepancies...")
def fetch_attribution_conflicts() -> list[dict]:
    return api.get_attribution_conflicts()


@st.cache_data(ttl=120, show_spinner="Auditing source document alignments...")
def fetch_source_mismatches() -> list[dict]:
    return api.get_source_mismatches()


st.title("⚖️ Janitorial Mutation Desk")
st.caption(
    "Orchestrates atomic multi-file graph repairs: reconciling publication authors, "
    "synchronizing issue tables of contents, and patching broken primary source coordinates."
)

tab_author, tab_sources = st.tabs(["Author Reconciliation", "Source Path Integrity"])

# =============================================================================
# TAB 1: Author Discrepancies
# =============================================================================
with tab_author:
    c_head1, c_head2 = st.columns([4, 1])
    with c_head1:
        st.subheader("Author Attribution Discrepancies")
        st.write(
            "Identifies publications where author profile bibliographies claim a work, "
            "but the publication stub frontmatter lists a mismatched variant (e.g. abbreviations, initials, or collisions)."
        )
    with c_head2:
        if st.button("🔄 Refresh Audit", key="refresh_authors_btn", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    conflicts = fetch_attribution_conflicts()

    if not conflicts:
        st.success("✨ Author attributions are completely aligned across the entire wiki graph!")
    else:
        st.warning(f"Found **{len(conflicts)}** pending author attribution conflicts.")

        # Group conflicts by (old_name, canonical_slug, canonical_name) for Bulk Actions
        groups: dict[tuple[str, str, str], list[dict]] = defaultdict(list)
        for conf in conflicts:
            old_name = (
                conf["article_stated_authors"][0]
                if conf.get("article_stated_authors")
                else "Unknown"
            )
            can_slug = conf.get("claiming_author_slug") or (
                conf["claimed_by_author_profiles"][0]
                if conf.get("claimed_by_author_profiles")
                else ""
            )
            can_name = conf.get("claiming_author_name") or can_slug.replace("-", " ").title()
            groups[(old_name, can_slug, can_name)].append(conf)

        bulk_eligible = {k: v for k, v in groups.items() if len(v) > 1}
        if bulk_eligible:
            st.subheader("⚡ Bulk Reassignments")
            st.caption("Apply identical author reconciliations across multiple articles in a single atomic batch.")
            for (old_name, can_slug, can_name), items in bulk_eligible.items():
                with st.container(border=True):
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.markdown(
                            f"**Pattern:** Reassign all **`{len(items)}`** articles from "
                            f"**`{old_name}`** to **`{can_name}`** (`{can_slug}`)"
                        )
                        st.caption(
                            ", ".join(x["publication_slug"] for x in items[:5])
                            + ("..." if len(items) > 5 else "")
                        )
                    with col2:
                        if st.button(
                            f"Fix All ({len(items)})",
                            key=f"bulk_{old_name}_{can_slug}",
                            type="primary",
                            use_container_width=True,
                        ):
                            with st.spinner(f"Reassigning {len(items)} articles across wiki graph..."):
                                try:
                                    res = api.batch_reassign_author(
                                        old_author_name=old_name,
                                        new_author_name=can_name,
                                        new_author_slug=can_slug,
                                    )
                                    st.success(res.get("detail", f"Successfully updated {len(items)} publications!"))
                                    st.cache_data.clear()
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Batch reassignment failed: {e}")

        st.markdown("---")
        st.subheader("Individual Conflict Queue")

        for idx, conf in enumerate(conflicts):
            pub_slug = conf["publication_slug"]
            with st.expander(f"Conflict #{idx+1}: {pub_slug}", expanded=(idx < 2)):
                col_a, col_b = st.columns(2)
                with col_a:
                    st.markdown(f"**Publication Slug:** `{pub_slug}`")
                    st.markdown(f"**Stated Authors (Frontmatter):** `{conf.get('article_stated_authors', [])}`")
                    if conf.get("article_stated_editors"):
                        st.markdown(f"**Stated Editors:** `{conf.get('article_stated_editors', [])}`")
                with col_b:
                    st.markdown(f"**Claimed By Profile:** `{conf.get('claimed_by_author_profiles', [])}`")
                    st.markdown(f"**Discrepancy:** `{conf.get('discrepancy_type', 'mismatch')}`")

                default_old_name = (
                    conf["article_stated_authors"][0]
                    if conf.get("article_stated_authors")
                    else ""
                )
                default_can_slug = conf.get("claiming_author_slug") or (
                    conf["claimed_by_author_profiles"][0]
                    if conf.get("claimed_by_author_profiles")
                    else ""
                )
                default_can_name = (
                    conf.get("claiming_author_name")
                    or default_can_slug.replace("-", " ").title()
                )

                with st.form(f"resolve_author_form_{idx}"):
                    f1, f2 = st.columns(2)
                    with f1:
                        old_auth = st.text_input("Old Author Name", value=default_old_name)
                        old_slug = st.text_input("Old Author Slug (Optional)", value="")
                    with f2:
                        new_auth = st.text_input("Canonical Author Name", value=default_can_name)
                        new_slug = st.text_input("Canonical Author Slug", value=default_can_slug)

                    submitted = st.form_submit_button("Reassign Across Wiki Graph", type="primary")
                    if submitted:
                        try:
                            res = api.reassign_author(
                                publication_slug=pub_slug,
                                old_author_name=old_auth,
                                new_author_name=new_auth,
                                new_author_slug=new_slug,
                                old_author_slug=old_slug.strip() or None,
                            )
                            st.success(
                                f"Patched {len(res.get('modified_files', []))} file(s): "
                                f"{', '.join(res.get('modified_files', [])[:3])}"
                            )
                            st.cache_data.clear()
                            st.rerun()
                        except Exception as e:
                            st.error(f"Reassignment failed: {e}")

# =============================================================================
# TAB 2: Source Path Mismatches
# =============================================================================
with tab_sources:
    # Initialize session state for tracking local resolutions
    if "resolved_source_slugs" not in st.session_state:
        st.session_state["resolved_source_slugs"] = set()

    c_shead1, c_shead2 = st.columns([4, 1])
    with c_shead1:
        st.subheader("Source Path Alignment & Verification")
        st.write(
            "Detects articles with unlinked sources, fragmented targets, "
            "or coordinate divergence between wiki stubs and primary OCR files."
        )
    with c_shead2:
        if st.button("🔄 Refresh Audit", key="refresh_sources_btn", use_container_width=True):
            st.cache_data.clear()
            st.session_state["resolved_source_slugs"].clear()
            st.rerun()

    raw_mismatches = fetch_source_mismatches()

    if not raw_mismatches:
        st.success("✨ All wiki publications resolve cleanly to authentic primary sources on disk!")
    else:
        # Filter out items resolved in the current session
        resolved_set = st.session_state["resolved_source_slugs"]
        mismatches = [m for m in raw_mismatches if m["wiki_slug"] not in resolved_set]

        missing_fields = [m for m in mismatches if m["error_type"] == "missing_source_field"]
        fragments = [m for m in mismatches if m["error_type"] == "fragment_target"]
        coord_clashes = [m for m in mismatches if m["error_type"] == "coordinate_mismatch"]
        missing_files = [m for m in mismatches if m["error_type"] == "file_not_found"]

        st.metric(
            "Pending Anomalies",
            len(mismatches),
            delta=f"-{len(resolved_set)} resolved this session" if resolved_set else None,
        )

        s_tab1, s_tab2, s_tab3, s_tab4 = st.tabs([
            f"🧩 Fragment Targets ({len(fragments)})",
            f"🔍 Missing Sources ({len(missing_fields)})",
            f"📏 Coordinate Clashes ({len(coord_clashes)})",
            f"📁 Missing Files ({len(missing_files)})",
        ])

        # --- SUBTAB 1: Fragment Targets ---
        with s_tab1:
            st.markdown("##### Auxiliary Fragment References")
            high_conf_frags = [
                f for f in fragments
                if (f.get("confidence") or 0.0) >= 0.95 and f.get("suggested_source_path")
            ]
            if high_conf_frags:
                with st.container(border=True):
                    col_b1, col_b2 = st.columns([3, 1])
                    with col_b1:
                        st.markdown(f"**Batch Action:** {len(high_conf_frags)} fragment targets have high-confidence remedies ($\ge 95\%$).")
                    with col_b2:
                        if st.button(f"⚡ Batch Fix All ({len(high_conf_frags)})", type="primary", use_container_width=True):
                            with st.spinner("Applying fragment remedies..."):
                                try:
                                    res = api.batch_fix_fragments(min_confidence=0.95)
                                    st.success(res.get("detail", "Fragments updated!"))
                                    st.cache_data.clear()
                                    st.session_state["resolved_source_slugs"].clear()
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Batch fix failed: {e}")

            for idx, m in enumerate(fragments):
                slug = m["wiki_slug"]
                with st.expander(f"🧩 {slug}", expanded=(idx < 2)):
                    st.write(f"**Detail:** {m['detail']}")
                    st.write(f"**Current Path:** `{m.get('current_source_path')}`")
                    if m.get("suggested_source_path"):
                        st.info(f"Remedy: `{m['suggested_source_path']}` (Confidence: {int((m.get('confidence') or 0)*100)}%)")
                        if st.button("Apply Suggested Fix", key=f"fix_frag_{idx}"):
                            try:
                                api.fix_source_path(slug, m["suggested_source_path"], m.get("suggested_doc_id"))
                                st.session_state["resolved_source_slugs"].add(slug)
                                st.rerun()
                            except Exception as e:
                                st.error(f"Failed to fix fragment: {e}")

        # --- SUBTAB 2: Missing Source Fields ---
        with s_tab2:
            st.markdown("##### Articles with No Declared Source")
            st.write("These articles are missing both `source_path` and `source_doc`.")

            for idx, m in enumerate(missing_fields):
                slug = m["wiki_slug"]
                with st.expander(f"🔍 {slug}", expanded=(idx < 2)):
                    st.write(f"**Status:** {m['detail']}")
                    if m.get("suggested_source_path"):
                        st.success(f"**Candidate Match:** `{m['suggested_source_path']}` (Confidence: {int((m.get('confidence') or 0)*100)}%)")
                        if st.button("Link Candidate Source", key=f"link_src_{idx}", type="primary"):
                            try:
                                api.fix_source_path(slug, m["suggested_source_path"], m.get("suggested_doc_id"))
                                # Optimistic local update: hide candidate and decrement counter without full re-audit
                                st.session_state["resolved_source_slugs"].add(slug)
                                st.toast(f"Linked source for {slug}!", icon="✅")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Failed to link source: {e}")
                    else:
                        st.caption("No high-probability source match identified in corpus.")

        # --- SUBTAB 3: Coordinate Clashes ---
        with s_tab3:
            st.markdown("##### Coordinate Clashes & Candidate Realignment")
            for idx, m in enumerate(coord_clashes):
                slug = m["wiki_slug"]
                with st.expander(f"📏 {slug}", expanded=(idx < 2)):
                    col_meta, col_cand = st.columns([1, 1])
                    with col_meta:
                        st.write(f"**Diagnostic:** {m['detail']}")
                        st.code(f"Current Path:\n{m.get('current_source_path') or 'None'}", language="text")
                    with col_cand:
                        if m.get("suggested_source_path"):
                            conf_pct = int((m.get("confidence") or 0.0) * 100)
                            st.success(f"Match Confidence: **{conf_pct}%**")
                            st.code(f"Suggested Path:\n{m['suggested_source_path']}", language="text")
                            if st.button("🔄 Replace Source with Candidate", key=f"fix_coord_{idx}", type="primary", use_container_width=True):
                                try:
                                    api.fix_source_path(slug, m["suggested_source_path"], m.get("suggested_doc_id"))
                                    st.session_state["resolved_source_slugs"].add(slug)
                                    st.toast(f"Realigned source for {slug}!", icon="✅")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Failed to realign: {e}")
                        else:
                            st.warning("No candidate source found matching coordinates.")

        # --- SUBTAB 4: Missing Files ---
        with s_tab4:
            st.markdown("##### Broken Links on Disk")
            for idx, m in enumerate(missing_files):
                with st.expander(f"📁 {m['wiki_slug']}", expanded=False):
                    st.error(m["detail"])