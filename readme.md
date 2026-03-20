# RedClaw

CLI security scanner that orchestrates Kali Linux tools via Docker.

## Features

- **Docker-based execution** — Security tools run in an isolated Kali Linux container
- **Multiple image variants** — Choose between minimal (~300 MB), standard (~400 MB), or full (~800 MB)
- **Target validation** — Blocks localhost, private networks, and injection attempts
- **Multiple scan profiles** — Quick, full, recon, web, stealth
- **SQLite storage** — Scan results and audit logs persisted locally
- **Rich CLI output** — Tables, progress bars, and colored output

## Docker Image Variants

RedClaw provides **3 optimized Docker images** for different use cases:

| Variant | Size | Tools | Use Case |
|---------|------|-------|----------|
| **Minimal** | ~300 MB | nmap, dig, whois | Quick scans, CI/CD |
| **Standard** | ~400 MB | + nikto, gobuster | Most users (default) ⭐ |
| **Full** | ~800 MB | + nuclei | Advanced pentesting |

```bash
# Use specific variant
claw scan example.com --docker-image minimal
claw scan example.com --docker-image standard  # default
claw scan example.com --docker-image full
```

## Supported Tools

| Tool | Category | Minimal | Standard | Full |
|------|----------|---------|----------|------|
| nmap | scanning | ✅ | ✅ | ✅ |
| dig | recon | ✅ | ✅ | ✅ |
| whois | recon | ✅ | ✅ | ✅ |
| nikto | scanning | ❌ | ✅ | ✅ |
| gobuster | enumeration | ❌ | ✅ | ✅ |
| nuclei | scanning | ❌ | ❌ | ✅ |

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
| `REDCLAW_DOCKER_IMAGE` | `standard` | Docker image variant: minimal, standard, full |
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

# Build Docker images
cd docker && make build-all        # Build all variants
cd docker && make build-standard   # Build standard only (recommended)
cd docker && make build-minimal    # Build minimal only
cd docker && make build-full       # Build full only

# Test images
cd docker && make test
```

### Docker Image Sizes

⚠️ **Important:** The old `Dockerfile.kali` created a **3.3 GB** image (deprecated).

New optimized images:
- `Dockerfile.minimal` → ~300 MB (8.3x smaller!)
- `Dockerfile.standard` → ~400 MB (8.3x smaller!)
- `Dockerfile.full` → ~800 MB (4x smaller!)

See `docker/README.md` for details.

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
