# app/agent.py  — final version with user_id injected via closures + message aggregation fix
import os
from datetime import date, timedelta
from typing import List, TypedDict

# For Python 3.9: Annotated is in typing_extensions
try:
    from typing import Annotated
except ImportError:
    from typing_extensions import Annotated

from langchain_openai import ChatOpenAI
from langchain.tools import tool
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, BaseMessage
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langgraph.graph.message import add_messages

from .prompts import SYSTEM_PROMPT
from .tools import (
    safe_select_sql, run_safe_select, raise_leave, cancel_leave,
    ProfileEdit, LeaveRequest
)

# -------- LLM (selectable via .env) --------
llm = ChatOpenAI(model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"), temperature=0)


# -------- LangGraph state with message aggregator --------
class AgentState(TypedDict):
    # add_messages makes LangGraph APPEND new messages, preserving the correct order
    messages: Annotated[List[BaseMessage], add_messages]


def build_graph_for(user_id: int):
    """
    Build a graph where tools CLOSE OVER user_id.
    Tool signatures do NOT include user_id, so the model never has to pass it.
    """

    @tool("ReadDB")
    def read_db(question: str):
        """Answer HR questions by reading allowed tables for the current user."""
        sql = safe_select_sql(question, user_id)
        rows = run_safe_select(sql, user_id)
        return {"rows": rows}

    @tool("RaiseLeave")
    def raise_leave_tool(start_date: str, end_date: str = "", days: int = 0, reason: str = ""):
        """
    Create a leave request for the current user.
    Provide EITHER end_date (YYYY-MM-DD) OR days (integer).
    If 'days' is given and end_date is omitted, we compute: end_date = start_date + (days - 1).
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
            start_date= s,
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
        from .db import run_write, run_select
        run_write(f"UPDATE users SET {p.field} = :v WHERE id = :uid", {"v": p.value, "uid": user_id})
        row = run_select(
            "SELECT id, username, full_name, address, contact_phone, email, employment_title, org_unit "
            "FROM users WHERE id=:uid",
            {"uid": user_id},
        )
        return {"ok": True, "profile": row[0] if row else None}

    tools = [read_db, raise_leave_tool, cancel_leave_tool, edit_profile_tool]
    llm_with_tools = llm.bind_tools(tools)

    # ---- Nodes ----
    def planner_node(state: AgentState):
        # Produce the next assistant message (may include tool calls)
        resp = llm_with_tools.invoke(state["messages"])
        # With add_messages, return ONLY the new message
        return {"messages": [resp]}

    def should_continue(state: AgentState) -> bool:
        last = state["messages"][-1]
        return isinstance(last, AIMessage) and bool(getattr(last, "tool_calls", None))

    # ---- Graph wiring ----
    graph = StateGraph(AgentState)
    graph.add_node("planner", planner_node)
    graph.add_node("tools", ToolNode(tools))
    graph.set_entry_point("planner")
    graph.add_conditional_edges("planner", should_continue, {True: "tools", False: END})
    graph.add_edge("tools", "planner")
    return graph.compile()


def agent_respond(text: str, user_id: int) -> str:
    """
    Build a per-user graph, run, and return the final assistant message.
    """
    app_graph = build_graph_for(user_id)

    messages: List[BaseMessage] = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=text),
    ]

    try:
        out = app_graph.invoke({"messages": messages}, config={"recursion_limit": 10})
        # Return the last non-tool assistant message
        for m in reversed(out["messages"]):
            if isinstance(m, AIMessage) and not getattr(m, "tool_calls", None):
                return m.content
        return "Done."
    except Exception as e:
        # Friendly error so FastAPI returns 200 with a message instead of a blank 500
        return f"Error while processing your request: {str(e)}"
