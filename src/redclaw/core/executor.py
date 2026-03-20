"""Docker-based tool executor."""
from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

import docker
from docker.errors import NotFound, ImageNotFound, APIError
from docker.models.containers import Container

from redclaw.models import RedClawConfig, get_config, ToolResult


@dataclass
class ExecResult:
    """Raw result from docker exec."""
    exit_code: int
    stdout: str
    stderr: str
    duration_ms: int
    command: str


class DockerExecutor:
    """Manages a persistent Kali container and runs commands inside it."""

    def __init__(self, config: RedClawConfig | None = None) -> None:
        self.config = config or get_config()
        self._client: docker.DockerClient | None = None

    @property
    def client(self) -> docker.DockerClient:
        if self._client is None:
            try:
                self._client = docker.from_env()
                self._client.ping()
            except Exception as exc:
                raise RuntimeError(
                    "Cannot connect to Docker. Is Docker Desktop running?"
                ) from exc
        return self._client

    # ── Image Management ──────────────────────────────────────────

    def image_exists(self) -> bool:
        """Check if the Kali image is available locally."""
        try:
            self.client.images.get(self.config.get_docker_image())
            return True
        except ImageNotFound:
            return False

    def build_image(self, dockerfile_dir: Path | None = None) -> str:
        """Build the Kali image from Dockerfile."""
        if dockerfile_dir is None:
            # Look for docker/Dockerfile.kali relative to package
            dockerfile_dir = Path(__file__).resolve().parents[3] / "docker"

        if not (dockerfile_dir / "Dockerfile.kali").exists():
            raise FileNotFoundError(
                f"Dockerfile.kali not found in {dockerfile_dir}. "
                "Run 'claw init' from the project root or pass --dockerfile-dir."
            )

        # Determine which Dockerfile to use based on variant
        variant = self.config.docker_image
        if variant in ("minimal", "standard", "full"):
            dockerfile = f"Dockerfile.{variant}"
        else:
            dockerfile = "Dockerfile.standard"  # Default

        if not (dockerfile_dir / dockerfile).exists():
            raise FileNotFoundError(
                f"{dockerfile} not found in {dockerfile_dir}. "
                f"Available: Dockerfile.minimal, Dockerfile.standard, Dockerfile.full"
            )

        image, _logs = self.client.images.build(
            path=str(dockerfile_dir),
            dockerfile=dockerfile,
            tag=self.config.get_docker_image(),
            rm=True,
        )
        return image.id

    def pull_base_image(self) -> None:
        """Pull kalilinux/kali-rolling if building from scratch."""
        self.client.images.pull("kalilinux/kali-rolling", tag="latest")

    # ── Container Management ──────────────────────────────────────

    def _get_container(self) -> Container | None:
        """Get existing container if running."""
        try:
            container = self.client.containers.get(self.config.container_name)
            if container.status == "running":
                return container
            if container.status in ("created", "exited"):
                container.start()
                time.sleep(1)
                return container
            return None
        except NotFound:
            return None

    def ensure_container(self) -> Container:
        """Get or create the persistent Kali container."""
        container = self._get_container()
        if container is not None:
            return container

        if not self.image_exists():
            raise RuntimeError(
                f"Image '{self.config.get_docker_image()}' not found. Run 'claw init' first."
            )

        container = self.client.containers.run(
            self.config.get_docker_image(),
            name=self.config.container_name,
            detach=True,
            tty=True,
            stdin_open=True,
            # Security: drop all capabilities, re-add only what's needed
            cap_drop=["ALL"],
            cap_add=["NET_RAW", "NET_ADMIN"],  # Required for nmap raw sockets
            # Resource limits
            mem_limit="512m",
            cpu_period=100000,
            cpu_quota=50000,  # 50% of one CPU
            # Network
            network_mode="bridge",
        )
        # Wait for container to be ready
        time.sleep(2)
        return container

    def container_running(self) -> bool:
        """Check if the tool container is running."""
        return self._get_container() is not None

    def stop_container(self) -> None:
        """Stop and remove the container."""
        try:
            container = self.client.containers.get(self.config.container_name)
            container.stop(timeout=10)
            container.remove(force=True)
        except NotFound:
            pass

    # ── Command Execution ─────────────────────────────────────────

    def exec_command(
        self,
        command: list[str],
        timeout: int | None = None,
        workdir: str = "/home/scanner",
    ) -> ExecResult:
        """Execute a command inside the Kali container.

        Args:
            command: Command and arguments as a list (e.g. ["nmap", "-sV", "target"])
            timeout: Timeout in seconds (default: config.container_timeout)
            workdir: Working directory inside container

        Returns:
            ExecResult with exit code, stdout, stderr, duration
        """
        timeout = timeout or self.config.container_timeout
        container = self.ensure_container()

        start = time.monotonic()
        try:
            exit_code, output = container.exec_run(
                cmd=command,
                workdir=workdir,
                demux=True,  # Separate stdout/stderr
                environment={"HOME": "/home/scanner"},
            )
            elapsed = int((time.monotonic() - start) * 1000)

            stdout = (output[0] or b"").decode("utf-8", errors="replace")
            stderr = (output[1] or b"").decode("utf-8", errors="replace")

            return ExecResult(
                exit_code=exit_code,
                stdout=stdout,
                stderr=stderr,
                duration_ms=elapsed,
                command=" ".join(command),
            )

        except APIError as exc:
            elapsed = int((time.monotonic() - start) * 1000)
            return ExecResult(
                exit_code=-1,
                stdout="",
                stderr=f"Docker API error: {exc}",
                duration_ms=elapsed,
                command=" ".join(command),
            )

    def run_tool(
        self,
        binary: str,
        args: list[str],
        timeout: int | None = None,
    ) -> ToolResult:
        """High-level: run a security tool and return a ToolResult.

        Args:
            binary: Tool binary name (e.g. "nmap")
            args: Arguments to pass to the tool
            timeout: Timeout in seconds

        Returns:
            ToolResult with parsed status
        """
        command = [binary] + args
        target = self._extract_target(args)
        result = self.exec_command(command, timeout=timeout)

        status = "success"
        error = None
        if result.exit_code != 0 and result.exit_code != -1:
            # Some tools return non-zero for findings (nuclei, nikto)
            # Only mark as error if stderr has real errors
            if result.stderr and "error" in result.stderr.lower():
                status = "error"
                error = result.stderr[:500]
        elif result.exit_code == -1:
            status = "error"
            error = result.stderr[:500]

        return ToolResult(
            tool_id=binary,
            target=target,
            command=result.command,
            raw_output=result.stdout,
            status=status,
            exit_code=result.exit_code,
            duration_ms=result.duration_ms,
            error=error,
        )

    @staticmethod
    def _extract_target(args: list[str]) -> str:
        """Try to extract the target from tool arguments."""
        # Usually the last non-flag argument
        for arg in reversed(args):
            if not arg.startswith("-"):
                return arg
        return "unknown"

    # ── Tool Availability ─────────────────────────────────────────

    def check_tool(self, binary: str) -> tuple[bool, str]:
        """Check if a tool is available in the container.

        Returns:
            (available: bool, version_info: str)
        """
        result = self.exec_command(["which", binary], timeout=10)
        if result.exit_code != 0:
            return False, f"{binary} not found"

        # Try to get version
        version_result = self.exec_command([binary, "--version"], timeout=10)
        version = version_result.stdout.strip().split("\n")[0] if version_result.exit_code == 0 else "version unknown"
        return True, version

    def list_available_tools(self, binaries: list[str]) -> dict[str, tuple[bool, str]]:
        """Check availability of multiple tools."""
        return {b: self.check_tool(b) for b in binaries}

    # ── Health Check ──────────────────────────────────────────────

    def health_check(self) -> dict[str, object]:
        """Full health check: Docker, image, container."""
        health: dict[str, object] = {
            "docker_available": False,
            "image_exists": False,
            "container_running": False,
        }

        try:
            self.client.ping()
            health["docker_available"] = True
        except Exception:
            return health

        health["image_exists"] = self.image_exists()
        health["container_running"] = self.container_running()
        return health
