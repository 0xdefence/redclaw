# RedClaw Docker Image Makefile

.PHONY: all build-minimal build-standard build-full build-all test clean

# Default target
all: build-standard

# Build minimal image (~300 MB)
build-minimal:
	@echo "Building RedClaw Minimal image (~300 MB)..."
	docker build -f Dockerfile.minimal -t redclaw/kali:minimal .
	@echo "✓ Built: redclaw/kali:minimal"
	@docker images redclaw/kali:minimal

# Build standard image (~500 MB) - DEFAULT
build-standard:
	@echo "Building RedClaw Standard image (~500 MB)..."
	docker build -f Dockerfile.standard -t redclaw/kali:standard .
	docker tag redclaw/kali:standard redclaw/kali:latest
	@echo "✓ Built: redclaw/kali:standard (also tagged as :latest)"
	@docker images redclaw/kali:standard

# Build full image (~800 MB)
build-full:
	@echo "Building RedClaw Full image (~800 MB)..."
	docker build -f Dockerfile.full -t redclaw/kali:full .
	@echo "✓ Built: redclaw/kali:full"
	@docker images redclaw/kali:full

# Build all variants
build-all: build-minimal build-standard build-full
	@echo ""
	@echo "All images built successfully!"
	@echo ""
	@docker images | grep redclaw/kali

# Test images
test:
	@echo "Testing minimal image..."
	@docker run --rm redclaw/kali:minimal nmap --version
	@echo "Testing standard image..."
	@docker run --rm redclaw/kali:standard nmap --version
	@docker run --rm redclaw/kali:standard nikto -Version
	@echo "Testing full image..."
	@docker run --rm redclaw/kali:full nuclei -version
	@echo "✓ All tests passed!"

# Clean old images
clean:
	@echo "Removing old RedClaw images..."
	docker rmi redclaw/kali:minimal redclaw/kali:standard redclaw/kali:full 2>/dev/null || true
	docker image prune -f
	@echo "✓ Cleaned"

# Rebuild all from scratch
rebuild-all: clean build-all

# Show image sizes
sizes:
	@echo "Image sizes:"
	@docker images | grep redclaw/kali | awk '{print $$1":"$$2" - "$$7" "$$8}'

# Push to registry (requires login)
push:
	docker push redclaw/kali:minimal
	docker push redclaw/kali:standard
	docker push redclaw/kali:full
	docker push redclaw/kali:latest

help:
	@echo "RedClaw Docker Image Builder"
	@echo ""
	@echo "Targets:"
	@echo "  make build-minimal   Build minimal image (~300 MB)"
	@echo "  make build-standard  Build standard image (~500 MB) [DEFAULT]"
	@echo "  make build-full      Build full image (~800 MB)"
	@echo "  make build-all       Build all variants"
	@echo "  make test            Test all images"
	@echo "  make clean           Remove old images"
	@echo "  make rebuild-all     Clean and rebuild all"
	@echo "  make sizes           Show image sizes"
	@echo "  make push            Push to registry"
