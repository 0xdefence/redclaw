"""Tool dependency graph with keyword-based scoring."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class IntentCategory(str, Enum):
    RECON = "recon"
    SCANNING = "scanning"
    ENUMERATION = "enumeration"
    EXPLOITATION = "exploitation"
    ANALYSIS = "analysis"


@dataclass
class ToolNode:
    """A node in the tool graph."""
    id: str
    name: str
    description: str
    category: IntentCategory
    keywords: list[str] = field(default_factory=list)
    risk_level: str = "active"


@dataclass
class ToolEdge:
    """Directed edge: source should run before target."""
    source: str
    target: str
    weight: float = 1.0


class ToolGraph:
    """Graph of tools with dependency edges and keyword scoring."""

    def __init__(self) -> None:
        self._nodes: dict[str, ToolNode] = {}
        self._edges: list[ToolEdge] = []
        self._build_default_graph()

    def _build_default_graph(self) -> None:
        """Build the default tool graph with 6 tools and dependency edges."""
        # Define nodes
        nodes = [
            ToolNode(
                id="dig",
                name="DNS Lookup",
                description="DNS record lookup — A, AAAA, MX, NS, TXT records",
                category=IntentCategory.RECON,
                keywords=["dns", "domain", "records", "mx", "nameserver", "resolve", "lookup"],
                risk_level="passive",
            ),
            ToolNode(
                id="whois",
                name="WHOIS Lookup",
                description="Domain registration lookup — registrar, dates, nameservers",
                category=IntentCategory.RECON,
                keywords=["whois", "domain", "registrar", "registration", "owner", "expiry"],
                risk_level="passive",
            ),
            ToolNode(
                id="nmap",
                name="Nmap Port Scanner",
                description="Network port scanning, service detection, OS fingerprinting",
                category=IntentCategory.SCANNING,
                keywords=["port", "scan", "service", "open", "tcp", "udp", "network", "host", "discover"],
                risk_level="active",
            ),
            ToolNode(
                id="nikto",
                name="Nikto Web Scanner",
                description="Web server vulnerability scanner — misconfigurations, outdated software",
                category=IntentCategory.SCANNING,
                keywords=["web", "http", "vulnerability", "server", "apache", "nginx", "scan", "website"],
                risk_level="intrusive",
            ),
            ToolNode(
                id="nuclei",
                name="Nuclei Scanner",
                description="Template-based vulnerability scanner with thousands of CVE checks",
                category=IntentCategory.SCANNING,
                keywords=["vulnerability", "cve", "template", "exploit", "security", "scan", "detect"],
                risk_level="intrusive",
            ),
            ToolNode(
                id="gobuster",
                name="Gobuster Directory Scanner",
                description="Directory and file brute-forcing, virtual host discovery",
                category=IntentCategory.ENUMERATION,
                keywords=["directory", "brute", "force", "files", "path", "enumerate", "discover", "hidden"],
                risk_level="active",
            ),
        ]

        for node in nodes:
            self._nodes[node.id] = node

        # Define edges (source runs before target)
        edges = [
            # DNS/WHOIS should run first (passive recon)
            ToolEdge("dig", "nmap", 1.0),
            ToolEdge("dig", "whois", 0.5),
            ToolEdge("whois", "nmap", 0.8),
            # Port scan before web scanning
            ToolEdge("nmap", "nikto", 1.0),
            ToolEdge("nmap", "nuclei", 1.0),
            ToolEdge("nmap", "gobuster", 0.9),
            # Web scanners can inform each other
            ToolEdge("nikto", "nuclei", 0.5),
            ToolEdge("gobuster", "nikto", 0.6),
            ToolEdge("gobuster", "nuclei", 0.6),
        ]

        self._edges = edges

    def get_node(self, tool_id: str) -> ToolNode | None:
        """Get a tool node by ID."""
        return self._nodes.get(tool_id)

    def list_nodes(self) -> list[ToolNode]:
        """List all tool nodes."""
        return list(self._nodes.values())

    def get_dependencies(self, tool_id: str) -> list[str]:
        """Get tools that should run before this tool."""
        return [e.source for e in self._edges if e.target == tool_id]

    def get_dependents(self, tool_id: str) -> list[str]:
        """Get tools that should run after this tool."""
        return [e.target for e in self._edges if e.source == tool_id]

    def analyze_query(self, query: str) -> dict[IntentCategory, float]:
        """Analyze a query and return intent category scores."""
        query_lower = query.lower()
        scores: dict[IntentCategory, float] = {cat: 0.0 for cat in IntentCategory}

        # Category keyword mappings
        category_keywords = {
            IntentCategory.RECON: ["recon", "reconnaissance", "discover", "find", "lookup", "dns", "whois", "domain", "information"],
            IntentCategory.SCANNING: ["scan", "port", "service", "vulnerability", "vuln", "detect", "check", "security"],
            IntentCategory.ENUMERATION: ["enumerate", "brute", "force", "directory", "file", "path", "list", "discover"],
            IntentCategory.EXPLOITATION: ["exploit", "attack", "compromise", "shell", "access", "rce", "injection"],
            IntentCategory.ANALYSIS: ["analyze", "report", "summary", "findings", "results", "review"],
        }

        for category, keywords in category_keywords.items():
            for keyword in keywords:
                if keyword in query_lower:
                    scores[category] += 1.0

        # Normalize scores
        total = sum(scores.values())
        if total > 0:
            for cat in scores:
                scores[cat] /= total

        return scores

    def score_tool(self, tool_id: str, query: str) -> float:
        """Score a tool's relevance to a query (0.0 - 1.0)."""
        node = self._nodes.get(tool_id)
        if not node:
            return 0.0

        query_lower = query.lower()
        query_words = set(query_lower.split())

        # Keyword match score
        keyword_matches = sum(1 for kw in node.keywords if kw in query_lower)
        keyword_score = min(keyword_matches / max(len(node.keywords), 1), 1.0)

        # Word overlap score
        node_words = set(node.description.lower().split())
        overlap = len(query_words & node_words)
        overlap_score = min(overlap / max(len(query_words), 1), 1.0)

        # Category match score
        intent_scores = self.analyze_query(query)
        category_score = intent_scores.get(node.category, 0.0)

        # Combined score (weighted)
        final_score = (
            0.5 * keyword_score +
            0.2 * overlap_score +
            0.3 * category_score
        )

        return min(final_score, 1.0)

    def recommend_tools(self, query: str, limit: int = 5) -> list[tuple[str, float, str]]:
        """Recommend tools for a query.

        Returns:
            List of (tool_id, score, rationale) tuples, sorted by score descending.
        """
        results: list[tuple[str, float, str]] = []

        for tool_id, node in self._nodes.items():
            score = self.score_tool(tool_id, query)
            if score > 0.1:  # Minimum threshold
                rationale = f"{node.name} — {node.description}"
                results.append((tool_id, score, rationale))

        # Sort by score descending
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:limit]

    def topological_sort(self, tool_ids: list[str]) -> list[str]:
        """Sort tools in dependency order (tools with no deps first)."""
        # Build adjacency for subset
        in_degree: dict[str, int] = {t: 0 for t in tool_ids}
        adj: dict[str, list[str]] = {t: [] for t in tool_ids}

        for edge in self._edges:
            if edge.source in tool_ids and edge.target in tool_ids:
                adj[edge.source].append(edge.target)
                in_degree[edge.target] += 1

        # Kahn's algorithm
        queue = [t for t in tool_ids if in_degree[t] == 0]
        result: list[str] = []

        while queue:
            node = queue.pop(0)
            result.append(node)
            for neighbor in adj[node]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        # Add any remaining (cycle or disconnected)
        for t in tool_ids:
            if t not in result:
                result.append(t)

        return result
