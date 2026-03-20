"""Application configuration."""
from __future__ import annotations

import os
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field


class RedClawConfig(BaseSettings):
    """Global configuration loaded from env vars and ~/.redclaw/config."""

    # Paths
    data_dir: Path = Field(default_factory=lambda: Path.home() / ".redclaw")
    db_path: Path | None = None  # Computed in model_post_init

    # Docker
    docker_image: str = "redclaw/kali:latest"
    container_name: str = "redclaw-kali"
    container_timeout: int = 300  # Max seconds per tool execution

    # Security policy
    allow_private_networks: bool = False
    max_concurrent_scans: int = 5
    max_daily_scans_per_target: int = 100

    # Display
    verbose: bool = False
    no_color: bool = False

    # Optional AI (not used in MVP)
    openrouter_api_key: str | None = None

    model_config = {"env_prefix": "REDCLAW_", "env_file": ".env"}

    def model_post_init(self, __context: object) -> None:
        if self.db_path is None:
            self.db_path = self.data_dir / "redclaw.db"
        self.data_dir.mkdir(parents=True, exist_ok=True)


def get_config() -> RedClawConfig:
    """Get or create the global config singleton."""
    return RedClawConfig()
