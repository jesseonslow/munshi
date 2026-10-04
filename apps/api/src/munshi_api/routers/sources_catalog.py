from __future__ import annotations
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from munshi_api.config import ApiConfig

router = APIRouter(prefix="/api/sources", tags=["Sources Catalog"])


class SourceDocSummary(BaseModel):
    doc_id: str
    primary_filename: str
    files: list[str]
    is_fragment: bool


class SourceDocContent(BaseModel):
    doc_id: str
    filename: str
    content: str
    word_count: int

def get_config() -> ApiConfig:
    return ApiConfig()

@router.get("", response_model=list[SourceDocSummary])
def list_sources(config: ApiConfig = Depends(get_config)):
    results: list[SourceDocSummary] = []
    if not config.sources_dir.exists():
        return results

    # Scans both standalone flat markdowns and multi-file subfolders
    for p in sorted(config.sources_dir.iterdir()):
        if p.is_file() and p.suffix == ".md":
            is_frag = p.name.lower() in {"glossary.md", "references.md", "appendix.md"}
            results.append(
                SourceDocSummary(
                    doc_id=p.stem,
                    primary_filename=p.name,
                    files=[p.name],
                    is_fragment=is_frag,
                )
            )
        elif p.is_dir() and not p.name.startswith("."):
            md_files = [f.name for f in sorted(p.glob("*.md"))]
            if md_files:
                primary = "frontmatter.md" if "frontmatter.md" in md_files else md_files[0]
                results.append(
                    SourceDocSummary(
                        doc_id=p.name,
                        primary_filename=primary,
                        files=md_files,
                        is_fragment=False,
                    )
                )
    return results


@router.get("/{doc_id}/content", response_model=SourceDocContent)
def get_source_content(doc_id: str, filename: str | None = None, config: ApiConfig = Depends(get_config)):
    target_path = None
    flat_candidate = config.sources_dir / f"{doc_id}.md"
    folder_candidate = config.sources_dir / doc_id

    if folder_candidate.is_dir():
        target_file = filename or "frontmatter.md"
        actual = folder_candidate / target_file
        if actual.exists():
            target_path = actual
        else:
            mds = sorted(folder_candidate.glob("*.md"))
            if mds:
                target_path = mds[0]
    elif flat_candidate.exists():
        target_path = flat_candidate

    if not target_path or not target_path.exists():
        raise HTTPException(status_code=404, detail="Source markdown document not found")

    text = target_path.read_text(encoding="utf-8")
    return SourceDocContent(
        doc_id=doc_id,
        filename=target_path.name,
        content=text,
        word_count=len(text.split()),
    )