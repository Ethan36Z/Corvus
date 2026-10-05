"""Historical recall provider for Corvus Working Context."""

from memory.hybrid_search import hybrid_search


def recall(query, limit=5, candidate_limit=20):
    """Return ranked canonical message rows using Corvus hybrid recall.

    Rows retain their canonical integer ID, role, content and retrieval
    metadata. Recent context, exclusions, token budgets and persistence
    remain the caller's responsibility.
    """
    return hybrid_search(
        query,
        limit=limit,
        candidate_limit=candidate_limit,
    )
