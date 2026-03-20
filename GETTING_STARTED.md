# Getting Started with RedClaw

Complete guide to installing, configuring, and running your first security scans with RedClaw.

---

## 📋 Prerequisites

Before you begin, ensure you have:

- **Python 3.10+** installed
- **Docker Desktop** installed and running
- **Terminal/Command Line** access

Check your setup:
```bash
python --version  # Should show 3.10 or higher
docker --version  # Should show Docker is installed
docker ps         # Should connect (proves Docker is running)
```

---

## 🚀 Installation

### Step 1: Clone or Navigate to RedClaw

```bash
cd /Users/elibelilty/Documents/GitHub/RedClaw
```

### Step 2: Install RedClaw

```bash
# Install with development dependencies
pip install -e ".[dev]"
```

This installs:
- RedClaw CLI (`claw` command)
- All dependencies (Click, Rich, Docker, SQLite)
- Development tools (pytest, ruff, mypy)

### Step 3: Verify Installation

```bash
claw --help
```

You should see the RedClaw CLI help menu with all available commands.

---

## ⚙️ Initial Setup

### Step 1: Initialize RedClaw

```bash
claw init
```

This command:
- ✅ Builds the Docker image (default: **standard** variant, ~400 MB)
- ✅ Creates the SQLite database at `~/.redclaw/redclaw.db`
- ✅ Sets up the data directory structure
- ⏱️ **First time**: Takes 2-3 minutes to download Kali base and build
- ⏱️ **Subsequent runs**: Instant (image is cached)

### Step 2: Check System Health

```bash
claw status
```

Expected output:
```
✓ Docker: Connected
✓ Image: redclaw/kali:standard (397 MB)
✓ Container: Not running (will auto-start on first scan)
✓ Database: Initialized
```

---

## 🔍 Your First Scan

### Quick Scan (Recommended for First Try)

Scan a safe test target:

```bash
claw scan scanme.nmap.org --profile quick
```

**What happens:**
1. 🎨 RedClaw banner displays
2. 📦 Docker container starts automatically
3. ⚡ Nmap runs a quick port scan
4. 📊 Results display in a formatted table
5. 💾 Scan saved to database

**Output example:**
```
     ╱╲    ╱╲    ╱╲
    ╱  ╲  ╱  ╲  ╱  ╲
   ╱    ╲╱    ╲╱    ╲
  ╱                   ╲
 ╱  ╲  ╱  ╲  ╱  ╲  ╱  ╲
  ██████╗ ███████╗██████╗  ██████╗██╗      █████╗ ██╗    ██╗
  ██╔══██╗██╔════╝██╔══██╗██╔════╝██║     ██╔══██╗██║    ██║
  ██████╔╝█████╗  ██║  ██║██║     ██║     ███████║██║ █╗ ██║
  ██╔══██╗██╔══╝  ██║  ██║██║     ██║     ██╔══██║██║███╗██║
  ██║  ██║███████╗██████╔╝╚██████╗███████╗██╔══██║╚███╔███╔╝
  ╚═╝  ╚═╝╚══════╝╚═════╝  ╚═════╝╚══════╝╚═╝  ╚═╝ ╚══╝╚══╝

  Security Scanner • v0.1.0

╭──────────────────────────────────────────────────────╮
│ Scan ID:     scan_20260320_143052                   │
│ Target:      scanme.nmap.org                         │
│ Profile:     quick                                   │
│ Tools:       nmap                                    │
╰──────────────────────────────────────────────────────╯

⚡ nmap  Quick port scan with service detection
✓ nmap  12 results — 2.3s

╭──────────────────────────────────────────────────────╮
│ Scan Complete                                        │
│ Duration: 2.3s • Findings: 12                        │
│ Severity: HIGH: 0  MEDIUM: 0  LOW: 5  INFO: 7       │
╰──────────────────────────────────────────────────────╯
```

---

## 📖 Common Commands

### View Available Tools

```bash
claw tools
```

Shows all security tools available in the Docker image:
- nmap (port scanning)
- dig (DNS lookup)
- whois (domain registration)
- nikto (web vulnerability scanning)
- gobuster (directory enumeration)
- nuclei (template-based vulnerability scanning - **full image only**)

### Search for Specific Tools

```bash
claw tools search web
claw tools search enumeration
```

### View Recent Scans

```bash
claw results
```

Shows last 10 scans with:
- Scan ID
- Target
- Timestamp
- Finding counts

### View Specific Scan Details

```bash
claw results <scan-id>
```

Example:
```bash
claw results scan_20260320_143052
```

### Generate a Report

```bash
# Human-readable report
claw report <scan-id>

# JSON format (for automation)
claw report <scan-id> --format json
```

---

## 🎯 Scan Profiles

RedClaw includes pre-configured profiles for common scenarios:

### Quick Profile (Default)
```bash
claw scan example.com --profile quick
```
- **Tools**: nmap (fast scan)
- **Use case**: Quick reconnaissance
- **Duration**: ~30 seconds

### Recon Profile
```bash
claw scan example.com --profile recon
```
- **Tools**: dig, whois
- **Use case**: Passive information gathering
- **Duration**: ~5 seconds

