"""Embedding utilities using HuggingFace SentenceTransformer."""
from sentence_transformers import SentenceTransformer
import numpy as np

# Load HF embedding model
# Model: all-MiniLM-L6-v2 (100% free, fast, and perfect for semantic matching)
model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")


def embed_text(text: str) -> np.ndarray:
    """Embed a single piece of text."""
    return model.encode(text, convert_to_numpy=True)


def embed_texts(texts: list[str]) -> np.ndarray:
    """Embed a list of texts and return an array of embeddings."""
    return model.encode(texts, convert_to_numpy=True)
