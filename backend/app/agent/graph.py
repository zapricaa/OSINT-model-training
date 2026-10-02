"""ZAPRICA Investigation Agent — LangGraph State Machine.

Implements the core investigation loop:
PLAN → EXECUTE → EXTRACT → NORMALIZE → RESOLVE → GRAPH → EVALUATE → PIVOT OR COMPLETE
"""

from typing import TypedDict, Annotated, Literal, Any
from langgraph.graph import StateGraph, END
import logging

logger = logging.getLogger("zaprica.agent")


class InvestigationState(TypedDict):
    """State managed by the LangGraph investigation loop."""
    # Investigation identity
    investigation_id: str
    case_id: str
    seed_type: str
    seed_value: str

    # Current plan
    plan: list[dict]  # List of planned steps
    current_plan_index: int

    # Iteration tracking
    iteration: int
    max_iterations: int
    tool_call_count: int
    max_tool_calls: int
    max_time_seconds: int
    start_time: float

    # Current step data
    current_tool: str
    current_tool_input: dict
    raw_tool_output: str  # Raw output from tool execution
    extracted_entities: list[dict]  # Entities from Extractor LLM
    extracted_edges: list[dict]  # Edges from Extractor LLM

    # Graph state
    known_entities: list[dict]  # All entities discovered so far
    unexplored_entities: list[dict]  # Entities not yet investigated
    explored_entity_keys: list[str]  # Normalized keys of explored entities

    # Decision
    should_continue: bool
    termination_reason: str

    # Error handling
    errors: list[str]
    consecutive_errors: int

    # Status
    status: str  # Current step name for UI display
    step_log: list[dict]  # Log of all steps taken


def plan_node(state: InvestigationState) -> dict:
    """PLANNER: Generate or update the investigation plan.

    The Privileged Planner LLM determines what tools to call next.
    It NEVER reads raw external web content (DualView pattern).
    """
    logger.info(f"[PLAN] Investigation {state['investigation_id']} - Iteration {state['iteration']}")

    # For MVP: generate a deterministic plan based on seed type
    seed_type = state["seed_type"]
    seed_value = state["seed_value"]
    iteration = state["iteration"]

    if iteration == 0:
        # Initial plan based on seed type
        plan = _generate_initial_plan(seed_type, seed_value)
    else:
        # Re-plan based on unexplored entities
        plan = _generate_pivot_plan(state)

    current_step = plan[0] if plan else None

    return {
        "plan": plan,
        "current_plan_index": 0,
        "current_tool": current_step["tool"] if current_step else "",
        "current_tool_input": current_step["input"] if current_step else {},
        "status": "planning",
    }


def execute_node(state: InvestigationState) -> dict:
    """EXECUTE: Call the selected tool via MCP registry.

    Routes to the appropriate isolated worker (Browser, Shell, API).
    """
    logger.info(
        f"[EXECUTE] Tool: {state['current_tool']} "
        f"Input: {state['current_tool_input']}"
    )

    from app.agent.tools import execute_tool

    tool_name = state["current_tool"]
    tool_input = state["current_tool_input"]

    try:
        result = execute_tool(tool_name, tool_input)
        return {
            "raw_tool_output": result,
            "tool_call_count": state["tool_call_count"] + 1,
            "status": "executing",
            "consecutive_errors": 0,
        }
    except Exception as e:
        error_msg = f"Tool execution failed: {tool_name} — {str(e)}"
        logger.error(error_msg)
        return {
            "raw_tool_output": "",
            "tool_call_count": state["tool_call_count"] + 1,
            "errors": state["errors"] + [error_msg],
            "consecutive_errors": state["consecutive_errors"] + 1,
            "status": "error",
        }


def extract_node(state: InvestigationState) -> dict:
    """EXTRACTOR: Process raw tool output with the Quarantined Extractor LLM.

    The Extractor has ZERO tool-calling privileges.
    It reads untrusted data and outputs structured JSON only.
    This is the DualView security boundary.
    """
    logger.info(f"[EXTRACT] Processing output from {state['current_tool']}")

    raw_output = state["raw_tool_output"]
    if not raw_output:
        return {
            "extracted_entities": [],
            "extracted_edges": [],
            "status": "extracting",
        }

    from app.agent.extractor import extract_entities

    try:
        entities, edges = extract_entities(
            raw_content=raw_output,
            source_tool=state["current_tool"],
            investigation_id=state["investigation_id"],
        )
        return {
            "extracted_entities": entities,
            "extracted_edges": edges,
            "status": "extracting",
        }
    except Exception as e:
        logger.error(f"Extraction failed: {e}")
        return {
            "extracted_entities": [],
            "extracted_edges": [],
            "errors": state["errors"] + [f"Extraction failed: {str(e)}"],
            "status": "extracting",
        }


