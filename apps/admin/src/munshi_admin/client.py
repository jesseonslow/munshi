"""HTTP client interface connecting the Streamlit dashboard to munshi-api."""
from __future__ import annotations

import os
from typing import Any
import httpx

API_BASE_URL = os.getenv("MUNSHI_API_URL", "http://127.0.0.1:8000/api")


class MunshiApiClient:
    def __init__(self, base_url: str = API_BASE_URL):
        self.base_url = base_url.rstrip("/")

    def _client(self) -> httpx.Client:
        return httpx.Client(base_url=self.base_url, timeout=120.0)

    def ping(self) -> bool:
        try:
            with self._client() as client:
                res = client.get("/ping")
                return res.status_code == 200
        except Exception:
            return False

    def list_wiki_articles(
        self,
        doc_type: str | None = None,
        article_type: str | None = None,
        summarized: bool | None = None,
        search: str | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {}
        if doc_type:
            params["type"] = doc_type
        if article_type:
            params["article_type"] = article_type
        if summarized is not None:
            params["summarized"] = summarized
        if search:
            params["search"] = search

        with self._client() as client:
            res = client.get("/wiki/articles", params=params)
            try:
                res.raise_for_status()
            except httpx.HTTPStatusError:
                return {"total": 0, "items": [], "error": f"HTTP {res.status_code}: {res.text}"}

            if not res.content:
                return {"total": 0, "items": []}

            return res.json()

    def get_wiki_detail(self, slug: str) -> dict[str, Any]:
        with self._client() as client:
            res = client.get(f"/wiki/articles/{slug}")
            res.raise_for_status()
            return res.json()

    def get_graph_health(self) -> dict[str, Any]:
        with self._client() as client:
            res = client.get("/audit/health")
            res.raise_for_status()
            return res.json()

    def get_attribution_conflicts(self) -> list[dict[str, Any]]:
        with self._client() as client:
            res = client.get("/audit/attributions")
            res.raise_for_status()
            return res.json()

    def get_source_mismatches(self) -> list[dict[str, Any]]:
        with self._client() as client:
            res = client.get("/audit/sources")
            res.raise_for_status()
            return res.json()

    def reassign_author(
        self,
        publication_slug: str,
        old_author_name: str,
        new_author_name: str,
        new_author_slug: str,
        old_author_slug: str | None = None,
    ) -> dict[str, Any]:
        payload = {
            "publication_slug": publication_slug,
            "old_author_name": old_author_name,
            "new_author_name": new_author_name,
            "new_author_slug": new_author_slug,
            "old_author_slug": old_author_slug,
        }
        with self._client() as client:
            res = client.post("/janitor/reassign-author", json=payload)
            res.raise_for_status()
            return res.json()

    def batch_reassign_author(
        self,
        old_author_name: str,
        new_author_name: str,
        new_author_slug: str,
        old_author_slug: str | None = None,
    ) -> dict[str, Any]:
        payload = {
            "old_author_name": old_author_name,
            "new_author_name": new_author_name,
            "new_author_slug": new_author_slug,
            "old_author_slug": old_author_slug,
        }
        with self._client() as client:
            res = client.post("/janitor/batch-reassign", json=payload)
            if res.status_code == 422:
                raise ValueError(f"FastAPI 422 Validation Error: {res.json()}")
            res.raise_for_status()
            return res.json()

    def fix_source_path(
        self,
        slug: str,
        new_path: str,
        new_doc_id: str | None = None,
    ) -> dict[str, Any]:
        payload = {
            "slug": slug,
            "new_path": new_path,
            "new_doc_id": new_doc_id,
        }
        with self._client() as client:
            res = client.post("/janitor/fix-source-path", json=payload)
            res.raise_for_status()
            return res.json()

    def trigger_summarizer(
        self,
        slug: str,
        force: bool = False,
        model_override: str | None = None,
    ) -> dict[str, Any]:
        payload = {
            "slugs": [slug],
            "force": force,
            "model_override": model_override,
        }
        with self._client() as client:
            res = client.post("/summarizer/run", json=payload)
            res.raise_for_status()
            return res.json()

    def list_ledger_entities(
        self,
        tier: str | None = None,
        category: str | None = None,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {}
        if tier:
            params["tier"] = tier
        if category:
            params["category"] = category
        with self._client() as client:
            res = client.get("/ledger/entities", params=params)
            return res.json() if res.status_code == 200 else []

    def batch_fix_fragments(self, min_confidence: float = 0.95) -> dict[str, Any]:
        with self._client() as client:
            res = client.post(
                "/janitor/batch-fix-fragments",
                params={"min_confidence": min_confidence},
            )
            res.raise_for_status()
            return res.json()

    def stream_docproc_run(
        self,
        files: list[tuple[str, bytes]],
        engine_override: str = "qwen-vl",
    ):
        """
        Uploads PDFs and yields real-time log lines streamed from the API via SSE.
        files: list of (filename, file_bytes) tuples
        """
        upload_payload = [
            ("files", (filename, data, "application/pdf"))
            for filename, data in files
        ]

        with httpx.Client(base_url=self.base_url, timeout=None) as client:
            with client.stream(
                "POST",
                "/docproc/pipeline/stream",
                files=upload_payload,
                params={"engine": engine_override},
            ) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if line:
                        yield line