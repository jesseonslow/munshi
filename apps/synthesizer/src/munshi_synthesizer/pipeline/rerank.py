from __future__ import annotations

import re
from sentence_transformers import CrossEncoder
from munshi_synthesizer.schema import OccurrenceRecord


class PassageReranker:
    def __init__(self, model_name: str = "BAAI/bge-reranker-base"):
        self.model = CrossEncoder(model_name)

    def filter_and_rerank(
        self,
        query: str,
        records: list[OccurrenceRecord],
        top_k: int = 25,
        min_score: float = 0.1,
    ) -> list[OccurrenceRecord]:
        clean_candidates: list[OccurrenceRecord] = []

        for r in records:
            text = r.context_snippet.strip()
            # 1. Eliminate short noise & CLI diagnostic lines
            if len(text.split()) < 35:
                continue
            if text.startswith(("File:", "Group:", "Context:", "Routes:", "#1 heading")):
                continue
            # 2. Eliminate footnote & bibliography fragments
            if text.startswith(("[^", "^", "## References", "## Bibliography")):
                continue
            if re.search(r"^\d+\.\s+.*?JMBRAS", text):
                continue

            clean_candidates.append(r)

        if not clean_candidates:
            return records[:top_k]

        # Score pairs with cross-encoder
        pairs = [[query, r.context_snippet] for r in clean_candidates]
        scores = self.model.predict(pairs)

        for rec, score in zip(clean_candidates, scores):
            rec.similarity_score = float(score)

        clean_candidates.sort(key=lambda x: x.similarity_score or 0.0, reverse=True)
        return [r for r in clean_candidates if (r.similarity_score or 0.0) >= min_score][:top_k]