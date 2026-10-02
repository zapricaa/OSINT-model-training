"""Entity Normalization and Resolution.

Normalizes entities to canonical forms and deduplicates
against known entities in the investigation graph.
"""

import re
import logging
from typing import Tuple

logger = logging.getLogger("zaprica.normalizer")


def normalize_value(entity_type: str, value: str) -> str:
    """Normalize an entity value to its canonical form.

    - Domains: lowercase, strip trailing dots, strip www prefix
    - IPs: strip leading zeros
    - Emails: lowercase
    - Hashes: lowercase
    """
    value = value.strip()

    if entity_type == "Domain":
        value = value.lower()
        value = value.rstrip(".")
        if value.startswith("www."):
            value = value[4:]
        return value

    if entity_type == "IP":
        # Normalize IP: strip leading zeros from octets
        parts = value.split(".")
        if len(parts) == 4:
            try:
                return ".".join(str(int(p)) for p in parts)
            except ValueError:
                return value
        return value

    if entity_type == "Email":
        return value.lower()

    if entity_type == "FileHash":
        return value.lower()

    if entity_type in ("Person", "Organization"):
        # Basic normalization: strip extra whitespace
        return re.sub(r"\s+", " ", value).strip()

    return value


def make_entity_key(entity_type: str, normalized_value: str) -> str:
    """Create a unique key for entity deduplication."""
    return f"{entity_type}:{normalized_value}"


def normalize_and_resolve(
    extracted_entities: list[dict],
    extracted_edges: list[dict],
    known_entities: list[dict],
    explored_keys: list[str],
) -> Tuple[list[dict], list[dict], list[dict]]:
    """Normalize entities and resolve duplicates.

    Returns:
        Tuple of (new_entities, new_edges, updated_known_entities)
    """
    # Build a lookup of known entities by key
    known_map = {}
    for entity in known_entities:
        key = entity.get("normalized_key", "")
        if key:
            known_map[key] = entity

    new_entities = []
    new_edges = []

    for entity in extracted_entities:
        entity_type = entity.get("entity_type", "")
        value = entity.get("value", "")

        # Normalize
        normalized = normalize_value(entity_type, value)
        entity_key = make_entity_key(entity_type, normalized)

        entity["normalized_value"] = normalized
        entity["normalized_key"] = entity_key

        if entity_key in known_map:
            # Duplicate found — merge properties
            existing = known_map[entity_key]
            existing_props = existing.get("properties", {})
            new_props = entity.get("properties", {})
            merged = {**existing_props, **new_props}
            existing["properties"] = merged
            logger.debug(f"Merged duplicate entity: {entity_key}")
        else:
            # New entity
            known_map[entity_key] = entity
            new_entities.append(entity)
            logger.debug(f"New entity: {entity_key}")

    # Normalize edge endpoints too
    for edge in extracted_edges:
        edge["source_value"] = normalize_value(
            edge.get("source_type", ""), edge.get("source_value", "")
        )
        edge["target_value"] = normalize_value(
            edge.get("target_type", ""), edge.get("target_value", "")
        )
        new_edges.append(edge)

    updated_known = list(known_map.values())
    logger.info(
        f"Normalized: {len(new_entities)} new entities, "
        f"{len(extracted_entities) - len(new_entities)} duplicates merged"
    )

    return new_entities, new_edges, updated_known
