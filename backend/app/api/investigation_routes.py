"""Investigation management API routes."""

import asyncio
from uuid import UUID
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.models import (
    Investigation, InvestigationStatus, Case, User,
    AuditLog, AuditAction, InvestigationStep,
)
from app.schemas.schemas import (
    InvestigationCreate, InvestigationResponse,
    InvestigationDetailResponse, InvestigationStepResponse,
)
from app.auth.auth import get_current_user

router = APIRouter(prefix="/api/v1", tags=["Investigations"])


@router.post(
    "/cases/{case_id}/investigations",
    response_model=InvestigationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_investigation(
    case_id: UUID,
    inv_data: InvestigationCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create and start a new autonomous investigation."""
    # Verify case exists and belongs to user's org
    result = await db.execute(
        select(Case).where(
            Case.id == case_id,
            Case.organization_id == current_user.organization_id,
        )
    )
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")

    if not case.authorization_attestation:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Case does not have authorization attestation",
        )

    # Validate seed type
    valid_seed_types = {"domain", "ip", "email", "hash", "person", "organization"}
    if inv_data.seed_type not in valid_seed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid seed_type. Must be one of: {valid_seed_types}",
        )

    # Create investigation
    investigation = Investigation(
        case_id=case_id,
        created_by=current_user.id,
        seed_type=inv_data.seed_type,
        seed_value=inv_data.seed_value,
        max_iterations=inv_data.max_iterations,
        max_tool_calls=inv_data.max_tool_calls,
        max_time_seconds=inv_data.max_time_seconds,
        status=InvestigationStatus.PENDING,
    )
    db.add(investigation)
    await db.flush()

    # Update case status
    if case.status == "open":
        case.status = "in_progress"

    # Audit log
    audit = AuditLog(
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        action=AuditAction.CREATE,
        resource_type="investigation",
        resource_id=str(investigation.id),
        details={
            "seed_type": inv_data.seed_type,
            "seed_value": inv_data.seed_value,
        },
    )
    db.add(audit)
    await db.flush()

    # Schedule the agent workflow in background
    background_tasks.add_task(
        _run_investigation_agent,
        str(investigation.id),
    )

    return InvestigationResponse.model_validate(investigation)


async def _run_investigation_agent(investigation_id: str):
    """Run the LangGraph investigation agent in the background.

    This is the entry point that will be called after the API response is sent.
    The actual agent logic is in app.agent.graph.
    """
    from app.agent.runner import run_investigation
    try:
        await run_investigation(investigation_id)
    except Exception as e:
        # Log error but don't crash — the investigation will be marked failed
        import logging
        logging.getLogger("zaprica.agent").error(
            f"Investigation {investigation_id} failed: {e}", exc_info=True
        )


@router.get(
    "/cases/{case_id}/investigations",
    response_model=list[InvestigationResponse],
)
async def list_investigations(
    case_id: UUID,
    status_filter: Optional[InvestigationStatus] = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List investigations for a case (tenant-isolated)."""
    # Verify case access
    result = await db.execute(
        select(Case).where(
            Case.id == case_id,
            Case.organization_id == current_user.organization_id,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")

    query = select(Investigation).where(Investigation.case_id == case_id)
    if status_filter:
        query = query.where(Investigation.status == status_filter)
    query = query.order_by(Investigation.created_at.desc())

    result = await db.execute(query)
    investigations = result.scalars().all()

    return [InvestigationResponse.model_validate(inv) for inv in investigations]


@router.get(
    "/investigations/{investigation_id}",
    response_model=InvestigationDetailResponse,
)
async def get_investigation(
    investigation_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get investigation details with all steps (tenant-isolated)."""
    result = await db.execute(
        select(Investigation).where(Investigation.id == investigation_id)
    )
    investigation = result.scalar_one_or_none()
    if not investigation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Investigation not found")

    # Verify tenant isolation via case
    result = await db.execute(
        select(Case).where(
            Case.id == investigation.case_id,
            Case.organization_id == current_user.organization_id,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Investigation not found")

    # Get steps
    steps_result = await db.execute(
        select(InvestigationStep)
        .where(InvestigationStep.investigation_id == investigation_id)
        .order_by(InvestigationStep.step_number)
    )
    steps = steps_result.scalars().all()

    inv_dict = {k: getattr(investigation, k) for k in InvestigationResponse.model_fields}
    inv_dict["steps"] = [InvestigationStepResponse.model_validate(s) for s in steps]

    return InvestigationDetailResponse(**inv_dict)


@router.post("/investigations/{investigation_id}/cancel")
async def cancel_investigation(
    investigation_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Cancel a running investigation."""
    result = await db.execute(
        select(Investigation).where(Investigation.id == investigation_id)
    )
    investigation = result.scalar_one_or_none()
    if not investigation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Investigation not found")

    # Tenant isolation
    result = await db.execute(
        select(Case).where(
            Case.id == investigation.case_id,
            Case.organization_id == current_user.organization_id,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Investigation not found")

    if investigation.status in (InvestigationStatus.COMPLETED, InvestigationStatus.CANCELLED):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Investigation is already {investigation.status.value}",
        )

    investigation.status = InvestigationStatus.CANCELLED
    investigation.completed_at = datetime.now(timezone.utc)
    await db.flush()

    return {"status": "cancelled", "investigation_id": str(investigation_id)}
