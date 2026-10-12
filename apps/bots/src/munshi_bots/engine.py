from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from openai import AsyncOpenAI

from munshi_bots.file_utils import apply_patch, read_wiki_page


async def execute_policy_on_file(
    file_path: Path,
    client: AsyncOpenAI,
    model: str,
    policy_instructions: str,
    threshold: float,
    execute: bool,
    provider: Any | None,
    wiki_dir: Path,
    call_llm_func: Any,
) -> dict[str, Any]:
    """Executes a declarative policy against a single file."""
    fm, body = read_wiki_page(file_path)

    # 1. Harvest candidates via provider (if configured)
    candidates_text = ""
    if provider:
        det_match, candidates_text = provider.get_candidates(fm, file_path.stem)
        if det_match:
            patch = {
                "source_doc": det_match["doc_id"],
                "source_path": det_match["rel_path"],
                "source_mismatch": False,
            }
            if execute:
                apply_patch(file_path, patch=patch, wiki_dir=wiki_dir)
            return {
                "file": file_path.name,
                "status": "FAST_PATH",
                "patch": patch,
                "confidence": 1.0,
                "applied": execute,
                "reasoning": f"Deterministic match via Master Issue #{det_match['master_no']}",
                "candidates_debug": "(Fast Path Hit)",
            }

    # 2. Build Prompt
    system_prompt = policy_instructions.replace("{{candidates}}", candidates_text)
    user_payload = (
        f"Target File: {file_path.name}\n\n"
        f"Frontmatter:\n{json.dumps(fm, indent=2)}\n\n"
        f"Body Excerpt:\n{body[:1500]}"
    )

    payload_kwargs = {
        "model": model,
        "temperature": 0.1,
        "response_format": {"type": "json_object"},
        "extra_body": {"reasoning": {"max_tokens": 128}},
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_payload},
        ],
        "timeout": 25.0,
    }

    # 3. Call LLM
    try:
        resp = await call_llm_func(client, payload_kwargs)
        result = json.loads(resp.choices[0].message.content or "{}")
        if isinstance(result, list):
            result = result[0] if (result and isinstance(result[0], dict)) else {}
    except Exception as e:
        return {
            "file": file_path.name,
            "status": "ERROR",
            "error": str(e),
            "patch": {},
            "confidence": 0.0,
            "applied": False,
            "reasoning": f"Execution failure: {e}",
            "candidates_debug": candidates_text,
        }

    # 4. Evaluate Threshold & Apply Uniform Patch
    should_patch = result.get("should_patch", False)
    confidence = float(result.get("confidence", 0.0))
    patch = result.get("patch") or {}
    if not isinstance(patch, dict):
        patch = {}

    applied = False
    if should_patch and confidence >= threshold and patch:
        if execute:
            apply_patch(
                file_path,
                patch=patch,
                keys_to_remove=result.get("keys_to_remove", []),
                reset_body=result.get("reset_body", False),
                wiki_dir=wiki_dir,
            )
            applied = True
        status = "PATCHED" if execute else "PROPOSED"
    else:
        status = "FLAGGED"

    return {
        "file": file_path.name,
        "status": status,
        "patch": patch,
        "confidence": confidence,
        "applied": applied,
        "reasoning": result.get("reasoning", ""),
        "candidates_debug": candidates_text,
    }