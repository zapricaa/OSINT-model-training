"""Investigation Runner — Orchestrates the LangGraph agent lifecycle.

Manages the investigation from start to finish:
1. Load investigation from database
2. Initialize agent state
3. Run the LangGraph state machine
4. Persist results back to database
"""

import time
import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import async_session_factory
from app.models.models import (
    Investigation, InvestigationStatus, InvestigationStep
)
from app.agent.graph import build_investigation_graph, InvestigationState

logger = logging.getLogger("zaprica.agent.runner")


async def run_investigation(investigation_id: str):
    """Run an investigation through the LangGraph state machine.

    This is the main entry point called from the background task.
    """
    logger.info(f"Starting investigation: {investigation_id}")

    async with async_session_factory() as db:
        # Load investigation
        result = await db.execute(
            select(Investigation).where(Investigation.id == investigation_id)
        )
        investigation = result.scalar_one_or_none()

        if not investigation:
            logger.error(f"Investigation not found: {investigation_id}")
            return

        if investigation.status == InvestigationStatus.CANCELLED:
            logger.info(f"Investigation {investigation_id} was cancelled before starting")
            return

        # Mark as started
        investigation.status = InvestigationStatus.PLANNING
        investigation.started_at = datetime.now(timezone.utc)
        await db.commit()

    # Build initial state
    initial_state: InvestigationState = {
        "investigation_id": investigation_id,
        "case_id": str(investigation.case_id),
        "seed_type": investigation.seed_type,
        "seed_value": investigation.seed_value,
        "plan": [],
        "current_plan_index": 0,
        "iteration": 0,
        "max_iterations": investigation.max_iterations,
        "tool_call_count": 0,
        "max_tool_calls": investigation.max_tool_calls,
        "max_time_seconds": investigation.max_time_seconds,
        "start_time": time.time(),
        "current_tool": "",
        "current_tool_input": {},
        "raw_tool_output": "",
        "extracted_entities": [],
        "extracted_edges": [],
        "known_entities": [],
        "unexplored_entities": [],
        "explored_entity_keys": [],
        "should_continue": True,
        "termination_reason": "",
        "errors": [],
        "consecutive_errors": 0,
        "status": "starting",
        "step_log": [],
    }

    # Build the LangGraph and run
    graph = build_investigation_graph()
    step_number = 0

    try:
        # Stream through graph states for observability
        final_state = None
        for state_update in graph.stream(initial_state):
            # state_update is a dict with node_name -> state
            for node_name, state in state_update.items():
                final_state = state
                step_number += 1

                # Persist step to database
                await _persist_step(
                    investigation_id=investigation_id,
                    step_number=step_number,
                    node_name=node_name,
                    state=state,
                )

                # Update investigation status
                await _update_investigation_status(
                    investigation_id=investigation_id,
                    state=state,
                    step_number=step_number,
                )

        # Mark as completed
        await _complete_investigation(
            investigation_id=investigation_id,
            final_state=final_state,
        )

    except Exception as e:
        logger.error(f"Investigation {investigation_id} failed: {e}", exc_info=True)
        await _fail_investigation(investigation_id, str(e))


async def _persist_step(
    investigation_id: str,
    step_number: int,
    node_name: str,
    state: dict,
):
    """Persist an investigation step to the database."""
    async with async_session_factory() as db:
        step = InvestigationStep(
            investigation_id=investigation_id,
            step_number=step_number,
            step_type=node_name,
            tool_name=state.get("current_tool", ""),
            tool_input=state.get("current_tool_input", {}),
            tool_output={"preview": state.get("raw_tool_output", "")[:1000]}
            if state.get("raw_tool_output") else None,
            entities_extracted=state.get("extracted_entities", []),
            edges_created=state.get("extracted_edges", []),
            status=state.get("status", "unknown"),
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
        )
        db.add(step)
        await db.commit()


async def _update_investigation_status(
    investigation_id: str,
    state: dict,
    step_number: int,
):
    """Update investigation status in the database."""
    status_map = {
        "planning": InvestigationStatus.PLANNING,
        "executing": InvestigationStatus.EXECUTING,
        "extracting": InvestigationStatus.EXTRACTING,
        "normalizing": InvestigationStatus.GRAPHING,
        "graphing": InvestigationStatus.GRAPHING,
        "evaluating": InvestigationStatus.EVALUATING,
    }

    async with async_session_factory() as db:
        result = await db.execute(
            select(Investigation).where(Investigation.id == investigation_id)
        )
        investigation = result.scalar_one_or_none()
        if investigation:
            new_status = status_map.get(state.get("status", ""))
            if new_status:
                investigation.status = new_status
            investigation.current_step = state.get("status", "")
            investigation.iteration_count = state.get("iteration", 0)
            investigation.tool_call_count = state.get("tool_call_count", 0)
            investigation.entity_count = len(state.get("known_entities", []))
            investigation.plan = state.get("plan", [])
            await db.commit()


async def _complete_investigation(investigation_id: str, final_state: dict):
    """Mark an investigation as completed."""
    async with async_session_factory() as db:
        result = await db.execute(
            select(Investigation).where(Investigation.id == investigation_id)
        )
        investigation = result.scalar_one_or_none()
        if investigation:
            investigation.status = InvestigationStatus.COMPLETED
            investigation.completed_at = datetime.now(timezone.utc)
            investigation.findings_summary = (
                f"Investigation completed. "
                f"Reason: {final_state.get('termination_reason', 'unknown')}. "
                f"Entities discovered: {len(final_state.get('known_entities', []))}. "
                f"Tool calls: {final_state.get('tool_call_count', 0)}. "
                f"Iterations: {final_state.get('iteration', 0)}."
            )
            if final_state:
                investigation.entity_count = len(final_state.get("known_entities", []))
                investigation.edge_count = len(final_state.get("step_log", []))
            await db.commit()
            logger.info(f"Investigation {investigation_id} completed successfully")


async def _fail_investigation(investigation_id: str, error_message: str):
    """Mark an investigation as failed."""
    async with async_session_factory() as db:
        result = await db.execute(
            select(Investigation).where(Investigation.id == investigation_id)
        )
        investigation = result.scalar_one_or_none()
        if investigation:
            investigation.status = InvestigationStatus.FAILED
            investigation.completed_at = datetime.now(timezone.utc)
            investigation.error_message = error_message
            investigation.error_count = (investigation.error_count or 0) + 1
            await db.commit()
            logger.error(f"Investigation {investigation_id} marked as failed: {error_message}")
