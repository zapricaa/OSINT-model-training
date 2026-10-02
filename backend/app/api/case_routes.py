"""Case management API routes with tenant isolation."""

from typing import Optional
from uuid import UUID
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.models import Case, CaseStatus, User, AuditLog, AuditAction
from app.schemas.schemas import (
    CaseCreate, CaseUpdate, CaseResponse, CaseListResponse,
)
from app.auth.auth import get_current_user

router = APIRouter(prefix="/api/v1/cases", tags=["Cases"])


async def _log_audit(
    db: AsyncSession, user: User, action: AuditAction,
    resource_type: str, resource_id: str, details: dict = None
):
    """Record an audit log entry."""
    log = AuditLog(
        organization_id=user.organization_id,
        user_id=user.id,
        action=action,
        resource_type=resource_type,
        resource_id=str(resource_id),
        details=details or {},
    )
    db.add(log)


@router.post("", response_model=CaseResponse, status_code=status.HTTP_201_CREATED)
async def create_case(
    case_data: CaseCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new investigation case. Requires authorization attestation."""
    if not case_data.authorization_attestation:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Authorization attestation is required per DPDP Act compliance. "
                   "You must confirm this investigation is authorized.",
        )

    case = Case(
        organization_id=current_user.organization_id,
        created_by=current_user.id,
        title=case_data.title,
        description=case_data.description,
        authorization_attestation=case_data.authorization_attestation,
        tags=case_data.tags,
    )
    db.add(case)
    await db.flush()

    await _log_audit(db, current_user, AuditAction.CREATE, "case", case.id,
                     {"title": case.title})

    return CaseResponse(
        **{k: getattr(case, k) for k in CaseResponse.model_fields if k != "investigation_count"},
        investigation_count=0,
    )


@router.get("", response_model=CaseListResponse)
async def list_cases(
    status_filter: Optional[CaseStatus] = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List cases for the current user's organization (tenant-isolated)."""
    query = select(Case).where(Case.organization_id == current_user.organization_id)
    count_query = select(func.count(Case.id)).where(
        Case.organization_id == current_user.organization_id
    )

    if status_filter:
        query = query.where(Case.status == status_filter)
        count_query = count_query.where(Case.status == status_filter)

    query = query.order_by(Case.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    cases = result.scalars().all()

    count_result = await db.execute(count_query)
    total = count_result.scalar()

    return CaseListResponse(
        cases=[
            CaseResponse(
                **{k: getattr(c, k) for k in CaseResponse.model_fields if k != "investigation_count"},
                investigation_count=len(c.investigations) if c.investigations else 0,
            )
            for c in cases
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{case_id}", response_model=CaseResponse)
async def get_case(
    case_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific case by ID (tenant-isolated)."""
    result = await db.execute(
        select(Case).where(
            Case.id == case_id,
            Case.organization_id == current_user.organization_id,
        )
    )
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")

    return CaseResponse(
        **{k: getattr(case, k) for k in CaseResponse.model_fields if k != "investigation_count"},
        investigation_count=len(case.investigations) if case.investigations else 0,
    )


@router.patch("/{case_id}", response_model=CaseResponse)
async def update_case(
    case_id: UUID,
    case_data: CaseUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a case (tenant-isolated)."""
    result = await db.execute(
        select(Case).where(
            Case.id == case_id,
            Case.organization_id == current_user.organization_id,
        )
    )
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")

    update_data = case_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(case, field, value)

    if case_data.status == CaseStatus.CLOSED:
        case.closed_at = datetime.now(timezone.utc)

    await db.flush()

    await _log_audit(db, current_user, AuditAction.UPDATE, "case", case.id, update_data)

    return CaseResponse(
        **{k: getattr(case, k) for k in CaseResponse.model_fields if k != "investigation_count"},
        investigation_count=len(case.investigations) if case.investigations else 0,
    )
