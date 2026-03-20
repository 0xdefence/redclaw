"""Application configuration."""
from __future__ import annotations

import os
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field


# Docker image variants
DOCKER_IMAGES = {
    "minimal": "redclaw/kali:minimal",      # ~300 MB - Basic tools (nmap, dig, whois)
    "standard": "redclaw/kali:standard",    # ~400 MB - Default (+ nikto, gobuster)
    "full": "redclaw/kali:full",            # ~800 MB - Full suite (+ nuclei)
    "latest": "redclaw/kali:standard",      # Alias for standard
}


class RedClawConfig(BaseSettings):
    """Global configuration loaded from env vars and ~/.redclaw/config."""

    # Paths
    data_dir: Path = Field(default_factory=lambda: Path.home() / ".redclaw")
    db_path: Path | None = None  # Computed in model_post_init

    # Docker
    docker_image: str = "standard"  # minimal, standard, full (or full image name)
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

    def get_docker_image(self) -> str:
        """Get the full Docker image name from variant or direct name.

        Returns:
            Full Docker image name (e.g., "redclaw/kali:standard")
        """
        # If it's a known variant, return the full image name
        if self.docker_image in DOCKER_IMAGES:
            return DOCKER_IMAGES[self.docker_image]

        # Otherwise, assume it's a full image name
        return self.docker_image


def get_config() -> RedClawConfig:
    """Get or create the global config singleton."""
    return RedClawConfig()
