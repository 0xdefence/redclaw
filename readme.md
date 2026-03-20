# RedClaw

CLI security scanner that orchestrates Kali Linux tools via Docker.

## Features

- **Docker-based execution** — Security tools run in an isolated Kali Linux container
- **Target validation** — Blocks localhost, private networks, and injection attempts
- **Multiple scan profiles** — Quick, full, recon, web, stealth
- **SQLite storage** — Scan results and audit logs persisted locally
- **Rich CLI output** — Tables, progress bars, and colored output

## Supported Tools

| Tool | Category | Description |
|------|----------|-------------|
| nmap | scanning | Port scanning and service detection |
| nikto | scanning | Web server vulnerability scanner |
| dig | recon | DNS record lookup |
| whois | recon | Domain registration lookup |

## Install

```bash
pip install -e ".[dev]"
```

## Quick Start

```bash
# Initialize (builds Docker image, creates database)
claw init

# Check system health
claw status

# Run a scan
claw scan example.com

# Run specific tools
claw scan example.com --tools nmap,nikto

# Run with a profile
claw scan example.com --profile full

# View results
claw results
claw results <scan-id>

# Generate report
claw report <scan-id>
claw report <scan-id> --format json
```

## Scan Profiles

| Profile | Tools | Description |
|---------|-------|-------------|
| quick | nmap (fast) | Quick port scan with service detection |
| recon | dig, whois | Passive reconnaissance |
| full | nmap (full), nikto | Comprehensive scan |
| web | nmap, nikto | Web server focused |
| stealth | nmap (stealth) | Low-profile scanning |

## Commands

```
claw init          # Initialize Docker image and database
claw status        # Show system health
claw scan TARGET   # Run a security scan
claw recon TARGET  # Passive reconnaissance (DNS + WHOIS)
claw portscan TARGET  # Port scan with Nmap
claw webscan TARGET   # Web vulnerability scan
claw tools         # List available tools
claw tools search QUERY  # Search tools by description
claw results       # List recent scans
claw results ID    # Show specific scan details
claw report ID     # Generate scan report
claw config        # Show configuration
```

## Configuration

Environment variables (prefix: `REDCLAW_`):

| Variable | Default | Description |
|----------|---------|-------------|
| `REDCLAW_DATA_DIR` | `~/.redclaw` | Data directory |
| `REDCLAW_DOCKER_IMAGE` | `redclaw/kali:latest` | Docker image name |
| `REDCLAW_CONTAINER_TIMEOUT` | `300` | Max seconds per tool |
| `REDCLAW_ALLOW_PRIVATE_NETWORKS` | `false` | Allow scanning private IPs |
| `REDCLAW_VERBOSE` | `false` | Enable verbose output |

## Security Policy

RedClaw enforces security policies:

- **Blocked targets**: localhost, 127.0.0.1, 10.x.x.x, 172.16-31.x.x, 192.168.x.x
- **Injection prevention**: Commands validated for shell metacharacters
- **Rate limiting**: Max 100 scans/day per target (configurable)

## Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest -v

# Build Docker image manually
cd docker && docker build -f Dockerfile.kali -t redclaw/kali:latest .
```

## Architecture

```
┌─────────────────────────────────────┐
│  CLI Layer (click)                  │
│  Commands → Validation → Dispatch   │
├─────────────────────────────────────┤
│  Core Layer                         │
│  ScanPlanner → DockerExecutor       │
│  SecurityPolicy, ToolRegistry       │
├─────────────────────────────────────┤
│  Storage Layer                      │
│  SQLite (scans, findings, audit)    │
├─────────────────────────────────────┤
│  Docker Layer                       │
│  Kali Linux container               │
│  nmap, nikto, dig, whois            │
└─────────────────────────────────────┘
```

## License

MIT
