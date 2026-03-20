"""Tests for the agent layer — memory, prompts, agent config."""
import pytest
from datetime import datetime, timezone

from redclaw.agent.memory import WorkingMemory, MemoryEntry
from redclaw.agent.prompts import get_prompt, SYSTEM_PROMPTS
from redclaw.agent.agent import AgentConfig, LLMAgent


class TestWorkingMemory:
    """Tests for WorkingMemory."""

    def test_create_memory(self):
        memory = WorkingMemory()
        assert memory.goal == ""
        assert memory.current_phase == "init"
        assert len(memory.entries) == 0

    def test_set_goal(self):
        memory = WorkingMemory()
        memory.set_goal("Scan for vulnerabilities")
        assert memory.goal == "Scan for vulnerabilities"
        assert len(memory.entries) == 1
        assert memory.entries[0].type == "goal"

    def test_add_thought(self):
        memory = WorkingMemory()
        memory.add_thought("I should start with DNS lookup")
        assert len(memory.entries) == 1
        assert memory.entries[0].type == "thought"
        assert "DNS" in memory.entries[0].content

    def test_add_action(self):
        memory = WorkingMemory()
        memory.add_action("nmap", {"profile": "quick"})
        assert "nmap" in memory.tools_executed
        assert len(memory.entries) == 1
        assert memory.entries[0].type == "action"

    def test_add_observation(self):
        memory = WorkingMemory()
        memory.add_observation("nmap", "Found 3 open ports", 3)
        assert len(memory.entries) == 1
        assert memory.entries[0].metadata["findings_count"] == 3

    def test_add_finding(self):
        memory = WorkingMemory()
        memory.add_finding("Open port 80", "info")
        assert "Open port 80" in memory.key_findings
        assert len(memory.entries) == 1

    def test_add_hypothesis(self):
        memory = WorkingMemory()
        memory.add_hypothesis("Target may be running Apache")
        assert "Apache" in memory.hypotheses[0]

    def test_set_phase(self):
        memory = WorkingMemory()
        memory.set_phase("scanning")
        assert memory.current_phase == "scanning"

    def test_to_context(self):
        memory = WorkingMemory()
        memory.set_goal("Test scan")
        memory.add_action("nmap", {})
        memory.add_finding("Open port 22", "info")

        context = memory.to_context()
        assert "Test scan" in context
        assert "nmap" in context
        assert "Open port 22" in context

    def test_get_recent(self):
        memory = WorkingMemory()
        for i in range(15):
            memory.add("test", f"Entry {i}")

        recent = memory.get_recent(5)
        assert len(recent) == 5
        assert recent[-1].content == "Entry 14"

    def test_get_recent_by_type(self):
        memory = WorkingMemory()
        memory.add_thought("thought 1")
        memory.add_action("nmap", {})
        memory.add_thought("thought 2")

        thoughts = memory.get_recent(10, "thought")
        assert len(thoughts) == 2

    def test_clear(self):
        memory = WorkingMemory()
        memory.set_goal("Test")
        memory.add_finding("Finding", "info")
        memory.clear()

        assert memory.goal == ""
        assert len(memory.entries) == 0
        assert len(memory.key_findings) == 0

    def test_max_entries_limit(self):
        memory = WorkingMemory(max_entries=10)
        for i in range(20):
            memory.add("test", f"Entry {i}")

        assert len(memory.entries) == 10
        assert memory.entries[0].content == "Entry 10"

    def test_serialization(self):
        memory = WorkingMemory()
        memory.set_goal("Test goal")
        memory.add_finding("Finding 1", "high")

        data = memory.to_dict()
        restored = WorkingMemory.from_dict(data)

        assert restored.goal == "Test goal"
        assert "Finding 1" in restored.key_findings


class TestMemoryEntry:
    """Tests for MemoryEntry."""

    def test_create_entry(self):
        entry = MemoryEntry(
            timestamp=datetime.now(timezone.utc),
            type="thought",
            content="Test thought",
        )
        assert entry.type == "thought"
        assert entry.content == "Test thought"

    def test_entry_to_dict(self):
        entry = MemoryEntry(
            timestamp=datetime.now(timezone.utc),
            type="action",
            content="Run nmap",
            metadata={"tool_id": "nmap"},
        )
        data = entry.to_dict()
        assert data["type"] == "action"
        assert data["metadata"]["tool_id"] == "nmap"

    def test_entry_from_dict(self):
        data = {
            "timestamp": "2024-01-01T00:00:00+00:00",
            "type": "finding",
            "content": "Open port",
            "metadata": {"severity": "info"},
        }
        entry = MemoryEntry.from_dict(data)
        assert entry.type == "finding"
        assert entry.metadata["severity"] == "info"


class TestPrompts:
    """Tests for prompt templates."""

    def test_all_prompts_exist(self):
        expected = ["tool_selection", "react_agent", "result_analysis", "scan_summary"]
        for name in expected:
            assert name in SYSTEM_PROMPTS

    def test_get_prompt_tool_selection(self):
        prompt = get_prompt("tool_selection", tools="- nmap: port scanner")
        assert "nmap" in prompt
        assert "JSON" in prompt

    def test_get_prompt_react_agent(self):
        prompt = get_prompt(
            "react_agent",
            tools="- nmap: scanner",
            memory="{}",
            max_steps=10,
        )
        assert "ReAct" in prompt
        assert "10" in prompt

    def test_get_prompt_invalid(self):
        with pytest.raises(ValueError):
            get_prompt("nonexistent")


class TestAgentConfig:
    """Tests for AgentConfig."""

    def test_default_config(self):
        config = AgentConfig()
        assert config.provider == "openrouter"
        assert "claude" in config.model
        assert config.temperature == 0.1

    def test_config_from_env(self, monkeypatch):
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
        config = AgentConfig.from_env()
        assert config.api_key == "test-key"


class TestLLMAgent:
    """Tests for LLMAgent (without actual API calls)."""

    def test_agent_not_available_without_key(self):
        config = AgentConfig(api_key=None)
        agent = LLMAgent(config)
        assert not agent.is_available

    def test_agent_available_with_key(self):
        config = AgentConfig(api_key="test-key")
        agent = LLMAgent(config)
        assert agent.is_available

    def test_generate_requires_key(self):
        config = AgentConfig(api_key=None)
        agent = LLMAgent(config)
        with pytest.raises(RuntimeError, match="not available"):
            agent.generate("test prompt")
