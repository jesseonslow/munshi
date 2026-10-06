"""Universal Policy-Driven Wiki Bot Runner (High-Throughput Async)."""
from __future__ import annotations

import asyncio
import json
import random
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import click
from openai import AsyncOpenAI

from munshi_bots.config import ROOT, BotConfig
from munshi_bots.file_utils import apply_frontmatter_patch, read_wiki_page
from munshi_bots.providers import get_candidate_provider

cfg = BotConfig()


def match_filter(fm: dict[str, Any], stem: str, filter_rules: dict[str, Any]) -> bool:
    """Generic predicate evaluating frontmatter and slug against policy criteria."""
    # 1. Generic exclusion patterns on slug (e.g. exclude_slug_patterns: ["-nq-"])
    slug_patterns = filter_rules.get("exclude_slug_patterns", [])
    for pat in slug_patterns:
        if re.search(pat, stem):
            return False

    # 2. Null/empty field constraints (e.g. source_doc: null)
    for key, expected in filter_rules.items():
        if key.startswith("exclude_"):
            continue
        actual = fm.get(key)
        if actual == "":
            actual = None
        if expected is None and actual is not None:
            return False

    # 3. Generic exclusion values for specific frontmatter fields
    for rule_key, excluded_vals in filter_rules.items():
        if rule_key.startswith("exclude_") and rule_key != "exclude_slug_patterns":
            field_name = rule_key.removeprefix("exclude_")  # e.g. "publication_types" -> check field
            singular_name = field_name.rstrip("s")  # e.g. "publication_type"
            val = str(fm.get(singular_name) or fm.get(field_name) or "").lower()
            if val in [str(x).lower() for x in excluded_vals]:
                return False

    # 4. Target type inclusions
    target_types = filter_rules.get("type")
    if target_types is not None:
        if isinstance(target_types, str):
            target_types = [target_types]
        actual_types = [
            str(fm.get("type") or "").lower(),
            str(fm.get("publication_type") or "").lower(),
            str(fm.get("article_type") or "").lower(),
        ]
        if not any(t in target_types for t in actual_types if t):
            return False

    return True


def resolve_policy_path(policy_arg: str) -> Path:
    p = Path(policy_arg)
    if p.exists() and p.is_file():
        return p.resolve()
    for candidate_dir in [cfg.policies_dir, ROOT / "policies"]:
        candidate = candidate_dir / f"{p.stem}.md"
        if candidate.exists():
            return candidate.resolve()
    raise click.BadParameter(f"Could not locate policy file for: '{policy_arg}'")


async def call_llm_with_retry(
    client: AsyncOpenAI,
    payload_kwargs: dict[str, Any],
    max_retries: int = 5,
) -> Any:
    delay = 1.0
    for attempt in range(1, max_retries + 1):
        try:
            return await client.chat.completions.create(**payload_kwargs)
        except Exception as e:
            err_str = str(e).lower()
            retryable = any(
                code in err_str
                for code in ["429", "502", "503", "504", "timeout", "rate limit", "connection reset"]
            )
            if attempt < max_retries and retryable:
                await asyncio.sleep(delay + random.uniform(0.1, 0.4))
                delay *= 2.0
            else:
                raise e


