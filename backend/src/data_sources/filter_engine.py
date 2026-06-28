"""Matching engine placeholder."""

from src.data_sources.keyword import keyword_score


async def match_job(text: str, keywords: list[str], threshold: float) -> tuple[float, bool]:
    """Return a placeholder match score and acceptance flag."""

    score = await keyword_score(text=text, keywords=keywords)
    return score, score >= threshold