"""ZAPRICA Tool Execution — MCP-compatible tool registry.

Implements tools/list and tools/call following JSON-RPC 2.0 conventions.
For MVP, tools return mock data. Real implementations will be added per slice.
"""

import json
import re
import logging
from typing import Any

logger = logging.getLogger("zaprica.tools")

# ── Tool Registry ──────────────────────────────────────────────────────

TOOL_REGISTRY = {
    "whois_lookup": {
        "name": "whois_lookup",
        "description": "Perform a WHOIS lookup for a domain or IP address",
        "inputSchema": {
            "type": "object",
            "properties": {
                "domain": {"type": "string", "description": "Domain or IP to look up"},
            },
            "required": ["domain"],
        },
    },
    "dns_lookup": {
        "name": "dns_lookup",
        "description": "Perform DNS record lookup",
        "inputSchema": {
            "type": "object",
            "properties": {
                "domain": {"type": "string", "description": "Domain to look up"},
                "record_type": {
                    "type": "string",
                    "enum": ["A", "AAAA", "MX", "NS", "TXT", "CNAME", "SOA"],
                    "description": "DNS record type",
                },
            },
            "required": ["domain", "record_type"],
        },
    },
    "reverse_dns": {
        "name": "reverse_dns",
        "description": "Perform reverse DNS lookup for an IP address",
        "inputSchema": {
            "type": "object",
            "properties": {
                "ip": {"type": "string", "description": "IP address"},
            },
            "required": ["ip"],
        },
    },
    "web_search": {
        "name": "web_search",
        "description": "Search the web for OSINT information",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
            },
            "required": ["query"],
        },
    },
    "email_domain_check": {
        "name": "email_domain_check",
        "description": "Check domain information for an email address",
        "inputSchema": {
            "type": "object",
            "properties": {
                "email": {"type": "string", "description": "Email address"},
            },
            "required": ["email"],
        },
    },
    "hash_lookup": {
        "name": "hash_lookup",
        "description": "Look up a file hash in threat databases",
        "inputSchema": {
            "type": "object",
            "properties": {
                "hash": {"type": "string", "description": "File hash (MD5, SHA1, SHA256)"},
            },
            "required": ["hash"],
        },
    },
}


# ── Input Validation (OWASP LLM06 — Excessive Agency) ─────────────────