def normalize_resolve_node(state: InvestigationState) -> dict:
    """NORMALIZE + RESOLVE: Normalize entities and deduplicate.

    - Normalize domain/IP/email to canonical form
    - Check for duplicates against known entities
    - Merge properties if duplicate found
    """
    logger.info(f"[NORMALIZE] Processing {len(state['extracted_entities'])} entities")

    from app.agent.normalizer import normalize_and_resolve

    new_entities, new_edges, updated_known = normalize_and_resolve(
        extracted_entities=state["extracted_entities"],
        extracted_edges=state["extracted_edges"],
        known_entities=state["known_entities"],
        explored_keys=state["explored_entity_keys"],
    )

    # Identify newly discovered entities for potential pivoting
    new_unexplored = [
        e for e in new_entities
        if e.get("normalized_key") not in state["explored_entity_keys"]
    ]

    return {
        "known_entities": updated_known,
        "unexplored_entities": state["unexplored_entities"] + new_unexplored,
        "extracted_entities": new_entities,
        "extracted_edges": new_edges,
        "status": "normalizing",
    }


def graph_node(state: InvestigationState) -> dict:
    """GRAPH: Store entities and edges in PostgreSQL + Apache AGE.

    Also stores evidence with SHA-256 hash and S3 URI.
    """
    logger.info(
        f"[GRAPH] Storing {len(state['extracted_entities'])} entities, "
        f"{len(state['extracted_edges'])} edges"
    )

    from app.agent.graph_store import store_to_graph

    entity_count, edge_count = store_to_graph(
        investigation_id=state["investigation_id"],
        entities=state["extracted_entities"],
        edges=state["extracted_edges"],
        raw_output=state["raw_tool_output"],
        tool_name=state["current_tool"],
    )

    return {
        "status": "graphing",
        "step_log": state["step_log"] + [{
            "iteration": state["iteration"],
            "tool": state["current_tool"],
            "entities_found": len(state["extracted_entities"]),
            "edges_created": len(state["extracted_edges"]),
        }],
    }


def evaluate_node(state: InvestigationState) -> dict:
    """EVALUATE: Decide whether to continue (pivot) or terminate.

    Termination conditions:
    - Max iterations reached
    - Max tool calls reached
    - Max time exceeded
    - No unexplored entities remain
    - Too many consecutive errors
    """
    import time

    logger.info(f"[EVALUATE] Iteration {state['iteration']}, "
                f"Unexplored: {len(state['unexplored_entities'])}")

    elapsed = time.time() - state["start_time"]

    # Check termination conditions
    if state["iteration"] >= state["max_iterations"]:
        return {
            "should_continue": False,
            "termination_reason": f"Max iterations reached ({state['max_iterations']})",
            "status": "evaluating",
        }

    if state["tool_call_count"] >= state["max_tool_calls"]:
        return {
            "should_continue": False,
            "termination_reason": f"Max tool calls reached ({state['max_tool_calls']})",
            "status": "evaluating",
        }

    if elapsed >= state["max_time_seconds"]:
        return {
            "should_continue": False,
            "termination_reason": f"Max time exceeded ({state['max_time_seconds']}s)",
            "status": "evaluating",
        }

    if state["consecutive_errors"] >= 3:
        return {
            "should_continue": False,
            "termination_reason": "Too many consecutive errors (3)",
            "status": "evaluating",
        }

    if not state["unexplored_entities"] and state["iteration"] > 0:
        return {
            "should_continue": False,
            "termination_reason": "No unexplored entities remain",
            "status": "evaluating",
        }

    # Mark current seed as explored
    explored = state["explored_entity_keys"] + [
        f"{state['seed_type']}:{state['seed_value']}"
    ] if state["iteration"] == 0 else state["explored_entity_keys"]

    return {
        "should_continue": True,
        "iteration": state["iteration"] + 1,
        "explored_entity_keys": explored,
        "status": "evaluating",
    }


def should_continue(state: InvestigationState) -> Literal["plan", "complete"]:
    """Routing function: continue investigating or complete."""
    if state.get("should_continue", False):
        return "plan"
    return "complete"


