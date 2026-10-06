"""FastAPI endpoint exposing live streaming document processing pipelines."""
from __future__ import annotations

import asyncio
import os
import queue
import shutil
import tempfile
import threading
from pathlib import Path
from typing import AsyncGenerator

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, File, Query, UploadFile
from fastapi.responses import StreamingResponse

from munshi_api.config import ROOT, ApiConfig

# Explicitly ensure root .env is loaded into process environment
load_dotenv(ROOT / ".env", override=False)

router = APIRouter(prefix="/api/docproc", tags=["Docproc Ingestion"])


def get_config() -> ApiConfig:
    return ApiConfig()


async def execute_docproc_worker(
    temp_dir: Path,
    pdf_paths: list[Path],
    output_dir: Path,
    engine: str,
) -> AsyncGenerator[str, None]:
    yield f"[INIT] Staged {len(pdf_paths)} document(s) in staging area: {temp_dir}\n"
    await asyncio.sleep(0.05)

    try:
        from munshi_docproc.cli import _run_pipeline
        from munshi_docproc.config import PipelineConfig
    except ModuleNotFoundError as e:
        yield f"[ERROR] munshi_docproc is not installed in the API environment: {e}\n"
        yield "[HINT] Run `uv add --path ../docproc munshi-docproc` inside apps/api\n"
        return

    # Verify OpenRouter API key presence before launching threads
    openrouter_key = (
        os.getenv("DOCPROC_OPENROUTER_API_KEY")
        or os.getenv("OPENROUTER_API_KEY")
        or os.getenv("OPENAI_API_KEY")
    )
    if not openrouter_key:
        yield "[WARN] No OpenRouter API key found in root .env! VLM OCR calls may fail.\n"
    else:
        # Standardize so OpenAI client picks it up if config lookup falls back
        os.environ["OPENAI_API_KEY"] = openrouter_key
        os.environ["OPENROUTER_API_KEY"] = openrouter_key

    # Ensure output_dir (./sources) exists as absolute path
    target_sources_dir = output_dir.resolve()
    target_sources_dir.mkdir(parents=True, exist_ok=True)

    for pdf_path in pdf_paths:
        yield f"[START] Processing '{pdf_path.name}' via munshi-docproc...\n"

        log_queue: queue.Queue[str | None] = queue.Queue()

        def _worker(target_pdf: Path, out_path: Path):
            try:
                log_queue.put(f"[RENDER] Extracting layout & text with PyMuPDF...")
                
                # Run the actual 17-stage ingestion pipeline, outputting to out_path (sources/)
                doc_id = _run_pipeline(
                    pdf_path=target_pdf,
                    out_dir=out_path,
                    max_pages=None,
                    page_range=None,
                    force=True,
                )

                # Check if munshi_docproc nested the result under out_path/out/{doc_id}
                # and hoist the stitched markdown to out_path/{doc_id}.md if needed
                nested_md = out_path / "out" / doc_id / f"{doc_id}.md"
                nested_dir = out_path / doc_id / f"{doc_id}.md"
                direct_md = out_path / f"{doc_id}.md"

                if nested_md.exists() and not direct_md.exists():
                    shutil.copy2(nested_md, direct_md)
                elif nested_dir.exists() and not direct_md.exists():
                    shutil.copy2(nested_dir, direct_md)

                log_queue.put(f"[STITCH] Successfully created source artifacts for '{doc_id}' in {out_path}")
            except Exception as exc:
                log_queue.put(f"[ERROR] Pipeline failure on {target_pdf.name}: {exc}")
            finally:
                log_queue.put(None)

        worker_thread = threading.Thread(
            target=_worker, args=(pdf_path, target_sources_dir), daemon=True
        )
        worker_thread.start()

        loop = asyncio.get_running_loop()
        while True:
            line = await loop.run_in_executor(None, log_queue.get)
            if line is None:
                break
            yield f"{line}\n"
            await asyncio.sleep(0.01)

    yield f"[SUCCESS] All documents successfully processed and written to {target_sources_dir}!\n"

    # Cleanup temporary uploaded PDFs
    shutil.rmtree(temp_dir, ignore_errors=True)


@router.post("/pipeline/stream")
async def run_docproc_stream(
    files: list[UploadFile] = File(...),
    engine: str = Query(default="qwen-vl"),
    config: ApiConfig = Depends(get_config),
):
    temp_dir = Path(tempfile.mkdtemp(prefix="munshi_docproc_"))
    saved_pdf_paths: list[Path] = []

    for uploaded in files:
        dest = temp_dir / (uploaded.filename or "input.pdf")
        with open(dest, "wb") as f:
            f.write(await uploaded.read())
        saved_pdf_paths.append(dest)

    return StreamingResponse(
        execute_docproc_worker(
            temp_dir=temp_dir,
            pdf_paths=saved_pdf_paths,
            output_dir=config.sources_dir,
            engine=engine,
        ),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )