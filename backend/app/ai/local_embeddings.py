"""Deterministic local text embeddings when the AI provider has no embed API."""

from __future__ import annotations

import hashlib
import math
import re


def local_text_embedding(text: str, dimensions: int = 768) -> list[float]:
    """Hash bag-of-words style vector — good enough for dev semantic similarity."""
    tokens = re.findall(r"[a-z0-9]+", text.lower())
    if not tokens:
        tokens = ["empty"]

    vector = [0.0] * dimensions
    for token in tokens:
        digest = hashlib.sha256(token.encode()).digest()
        for index in range(dimensions):
            vector[index] += (digest[index % len(digest)] / 255.0) - 0.5

    norm = math.sqrt(sum(value * value for value in vector)) or 1.0
    return [value / norm for value in vector]
