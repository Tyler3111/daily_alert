"""Keyword matching placeholder logic."""


async def keyword_score(text: str, keywords: list[str]) -> float:
    """Compute a placeholder keyword score."""

    if not text or not keywords:
        return 0.0
    text_lower = text.lower()
    matches = sum(1 for keyword in keywords if keyword.lower() in text_lower)
    return matches / len(keywords)
