# RedClaw Docker Images

## Image Variants

RedClaw provides three Docker image variants optimized for different use cases:

### 🟢 Minimal (~300 MB) - Quick Scans
```bash
docker build -f Dockerfile.minimal -t redclaw/kali:minimal .
```
**Tools:** nmap, dig, whois
**Use case:** Basic reconnaissance, CI/CD, quick scans
**Pull time:** ~30 seconds

### 🟡 Standard (~500 MB) - **DEFAULT**
```bash
docker build -f Dockerfile.standard -t redclaw/kali:standard .
```
**Tools:** nmap, nikto, gobuster, dig, whois
**Use case:** Most pentesting scenarios, web app security
**Pull time:** ~45 seconds

### 🔴 Full (~800 MB) - Advanced Scanning
```bash
docker build -f Dockerfile.full -t redclaw/kali:full .
```
**Tools:** nmap, nikto, nuclei, gobuster, dig, whois
**Use case:** Advanced vulnerability scanning
**Pull time:** ~1 minute

---

## ⚠️ Old Image Warning

The previous `Dockerfile.kali` created a **3.3 GB** image due to bundled wordlists.

**DO NOT USE** `Dockerfile.kali` for production!

---

## Quick Start

### Build All Images
```bash
make build-images
```

### Build Specific Image
```bash
# Minimal
docker build -f Dockerfile.minimal -t redclaw/kali:minimal .

# Standard (recommended)
docker build -f Dockerfile.standard -t redclaw/kali:standard .

# Full
docker build -f Dockerfile.full -t redclaw/kali:full .
```

### Use with RedClaw CLI
```bash
# Use minimal image
claw scan example.com --docker-image=minimal

# Use standard image (default)
claw scan example.com

# Use full image
claw scan example.com --docker-image=full
```

---

## Wordlists

**Wordlists are NOT included** in Docker images to keep them small.

### Option 1: Mount Wordlists as Volume
```bash
# Download seclists once
wget https://github.com/danielmiessler/SecLists/archive/master.zip
unzip master.zip -d /opt/seclists

# Use with RedClaw
claw scan example.com -v /opt/seclists:/wordlists
```

### Option 2: Use Wordlist Container
```bash
# Pull wordlist container (1.5 GB, one-time)
docker pull danielmiessler/seclists

# Use with RedClaw (shares wordlists)
claw scan example.com --wordlist-container=danielmiessler/seclists
```

---

## Image Comparison

| Variant | Size | Tools | Pull Time | Best For |
|---------|------|-------|-----------|----------|
| Minimal | 300 MB | Basic | ~30s | CI/CD, quick scans |
| Standard | 500 MB | Web + Basic | ~45s | Most users ⭐ |
| Full | 800 MB | All tools | ~1m | Advanced pentesting |
| ~~Old~~ | ~~3.3 GB~~ | ~~+ wordlists~~ | ~~4-6m~~ | ❌ Deprecated |

---

## Build Options

### Multi-Architecture Build
```bash
docker buildx build --platform linux/amd64,linux/arm64 \
  -f Dockerfile.standard \
  -t redclaw/kali:standard .
```

### With Build Cache
```bash
DOCKER_BUILDKIT=1 docker build \
  --cache-from redclaw/kali:standard \
  -f Dockerfile.standard \
  -t redclaw/kali:standard .
```

---

## Maintenance

### Update Base Image
```bash
docker pull kalilinux/kali-rolling:latest
make rebuild-all
```

### Clean Old Images
```bash
docker image prune -a
```

### Check Image Sizes
```bash
docker images | grep redclaw
```

---

## Security

All images:
- ✅ Run as non-root user (`scanner`)
- ✅ Minimal attack surface
- ✅ No unnecessary packages
- ✅ Regular base image updates
- ✅ Health checks included

---

## Troubleshooting

### Image Too Large
Use minimal or standard variant instead of full.

### Missing Tool
Check which variant you're using. Some tools are only in full variant.

### Wordlist Not Found
Mount wordlists as volume or use wordlist container.

---

## Contributing

When adding new tools:
1. Add to appropriate Dockerfile variant
2. Update this README
3. Rebuild and test
4. Update size estimates
