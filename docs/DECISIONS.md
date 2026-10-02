# ZAPRICA — Engineering Decisions

## Decision Log

### D-001: MVP Phase — Skip Temporal, Use In-Process LangGraph
**Date:** 2026-10-01
**Context:** The PRD specifies Temporal.io for durable execution (Phase 2). For Slice 1-6 MVP, LangGraph provides sufficient state management.
**Decision:** Implement the agent loop with LangGraph only. Temporal integration is deferred to Slice 8 as specified in the roadmap.
**Rationale:** Temporal adds significant infrastructure complexity. The PRD Phase 1 goal is "Hackathon demo and angel pitching" — LangGraph alone meets this requirement. The architecture is designed so Temporal wraps the LangGraph workflows, making this a non-breaking addition.

### D-002: MVP Phase — Use MinIO Instead of AWS S3
**Date:** 2026-10-01
**Context:** Techstack specifies "AWS S3 (or MinIO for self-hosted instances)" for evidence storage.
**Decision:** Use MinIO in Docker Compose for local development. S3-compatible API ensures seamless migration.
**Rationale:** No cloud credentials required for MVP development.

### D-003: Authentication — JWT with bcrypt
**Date:** 2026-10-01
**Context:** PRD requires authentication and RBAC. No specific auth provider specified for MVP.
**Decision:** Implement JWT-based authentication with bcrypt password hashing. SAML/SSO deferred to Phase 3 per PRD.
**Rationale:** Simplest secure auth that meets MVP requirements.

### D-004: LLM Provider — Mock for Initial Development
**Date:** 2026-10-01
**Context:** Techstack specifies Claude 3.5 Sonnet / GPT-4o for Planner and Llama-3-8B / GPT-4o-mini for Extractor.
**Decision:** Build with a configurable LLM provider interface. Use mock LLM responses for initial development, allowing real LLM integration once API keys are provided.
**Rationale:** Enables full pipeline development and testing without API key dependency.

### D-005: Kong API Gateway — Deferred to Phase 3
**Date:** 2026-10-01
**Context:** Techstack specifies Kong for rate limiting and tenant access control.
**Decision:** FastAPI middleware handles rate limiting for MVP. Kong deferred per PRD Phase 3 roadmap.
**Rationale:** PRD explicitly marks Kong as Phase 3 (Series A).

### D-006: Kubernetes — Deferred to Phase 2
**Date:** 2026-10-01
**Context:** Techstack specifies EKS/GKE for container orchestration.
**Decision:** Docker Compose for MVP. Kubernetes deferred per PRD Phase 2 roadmap.
**Rationale:** PRD Phase 2 (Seed Stage) explicitly includes K8s HPA.
