"""ZAPRICA Quarantined Extractor — DualView Security Boundary.

The Extractor LLM processes raw, untrusted tool output and extracts
structured entities. It has ZERO tool-calling privileges.

This is the critical security boundary that prevents Indirect Prompt
Injection (OWASP LLM01). Malicious instructions in web content are
processed as inert text and converted to structured JSON only.
"""

import json
import re
import logging
from typing import Tuple

logger = logging.getLogger("zaprica.extractor")


def extract_entities(
    raw_content: str,
    source_tool: str,
    investigation_id: str,
) -> Tuple[list[dict], list[dict]]:
    """Extract structured entities from raw tool output.

    This function implements the Quarantined Extractor role:
    - Reads untrusted external data
    - Has NO tool-calling capability
    - Outputs only structured JSON entities

    For MVP, this uses pattern-based extraction.
    With real LLM integration, this will use the Extractor LLM
    (e.g., Llama-3-8B / GPT-4o-mini) with a strict output schema.

    Returns:
        Tuple of (entities, edges)
    """
    logger.info(f"Extracting entities from {source_tool} output")

    try:
        data = json.loads(raw_content)
    except json.JSONDecodeError:
        logger.warning("Raw content is not valid JSON, attempting text extraction")
        return _extract_from_text(raw_content, source_tool, investigation_id)

    entities = []
    edges = []

    # Route to appropriate extractor based on tool type
    if source_tool == "whois_lookup":
        entities, edges = _extract_whois(data, investigation_id)
    elif source_tool == "dns_lookup":
        entities, edges = _extract_dns(data, investigation_id)
    elif source_tool == "reverse_dns":
        entities, edges = _extract_reverse_dns(data, investigation_id)
    elif source_tool == "web_search":
        entities, edges = _extract_web_search(data, investigation_id)
    elif source_tool == "email_domain_check":
        entities, edges = _extract_email_domain(data, investigation_id)
    elif source_tool == "hash_lookup":
        entities, edges = _extract_hash(data, investigation_id)
    else:
        logger.warning(f"No extractor for tool: {source_tool}")

    logger.info(f"Extracted {len(entities)} entities, {len(edges)} edges")
    return entities, edges


def _extract_whois(data: dict, investigation_id: str) -> Tuple[list, list]:
    """Extract entities from WHOIS data."""
    entities = []
    edges = []

    domain = data.get("domain", "")
    if domain:
        entities.append({
            "entity_type": "Domain",
            "value": domain,
            "properties": {
                "registrar": data.get("registrar", ""),
                "creation_date": data.get("creation_date", ""),
                "expiration_date": data.get("expiration_date", ""),
                "status": data.get("status", []),
            },
            "source_investigation_id": investigation_id,
        })

    # Extract registrant info
    registrant = data.get("registrant", {})
    if registrant:
        if registrant.get("organization"):
            entities.append({
                "entity_type": "Organization",
                "value": registrant["organization"],
                "properties": {"country": registrant.get("country", "")},
                "source_investigation_id": investigation_id,
            })
            edges.append({
                "source_type": "Domain",
                "source_value": domain,
                "target_type": "Organization",
                "target_value": registrant["organization"],
                "relationship": "registered_by",
            })

        if registrant.get("email"):
            entities.append({
                "entity_type": "Email",
                "value": registrant["email"],
                "properties": {},
                "source_investigation_id": investigation_id,
            })
            edges.append({
                "source_type": "Domain",
                "source_value": domain,
                "target_type": "Email",
                "target_value": registrant["email"],
                "relationship": "associated_with",
            })

    # Extract nameservers
    for ns in data.get("name_servers", []):
        entities.append({
            "entity_type": "Domain",
            "value": ns,
            "properties": {"role": "nameserver"},
            "source_investigation_id": investigation_id,
        })
        edges.append({
            "source_type": "Domain",
            "source_value": domain,
            "target_type": "Domain",
            "target_value": ns,
            "relationship": "resolves_to",
        })

    return entities, edges


def _extract_dns(data: dict, investigation_id: str) -> Tuple[list, list]:
    """Extract entities from DNS records."""
    entities = []
    edges = []

    domain = data.get("domain", "")
    record_type = data.get("record_type", "")

    for record in data.get("records", []):
        value = record.get("value", "")
        if not value:
            continue

        if record_type == "A":
            entities.append({
                "entity_type": "IP",
                "value": value,
                "properties": {"ttl": record.get("ttl")},
                "source_investigation_id": investigation_id,
            })
            edges.append({
                "source_type": "Domain",
                "source_value": domain,
                "target_type": "IP",
                "target_value": value,
                "relationship": "resolves_to",
            })
        elif record_type == "MX":
            entities.append({
                "entity_type": "Domain",
                "value": value,
                "properties": {"role": "mail_server", "priority": record.get("priority")},
                "source_investigation_id": investigation_id,
            })
            edges.append({
                "source_type": "Domain",
                "source_value": domain,
                "target_type": "Domain",
                "target_value": value,
                "relationship": "associated_with",
            })
        elif record_type in ("NS", "CNAME"):
            entities.append({
                "entity_type": "Domain",
                "value": value,
                "properties": {"role": record_type.lower()},
                "source_investigation_id": investigation_id,
            })
            edges.append({
                "source_type": "Domain",
                "source_value": domain,
                "target_type": "Domain",
                "target_value": value,
                "relationship": "resolves_to",
            })

    return entities, edges