def complete_node(state: InvestigationState) -> dict:
    """COMPLETE: Finalize the investigation."""
    logger.info(
        f"[COMPLETE] Investigation {state['investigation_id']} "
        f"finished. Reason: {state.get('termination_reason', 'unknown')}"
    )
    return {
        "status": "completed",
    }


# ── Plan generation helpers ────────────────────────────────────────────

def _generate_initial_plan(seed_type: str, seed_value: str) -> list[dict]:
    """Generate an initial investigation plan based on seed type.

    For MVP, this is a deterministic plan. With real LLM, the Planner
    would reason about what tools to use.
    """
    plans = {
        "domain": [
            {"tool": "whois_lookup", "input": {"domain": seed_value},
             "description": f"WHOIS lookup for {seed_value}"},
            {"tool": "dns_lookup", "input": {"domain": seed_value, "record_type": "A"},
             "description": f"DNS A record lookup for {seed_value}"},
            {"tool": "dns_lookup", "input": {"domain": seed_value, "record_type": "MX"},
             "description": f"DNS MX record lookup for {seed_value}"},
        ],
        "ip": [
            {"tool": "reverse_dns", "input": {"ip": seed_value},
             "description": f"Reverse DNS lookup for {seed_value}"},
            {"tool": "whois_lookup", "input": {"ip": seed_value},
             "description": f"IP WHOIS lookup for {seed_value}"},
        ],
        "email": [
            {"tool": "email_domain_check", "input": {"email": seed_value},
             "description": f"Domain check for email {seed_value}"},
        ],
        "hash": [
            {"tool": "hash_lookup", "input": {"hash": seed_value},
             "description": f"Hash lookup for {seed_value}"},
        ],
        "person": [
            {"tool": "web_search", "input": {"query": seed_value},
             "description": f"Web search for person: {seed_value}"},
        ],
        "organization": [
            {"tool": "web_search", "input": {"query": seed_value},
             "description": f"Web search for organization: {seed_value}"},
            {"tool": "whois_lookup", "input": {"domain": seed_value},
             "description": f"WHOIS lookup for {seed_value}"},
        ],
    }
    return plans.get(seed_type, [{"tool": "web_search", "input": {"query": seed_value},
                                   "description": f"General search for {seed_value}"}])


def _generate_pivot_plan(state: InvestigationState) -> list[dict]:
    """Generate a pivot plan from unexplored entities.

    For MVP: picks the first unexplored entity and plans appropriate tools.
    With real LLM: the Planner would reason about priority and relevance.
    """
    if not state["unexplored_entities"]:
        return []

    # Pop the first unexplored entity
    entity = state["unexplored_entities"][0]
    entity_type = entity.get("entity_type", "unknown")
    entity_value = entity.get("normalized_value", entity.get("value", ""))

    # Remove it from unexplored
    remaining = state["unexplored_entities"][1:]

    # Map entity type to seed type for planning
    type_map = {
        "Domain": "domain",
        "IP": "ip",
        "Email": "email",
        "FileHash": "hash",
        "Person": "person",
        "Organization": "organization",
    }
    seed_type = type_map.get(entity_type, "domain")

    plan = _generate_initial_plan(seed_type, entity_value)

    # Update unexplored in state (this will be done in evaluate_node actually)
    return plan


# ── Build the Graph ────────────────────────────────────────────────────

def build_investigation_graph() -> StateGraph:
    """Build the LangGraph state machine for the investigation loop."""
    workflow = StateGraph(InvestigationState)

    # Add nodes
    workflow.add_node("plan", plan_node)
    workflow.add_node("execute", execute_node)
    workflow.add_node("extract", extract_node)
    workflow.add_node("normalize_resolve", normalize_resolve_node)
    workflow.add_node("graph", graph_node)
    workflow.add_node("evaluate", evaluate_node)
    workflow.add_node("complete", complete_node)

    # Define edges (the investigation loop)
    workflow.set_entry_point("plan")
    workflow.add_edge("plan", "execute")
    workflow.add_edge("execute", "extract")
    workflow.add_edge("extract", "normalize_resolve")
    workflow.add_edge("normalize_resolve", "graph")
    workflow.add_edge("graph", "evaluate")

    # Conditional: continue or complete
    workflow.add_conditional_edges(
        "evaluate",
        should_continue,
        {
            "plan": "plan",
            "complete": "complete",
        },
    )

    workflow.add_edge("complete", END)

    return workflow.compile()
