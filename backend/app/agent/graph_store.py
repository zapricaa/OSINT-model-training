"""Graph Store — PostgreSQL + Apache AGE integration.

Stores entities as graph nodes and relationships as edges
in the Apache AGE knowledge graph. Also stores evidence with
SHA-256 hashing for provenance.

For MVP: Uses in-memory storage with the same interface.
Apache AGE openCypher queries will be added in Slice 4.
"""

import hashlib
import json
import logging
from typing import Tuple
from datetime import datetime, timezone

logger = logging.getLogger("zaprica.graph_store")

# In-memory graph store for MVP (replaced by Apache AGE in Slice 4)
_graph_nodes: dict[str, dict] = {}
_graph_edges: list[dict] = []
_evidence_store: list[dict] = []


def store_to_graph(
    investigation_id: str,
    entities: list[dict],
    edges: list[dict],
    raw_output: str,
    tool_name: str,
) -> Tuple[int, int]:
    """Store entities and edges in the knowledge graph.

    Also creates an evidence record with SHA-256 hash
    for the raw tool output.

    Returns:
        Tuple of (entities_stored, edges_stored)
    """
    entities_stored = 0
    edges_stored = 0

    # Store entities as nodes
    for entity in entities:
        key = entity.get("normalized_key", "")
        if not key:
            continue

        _graph_nodes[key] = {
            "entity_type": entity.get("entity_type"),
            "value": entity.get("value"),
            "normalized_value": entity.get("normalized_value"),
            "properties": entity.get("properties", {}),
            "investigation_id": investigation_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        entities_stored += 1

    # Store edges
    for edge in edges:
        edge_record = {
            "source_key": f"{edge['source_type']}:{edge['source_value']}",
            "target_key": f"{edge['target_type']}:{edge['target_value']}",
            "relationship": edge.get("relationship", "associated_with"),
            "properties": edge.get("properties", {}),
            "investigation_id": investigation_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        _graph_edges.append(edge_record)
        edges_stored += 1

    # Create evidence record with SHA-256 hash
    if raw_output:
        evidence_hash = hashlib.sha256(raw_output.encode("utf-8")).hexdigest()
        _evidence_store.append({
            "investigation_id": investigation_id,
            "tool_name": tool_name,
            "sha256_hash": evidence_hash,
            "collected_at": datetime.now(timezone.utc).isoformat(),
            "content_preview": raw_output[:500],
            "content_length": len(raw_output),
        })

    logger.info(
        f"Stored {entities_stored} entities, {edges_stored} edges "
        f"for investigation {investigation_id}"
    )

    return entities_stored, edges_stored


def get_graph_data(investigation_id: str = None) -> dict:
    """Get graph data, optionally filtered by investigation.

    Returns nodes and edges in a format suitable for visualization.
    """
    nodes = []
    for key, node in _graph_nodes.items():
        if investigation_id and node.get("investigation_id") != investigation_id:
            continue
        nodes.append({
            "id": key,
            **node,
        })

    edges = []
    for edge in _graph_edges:
        if investigation_id and edge.get("investigation_id") != investigation_id:
            continue
        edges.append(edge)

    return {"nodes": nodes, "edges": edges}


def get_evidence(investigation_id: str = None) -> list[dict]:
    """Get evidence records, optionally filtered by investigation."""
    if investigation_id:
        return [e for e in _evidence_store if e["investigation_id"] == investigation_id]
    return _evidence_store


def clear_graph():
    """Clear the in-memory graph (for testing)."""
    _graph_nodes.clear()
    _graph_edges.clear()
    _evidence_store.clear()
