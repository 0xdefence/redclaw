"""Shared fixtures for all tests."""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def tmp_data_dir(tmp_path: Path) -> Path:
    """Use a temp directory for all data so tests don't pollute real data."""
    os.environ["REDCLAW_DATA_DIR"] = str(tmp_path)
    os.environ["REDCLAW_ALLOW_PRIVATE_NETWORKS"] = "false"
    return tmp_path


@pytest.fixture
def sample_nmap_xml() -> str:
    return '''<?xml version="1.0"?>
<nmaprun>
  <host>
    <address addr="93.184.216.34"/>
    <hostnames><hostname name="example.com"/></hostnames>
    <ports>
      <port protocol="tcp" portid="80">
        <state state="open"/>
        <service name="http" product="nginx" version="1.24.0"/>
      </port>
      <port protocol="tcp" portid="443">
        <state state="open"/>
        <service name="https" product="nginx" version="1.24.0"/>
      </port>
      <port protocol="tcp" portid="22">
        <state state="closed"/>
        <service name="ssh"/>
      </port>
    </ports>
  </host>
</nmaprun>'''


@pytest.fixture
def sample_nmap_text() -> str:
    return """Starting Nmap 7.94 ( https://nmap.org )
PORT    STATE SERVICE VERSION
22/tcp  open  ssh     OpenSSH 8.9p1
80/tcp  open  http    nginx 1.24.0
443/tcp open  https   nginx 1.24.0
Nmap done: 1 IP address (1 host up) scanned in 3.45 seconds"""


@pytest.fixture
def sample_nikto_output() -> str:
    return """- Nikto v2.5.0
---------------------------------------------------------------------------
+ Target IP:          93.184.216.34
+ Target Hostname:    example.com
+ Target Port:        80
+ Start Time:         2025-01-01 00:00:00
---------------------------------------------------------------------------
+ Server: nginx/1.24.0
+ /: The anti-clickjacking X-Frame-Options header is not present. See: OSVDB-12345
+ /: Server leaks version info via "Server" HTTP response header. See: OSVDB-0
+ /admin/: This might be interesting.
+ /backup.sql: Backup file found. OSVDB-67890
+ 1234 requests: 0 error(s) and 4 item(s) reported"""


@pytest.fixture
def sample_dig_output() -> str:
    return """example.com.\t\t300\tIN\tA\t93.184.216.34
example.com.\t\t300\tIN\tAAAA\t2606:2800:220:1:248:1893:25c8:1946
example.com.\t\t86400\tIN\tMX\t10 mail.example.com.
example.com.\t\t86400\tIN\tNS\ta.iana-servers.net.
example.com.\t\t86400\tIN\tNS\tb.iana-servers.net."""


@pytest.fixture
def sample_whois_output() -> str:
    return """Domain Name: EXAMPLE.COM
Registry Domain ID: 2336799_DOMAIN_COM-VRSN
Registrar: RESERVED-Internet Assigned Numbers Authority
Creation Date: 1995-08-14T04:00:00Z
Registry Expiry Date: 2025-08-13T04:00:00Z
Name Server: A.IANA-SERVERS.NET
Name Server: B.IANA-SERVERS.NET
Domain Status: clientDeleteProhibited
Domain Status: clientTransferProhibited
Registrant Name: REDACTED"""