# Allowlisted patterns for each input parameter
INPUT_VALIDATORS = {
    "domain": re.compile(r"^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z]{2,})+$"),
    "ip": re.compile(r"^(\d{1,3}\.){3}\d{1,3}$"),
    "email": re.compile(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$"),
    "hash": re.compile(r"^[a-fA-F0-9]{32,64}$"),
    "record_type": re.compile(r"^(A|AAAA|MX|NS|TXT|CNAME|SOA)$"),
    "query": re.compile(r"^[a-zA-Z0-9\s\.\-_@:\/\(\)]{1,500}$"),
}


def validate_tool_input(tool_name: str, tool_input: dict) -> dict:
    """Validate tool input against regex allowlists.

    Prevents command injection and excessive agency (OWASP LLM06).
    """
    schema = TOOL_REGISTRY.get(tool_name)
    if not schema:
        raise ValueError(f"Unknown tool: {tool_name}")

    properties = schema["inputSchema"].get("properties", {})
    required = schema["inputSchema"].get("required", [])

    # Check required fields
    for field in required:
        if field not in tool_input:
            raise ValueError(f"Missing required field: {field}")

    # Validate each field
    validated = {}
    for field, value in tool_input.items():
        if field not in properties:
            raise ValueError(f"Unknown field: {field}")

        value_str = str(value).strip()

        # Check against allowlist
        validator = INPUT_VALIDATORS.get(field)
        if validator and not validator.match(value_str):
            raise ValueError(
                f"Invalid value for {field}: '{value_str}' — "
                f"does not match allowed pattern"
            )

        validated[field] = value_str

    return validated


# ── Tool Execution ─────────────────────────────────────────────────────

def list_tools() -> list[dict]:
    """MCP tools/list — return available tools."""
    return list(TOOL_REGISTRY.values())


def execute_tool(tool_name: str, tool_input: dict) -> str:
    """MCP tools/call — validate and execute a tool.

    All external tool execution is validated against regex allowlists
    before being routed to the appropriate worker.
    """
    logger.info(f"Executing tool: {tool_name}")

    # Validate input (security boundary)
    validated_input = validate_tool_input(tool_name, tool_input)

    # Route to tool implementation
    handler = TOOL_HANDLERS.get(tool_name)
    if not handler:
        raise ValueError(f"No handler for tool: {tool_name}")

    return handler(validated_input)


# ── Mock Tool Implementations (MVP) ───────────────────────────────────

def _mock_whois(input_data: dict) -> str:
    """Mock WHOIS lookup returning realistic data."""
    domain = input_data.get("domain", "unknown.com")
    return json.dumps({
        "domain": domain,
        "registrar": "GoDaddy.com, LLC",
        "creation_date": "2020-03-15T00:00:00Z",
        "expiration_date": "2027-03-15T00:00:00Z",
        "updated_date": "2026-01-10T00:00:00Z",
        "registrant": {
            "name": "Domain Admin",
            "organization": "Privacy Shield Corp",
            "email": f"admin@{domain}",
            "country": "US",
        },
        "name_servers": [
            f"ns1.{domain}",
            f"ns2.{domain}",
        ],
        "status": ["clientTransferProhibited"],
        "dnssec": "unsigned",
    }, indent=2)


def _mock_dns(input_data: dict) -> str:
    """Mock DNS lookup returning realistic data."""
    domain = input_data.get("domain", "unknown.com")
    record_type = input_data.get("record_type", "A")

    records = {
        "A": [{"value": "93.184.216.34", "ttl": 3600}],
        "AAAA": [{"value": "2606:2800:220:1:248:1893:25c8:1946", "ttl": 3600}],
        "MX": [
            {"value": f"mail1.{domain}", "priority": 10, "ttl": 3600},
            {"value": f"mail2.{domain}", "priority": 20, "ttl": 3600},
        ],
        "NS": [
            {"value": f"ns1.{domain}", "ttl": 86400},
            {"value": f"ns2.{domain}", "ttl": 86400},
        ],
        "TXT": [
            {"value": "v=spf1 include:_spf.google.com ~all", "ttl": 3600},
        ],
    }

    return json.dumps({
        "domain": domain,
        "record_type": record_type,
        "records": records.get(record_type, []),
    }, indent=2)


def _mock_reverse_dns(input_data: dict) -> str:
    """Mock reverse DNS lookup."""
    ip = input_data.get("ip", "0.0.0.0")
    return json.dumps({
        "ip": ip,
        "hostnames": [f"host-{ip.replace('.', '-')}.example.net"],
        "organization": "Example ISP",
        "asn": "AS12345",
        "asn_name": "EXAMPLE-ISP",
    }, indent=2)


def _mock_web_search(input_data: dict) -> str:
    """Mock web search results."""
    query = input_data.get("query", "")
    return json.dumps({
        "query": query,
        "results": [
            {
                "title": f"Information about {query}",
                "url": f"https://example.com/info/{query.replace(' ', '-')}",
                "snippet": f"Detailed information about {query} found in public records.",
            },
            {
                "title": f"{query} - Public Records",
                "url": f"https://records.example.org/{query.replace(' ', '-')}",
                "snippet": f"Public records and data related to {query}.",
            },
        ],
    }, indent=2)


def _mock_email_domain(input_data: dict) -> str:
    """Mock email domain check."""
    email = input_data.get("email", "unknown@example.com")
    domain = email.split("@")[1] if "@" in email else "unknown.com"
    return json.dumps({
        "email": email,
        "domain": domain,
        "mx_records": [f"mail.{domain}"],
        "has_spf": True,
        "has_dmarc": True,
        "domain_age_days": 2200,
    }, indent=2)


def _mock_hash_lookup(input_data: dict) -> str:
    """Mock hash lookup."""
    hash_val = input_data.get("hash", "")
    return json.dumps({
        "hash": hash_val,
        "hash_type": "sha256" if len(hash_val) == 64 else "md5" if len(hash_val) == 32 else "sha1",
        "found": False,
        "detections": 0,
        "total_engines": 70,
        "first_seen": None,
        "file_name": None,
    }, indent=2)


# Handler mapping
TOOL_HANDLERS = {
    "whois_lookup": _mock_whois,
    "dns_lookup": _mock_dns,
    "reverse_dns": _mock_reverse_dns,
    "web_search": _mock_web_search,
    "email_domain_check": _mock_email_domain,
    "hash_lookup": _mock_hash_lookup,
}
