"""Knowledge Graph API routes."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.models import Case, User, Evidence
from app.schemas.schemas import GraphQueryResponse, GraphEntity, GraphEdge, EvidenceResponse
from app.auth.auth import get_current_user
from app.agent.graph_store import get_graph_data, get_evidence

router = APIRouter(prefix="/api/v1", tags=["Knowledge Graph"])


@router.get("/investigations/{investigation_id}/graph", response_model=GraphQueryResponse)
async def get_investigation_graph(
    investigation_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get the knowledge graph for an investigation."""
    # TODO: Add tenant isolation check via case

    graph_data = get_graph_data(str(investigation_id))

    nodes = []
    for node in graph_data["nodes"]:
        nodes.append(GraphEntity(
            entity_type=node.get("entity_type", ""),
            value=node.get("value", ""),
            normalized_value=node.get("normalized_value", ""),
            properties=node.get("properties", {}),
            source_investigation_id=node.get("investigation_id"),
        ))

    edges = []
    for edge in graph_data["edges"]:
        source_parts = edge.get("source_key", ":").split(":", 1)
        target_parts = edge.get("target_key", ":").split(":", 1)
        edges.append(GraphEdge(
            source_type=source_parts[0] if len(source_parts) > 0 else "",
            source_value=source_parts[1] if len(source_parts) > 1 else "",
            target_type=target_parts[0] if len(target_parts) > 0 else "",
            target_value=target_parts[1] if len(target_parts) > 1 else "",
            relationship=edge.get("relationship", ""),
            properties=edge.get("properties", {}),
        ))

    return GraphQueryResponse(nodes=nodes, edges=edges)


@router.get("/investigations/{investigation_id}/evidence", response_model=list[EvidenceResponse])
async def get_investigation_evidence(
    investigation_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get evidence records for an investigation."""
    result = await db.execute(
        select(Evidence).where(Evidence.investigation_id == investigation_id)
    )
    evidence_list = result.scalars().all()
    return [EvidenceResponse.model_validate(e) for e in evidence_list]


@router.get("/tools", response_model=list[dict])
async def list_tools(
    current_user: User = Depends(get_current_user),
):
    """MCP tools/list — list available OSINT tools."""
    from app.agent.tools import list_tools as get_tools
    return get_tools()
