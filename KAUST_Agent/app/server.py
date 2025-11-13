from fastapi import FastAPI, Body
from pydantic import BaseModel
from .agent import agent_respond
from .db import run_select

app = FastAPI(title="HR Agent")

class ChatIn(BaseModel):
  user: str
  text: str
  session: str | None = None  # new

def resolve_user(username: str) -> int:
  row = run_select("SELECT id FROM users WHERE username=:u", {"u": username})
  return row[0]["id"] if row else 1

@app.post("/chat")
def chat(inp: ChatIn):
  uid = resolve_user(inp.user)
  thread_id = f"user:{uid}:{inp.session or 'default'}"
  reply = agent_respond(inp.text, uid, thread_id=thread_id)

  return {"reply": reply}



# Quick health
@app.get("/whoami/{username}")
def whoami(username: str):
  uid = resolve_user(username)
  me = run_select("SELECT * FROM users WHERE id=:uid", {"uid": uid})
  return me[0]
