"""Pydantic schemas for API request/response validation."""

from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional, List, Any
from datetime import datetime
from uuid import UUID
from app.models.models import (
    UserRole, CaseStatus, InvestigationStatus, EvidenceType, AuditAction
)


# ── Auth Schemas ───────────────────────────────────────────────────────

class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=255)
    role: UserRole = UserRole.ANALYST


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    email: str
    full_name: str
    role: UserRole
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime] = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


# ── Organization Schemas ───────────────────────────────────────────────

class OrganizationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    slug: str = Field(min_length=1, max_length=100, pattern=r"^[a-z0-9\-]+$")


class OrganizationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    slug: str
    is_active: bool
    created_at: datetime


class RegistrationRequest(BaseModel):
    """Combined registration request for org + admin user."""
    name: str = Field(min_length=1, max_length=255, description="Organization name")
    slug: str = Field(min_length=1, max_length=100, pattern=r"^[a-z0-9\-]+$", description="Organization slug")
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=255)
    role: UserRole = UserRole.ADMIN



# ── Case Schemas ───────────────────────────────────────────────────────

class CaseCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    description: Optional[str] = None
    authorization_attestation: bool = Field(
        description="Digital attestation confirming authorized use per DPDP Act compliance"
    )
    tags: List[str] = Field(default_factory=list)


class CaseUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    description: Optional[str] = None
    status: Optional[CaseStatus] = None
    tags: Optional[List[str]] = None


class CaseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    created_by: UUID
    title: str
    description: Optional[str]
    status: CaseStatus
    authorization_attestation: bool
    tags: List[str]
    created_at: datetime
    updated_at: datetime
    closed_at: Optional[datetime] = None
    investigation_count: int = 0


class CaseListResponse(BaseModel):
    cases: List[CaseResponse]
    total: int
    page: int
    page_size: int


# ── Investigation Schemas ──────────────────────────────────────────────

class InvestigationCreate(BaseModel):
    seed_type: str = Field(
        description="Type of OSINT seed: domain, ip, email, hash, person, organization"
    )
    seed_value: str = Field(min_length=1, max_length=1000)
    max_iterations: int = Field(default=50, ge=1, le=500)
    max_tool_calls: int = Field(default=200, ge=1, le=1000)
    max_time_seconds: int = Field(default=3600, ge=60, le=86400)


class InvestigationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    case_id: UUID
    created_by: UUID
    seed_type: str
    seed_value: str
    status: InvestigationStatus
    current_step: Optional[str]
    iteration_count: int
    tool_call_count: int
    max_iterations: int
    max_tool_calls: int
    max_time_seconds: int
    plan: List[Any]
    findings_summary: Optional[str]
    entity_count: int
    edge_count: int
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    error_message: Optional[str]
    error_count: int


class InvestigationStepResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    investigation_id: UUID
    step_number: int
    step_type: str
    tool_name: Optional[str]
    tool_input: Optional[Any]
    tool_output: Optional[Any]
    entities_extracted: List[Any]
    edges_created: List[Any]
    status: str
    error_message: Optional[str]
    duration_ms: Optional[int]
    started_at: datetime
    completed_at: Optional[datetime]


class InvestigationDetailResponse(InvestigationResponse):
    steps: List[InvestigationStepResponse] = []


# ── Evidence Schemas ───────────────────────────────────────────────────

class EvidenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    investigation_id: UUID
    evidence_type: EvidenceType
    source_url: Optional[str]
    collected_at: datetime
    sha256_hash: str
    s3_uri: str
    file_size_bytes: Optional[int]
    content_type: Optional[str]
    description: Optional[str]


# ── Audit Schemas ──────────────────────────────────────────────────────

class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    user_id: Optional[UUID]
    action: AuditAction
    resource_type: str
    resource_id: Optional[str]
    details: dict
    ip_address: Optional[str]
    timestamp: datetime


# ── Graph Entity Schemas ───────────────────────────────────────────────

class GraphEntity(BaseModel):
    """Entity extracted by the Quarantined Extractor."""
    entity_type: str  # Person, Organization, Domain, IP, Email, FileHash
    value: str
    normalized_value: str = ""
    properties: dict = Field(default_factory=dict)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    source_investigation_id: Optional[str] = None


class GraphEdge(BaseModel):
    """Relationship between graph entities."""
    source_type: str
    source_value: str
    target_type: str
    target_value: str
    relationship: str  # resolves_to, associated_with, mentions
    properties: dict = Field(default_factory=dict)
    evidence_id: Optional[str] = None


class GraphQueryResponse(BaseModel):
    nodes: List[GraphEntity]
    edges: List[GraphEdge]
