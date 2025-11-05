from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_openai import ChatOpenAI
from langchain.tools import tool
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from dotenv import load_dotenv
import os, requests
from typing import TypedDict, List, Any
from agent.assets import system_msg


class State(TypedDict):
    messages: List[Any]


@tool
def fetch_local_site(path: str) -> str:
    """Fetch HTML content from the local site on localhost:8000."""
    base_url = "http://127.0.0.1:8000"
    url = f"{base_url}/{path}".rstrip('/')
    print(f"🌐 [Tool] Fetching URL: {url}")  
    r = requests.get(url)
    r.raise_for_status()
    print("✅ [Tool] Fetch complete.")
    return r.text


def route_after_agent(state: State) -> str:
    """
    Decides what node to go to after the agent runs.
    If the LLM wants to call a tool → go to 'tools'.
    Otherwise → END.
    """
    last_msg = state["messages"][-1]
    finish_reason = getattr(last_msg, "response_metadata", {}).get("finish_reason", "")

    if finish_reason == "stop":
        print("🛑 LLM finished reasoning — END graph.")
        return END
    elif getattr(last_msg, "tool_calls", None):
        print("🔀 [Router] Next node: tools")
        return "tools"
    else:
        print("🟡 No tool calls — END graph.")
        return END


def call_agent(user_input: str):
    load_dotenv()
    os.getenv("OPENAI_API_KEY")

    llm = ChatOpenAI(model="gpt-5", temperature=0).bind_tools([fetch_local_site], tool_choice="auto")

    graph_builder = StateGraph(State)

    # START node 
    def start_node(state):
        print("➡️ START node executing")
        return {
            "messages": [
                SystemMessage(content=system_msg["content"]),
                HumanMessage(content=user_input)
            ]
        }
        

    # AGENT node 
    def agent_node(state):
        print("➡️ Agent node executing")
        messages = state["messages"]
        if not messages:
         raise ValueError("🚨 agent_node received empty messages — aborting early.")
        response = llm.invoke(messages)
        print(f"🧠 Agent replied: {response.content}")
        # --- Require a real tool call ---
        if not getattr(response, "tool_calls", None):
         print("⚠️ No tool_calls found in assistant message.")
        else:
         print(f"🧩 tool_calls detected: {response.tool_calls}")
        messages.append(response)
        return {"messages": messages}

    # TOOLS node 
    def tool_node_with_id(state):
      print("🔧 [ToolNode] Handling tool call...")
      messages = state["messages"]

      # Get last assistant message (must contain tool_calls)
      last_ai = messages[-1]
      tool_call = last_ai.tool_calls[0]
      tool_name = tool_call["name"]
      tool_args = tool_call["args"]
      tool_call_id = tool_call["id"]

      # Run the actual tool
      print(f"🌐 Running {tool_name} with args {tool_args}")
      result = fetch_local_site.invoke(tool_args)

      # Append formatted ToolMessage
      tool_msg = ToolMessage(
          content=result,
          name=tool_name,
          tool_call_id=tool_call_id
      )
      messages.append(tool_msg)

      print("✅ Tool executed and linked with tool_call_id.")
      return {"messages": messages}
    #tool_node = ToolNode([fetch_local_site])
    

    #---------build the graph----------
    #  nodes
    graph_builder.add_node("start", start_node)
    graph_builder.add_node("agent", agent_node)
    graph_builder.add_node("tools", tool_node_with_id)

    #  edges (with proper condition)
    graph_builder.add_edge(START, "start")
    graph_builder.add_edge("start", "agent")
    graph_builder.add_conditional_edges("agent", route_after_agent, { "tools": "tools", END: END })
    graph_builder.add_edge("tools", "agent")

    # --- Entry point ---
    graph_builder.set_entry_point("start")

    # --- Compile and run ---
    print("🧩 Compiling and running graph...")
    graph = graph_builder.compile()
    final_state = graph.invoke({})

    print("🏁 END of execution")
    last_msg = final_state["messages"][-1]
    last_message = getattr(last_msg, "content", str(last_msg))
    print("💬 Final reply:", last_message)
    return last_message