### Full Profile
```bash
claw scan example.com --profile full
```
- **Tools**: nmap (comprehensive), nikto
- **Use case**: Thorough security assessment
- **Duration**: 2-5 minutes

### Web Profile
```bash
claw scan example.com --profile web
```
- **Tools**: nmap, nikto
- **Use case**: Web application testing
- **Duration**: 1-3 minutes

### Stealth Profile
```bash
claw scan example.com --profile stealth
```
- **Tools**: nmap (slow, evasive)
- **Use case**: Avoiding detection
- **Duration**: 5-10 minutes

---

## 🔧 Docker Image Variants

RedClaw offers 3 Docker image sizes. Choose based on your needs:

### Minimal (~300 MB) — Fast & Lightweight

```bash
claw scan example.com --docker-image minimal
```

**Includes:**
- nmap
- dig
- whois

**Best for:**
- CI/CD pipelines
- Quick reconnaissance
- Resource-constrained environments

### Standard (~400 MB) — Recommended Default ⭐

```bash
claw scan example.com --docker-image standard
```

**Includes:**
- nmap
- dig
- whois
- nikto
- gobuster

**Best for:**
- Most users
- General pentesting
- Web application testing

### Full (~800 MB) — Advanced Features

```bash
claw scan example.com --docker-image full
```

**Includes:**
- nmap
- dig
- whois
- nikto
- gobuster
- nuclei (vulnerability templates)

**Best for:**
- Professional pentesting
- Template-based vulnerability detection
- Comprehensive assessments

---

## 🛠️ Advanced Usage

### Run Specific Tools

Override the profile and run custom tools:

```bash
claw scan example.com --tools nmap,nikto
claw scan example.com --tools dig,whois
```

### Multiple Targets

Scan multiple targets sequentially:

```bash
claw scan example.com
claw scan test.com
claw scan demo.org
```

### AI-Powered Scans (Experimental)

Use AI to select tools autonomously:

```bash
# Set API key first
export OPENROUTER_API_KEY="your-key-here"

# Run AI scan
claw aiscan example.com
claw aiscan example.com "find all web vulnerabilities"
```

### Specialized Scan Commands

**Reconnaissance only:**
```bash
claw recon example.com
```

**Port scan only:**
```bash
claw portscan example.com
claw portscan example.com --profile full  # All ports
```

**Web scan only:**
```bash
claw webscan example.com
```

---

## ⚙️ Configuration

### Environment Variables

Configure RedClaw using environment variables:

```bash
# Set default Docker image variant
export REDCLAW_DOCKER_IMAGE=minimal

# Set custom data directory
export REDCLAW_DATA_DIR=/custom/path

# Increase timeout for slow scans
export REDCLAW_CONTAINER_TIMEOUT=600

# Enable verbose output
export REDCLAW_VERBOSE=true

# Allow scanning private networks (use with caution!)
export REDCLAW_ALLOW_PRIVATE_NETWORKS=true
```

### Using .env File

Create a `.env` file in the project root:

```bash
# .env
REDCLAW_DOCKER_IMAGE=standard
REDCLAW_CONTAINER_TIMEOUT=300
REDCLAW_VERBOSE=false
```

### View Current Configuration

```bash
claw config
```

Shows all active settings and their values.

---

## 🔒 Security Policy

RedClaw enforces security policies to prevent misuse:

### Blocked Targets

The following are **automatically blocked**:
- `localhost`, `127.0.0.1`
- Private networks: `10.x.x.x`, `172.16-31.x.x`, `192.168.x.x`
- Link-local: `169.254.x.x`

To override (for authorized testing only):
```bash
export REDCLAW_ALLOW_PRIVATE_NETWORKS=true
```

### Injection Prevention

RedClaw validates all commands for shell metacharacters:
- `;`, `|`, `&`, `$`, `` ` ``
- `>`, `<`, `&&`, `||`

Injection attempts are **blocked** and logged.

### Rate Limiting

Default: Max **100 scans per day** per target.

Prevents accidental DoS and excessive resource usage.

---

## 📊 Output Modes

### Normal Mode (Default)

Rich formatted output with colors, tables, and progress indicators:

```bash
claw scan example.com
```

### Stealth Mode

Minimal parseable output for logging/piping:

```bash
claw scan example.com --stealth
```

Output:
```
[RECON] dig: 4
[SCAN]  nmap: 12 (3 medium, 9 info)
[DONE]  16 findings total (3 medium, 13 info)
```

### JSON Mode

Structured JSON output for automation:

```bash
claw scan example.com --output json
```

Perfect for:
- CI/CD integration
- Parsing with `jq`
- Automated reporting

---

## 🐳 Docker Management

### Build Custom Image

```bash
cd docker

# Build specific variant
make build-minimal
make build-standard
make build-full

# Build all variants
make build-all
```

### Test Images

```bash
cd docker
make test
```

Runs automated tests on all Docker images to verify tools work.

### Clean Up Old Images

```bash
# Remove old 3.3 GB image (if you have it)
docker rmi redclaw/kali:latest

