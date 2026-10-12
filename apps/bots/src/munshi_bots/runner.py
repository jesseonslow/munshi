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
from munshi_bots.engine import execute_policy_on_file
from munshi_bots.file_utils import read_wiki_page
from munshi_bots.providers import get_candidate_provider

cfg = BotConfig()


def match_filter(fm: dict[str, Any], stem: str, filter_rules: dict[str, Any]) -> bool:
    """Generic predicate evaluating frontmatter and slug against policy criteria."""
    slug_patterns = filter_rules.get("exclude_slug_patterns", [])
    for pat in slug_patterns:
        if re.search(pat, stem):
            return False

    for key, expected in filter_rules.items():
        if key.startswith("exclude_"):
            continue
        actual = fm.get(key)
        if actual == "":
            actual = None
        if expected is None and actual is not None:
            return False

    for rule_key, excluded_vals in filter_rules.items():
        if rule_key.startswith("exclude_") and rule_key != "exclude_slug_patterns":
            field_name = rule_key.removeprefix("exclude_")
            singular_name = field_name.rstrip("s")
            val = str(fm.get(singular_name) or fm.get(field_name) or "").lower()
            if val in [str(x).lower() for x in excluded_vals]:
                return False

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

    async def sem_worker(f: Path) -> dict[str, Any]:
        async with semaphore:
            return await execute_policy_on_file(
                file_path=f,
                client=client,
                model=model,
                policy_instructions=policy_instructions,
                threshold=threshold,
                execute=execute,
                provider=provider,
                wiki_dir=wiki_dir,
                call_llm_func=call_llm_with_retry,
            )

    tasks = [sem_worker(f) for f in files]
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
            if reason:
                click.echo(f"   ├─ Reasoning: {reason[:120]}")
            first_cand_line = cands.strip().splitlines()[0] if cands.strip() else "(None)"
            click.echo(f"   └─ Top Candidate Provided: {first_cand_line}")

            log.write(
                json.dumps({
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "policy": policy_name,
                    **res,
                }) + "\n"
            )


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