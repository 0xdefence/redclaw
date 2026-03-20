"""Tests for tool output parsers."""
from redclaw.tools import NmapTool, NiktoTool, DigTool, WhoisTool, create_default_registry
from redclaw.models import Severity


class TestNmapParser:
    def setup_method(self) -> None:
        self.tool = NmapTool()

    def test_parse_xml(self, sample_nmap_xml: str) -> None:
        parsed = self.tool.parse_output(sample_nmap_xml)
        assert "hosts" in parsed
        assert len(parsed["hosts"]) == 1
        host = parsed["hosts"][0]
        assert host["address"] == "93.184.216.34"
        assert host["hostname"] == "example.com"
        # XML includes all ports regardless of state
        ports = host["ports"]
        assert len(ports) == 3

    def test_parse_text_fallback(self, sample_nmap_text: str) -> None:
        parsed = self.tool.parse_output(sample_nmap_text)
        assert "hosts" in parsed
        ports = parsed["hosts"][0]["ports"]
        assert len(ports) == 3
        assert ports[0]["port"] == 22
        assert ports[0]["service"] == "ssh"

    def test_extract_findings(self, sample_nmap_xml: str) -> None:
        parsed = self.tool.parse_output(sample_nmap_xml)
        findings = self.tool.extract_findings(parsed, "example.com")
        # Only open ports become findings
        open_findings = [f for f in findings if "open" in f.evidence.lower() or f.severity == Severity.INFO]
        assert len(open_findings) >= 2  # port 80 and 443

    def test_build_args_quick(self) -> None:
        args = self.tool.build_args("example.com", profile="quick")
        assert "example.com" in args
        assert "-F" in args

    def test_build_args_full(self) -> None:
        args = self.tool.build_args("example.com", profile="full")
        assert "-p-" in args


class TestNiktoParser:
    def setup_method(self) -> None:
        self.tool = NiktoTool()

    def test_parse_output(self, sample_nikto_output: str) -> None:
        parsed = self.tool.parse_output(sample_nikto_output)
        assert parsed["server"] == "nginx/1.24.0"
        assert parsed["port"] == 80
        assert len(parsed["items"]) >= 3

    def test_extract_findings(self, sample_nikto_output: str) -> None:
        parsed = self.tool.parse_output(sample_nikto_output)
        findings = self.tool.extract_findings(parsed, "example.com")
        assert len(findings) >= 3
        # Check OSVDB references are captured
        has_osvdb = any(f.references for f in findings)
        assert has_osvdb

    def test_build_args(self) -> None:
        args = self.tool.build_args("example.com")
        assert "-h" in args
        assert "example.com" in args


class TestDigParser:
    def setup_method(self) -> None:
        self.tool = DigTool()

    def test_parse_output(self, sample_dig_output: str) -> None:
        parsed = self.tool.parse_output(sample_dig_output)
        assert len(parsed["records"]) == 5
        types = {r["type"] for r in parsed["records"]}
        assert "A" in types
        assert "MX" in types
        assert "NS" in types

    def test_extract_findings(self, sample_dig_output: str) -> None:
        parsed = self.tool.parse_output(sample_dig_output)
        findings = self.tool.extract_findings(parsed, "example.com")
        assert len(findings) == 5


class TestWhoisParser:
    def setup_method(self) -> None:
        self.tool = WhoisTool()

    def test_parse_output(self, sample_whois_output: str) -> None:
        parsed = self.tool.parse_output(sample_whois_output)
        assert "RESERVED" in parsed["registrar"]
        assert "1995" in parsed["creation_date"]
        assert len(parsed["name_servers"]) == 2

    def test_extract_findings(self, sample_whois_output: str) -> None:
        parsed = self.tool.parse_output(sample_whois_output)
        findings = self.tool.extract_findings(parsed, "example.com")
        assert len(findings) >= 1
        assert findings[0].severity == Severity.INFO


class TestRegistry:
    def test_default_registry(self) -> None:
        reg = create_default_registry()
        assert reg.count == 4
        assert "nmap" in reg.list_ids()
        assert "nikto" in reg.list_ids()
        assert "dig" in reg.list_ids()
        assert "whois" in reg.list_ids()

    def test_get_tool(self) -> None:
        reg = create_default_registry()
        nmap = reg.get("nmap")
        assert nmap is not None
        assert nmap.meta.id == "nmap"

    def test_get_nonexistent(self) -> None:
        reg = create_default_registry()
        assert reg.get("doesntexist") is None

    def test_filter_by_category(self) -> None:
        reg = create_default_registry()
        recon_tools = reg.filter_by_category("recon")
        assert len(recon_tools) == 2  # dig + whois
