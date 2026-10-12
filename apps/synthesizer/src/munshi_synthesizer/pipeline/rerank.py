from __future__ import annotations

from sentence_transformers import CrossEncoder
from munshi_synthesizer.schema import PublicationSource


class PublicationReranker:
    """Uses a cross-encoder to rank and stratify publication sources based on subtopic relevance."""

    def __init__(self, model_name: str = "BAAI/bge-reranker-base"):
        self.model = CrossEncoder(model_name)

    def prioritize_sources(
        self,
        query: str,
        sources: list[PublicationSource],
        top_k: int = 5,
    ) -> tuple[list[PublicationSource], list[PublicationSource]]:
        """
        Reranks publication sources. 
        Returns:
            (primary_anchors, supplementary_sources)
        """
        if len(sources) <= top_k:
            return sources, []

        # Construct scoring pairs from Title + Lede + Summary
        pairs = [
            [query, f"{s.title}. {s.lede} {s.summary} {' '.join(s.key_findings[:3])}"]
            for s in sources
        ]
        scores = self.model.predict(pairs)

        for src, score in zip(sources, scores):
            src.relevance_score = float(score)

        # Sort descending
        ranked = sorted(sources, key=lambda x: x.relevance_score, reverse=True)
        return ranked[:top_k], ranked[top_k:]