"""Shared text processing utilities for retrieval."""

from __future__ import annotations

import math
import re


LATIN_TOKEN_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._/-]*")
CJK_SPAN_PATTERN = re.compile(r"[\u4e00-\u9fff]+")


def tokenize_for_retrieval(text: str) -> list[str]:
    normalized = " ".join(text.lower().split())
    tokens: list[str] = []
    tokens.extend(LATIN_TOKEN_PATTERN.findall(normalized))

    for span in CJK_SPAN_PATTERN.findall(normalized):
        if len(span) == 1:
            tokens.append(span)
            continue
        tokens.append(span)
        tokens.extend(span[index : index + 2] for index in range(len(span) - 1))

    return tokens


def l2_normalize(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0.0:
        return vector[:]
    return [value / norm for value in vector]
