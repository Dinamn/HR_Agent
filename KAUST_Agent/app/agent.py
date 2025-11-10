# app/agent.py
# Agentic HR agent wired with LangGraph, Azure OpenAI, and DB tools.
# - Per-user closures so tools never accept user_id from the model
# - Separate read tools (balance/history/pending/profile)
# - Write tools (raise/cancel/edit)
# - RAG retriever tool (labor law)
# - SQLite checkpointer for per-session memory (thread_id)

import os
import sqlite3
from datetime import date, timedelta
from typing import List, Optional, TypedDict, Annotated

from langchain_openai import AzureChatOpenAI
from langchain.tools import tool
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, BaseMessage

from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langgraph.graph.message import add_messages
from langgraph.checkpoint.sqlite import SqliteSaver

from .prompts import SYSTEM_PROMPT
from .rag_tool import get_retriever_tool
from .tools import (
    # READ helpers (pure functions)
    get_leave_balance_for,
    get_leave_history_for,
    get_pending_leaves_for,
    get_profile_summary_for,
    # ACTION helpers / schemas
    raise_leave,
    cancel_leave,
    ProfileEdit,
    LeaveRequest,
)
from .db import run_select, run_write  # used by EditProfile tool



# -------- LLM (Azure OpenAI) --------
# Uses environment variables:
#   AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_VERSION, AZURE_CHAT_DEPLOYMENT
llm = AzureChatOpenAI(
    azure_deployment=os.getenv("AZURE_CHAT_DEPLOYMENT"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    temperature=0,
)

# -------- Memory (SQLite checkpointer) --------
# Your langgraph version expects a sqlite3.Connection in the ctor.
_sqlite_conn = sqlite3.connect("graph_state.sqlite", check_same_thread=False)
checkpointer = SqliteSaver(_sqlite_conn)


# -------- LangGraph state with message aggregation --------
class AgentState(TypedDict):
    # add_messages makes LangGraph APPEND new messages in order (system → user → ai → tool → ai ...)
    messages: Annotated[List[BaseMessage], add_messages]


def build_graph_for(user_id: int):
    """
    Build a graph where tools CLOSE OVER user_id.
    Tool signatures do NOT include user_id, so the model never sees or passes it.
    """

    # ----- READ TOOLS -----

    @tool("GetLeaveBalance")
    def get_leave_balance_tool():
        """Return remaining leave balance for the current user (this year)."""
        return get_leave_balance_for(user_id)

    @tool("GetLeaveHistory")
    def get_leave_history_tool(limit: int = 20):
        """Return recent leave history for the current user. limit<=100."""
        return get_leave_history_for(user_id, limit=limit)

    @tool("GetPendingLeaves")
    def get_pending_leaves_tool():
        """List pending leave requests for the current user."""
        return get_pending_leaves_for(user_id)

    @tool("GetProfileSummary")
    def get_profile_summary_tool():
        """Return non-sensitive profile info for the current user."""
        return get_profile_summary_for(user_id)

    # ----- WRITE TOOLS -----

    @tool("RaiseLeave")
    def raise_leave_tool(start_date: str, end_date: str = "", days: int = 0, reason: str = ""):
        """
        Create a leave request for the current user.
        Provide EITHER end_date (YYYY-MM-DD) OR days (integer).
        If 'days' is given and end_date is omitted, compute inclusive end_date = start + (days - 1).
        """
        s = date.fromisoformat(start_date)
        if not end_date:
            if days and days > 0:
                e = s + timedelta(days=days - 1)   # inclusive range
                end_date = e.isoformat()
            else:
                raise ValueError("Please provide either 'end_date' or a positive 'days' value.")
        req = LeaveRequest(
            user_id=user_id,
            start_date=s,
            end_date=date.fromisoformat(end_date),
            reason=reason or None,
        )
        return raise_leave(req)

    @tool("CancelLeave")
    def cancel_leave_tool(leave_id: int):
        """Cancel an existing leave if allowed."""
        return cancel_leave(user_id, leave_id)

    @tool("EditProfile")
    def edit_profile_tool(field: str, value: str):
        """Edit allowed fields: address, contact_phone, email, employment_title, org_unit."""
        p = ProfileEdit(user_id=user_id, field=field, value=value)
        p.validate_field()
        # Apply update (parameterized; field name is validated above)
        run_write(f"UPDATE users SET {p.field} = :v WHERE id = :uid", {"v": p.value, "uid": user_id})
        row = run_select(
            "SELECT id, username, full_name, address, contact_phone, email, employment_title, org_unit "
            "FROM users WHERE id=:uid",
            {"uid": user_id},
        )
        return {"ok": True, "profile": row[0] if row else None}

    # ----- RAG TOOL -----
    labor_law_retriever = get_retriever_tool()

    # Bind all tools
    tools = [
        get_leave_balance_tool,
        get_leave_history_tool,
        get_pending_leaves_tool,
        get_profile_summary_tool,
        raise_leave_tool,
        cancel_leave_tool,
        edit_profile_tool,
        labor_law_retriever,
    ]
    llm_with_tools = llm.bind_tools(tools)

    # ----- NODES -----

    def planner_node(state: AgentState):
        """Produce the next assistant message (may include tool calls)."""
        resp = llm_with_tools.invoke(state["messages"])

        # For Logging Tool Chosen By Agent
        if hasattr(resp, "tool_calls") and resp.tool_calls:
            for tool_call in resp.tool_calls:
                name = tool_call.name if hasattr(tool_call, "name") else tool_call.get("name")
                print(f"🔧 Tool: {name}")


        return {"messages": [resp]}  # with add_messages, we only return the new message

    def should_continue(state: AgentState) -> bool:
        last = state["messages"][-1]
        return isinstance(last, AIMessage) and bool(getattr(last, "tool_calls", None))

    # ----- GRAPH WIRING -----
    graph = StateGraph(AgentState)
    graph.add_node("planner", planner_node)
    graph.add_node("tools", ToolNode(tools))
    graph.set_entry_point("planner")
    graph.add_conditional_edges("planner", should_continue, {True: "tools", False: END})
    graph.add_edge("tools", "planner")

    return graph.compile(checkpointer=checkpointer)


def agent_respond(text: str, user_id: int, thread_id: Optional[str] = None) -> str:
    """
    Build a per-user graph, run, and return the final assistant message.
    Uses LangGraph checkpointer memory keyed by thread_id.
    """
    app_graph = build_graph_for(user_id)

    messages: List[BaseMessage] = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=text),
    ]

    # Respect the caller's thread_id; fallback to a deterministic default
    thread_key = thread_id or f"user:{user_id}:default"

    try:
        out = app_graph.invoke(
            {"messages": messages},
            config={
                "recursion_limit": 10,
                "configurable": {"thread_id": thread_key},
            },
        )

        # Return the last assistant message that isn't a tool-call container
        for m in reversed(out["messages"]):
            if isinstance(m, AIMessage) and not getattr(m, "tool_calls", None):
                ind = m.content.find("}")
                trunacted_msg = m.content
                if ind != -1:
                    trunacted_msg = m.content[ind+2:]
                    
        return trunacted_msg
    except Exception as e:
        # Friendly error instead of a 500 from FastAPI
        return f"Error while processing your request: {str(e)}"
