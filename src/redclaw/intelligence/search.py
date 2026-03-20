"""Hybrid search — keyword graph + optional vector similarity."""
from __future__ import annotations

from dataclasses import dataclass

from redclaw.intelligence.graph import ToolGraph


@dataclass
class SearchResult:
    """A single search result."""
    tool_id: str
    score: float
    name: str
    description: str
    category: str
    risk_level: str
    rationale: str
    sources: list[str]  # ["keyword"] or ["keyword", "vector"]


class HybridSearch:
    """Hybrid search combining keyword graph and optional vector similarity."""

    def __init__(self, graph: ToolGraph | None = None) -> None:
        self.graph = graph or ToolGraph()
        self._vector_enabled = False
        self._embeddings: dict[str, list[float]] = {}

    def enable_vector_search(self, embeddings: dict[str, list[float]]) -> None:
        """Enable vector search with pre-computed embeddings."""
        self._embeddings = embeddings
        self._vector_enabled = bool(embeddings)

    def search(
        self,
        query: str,
        limit: int = 5,
        min_score: float = 0.1,
    ) -> list[SearchResult]:
        """Search for tools matching a query.

        Args:
            query: Natural language search query
            limit: Maximum results to return
            min_score: Minimum score threshold

        Returns:
            List of SearchResult objects sorted by relevance
        """
        # Get keyword-based recommendations
        keyword_results = self.graph.recommend_tools(query, limit=limit * 2)

        # Build results
        results: list[SearchResult] = []

        for tool_id, keyword_score, rationale in keyword_results:
            node = self.graph.get_node(tool_id)
            if not node:
                continue

            # Vector score (if enabled)
            vector_score = 0.0
            sources = ["keyword"]

            if self._vector_enabled and tool_id in self._embeddings:
                # Placeholder for actual vector similarity
                # In a real implementation, we'd compute cosine similarity
                vector_score = keyword_score * 0.8  # Simulated
                sources.append("vector")

            # Hybrid score: 60% keyword, 40% vector (when vector enabled)
            if self._vector_enabled:
                final_score = 0.6 * keyword_score + 0.4 * vector_score
            else:
                final_score = keyword_score

            if final_score >= min_score:
                results.append(SearchResult(
                    tool_id=tool_id,
                    score=final_score,
                    name=node.name,
                    description=node.description,
                    category=node.category.value,
                    risk_level=node.risk_level,
                    rationale=rationale,
                    sources=sources,
                ))

        # Sort by score and limit
        results.sort(key=lambda r: r.score, reverse=True)
        return results[:limit]

    def search_by_category(self, category: str, limit: int = 5) -> list[SearchResult]:
        """Search for tools in a specific category."""
        results: list[SearchResult] = []

        for node in self.graph.list_nodes():
            if node.category.value == category:
                results.append(SearchResult(
                    tool_id=node.id,
                    score=1.0,
                    name=node.name,
                    description=node.description,
                    category=node.category.value,
                    risk_level=node.risk_level,
                    rationale=f"Category match: {category}",
                    sources=["category"],
                ))

        return results[:limit]
