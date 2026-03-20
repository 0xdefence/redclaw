"""LLM Agent for tool selection and reasoning."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any

from redclaw.models import get_config
from redclaw.agent.prompts import get_prompt


@dataclass
class AgentConfig:
    """Configuration for the LLM agent."""
    provider: str = "openrouter"  # openrouter, openai, local
    model: str = "anthropic/claude-3.5-sonnet"
    api_key: str | None = None
    base_url: str = "https://openrouter.ai/api/v1"
    temperature: float = 0.1
    max_tokens: int = 2000
    timeout: int = 60

    @classmethod
    def from_env(cls) -> "AgentConfig":
        """Load config from environment variables."""
        config = get_config()
        api_key = config.openrouter_api_key or os.environ.get("OPENROUTER_API_KEY")

        return cls(
            api_key=api_key,
            model=os.environ.get("REDCLAW_MODEL", "anthropic/claude-3.5-sonnet"),
            temperature=float(os.environ.get("REDCLAW_TEMPERATURE", "0.1")),
        )


class LLMAgent:
    """LLM-powered agent for security scanning decisions."""

    def __init__(self, config: AgentConfig | None = None) -> None:
        self.config = config or AgentConfig.from_env()
        self._client: Any = None

    @property
    def is_available(self) -> bool:
        """Check if the LLM is available (API key set)."""
        return bool(self.config.api_key)

    def _get_client(self) -> Any:
        """Get or create the HTTP client."""
        if self._client is None:
            try:
                import httpx
                self._client = httpx.Client(timeout=self.config.timeout)
            except ImportError:
                raise RuntimeError(
                    "httpx is required for LLM features. Install with: pip install redclaw[ai]"
                )
        return self._client

    def generate(
        self,
        prompt: str,
        system: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str:
        """Generate a response from the LLM.

        Args:
            prompt: User prompt
            system: System prompt (optional)
            temperature: Override temperature
            max_tokens: Override max tokens

        Returns:
            Generated text response
        """
        if not self.is_available:
            raise RuntimeError(
                "LLM not available. Set OPENROUTER_API_KEY or REDCLAW_OPENROUTER_API_KEY."
            )

        client = self._get_client()

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.config.model,
            "messages": messages,
            "temperature": temperature or self.config.temperature,
            "max_tokens": max_tokens or self.config.max_tokens,
        }

        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/0xdefence/redclaw",
            "X-Title": "RedClaw Security Scanner",
        }

        response = client.post(
            f"{self.config.base_url}/chat/completions",
            json=payload,
            headers=headers,
        )

        if response.status_code != 200:
            raise RuntimeError(f"LLM API error: {response.status_code} - {response.text}")

        data = response.json()
        return data["choices"][0]["message"]["content"]

    def generate_json(
        self,
        prompt: str,
        system: str | None = None,
        temperature: float | None = None,
    ) -> dict:
        """Generate a JSON response from the LLM.

        Args:
            prompt: User prompt
            system: System prompt
            temperature: Override temperature

        Returns:
            Parsed JSON dict
        """
        response = self.generate(prompt, system, temperature)

        # Try to parse JSON from response
        # Handle markdown code blocks
        if "```json" in response:
            start = response.find("```json") + 7
            end = response.find("```", start)
            response = response[start:end].strip()
        elif "```" in response:
            start = response.find("```") + 3
            end = response.find("```", start)
            response = response[start:end].strip()

        try:
            return json.loads(response)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON response: {response[:200]}") from exc

    def select_tools(
        self,
        target: str,
        objective: str,
        available_tools: list[dict],
    ) -> dict:
        """Use LLM to select appropriate tools for an objective.

        Args:
            target: Scan target
            objective: What to accomplish
            available_tools: List of available tools with metadata

        Returns:
            Dict with "tools", "reasoning", "estimated_duration_s"
        """
        tools_str = "\n".join(
            f"- {t['id']}: {t['description']} (category: {t['category']}, risk: {t['risk_level']})"
            for t in available_tools
        )

        system = get_prompt("tool_selection", tools=tools_str)
        prompt = f"Target: {target}\nObjective: {objective}"

        return self.generate_json(prompt, system)

    def analyze_result(
        self,
        tool_id: str,
        target: str,
        output: str,
    ) -> str:
        """Use LLM to analyze tool output.

        Args:
            tool_id: Tool that produced the output
            target: Scan target
            output: Raw tool output

        Returns:
            Analysis text
        """
        system = get_prompt(
            "result_analysis",
            tool_id=tool_id,
            target=target,
            output=output[:4000],  # Truncate long outputs
        )

        return self.generate(
            "Analyze this output and provide insights.",
            system,
            temperature=0.2,
        )

    def summarize_scan(
        self,
        target: str,
        tools: list[str],
        findings: list[dict],
    ) -> str:
        """Use LLM to summarize scan results.

        Args:
            target: Scan target
            tools: Tools that were used
            findings: List of findings

        Returns:
            Summary text
        """
        findings_str = "\n".join(
            f"- [{f.get('severity', 'info')}] {f.get('title', 'Unknown')}: {f.get('description', '')[:100]}"
            for f in findings[:20]  # Limit to 20 findings
        )

        system = get_prompt(
            "scan_summary",
            target=target,
            tools=", ".join(tools),
            findings=findings_str,
        )

        return self.generate(
            "Summarize these scan results.",
            system,
            temperature=0.3,
        )


# Singleton for easy access
_agent: LLMAgent | None = None


def get_agent() -> LLMAgent:
    """Get or create the global agent instance."""
    global _agent
    if _agent is None:
        _agent = LLMAgent()
    return _agent
