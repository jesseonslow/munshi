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
        """
        Fast bulk reassignment:
        1. Finds all publications with old_author_name and updates them.
        2. Updates old and new author bibliography profiles once.
        3. Scans issue files once for all modified publications.
        """
        modified_files = set()
        affected_pubs = []

        # 1. Update all matching publication frontmatters
        for pub_file in self.wiki_dir.glob("*.md"):
            try:
                raw = pub_file.read_text(encoding="utf-8")
                if "type: article" not in raw and "type: publication" not in raw:
                    continue
                parts = raw.split("---", 2)
                if len(parts) < 3:
                    continue
                fm = yaml.safe_load(parts[1]) or {}
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
            except Exception as e:
                logger.warning("Error processing %s: %s", pub_file.name, e)
                continue

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
            if not issue_file.stem.startswith(("mbras-", "jsbras-", "issue-")):
                continue
            i_text = issue_file.read_text(encoding="utf-8")
            if payload.publication_slug not in i_text:
                continue

            i_fm, i_body = split_frontmatter(i_text)
            pattern = (
                rf"(\[.*?\]\(\./{re.escape(payload.publication_slug)}\.md\)[^—\n]*[—–-]\s*)"
                rf"\[{re.escape(payload.old_author_name)}\]\(\./[^\)]+\)"
            )
            replacement = rf"\g<1>[{payload.new_author_name}](./{payload.new_author_slug}.md)"
            i_body_patched = re.sub(pattern, replacement, i_body)

            contribs = i_fm.get("contributors") or []
            if not any(c.get("id") == payload.new_author_slug for c in contribs if isinstance(c, dict)):
                contribs.append({"id": payload.new_author_slug, "name": payload.new_author_name})
                i_fm["contributors"] = contribs

            issue_file.write_text(join_frontmatter(i_fm, i_body_patched), encoding="utf-8")
            modified.append(issue_file.name)

        return MutationResult(
            status="success",
            action="reassign_author",
            modified_files=list(set(modified)),
        )