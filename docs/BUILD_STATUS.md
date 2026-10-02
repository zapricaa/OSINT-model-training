# ZAPRICA — Build Status

## Completed Slices

### SLICE 1: Foundation & Core Backend ✅
**Date:** 2026-10-01

| Component | Status |
|-----------|--------|
| Docker Compose (PostgreSQL+AGE, MinIO, Redis, FastAPI) | ✅ Complete |
| Backend Dockerfile | ✅ Complete |
| PostgreSQL + Apache AGE init script | ✅ Complete |
| Core SQLAlchemy models (7 models) | ✅ Complete |
| Pydantic schemas for all endpoints | ✅ Complete |
| FastAPI app (CORS, error handling, health) | ✅ Complete |
| JWT Authentication with bcrypt | ✅ Complete |
| Case CRUD API (create, list, get, update) | ✅ Complete |
| Investigation CRUD API (create, list, get, cancel) | ✅ Complete |
| Graph query API (nodes, edges, evidence) | ✅ Complete |
| MCP Tool Registry (6 tools, JSON-RPC 2.0 schema) | ✅ Complete |
| Tool input validation (regex allowlists, OWASP LLM06) | ✅ Complete |
| LangGraph state machine (8 nodes, full loop) | ✅ Complete |
| DualView Extractor (quarantined, zero tool access) | ✅ Complete |
| Entity normalizer + deduplication | ✅ Complete |
| In-memory graph store + SHA-256 evidence | ✅ Complete |
| Investigation runner (background orchestration) | ✅ Complete |
| Test suite (tool, extractor, normalizer, graph, security) | ✅ Complete |
| Audit logging (immutable) | ✅ Complete |
| Tenant isolation (all APIs) | ✅ Complete |

---

## Current Task
**SLICE 7:** Frontend — Next.js dashboard, case management, investigation UI, knowledge graph visualization.

## In Progress
- [x] Next.js project scaffolding
- [ ] Design system (CSS variables, dark mode)
- [ ] Auth pages (login/register)
- [ ] Dashboard
- [ ] Case management
- [ ] Investigation UI with live status
- [ ] Knowledge graph visualization (react-force-graph)
- [ ] Evidence viewer

## Tests Passed
- Tool registry (7 tests)
- Tool input validation / security (8 tests)
- Extractor (5 tests, including prompt injection)
- Normalizer (6 tests)
- Graph store (4 tests)
- Agent graph (3 tests)
- Security controls (4 tests)

## Known Problems
- None (all tests pass)

## Blocked Items
- LLM API keys needed for real Planner/Extractor (using mocks)
- Cloud credentials for S3 (using MinIO locally)
