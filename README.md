# ZAPRICA — Enterprise AI OSINT Platform

## Overview
ZAPRICA is an enterprise-grade, autonomous AI OSINT investigation platform. It deploys reasoning agents capable of operating authorized web browsers and shell environments to conduct multi-step investigations autonomously.

## Architecture
```
┌─────────────────────────────────────────────────────────────┐
│                    Presentation Layer                       │
│                 Next.js / React / Zustand                   │
│              react-force-graph (Knowledge Graph)            │
├─────────────────────────────────────────────────────────────┤
│                   API Gateway & Auth                        │
│               FastAPI + JWT + RBAC                          │
├─────────────────────────────────────────────────────────────┤
│                 Orchestration Layer                         │
│         LangGraph (State Machine) + Temporal (Phase 2)     │
├────────────┬───────────────┬────────────────────────────────┤
│  Browser   │  Shell        │  MCP Tool                     │
│  Worker    │  Sandbox      │  Registry                     │
│ (Playwright│ (Docker +     │ (JSON-RPC 2.0)               │
│  browser-  │  seccomp)     │                               │
│  use)      │               │                               │
├────────────┴───────────────┴────────────────────────────────┤
│                 Database & Storage                          │
│     PostgreSQL + Apache AGE │ MinIO/S3 (Evidence)          │
└─────────────────────────────────────────────────────────────┘
```

## Security: DualView Pattern
```
┌─────────────────────┐     ┌─────────────────────┐
│  Privileged Planner │     │ Quarantined         │
│  LLM                │     │ Extractor LLM       │
│                     │     │                     │
│  ✅ Tool access     │     │  ❌ NO tool access   │
│  ✅ Planning        │     │  ✅ Reads raw data   │
│  ❌ NO raw web data │     │  ✅ Outputs JSON     │
│                     │     │  only               │
└─────────────────────┘     └─────────────────────┘
```

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Node.js 18+
- Python 3.11+

### Development Setup
```bash
# Start infrastructure (PostgreSQL + AGE, MinIO, Redis)
docker-compose up -d postgres minio redis

# Backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend (coming in Slice 7)
cd frontend
npm install
npm run dev
```

### Run Tests
```bash
cd backend
pytest tests/ -v
```

## API Documentation
Once the backend is running, visit:
- Swagger UI: http://localhost:8000/api/docs
- ReDoc: http://localhost:8000/api/redoc

## Project Structure
```
├── backend/
│   ├── app/
│   │   ├── agent/          # LangGraph investigation agent
│   │   │   ├── graph.py    # State machine (Plan→Execute→Extract→Graph→Evaluate)
│   │   │   ├── tools.py    # MCP tool registry
│   │   │   ├── extractor.py # Quarantined Extractor (DualView)
│   │   │   ├── normalizer.py # Entity normalization & deduplication
│   │   │   ├── graph_store.py # Knowledge graph storage
│   │   │   └── runner.py   # Investigation lifecycle runner
│   │   ├── api/            # FastAPI routes
│   │   ├── auth/           # JWT authentication & RBAC
│   │   ├── db/             # Database engine & migrations
│   │   ├── models/         # SQLAlchemy models
│   │   ├── schemas/        # Pydantic validation schemas
│   │   ├── config.py       # Application configuration
│   │   └── main.py         # FastAPI application
│   ├── tests/              # Test suite
│   ├── alembic/            # Database migrations
│   └── Dockerfile
├── frontend/               # Next.js (Slice 7)
├── docs/                   # Documentation
│   ├── BUILD_STATUS.md
│   ├── TASKS.md
│   └── DECISIONS.md
├── docker-compose.yml      # Development infrastructure
└── PRD.docx, Design.docx, techstack.docx
```

## License
Proprietary — ZAPRICA
