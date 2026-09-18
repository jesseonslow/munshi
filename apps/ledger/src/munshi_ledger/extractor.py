from gliner import GLiNER
from typing import Dict, Any, List

class Gliner2Extractor:
    def __init__(self, model_name: str = "knowledgator/gliner-multitask-v1.0"):
        self.model = GLiNER.from_pretrained(model_name)
        
        self.entity_labels = [
            "person", "place", "group", "event", "concept", "publication"
        ]
        
        # Historical predicates for tuplet extraction
        self.relation_labels = [
            "HELD_OFFICE",
            "ADMINISTERED_REGION",
            "AUTHORED",
            "COLLECTED_OR_OWNED",
            "OPPOSED",
            "MET_WITH"
        ]

    def extract(self, text: str, threshold: float = 0.5) -> Dict[str, Any]:
        """Extracts both entities and relational tuplets from a paragraph."""
        
        # Note: Depending on the specific GLiNER2 API version installed, 
        # this syntax may adapt to model.predict_relations()
        try:
            results = self.model.predict_entities(text, self.entity_labels, threshold=threshold)
            # Placeholder for GLiNER2 relation extraction API:
            relations = getattr(self.model, "predict_relations", lambda t, e, r: [])(text, results, self.relation_labels)
        except Exception:
            results = []
            relations = []

        return {
            "entities": results,
            "relations": relations
        }