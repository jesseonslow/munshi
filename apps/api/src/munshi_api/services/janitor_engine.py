from __future__ import annotations

import re
from pathlib import Path
from typing import Any
import yaml
from fastapi import HTTPException
from munshi_api.models.janitor import MutationResult, ReassignAuthorPayload


def split_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    parts = text.split("---", 2)
    if len(parts) >= 3:
        return yaml.safe_load(parts[1]) or {}, parts[2]
    return {}, text


def join_frontmatter(fm: dict[str, Any], body: str) -> str:
    yaml_str = yaml.dump(fm, sort_keys=False, allow_unicode=True)
    return f"---\n{yaml_str}---\n{body.lstrip()}"


class JanitorEngine:
    def __init__(self, wiki_dir: Path):
        self.wiki_dir = wiki_dir

    def fix_source_path(
        self, slug: str, new_path: str, new_doc_id: str | None = None
    ) -> MutationResult:
        """Updates source_path and source_doc in the article's frontmatter."""
        pub_path = self.wiki_dir / f"{slug}.md"
        if not pub_path.exists():
            raise HTTPException(
                status_code=404, detail=f"Article {pub_path.name} not found"
            )

        fm, body = split_frontmatter(pub_path.read_text(encoding="utf-8"))
        fm["source_path"] = new_path
        if new_doc_id:
            fm["source_doc"] = new_doc_id

        pub_path.write_text(join_frontmatter(fm, body), encoding="utf-8")
        return MutationResult(
            status="success", action="fix_source_path", modified_files=[pub_path.name]
        )
    
    def batch_reassign_author(self, payload: BatchReassignPayload) -> MutationResult:
        modified_files = set()
        affected_pubs = []

        for pub_file in self.wiki_dir.glob("*.md"):
            try:
                raw = pub_file.read_text(encoding="utf-8")
                if not raw.startswith("---"):
                    continue
                parts = raw.split("---", 2)
                if len(parts) < 3:
                    continue
                fm = yaml.safe_load(parts[1]) or {}
                if fm.get("type") != "article":
                    continue

                authors = fm.get("authors") or []
                if payload.old_author_name in authors:
                    single_payload = ReassignAuthorPayload(
                        publication_slug=pub_file.stem,
                        old_author_name=payload.old_author_name,
                        new_author_name=payload.new_author_name,
                        new_author_slug=payload.new_author_slug,
                        old_author_slug=payload.old_author_slug,
                    )
                    res = self.reassign_author(single_payload)
                    modified_files.update(res.modified_files)
                    affected_pubs.append(pub_file.stem)
            except Exception:
                continue

        # Invalidate in-memory graph index so API reflects changes immediately
        from munshi_api.services.wiki_index import WikiGraphIndex
        WikiGraphIndex.get_instance(self.wiki_dir).reload()

        return MutationResult(
            status="success",
            action="batch_reassign_author",
            modified_files=sorted(list(modified_files)),
            detail=f"Reassigned {len(affected_pubs)} articles from '{payload.old_author_name}' to '{payload.new_author_name}'.",
        )

    def reassign_author(self, payload: ReassignAuthorPayload) -> MutationResult:
        """
        Surgically shifts an article's authorship:
        1. Updates authors & resolved_author_slugs in publication stub frontmatter.
        2. Removes the entry from old author's ## Bibliography.
        3. Appends the entry to the new author's ## Bibliography.
        4. Rewrites the link in the parent journal issue Table of Contents and contributors list.
        """
        modified: list[str] = []
        pub_path = self.wiki_dir / f"{payload.publication_slug}.md"
        if not pub_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Publication '{payload.publication_slug}.md' not found."
            )

        pub_fm, pub_body = split_frontmatter(pub_path.read_text(encoding="utf-8"))

        # 1. Update Publication Frontmatter
        authors = pub_fm.get("authors") or []
        updated_authors = [
            payload.new_author_name if a == payload.old_author_name else a
            for a in authors
        ]
        if payload.new_author_name not in updated_authors:
            updated_authors.append(payload.new_author_name)
        pub_fm["authors"] = updated_authors

        if "resolved_author_slugs" in pub_fm and payload.old_author_slug:
            pub_fm["resolved_author_slugs"] = [
                payload.new_author_slug if s == payload.old_author_slug else s
                for s in pub_fm["resolved_author_slugs"]
            ]

        pub_path.write_text(join_frontmatter(pub_fm, pub_body), encoding="utf-8")
        modified.append(pub_path.name)

        title = pub_fm.get("title", payload.publication_slug)
        year = pub_fm.get("year", "n.d.")
        journal = pub_fm.get("journal_code", "JMBRAS")
        vol = pub_fm.get("volume", "")
        issue = pub_fm.get("issue", "")
        pages = pub_fm.get("pages", "")
        biblio_line = f"- ({year}) [{title}](./{payload.publication_slug}.md). *{journal}* {vol}({issue}): {pages}"

        # 2. Update Old Author Bibliography (Remove entry)
        if payload.old_author_slug:
            old_path = self.wiki_dir / f"{payload.old_author_slug}.md"
            if old_path.exists():
                o_fm, o_body = split_frontmatter(old_path.read_text(encoding="utf-8"))
                o_body_clean = re.sub(
                    rf"^\s*-\s*.*?\(\./{re.escape(payload.publication_slug)}\.md\).*?\n?",
                    "",
                    o_body,
                    flags=re.MULTILINE,
                )
                old_path.write_text(join_frontmatter(o_fm, o_body_clean), encoding="utf-8")
                modified.append(old_path.name)

        # 3. Update New Author Bibliography (Add entry)
        new_path = self.wiki_dir / f"{payload.new_author_slug}.md"
        if new_path.exists():
            n_fm, n_body = split_frontmatter(new_path.read_text(encoding="utf-8"))
            n_fm["is_contributor"] = True
            if payload.publication_slug not in n_body:
                if "## Bibliography" in n_body:
                    n_body = re.sub(
                        r"(## Bibliography\s*\n)",
                        rf"\1{biblio_line}\n",
                        n_body,
                        count=1,
                    )
                else:
                    n_body = n_body.rstrip() + f"\n\n## Bibliography\n{biblio_line}\n"
                new_path.write_text(join_frontmatter(n_fm, n_body), encoding="utf-8")
                modified.append(new_path.name)

        # 4. Update JMBRAS/JSBRAS Issue TOC and Contributors List
        for issue_file in self.wiki_dir.glob("*.md"):
            # Check issue types from filename or content
            if not (issue_file.stem.startswith(("mbras-", "jsbras-", "issue-"))):
                continue

            changed = self._patch_issue_contributors_and_toc(
                issue_file=issue_file,
                publication_slug=payload.publication_slug,
                old_author_name=payload.old_author_name,
                new_author_name=payload.new_author_name,
                new_author_slug=payload.new_author_slug,
                old_author_slug=payload.old_author_slug,
            )
            if changed:
                modified.append(issue_file.name)

        return MutationResult(
            status="success",
            action="reassign_author",
            modified_files=list(set(modified)),
        )

    def batch_fix_fragments(self, min_confidence: float = 0.95) -> MutationResult:
        """Finds all fragment anomalies and applies their remedy in one pass."""
        from munshi_api.services.graph_auditor import GraphAuditorEngine
        auditor = GraphAuditorEngine(self.wiki_dir)
        mismatches = auditor.audit_source_paths()

        modified = []
        fixed_count = 0

        for m in mismatches:
            if m.error_type == "fragment_target" and m.suggested_source_path:
                if (m.confidence or 0.0) >= min_confidence:
                    res = self.fix_source_path(
                        slug=m.wiki_slug,
                        new_path=m.suggested_source_path,
                        new_doc_id=m.suggested_doc_id,
                    )
                    modified.extend(res.modified_files)
                    fixed_count += 1

        return MutationResult(
            status="success",
            action="batch_fix_fragments",
            modified_files=list(set(modified)),
            detail=f"Successfully patched {fixed_count} fragment targets (Confidence >= {int(min_confidence*100)}%).",
        )
    
    def _patch_issue_contributors_and_toc(
        self,
        issue_file: Path,
        publication_slug: str,
        old_author_name: str,
        new_author_name: str,
        new_author_slug: str,
        old_author_slug: str | None = None,
    ) -> bool:
        raw_text = issue_file.read_text(encoding="utf-8")
        if publication_slug not in raw_text:
            return False

        fm, body = split_frontmatter(raw_text)
        modified = False

        # ---------------------------------------------------------------------
        # 1. Patch Table of Contents Line
        # Matches: [Article Title](./pub-slug.md) — [Old Author](./old-slug.md)
        # Also handles em-dashes (—), en-dashes (–), hyphens (-), and plain spaces
        # ---------------------------------------------------------------------
        toc_pattern = re.compile(
            rf"(\[.*?\]\(\./{re.escape(publication_slug)}\.md\)[^—–\n]*[—–-]\s*)"
            rf"\[?{re.escape(old_author_name)}\]?(?:\(\./[^\)]+\))?",
            re.IGNORECASE,
        )
        new_toc_link = f"\\g<1>[{new_author_name}](./{new_author_slug}.md)"
        new_body, count = toc_pattern.subn(new_toc_link, body)
        if count > 0:
            body = new_body
            modified = True

        # ---------------------------------------------------------------------
        # 2. Check if Old Author Has OTHER Articles in this Issue TOC
        # ---------------------------------------------------------------------
        toc_part = body.split("## Contributors")[0] if "## Contributors" in body else body
        old_name_pattern = re.compile(
            rf"[—–-]\s*\[?{re.escape(old_author_name)}\]?(?:\(\./[^\)]+\))?",
            re.IGNORECASE,
        )
        old_author_still_in_toc = bool(old_name_pattern.search(toc_part))

        # ---------------------------------------------------------------------
        # 3. Patch ## Contributors Body Markdown Section
        # ---------------------------------------------------------------------
        contrib_match = re.search(
            r"(?:\r?\n|^)(##\s+Contributors\s*\r?\n)(.*?)(?=(?:\r?\n)##\s+|\Z)",
            body,
            re.DOTALL | re.IGNORECASE,
        )
        if contrib_match:
            c_header = contrib_match.group(1)
            c_content = contrib_match.group(2)
            c_lines = [
                line.strip()
                for line in c_content.splitlines()
                if line.strip().startswith(("*", "-"))
            ]

            target_bullet = f"* [{new_author_name}](./{new_author_slug}.md)"
            updated_bullets = []

            for line in c_lines:
                # Check if this line represents the old author
                is_old = False
                if old_author_slug and f"./{old_author_slug}.md" in line:
                    is_old = True
                elif re.search(rf"\b{re.escape(old_author_name)}\b", line, re.IGNORECASE):
                    is_old = True

                if is_old:
                    if old_author_still_in_toc:
                        # Keep bullet if they still authored another piece in this issue
                        updated_bullets.append(line)
                    else:
                        modified = True  # Dropping old author
                else:
                    updated_bullets.append(line)

            # Insert new author if not already in the list
            if not any(f"./{new_author_slug}.md" in b for b in updated_bullets):
                updated_bullets.append(target_bullet)
                modified = True

            # Sort contributors alphabetically by display name
            def _extract_name(bullet_str: str) -> str:
                m = re.search(r"\[([^\]]+)\]", bullet_str)
                return m.group(1).lower() if m else bullet_str.lower()

            updated_bullets.sort(key=_extract_name)
            new_c_section = c_header + "\n".join(updated_bullets) + "\n"

            start_idx = contrib_match.start(1)
            end_idx = contrib_match.end()
            body = body[:start_idx] + new_c_section + body[end_idx:]

        # ---------------------------------------------------------------------
        # 4. Patch Frontmatter contributors list
        # ---------------------------------------------------------------------
        contribs = fm.get("contributors") or []
        if isinstance(contribs, list):
            new_contribs = []
            for c in contribs:
                c_id = c.get("id") if isinstance(c, dict) else str(c)
                c_name = c.get("name") if isinstance(c, dict) else str(c)
                if (old_author_slug and c_id == old_author_slug) or c_name.lower() == old_author_name.lower():
                    if old_author_still_in_toc:
                        new_contribs.append(c)
                    else:
                        modified = True
                else:
                    new_contribs.append(c)

            if not any(
                (c.get("id") if isinstance(c, dict) else str(c)) == new_author_slug
                for c in new_contribs
            ):
                new_contribs.append({"id": new_author_slug, "name": new_author_name})
                modified = True

            new_contribs.sort(key=lambda x: (x.get("name") if isinstance(x, dict) else str(x)).lower())
            fm["contributors"] = new_contribs

        if modified:
            issue_file.write_text(join_frontmatter(fm, body), encoding="utf-8")

        return modified