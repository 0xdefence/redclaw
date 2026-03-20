"""Tests for SecurityPolicy."""
from redclaw.core.policy import SecurityPolicy


class TestTargetValidation:
    def setup_method(self) -> None:
        self.policy = SecurityPolicy()

    def test_valid_domain(self) -> None:
        r = self.policy.validate_target("scanme.nmap.org")
        assert r.allowed

    def test_valid_ip(self) -> None:
        r = self.policy.validate_target("93.184.216.34")
        assert r.allowed

    def test_valid_url(self) -> None:
        r = self.policy.validate_target("https://example.com/path")
        assert r.allowed

    def test_empty_target(self) -> None:
        r = self.policy.validate_target("")
        assert not r.allowed

    def test_whitespace_target(self) -> None:
        r = self.policy.validate_target("   ")
        assert not r.allowed

    def test_block_localhost_ip(self) -> None:
        r = self.policy.validate_target("127.0.0.1")
        assert not r.allowed
        assert "private" in r.reason.lower() or "reserved" in r.reason.lower()

    def test_block_localhost_name(self) -> None:
        r = self.policy.validate_target("localhost")
        assert not r.allowed

    def test_block_private_10(self) -> None:
        r = self.policy.validate_target("10.0.0.1")
        assert not r.allowed

    def test_block_private_172(self) -> None:
        r = self.policy.validate_target("172.16.0.1")
        assert not r.allowed

    def test_block_private_192(self) -> None:
        r = self.policy.validate_target("192.168.1.1")
        assert not r.allowed

    def test_block_ipv6_localhost(self) -> None:
        r = self.policy.validate_target("::1")
        assert not r.allowed

    def test_block_ftp_scheme(self) -> None:
        r = self.policy.validate_target("ftp://evil.com")
        assert not r.allowed

    def test_injection_semicolon(self) -> None:
        r = self.policy.validate_target("example.com; rm -rf /")
        assert not r.allowed

    def test_injection_pipe(self) -> None:
        r = self.policy.validate_target("target | whoami")
        assert not r.allowed

    def test_injection_backtick(self) -> None:
        r = self.policy.validate_target("target`id`")
        assert not r.allowed

    def test_injection_newline(self) -> None:
        r = self.policy.validate_target("target\nwhoami")
        assert not r.allowed


class TestArgValidation:
    def setup_method(self) -> None:
        self.policy = SecurityPolicy()

    def test_clean_args(self) -> None:
        r = self.policy.validate_args("nmap", ["-sV", "-F", "example.com"])
        assert r.allowed

    def test_injection_in_args(self) -> None:
        r = self.policy.validate_args("nmap", ["-sV", "target; whoami"])
        assert not r.allowed

    def test_arg_length_limit(self) -> None:
        r = self.policy.validate_args("nmap", ["a" * 3000])
        assert not r.allowed

    def test_empty_args(self) -> None:
        r = self.policy.validate_args("nmap", [])
        assert r.allowed
