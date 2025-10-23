# tools.py
from langchain.tools import tool
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
import requests
import os
from agent.assets import system_msg
from dotenv import load_dotenv

########  tools ###########

@tool
def fetch_local_site(path: str) -> str:
   """Fetch HTML content from the local site on localhost:8000.""" # create and run your local host before running this!
   base_url = "http://127.0.0.1:8000"
   url = f"{base_url}/{path}".rstrip('/')
   r = requests.get(url)
   r.raise_for_status()
   return r.text

def call_agent(user_input):
   # Initialize LLM
   load_dotenv()
   api = os.getenv('OPENAI_API_KEY')
   llm = ChatOpenAI(model="gpt-5", temperature=0)
   tools = [fetch_local_site]
   graph = create_agent(llm, tools)
   final_state = graph.invoke({
   "messages": [
      system_msg, 
      {"role": "user", "content": user_input}
      ]
      })
   last = final_state["messages"][-1]
   return last.content
   


####### agent #########

# Initialize LLM
load_dotenv()
api = os.getenv('OPENAI_API_KEY')
llm = ChatOpenAI(model="gpt-5", temperature=0)

# tools
tools = [fetch_local_site]

# LangGraph ReAct-style agent
graph = create_agent(llm, tools)

# User request
user_input = "how many days can i take off?"

final_state = graph.invoke({
   "messages": [
      system_msg, 
      {"role": "user", "content": user_input}
      ]
      })

# final message
print("\n=== Agent Output ===")
last = final_state["messages"][-1]
print(last.content)  # <-- not subscriptable; use attribute
print("=== === === ===\n")
 