def _extract_reverse_dns(data: dict, investigation_id: str) -> Tuple[list, list]:
    """Extract entities from reverse DNS."""
    entities = []
    edges = []

    ip = data.get("ip", "")
    for hostname in data.get("hostnames", []):
        entities.append({
            "entity_type": "Domain",
            "value": hostname,
            "properties": {},
            "source_investigation_id": investigation_id,
        })
        edges.append({
            "source_type": "IP",
            "source_value": ip,
            "target_type": "Domain",
            "target_value": hostname,
            "relationship": "resolves_to",
        })

    org = data.get("organization")
    if org:
        entities.append({
            "entity_type": "Organization",
            "value": org,
            "properties": {
                "asn": data.get("asn", ""),
                "asn_name": data.get("asn_name", ""),
            },
            "source_investigation_id": investigation_id,
        })
        edges.append({
            "source_type": "IP",
            "source_value": ip,
            "target_type": "Organization",
            "target_value": org,
            "relationship": "associated_with",
        })

    return entities, edges


def _extract_web_search(data: dict, investigation_id: str) -> Tuple[list, list]:
    """Extract entities from web search results."""
    entities = []
    edges = []

    for result in data.get("results", []):
        url = result.get("url", "")
        if url:
            # Extract domain from URL
            domain_match = re.match(r"https?://([^/]+)", url)
            if domain_match:
                domain = domain_match.group(1)
                entities.append({
                    "entity_type": "Domain",
                    "value": domain,
                    "properties": {
                        "source_url": url,
                        "title": result.get("title", ""),
                    },
                    "source_investigation_id": investigation_id,
                })

    return entities, edges


def _extract_email_domain(data: dict, investigation_id: str) -> Tuple[list, list]:
    """Extract entities from email domain check."""
    entities = []
    edges = []

    email = data.get("email", "")
    domain = data.get("domain", "")

    if email:
        entities.append({
            "entity_type": "Email",
            "value": email,
            "properties": {
                "has_spf": data.get("has_spf"),
                "has_dmarc": data.get("has_dmarc"),
            },
            "source_investigation_id": investigation_id,
        })

    if domain:
        entities.append({
            "entity_type": "Domain",
            "value": domain,
            "properties": {"domain_age_days": data.get("domain_age_days")},
            "source_investigation_id": investigation_id,
        })
        if email:
            edges.append({
                "source_type": "Email",
                "source_value": email,
                "target_type": "Domain",
                "target_value": domain,
                "relationship": "associated_with",
            })

    for mx in data.get("mx_records", []):
        entities.append({
            "entity_type": "Domain",
            "value": mx,
            "properties": {"role": "mail_server"},
            "source_investigation_id": investigation_id,
        })

    return entities, edges


def _extract_hash(data: dict, investigation_id: str) -> Tuple[list, list]:
    """Extract entities from hash lookup."""
    entities = []
    edges = []

    hash_val = data.get("hash", "")
    if hash_val:
        entities.append({
            "entity_type": "FileHash",
            "value": hash_val,
            "properties": {
                "hash_type": data.get("hash_type", ""),
                "found": data.get("found", False),
                "detections": data.get("detections", 0),
                "file_name": data.get("file_name"),
            },
            "source_investigation_id": investigation_id,
        })

    return entities, edges


def _extract_from_text(raw_text: str, source_tool: str, investigation_id: str) -> Tuple[list, list]:
    """Fallback: extract entities from plain text using regex patterns.

    This is a safety net for when the tool output is not JSON.
    """
    entities = []

    # IP addresses
    for ip in re.findall(r"\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\b", raw_text):
        entities.append({
            "entity_type": "IP",
            "value": ip,
            "properties": {},
            "source_investigation_id": investigation_id,
        })

    # Domains
    for domain in re.findall(r"\b([a-zA-Z0-9\-]+\.[a-zA-Z]{2,}(?:\.[a-zA-Z]{2,})?)\b", raw_text):
        if not re.match(r"\d+\.\d+", domain):  # Skip version numbers
            entities.append({
                "entity_type": "Domain",
                "value": domain,
                "properties": {},
                "source_investigation_id": investigation_id,
            })

    # Emails
    for email in re.findall(r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b", raw_text):
        entities.append({
            "entity_type": "Email",
            "value": email,
            "properties": {},
            "source_investigation_id": investigation_id,
        })

    return entities, []