async def process_file(
    file_path: Path,
    client: AsyncOpenAI,
    model: str,
    policy_instructions: str,
    threshold: float,
    execute: bool,
    provider: Any | None,
    semaphore: asyncio.Semaphore,
) -> dict[str, Any]:
    fm, body = read_wiki_page(file_path)

    # Resolve candidates via injected provider if configured by policy
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
                apply_frontmatter_patch(file_path, patch=patch)
            return {
                "file": file_path.name,
                "status": "FAST_PATH",
                "patch": patch,
                "confidence": 1.0,
                "applied": execute,
                "reasoning": f"Deterministic match via Master Issue #{det_match['master_no']}",
                "candidates_debug": "(Fast Path Hit)",
            }

    # Interpolate variables into policy instructions
    interpolated_system_prompt = policy_instructions.replace("{{candidates}}", candidates_text)

    user_payload = (
        f"Target File: {file_path.name}\n\n"
        f"Frontmatter:\n{json.dumps(fm, indent=2)}\n\n"
        f"Body Excerpt:\n{body[:1500]}"
    )

    async with semaphore:
        payload_kwargs = {
            "model": model,
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
            "extra_body": {"reasoning": {"max_tokens": 128}},
            "messages": [
                {"role": "system", "content": interpolated_system_prompt},
                {"role": "user", "content": user_payload},
            ],
            "timeout": 25.0,
        }

        try:
            resp = await call_llm_with_retry(client, payload_kwargs)
            raw_content = resp.choices[0].message.content or "{}"
            result = json.loads(raw_content)

            # Defensive unwrap if LLM wrapped in a list: [{...}] -> {...}
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
                "reasoning": f"Execution or JSON decode failure: {e}",
                "candidates_debug": candidates_text,
            }

    should_patch = result.get("should_patch", False)
    confidence = float(result.get("confidence", 0.0))
    patch = result.get("patch") or {}
    if not isinstance(patch, dict):
        patch = {}

    keys_to_remove = result.get("keys_to_remove", [])
    reset_body = result.get("reset_body", False)

    applied = False
    if should_patch and confidence >= threshold and patch:
        if execute:
            apply_frontmatter_patch(
                file_path,
                patch=patch,
                keys_to_remove=keys_to_remove,
                reset_body=reset_body,
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


async def run_async_pipeline(
    policy: str,
    limit: int | None,
    execute: bool,
    concurrency: int,
    shuffle: bool | None,
    seed: int | None,
    wiki_dir: Path,
    triage_dir: Path,
):
    policy_path = resolve_policy_path(policy)
    policy_meta, policy_instructions = read_wiki_page(policy_path)

    policy_name = policy_meta.get("name", policy_path.stem)
    filter_rules = policy_meta.get("filter", {})
    threshold = float(policy_meta.get("confidence_threshold", 0.85))
    model = policy_meta.get("model", cfg.default_model)
    provider_name = policy_meta.get("candidate_provider")

    provider = get_candidate_provider(provider_name, wiki_dir, ROOT) if provider_name else None

    client = AsyncOpenAI(base_url=cfg.openrouter_base_url, api_key=cfg.openrouter_api_key)
    triage_dir.mkdir(parents=True, exist_ok=True)
    audit_file = triage_dir / f"{policy_name}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.jsonl"

    files = [
        f for f in sorted(list(wiki_dir.glob("*.md")))
        if match_filter(read_wiki_page(f)[0], f.stem, filter_rules)
    ]

    if shuffle or (shuffle is None and limit is not None):
        if seed:
            random.seed(seed)
        random.shuffle(files)

    if limit:
        files = files[:limit]

    click.echo(f"Loaded policy: {policy_name} ({policy_path.name})")
    click.echo(f"Targeting: {len(files)} files | Concurrency: {concurrency} | Mode: {'EXECUTE' if execute else 'DRY RUN'}\n")

    semaphore = asyncio.Semaphore(concurrency)
    tasks = [
        process_file(f, client, model, policy_instructions, threshold, execute, provider, semaphore)
        for f in files
    ]

    processed = 0
    with open(audit_file, "a", encoding="utf-8") as log:
        for fut in asyncio.as_completed(tasks):
            res = await fut
            processed += 1
            status = res.get("status")
            f_name = res.get("file")
            patch = res.get("patch")
            conf = res.get("confidence", 0.0)
            reason = res.get("reasoning", "")
            cands = res.get("candidates_debug", "")

            click.echo(f"[{processed}/{len(files)}] [{status}] {f_name} (conf: {conf:.2f})")
            if patch:
                click.echo(f"   ├─ Patch: {patch}")
            click.echo(f"   ├─ Reasoning: {reason[:120]}")
            # Print the candidates that were provided to the model:
            first_cand_line = cands.strip().splitlines()[0] if cands.strip() else "(None)"
            click.echo(f"   └─ Top Candidate Provided: {first_cand_line}")


@click.command()
@click.argument("policy")
@click.option("--limit", type=int, default=None)
@click.option("--execute", is_flag=True, default=False)
@click.option("--concurrency", type=int, default=8)
@click.option("--shuffle/--no-shuffle", "shuffle", default=None)
@click.option("--seed", type=int, default=None)
@click.option("--wiki-dir", type=click.Path(path_type=Path), default=None)
@click.option("--triage-dir", type=click.Path(path_type=Path), default=None)
def run_policy(policy, limit, execute, concurrency, shuffle, seed, wiki_dir, triage_dir):
    asyncio.run(
        run_async_pipeline(
            policy=policy,
            limit=limit,
            execute=execute,
            concurrency=concurrency,
            shuffle=shuffle,
            seed=seed,
            wiki_dir=wiki_dir or cfg.wiki_dir,
            triage_dir=triage_dir or cfg.triage_dir,
        )
    )


if __name__ == "__main__":
    run_policy()