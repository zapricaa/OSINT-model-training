# ZAPRICA — Implementation Backlog

## SLICE 1: Foundation & Core Backend
- [ ] Project directory scaffolding
- [ ] Docker Compose (PostgreSQL + AGE, MinIO, Redis, FastAPI)
- [ ] PostgreSQL + Apache AGE database initialization
- [ ] Alembic migrations setup
- [ ] Core SQLAlchemy models (Organization, User, Case, Investigation, AuditLog)
- [ ] FastAPI app skeleton with CORS, error handling
- [ ] Authentication (JWT-based)
- [ ] Case CRUD API
- [ ] Investigation CRUD API
- [ ] LangGraph agent skeleton (Plan → Execute → Extract → Graph states)
- [ ] Mock tool execution (return hardcoded WHOIS data)
- [ ] Investigation lifecycle: create → plan → execute mock → extract → complete
- [ ] Basic API tests (case/investigation CRUD)
- [ ] Agent state tests (state transitions)

## SLICE 2: MCP Tool Registry & Tool Execution
- [ ] MCP server implementation (JSON-RPC 2.0)
- [ ] tools/list endpoint
- [ ] tools/call endpoint
- [ ] Tool schema validation (Pydantic)
- [ ] WHOIS tool (real implementation)
- [ ] DNS lookup tool
- [ ] Tool argument allowlisting & regex validation
- [ ] Planner → MCP tool selection → execution → structured result
- [ ] Tool registry tests
- [ ] Security tests (malformed arguments, unauthorized tools)

## SLICE 3: Dual-LLM Extractor
- [ ] Quarantined Extractor LLM service (zero tool access)
- [ ] Structured JSON entity extraction from raw content
- [ ] Entity schema (Person, Organization, Domain, IP, Email, FileHash)
- [ ] Input sanitization (strip injection attempts)
- [ ] Extractor → validated entities pipeline
- [ ] Extractor security tests (prompt injection payloads)

## SLICE 4: Knowledge Graph (PostgreSQL + Apache AGE)
- [ ] Apache AGE graph schema creation
- [ ] Graph node CRUD (openCypher)
- [ ] Graph edge CRUD with evidence linkage
- [ ] Entity resolution (deduplication by normalized key)
- [ ] Entity normalization (domain/IP/email canonicalization)
- [ ] Graph query API (neighbors, paths, subgraphs)
- [ ] Graph integration tests
- [ ] Duplicate detection tests

## SLICE 5: Evidence Provenance
- [ ] MinIO/S3 integration for evidence storage
- [ ] Evidence hashing (SHA-256)
- [ ] Evidence model (source URL, timestamp, hash, S3 URI)
- [ ] Evidence API (upload, retrieve, verify)
- [ ] Evidence linked to graph edges
- [ ] Screenshot/HTML storage from browser worker
- [ ] Provenance integrity tests

## SLICE 6: Recursive Investigation & Pivoting
- [ ] Planner re-evaluation after graph update
- [ ] Pivot detection (new unexplored nodes)
- [ ] Recursive investigation loop
- [ ] Termination controls (max iterations, time, tool calls)
- [ ] Duplicate detection in investigation scope
- [ ] Resource budget enforcement
- [ ] Infinite loop prevention tests
- [ ] Pivot logic tests

## SLICE 7: Frontend
- [ ] Next.js project setup
- [ ] Authentication pages (login/register)
- [ ] Dashboard (case overview, investigation stats)
- [ ] Case management (create, list, detail)
- [ ] Investigation management (create, detail, live status)
- [ ] Knowledge graph visualization (react-force-graph)
- [ ] Entity detail panels
- [ ] Evidence viewer
- [ ] Audit log viewer
- [ ] Tool registry management
- [ ] Settings page
- [ ] Real-time investigation updates (WebSocket/SSE)
- [ ] Zustand state management
- [ ] Frontend tests

## SLICE 8: Temporal Durable Execution
- [ ] Temporal server integration in Docker Compose
- [ ] Temporal workflow wrapping LangGraph
- [ ] HITL CAPTCHA signal handling
- [ ] Crash recovery and state persistence
- [ ] Rate-limit pause/resume
- [ ] Temporal workflow tests

## SLICE 9: Security & Adversarial Testing
- [ ] Indirect prompt injection testing
- [ ] Excessive agency testing
- [ ] Command injection testing (shell sandbox)
- [ ] SSRF prevention
- [ ] Path traversal prevention
- [ ] Cross-tenant isolation tests
- [ ] Malformed JSON handling
- [ ] Unauthorized tool call tests
- [ ] Browser content isolation verification
- [ ] seccomp profile enforcement tests

## INFRASTRUCTURE
- [!] LLM API keys (blocked — need user credentials)
- [ ] Production Docker images
- [ ] CI/CD pipeline
- [ ] Kubernetes manifests (Phase 2)
- [ ] Kong API Gateway (Phase 3)
