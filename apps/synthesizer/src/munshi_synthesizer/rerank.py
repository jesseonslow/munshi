"""ONNX Runtime-based passage reranker for scoring publication relevance."""
from __future__ import annotations

import math
from pathlib import Path
import numpy as np
import onnxruntime as ort
from tokenizers import Tokenizer

from munshi_synthesizer.schema import PublicationSource


def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


class PublicationReranker:
    """Uses ONNX Runtime CPU inference to score and stratify publication sources."""

    def __init__(self, model_dir: Path | str = "models/bge-reranker-base-onnx"):
        self.model_dir = Path(model_dir)
        onnx_model_path = self.model_dir / "onnx" / "model.onnx"
        tokenizer_path = self.model_dir / "tokenizer.json"

        if not onnx_model_path.exists():
            raise FileNotFoundError(f"ONNX model file not found at: {onnx_model_path}")

        # 1. Initialize tokenizer
        self.tokenizer = Tokenizer.from_file(str(tokenizer_path))
        self.tokenizer.enable_truncation(max_length=512)
        self.tokenizer.enable_padding(length=512)

        # 2. Configure ONNX Runtime CPU Session
        sess_options = ort.SessionOptions()
        sess_options.intra_op_num_threads = 4
        sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL

        self.session = ort.InferenceSession(
            str(onnx_model_path),
            sess_options=sess_options,
            providers=["CPUExecutionProvider"],
        )

    def score_pairs(self, pairs: list[tuple[str, str]]) -> list[float]:
        """Scores a list of (query, document) pairs using ONNX Runtime."""
        if not pairs:
            return []

        # Tokenize query + document pairs together as sentence pairs
        encodings = [self.tokenizer.encode(query, doc) for query, doc in pairs]

        input_ids = np.array([enc.ids for enc in encodings], dtype=np.int64)
        attention_mask = np.array([enc.attention_mask for enc in encodings], dtype=np.int64)

        onnx_inputs = {
            "input_ids": input_ids,
            "attention_mask": attention_mask,
        }

        # Check if the ONNX graph expects token_type_ids
        model_input_names = [inp.name for inp in self.session.get_inputs()]
        if "token_type_ids" in model_input_names:
            token_type_ids = np.array([enc.type_ids for enc in encodings], dtype=np.int64)
            onnx_inputs["token_type_ids"] = token_type_ids

        # Run ONNX inference
        raw_outputs = self.session.run(None, onnx_inputs)
        logits = raw_outputs[0].squeeze(-1)

        # Convert logits to probability via sigmoid
        if isinstance(logits, np.ndarray) and logits.ndim == 0:
            return [_sigmoid(float(logits))]
        return [_sigmoid(float(logit)) for logit in logits]

    def prioritize_sources(
        self,
        query: str,
        sources: list[PublicationSource],
        top_k: int = 5,
    ) -> tuple[list[PublicationSource], list[PublicationSource]]:
        """Stratifies candidates into primary anchors and supplementary sources."""
        if len(sources) <= top_k:
            return sources, []

        pairs = [
            (query, f"{s.title}. {s.lede} {s.summary} {' '.join(s.key_findings[:3])}")
            for s in sources
        ]

        scores = self.score_pairs(pairs)

        for src, score in zip(sources, scores):
            src.relevance_score = float(score)

        ranked = sorted(sources, key=lambda x: x.relevance_score, reverse=True)
        return ranked[:top_k], ranked[top_k:]