# Remove all RedClaw images
docker images | grep redclaw | awk '{print $3}' | xargs docker rmi -f
```

### Stop Running Container

```bash
claw stop  # (if command exists)

# Or manually:
docker stop redclaw-kali
docker rm redclaw-kali
```

---

## 🧪 Testing

### Run Unit Tests

```bash
pytest -v
```

**Expected:** 184/184 tests passing

### Run Specific Test Suite

```bash
pytest tests/test_output.py -v
pytest tests/test_integration_output.py -v
pytest tests/test_stress.py -v
```

### Run Benchmarks

```bash
pytest tests/test_benchmark.py -v --benchmark-only
```

### Visual Output Test

```bash
python scripts/test_output.py
```

Shows all output modes and components visually.

---

## 📁 Directory Structure

After initialization, your RedClaw setup looks like this:

```
~/.redclaw/                    # Data directory
├── redclaw.db                 # SQLite database (scans, findings, audit)
└── logs/                      # Log files

/path/to/RedClaw/              # Project directory
├── src/redclaw/               # Source code
│   ├── cli/                   # CLI commands
│   ├── core/                  # Core logic (executor, planner, policy)
│   ├── models/                # Data models (config, scan, finding)
│   ├── output/                # Output system (banner, display, stealth, JSON)
│   └── storage/               # Database layer
├── docker/                    # Docker images
│   ├── Dockerfile.minimal
│   ├── Dockerfile.standard
│   ├── Dockerfile.full
│   └── Makefile
├── tests/                     # Test suite (184 tests)
└── README.md                  # Documentation
```

---

## 🔥 Quick Start Cheat Sheet

```bash
# 1. Install
pip install -e ".[dev]"

# 2. Initialize
claw init

# 3. Check status
claw status

# 4. Run first scan
claw scan scanme.nmap.org

# 5. View results
claw results

# 6. Generate report
claw report <scan-id>

# 7. Try different profiles
claw scan example.com --profile recon
claw scan example.com --profile full

# 8. Use minimal image (faster)
claw scan example.com --docker-image minimal

# 9. Run specific tools
claw scan example.com --tools nmap,nikto

# 10. View all commands
claw --help
```

---

## 🆘 Troubleshooting

### "Cannot connect to Docker"

**Problem:** Docker Desktop is not running.

**Solution:**
1. Start Docker Desktop
2. Wait for it to fully start (~30 seconds)
3. Verify: `docker ps`
4. Try again: `claw status`

### "Image not found"

**Problem:** Docker image not built yet.

**Solution:**
```bash
claw init
```

### "Target blocked by security policy"

**Problem:** Trying to scan localhost or private network.

**Solution:**
- For authorized testing only:
```bash
export REDCLAW_ALLOW_PRIVATE_NETWORKS=true
claw scan 192.168.1.1
```

### "Tool not found in container"

**Problem:** Using a tool not available in current variant.

**Example:** `nuclei` only in **full** image.

**Solution:**
```bash
claw scan example.com --docker-image full --tools nuclei
```

### Slow Scans

**Problem:** Full scans taking too long.

**Solutions:**
- Use `--profile quick` instead of `--profile full`
- Use `--docker-image minimal` for faster startup
- Increase timeout: `export REDCLAW_CONTAINER_TIMEOUT=600`

### Database Issues

**Problem:** Corrupted database or permission errors.

**Solution:**
```bash
# Backup old database
mv ~/.redclaw/redclaw.db ~/.redclaw/redclaw.db.backup

# Reinitialize
claw init
```

---

## 📚 Next Steps

Now that you're up and running:

1. **Read the full documentation**: `README.md`
2. **Check out Docker optimization**: `DOCKER_OPTIMIZATION_COMPLETE.md`
3. **Review output system**: `OUTPUT_IMPLEMENTATION.md`
4. **Explore scan profiles**: Try all profiles to see differences
5. **Integrate with CI/CD**: Use JSON output mode for automation
6. **Contribute**: Report issues, suggest features

---

## 🎓 Example Workflows

### Workflow 1: Quick Recon

```bash
# Get basic info about target
claw recon example.com

# Review findings
claw results
```

### Workflow 2: Comprehensive Web Assessment

```bash
# Full web scan with standard image
claw scan example.com --profile web

# Generate report
claw report <scan-id>

# Export to JSON for parsing
claw report <scan-id> --format json > report.json
```

### Workflow 3: CI/CD Integration

```bash
# Use minimal image, stealth output, exit code on findings
claw scan example.com \
  --docker-image minimal \
  --profile quick \
  --output stealth
```

### Workflow 4: Progressive Scanning

```bash
# Start with recon
claw recon example.com

# If interesting, run port scan
claw portscan example.com --profile quick

# If services found, run web scan
claw webscan example.com

# Generate comprehensive report
claw report <scan-id>
```

---

## 🚀 You're Ready!

You now have everything you need to use RedClaw effectively:

✅ Installed and initialized
✅ Understand scan profiles
✅ Know how to choose Docker variants
✅ Can run scans and view results
✅ Configured for your needs
✅ Ready to troubleshoot issues

**Happy scanning! 🎉**

---

**Questions or Issues?**
Check the documentation or run `claw --help` for inline help.
