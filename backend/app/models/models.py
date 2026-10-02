"""SQLAlchemy models for ZAPRICA core entities."""

import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Text, DateTime, ForeignKey, Enum as SAEnum,
    Integer, Boolean, JSON, Index
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.database import Base
import enum


# ── Enums ──────────────────────────────────────────────────────────────

class UserRole(str, enum.Enum):
    ADMIN = "admin"
    ANALYST = "analyst"
    VIEWER = "viewer"


class CaseStatus(str, enum.Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    CLOSED = "closed"
    ARCHIVED = "archived"


class InvestigationStatus(str, enum.Enum):
    PENDING = "pending"
    PLANNING = "planning"
    EXECUTING = "executing"
    EXTRACTING = "extracting"
    GRAPHING = "graphing"
    EVALUATING = "evaluating"
    PIVOTING = "pivoting"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED_HITL = "paused_hitl"  # Human-in-the-loop pause


class AuditAction(str, enum.Enum):
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    EXECUTE = "execute"
    LOGIN = "login"
    LOGOUT = "logout"


class EvidenceType(str, enum.Enum):
    SCREENSHOT = "screenshot"
    HTML_DUMP = "html_dump"
    TOOL_OUTPUT = "tool_output"
    API_RESPONSE = "api_response"
    SHELL_OUTPUT = "shell_output"


# ── Models ─────────────────────────────────────────────────────────────

class Organization(Base):
    """Tenant/organization for multi-tenancy."""
    __tablename__ = "organizations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, unique=True)
    slug = Column(String(100), nullable=False, unique=True, index=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))
    is_active = Column(Boolean, default=True)

    # Relationships
    users = relationship("User", back_populates="organization", lazy="selectin")
    cases = relationship("Case", back_populates="organization", lazy="selectin")


class User(Base):
    """User account with RBAC."""
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    email = Column(String(255), nullable=False, unique=True, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(SAEnum(UserRole), nullable=False, default=UserRole.ANALYST)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    last_login = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    organization = relationship("Organization", back_populates="users")
    cases = relationship("Case", back_populates="created_by_user", lazy="selectin")

    __table_args__ = (
        Index("ix_users_org_email", "organization_id", "email"),
    )


class Case(Base):
    """Investigation case — top-level container for related investigations."""
    __tablename__ = "cases"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(SAEnum(CaseStatus), nullable=False, default=CaseStatus.OPEN)
    authorization_attestation = Column(Boolean, default=False, nullable=False)
    tags = Column(JSON, default=list)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))
    closed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    organization = relationship("Organization", back_populates="cases")
    created_by_user = relationship("User", back_populates="cases")
    investigations = relationship("Investigation", back_populates="case", lazy="selectin")

    __table_args__ = (
        Index("ix_cases_org_status", "organization_id", "status"),
    )


class Investigation(Base):
    """An autonomous OSINT investigation within a case."""
    __tablename__ = "investigations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = Column(UUID(as_uuid=True), ForeignKey("cases.id"), nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # Investigation seed
    seed_type = Column(String(50), nullable=False)  # domain, ip, email, hash, person, org
    seed_value = Column(String(1000), nullable=False)

    # Status tracking
    status = Column(SAEnum(InvestigationStatus), nullable=False, default=InvestigationStatus.PENDING)
    current_step = Column(String(100), nullable=True)

    # Resource tracking
    iteration_count = Column(Integer, default=0)
    tool_call_count = Column(Integer, default=0)
    max_iterations = Column(Integer, default=50)
    max_tool_calls = Column(Integer, default=200)
    max_time_seconds = Column(Integer, default=3600)

    # Agent state (serialized LangGraph state)
    agent_state = Column(JSON, default=dict)
    plan = Column(JSON, default=list)  # Current investigation plan steps

    # Results
    findings_summary = Column(Text, nullable=True)
    entity_count = Column(Integer, default=0)
    edge_count = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    # Error tracking
    error_message = Column(Text, nullable=True)
    error_count = Column(Integer, default=0)

    # Relationships
    case = relationship("Case", back_populates="investigations")
    evidence = relationship("Evidence", back_populates="investigation", lazy="selectin")
    steps = relationship("InvestigationStep", back_populates="investigation",
                         lazy="selectin", order_by="InvestigationStep.step_number")

    __table_args__ = (
        Index("ix_investigations_case_status", "case_id", "status"),
    )


class InvestigationStep(Base):
    """Individual step in an investigation — records what the agent did."""
    __tablename__ = "investigation_steps"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    investigation_id = Column(UUID(as_uuid=True), ForeignKey("investigations.id"), nullable=False)
    step_number = Column(Integer, nullable=False)

    # What happened
    step_type = Column(String(50), nullable=False)  # plan, tool_call, extract, graph, evaluate, pivot
    tool_name = Column(String(200), nullable=True)
    tool_input = Column(JSON, nullable=True)
    tool_output = Column(JSON, nullable=True)

    # Extraction results
    entities_extracted = Column(JSON, default=list)
    edges_created = Column(JSON, default=list)

    # Status
    status = Column(String(50), default="pending")
    error_message = Column(Text, nullable=True)
    duration_ms = Column(Integer, nullable=True)

    # Timestamps
    started_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    investigation = relationship("Investigation", back_populates="steps")


class Evidence(Base):
    """Cryptographically anchored evidence with provenance."""
    __tablename__ = "evidence"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    investigation_id = Column(UUID(as_uuid=True), ForeignKey("investigations.id"), nullable=False)

    # Provenance
    evidence_type = Column(SAEnum(EvidenceType), nullable=False)
    source_url = Column(String(2000), nullable=True)
    collected_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Integrity
    sha256_hash = Column(String(64), nullable=False, index=True)
    s3_uri = Column(String(500), nullable=False)
    file_size_bytes = Column(Integer, nullable=True)
    content_type = Column(String(100), nullable=True)

    # Metadata
    description = Column(Text, nullable=True)
    metadata_ = Column("metadata", JSON, default=dict)

    # Relationships
    investigation = relationship("Investigation", back_populates="evidence")


class AuditLog(Base):
    """Immutable audit log for compliance."""
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    action = Column(SAEnum(AuditAction), nullable=False)
    resource_type = Column(String(100), nullable=False)
    resource_id = Column(String(255), nullable=True)
    details = Column(JSON, default=dict)
    ip_address = Column(String(45), nullable=True)
    timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_audit_logs_org_timestamp", "organization_id", "timestamp"),
        Index("ix_audit_logs_resource", "resource_type", "resource_id"),
    )
