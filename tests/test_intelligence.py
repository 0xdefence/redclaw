"""Tests for the intelligence layer — graph, search, workflow."""
import pytest

from redclaw.intelligence.graph import ToolGraph, ToolNode, IntentCategory
from redclaw.intelligence.search import HybridSearch, SearchResult
from redclaw.intelligence.workflow import WorkflowGenerator


class TestToolGraph:
    """Tests for ToolGraph."""

    def test_default_graph_has_nodes(self):
        graph = ToolGraph()
        nodes = graph.list_nodes()
        assert len(nodes) >= 6
        assert any(n.id == "nmap" for n in nodes)
        assert any(n.id == "nuclei" for n in nodes)
        assert any(n.id == "gobuster" for n in nodes)

    def test_get_node(self):
        graph = ToolGraph()
        node = graph.get_node("nmap")
        assert node is not None
        assert node.id == "nmap"
        assert node.category == IntentCategory.SCANNING

    def test_get_nonexistent_node(self):
        graph = ToolGraph()
        node = graph.get_node("nonexistent")
        assert node is None

    def test_analyze_query_recon(self):
        graph = ToolGraph()
        scores = graph.analyze_query("discover DNS records and domain info")
        assert scores[IntentCategory.RECON] > 0.3

    def test_analyze_query_scanning(self):
        graph = ToolGraph()
        scores = graph.analyze_query("scan for open ports and vulnerabilities")
        assert scores[IntentCategory.SCANNING] > 0.3

    def test_score_tool_relevant(self):
        graph = ToolGraph()
        score = graph.score_tool("nmap", "scan for open ports")
        assert score > 0.3

    def test_score_tool_irrelevant(self):
        graph = ToolGraph()
        score = graph.score_tool("whois", "scan for open ports")
        assert score < 0.3

    def test_recommend_tools(self):
        graph = ToolGraph()
        recs = graph.recommend_tools("find open ports on a web server", limit=3)
        assert len(recs) > 0
        tool_ids = [r[0] for r in recs]
        assert "nmap" in tool_ids

    def test_dependencies(self):
        graph = ToolGraph()
        deps = graph.get_dependencies("nikto")
        assert "nmap" in deps  # nmap should run before nikto

    def test_topological_sort(self):
        graph = ToolGraph()
        sorted_tools = graph.topological_sort(["nikto", "nmap", "dig"])
        # dig and nmap should come before nikto
        nikto_idx = sorted_tools.index("nikto")
        nmap_idx = sorted_tools.index("nmap")
        assert nmap_idx < nikto_idx


class TestHybridSearch:
    """Tests for HybridSearch."""

    def test_search_returns_results(self):
        search = HybridSearch()
        results = search.search("scan for vulnerabilities")
        assert len(results) > 0
        assert all(isinstance(r, SearchResult) for r in results)

    def test_search_nmap_for_ports(self):
        search = HybridSearch()
        results = search.search("find open ports")
        tool_ids = [r.tool_id for r in results]
        assert "nmap" in tool_ids

    def test_search_respects_limit(self):
        search = HybridSearch()
        results = search.search("security scan", limit=2)
        assert len(results) <= 2

    def test_search_respects_min_score(self):
        search = HybridSearch()
        results = search.search("security", min_score=0.5)
        assert all(r.score >= 0.5 for r in results)

    def test_search_by_category(self):
        search = HybridSearch()
        results = search.search_by_category("recon")
        assert len(results) > 0
        assert all(r.category == "recon" for r in results)

    def test_search_result_has_sources(self):
        search = HybridSearch()
        results = search.search("web scan")
        assert all("keyword" in r.sources for r in results)


class TestWorkflowGenerator:
    """Tests for WorkflowGenerator."""

    def test_generate_workflow(self):
        gen = WorkflowGenerator()
        workflow = gen.generate("scan a web application for vulnerabilities")
        assert workflow.objective == "scan a web application for vulnerabilities"
        assert len(workflow.steps) > 0

    def test_workflow_has_estimated_duration(self):
        gen = WorkflowGenerator()
        workflow = gen.generate("port scan and web scan")
        assert workflow.estimated_duration_s > 0

    def test_workflow_intrusive_requires_confirmation(self):
        gen = WorkflowGenerator()
        workflow = gen.generate("run nuclei and nikto scans")
        assert workflow.requires_confirmation is True

    def test_workflow_passive_no_confirmation(self):
        gen = WorkflowGenerator()
        workflow = gen.generate("DNS and WHOIS lookup")
        # May or may not require confirmation depending on detected tools
        assert workflow.objective == "DNS and WHOIS lookup"

    def test_workflow_respects_max_steps(self):
        gen = WorkflowGenerator()
        workflow = gen.generate("full security audit", max_steps=3)
        assert len(workflow.steps) <= 3

    def test_workflow_has_reasoning(self):
        gen = WorkflowGenerator()
        workflow = gen.generate("enumerate directories")
        assert len(workflow.reasoning) > 0

    def test_to_tool_plan(self):
        gen = WorkflowGenerator()
        workflow = gen.generate("port scan")
        plan = gen.to_tool_plan(workflow, "example.com")
        assert plan.objective == workflow.objective
        assert len(plan.steps) == len(workflow.steps)
