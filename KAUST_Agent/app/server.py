from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi.staticfiles import StaticFiles

from .agent import agent_respond
from .db import run_select, run_write

app = FastAPI(title="HR Agent")

# Serve the /ui folder (static mock SAP pages)
app.mount("/ui", StaticFiles(directory="ui", html=True), name="ui")


# ----------------------------
# Models
# ----------------------------

class ChatIn(BaseModel):
    user: str
    text: str
    session: str | None = None


class LeaveUsedUpdate(BaseModel):
    annual_used: int


class LeaveCreate(BaseModel):
    start_date: str  # "YYYY-MM-DD"
    end_date: str    # "YYYY-MM-DD"
    days: int
    reason: Optional[str] = None


# ----------------------------
# Helpers
# ----------------------------

def resolve_user(username: str) -> int:
    row = run_select("SELECT id FROM users WHERE username=:u", {"u": username})
    if not row:
        raise HTTPException(status_code=404, detail=f"User '{username}' not found")
    return int(row[0]["id"])


def compute_profile_completeness(user_row: Dict[str, Any]) -> Dict[str, Any]:
    # Hard-coded for mock SAP demo
    return {
        "percent": 0,
        "missing_fields": []
    }


# ----------------------------
# Chat
# ----------------------------

@app.post("/chat")
def chat(inp: ChatIn):
    uid = resolve_user(inp.user)
    thread_id = f"user:{uid}:{inp.session or 'default'}"
    reply = agent_respond(inp.text, uid, thread_id=thread_id)
    return {"reply": reply}


# ----------------------------
# Existing quick user endpoint
# ----------------------------

@app.get("/whoami/{username}")
def whoami(username: str):
    uid = resolve_user(username)
    me = run_select("SELECT * FROM users WHERE id=:uid", {"uid": uid})
    return me[0]


# ----------------------------
# Leave balance API (your original)
# ----------------------------

@app.get("/api/leave-balance/{username}")
def get_leave_balance(username: str):
    uid = resolve_user(username)
    year = datetime.now().year

    rows = run_select(
        """
        SELECT annual_total, annual_used
        FROM leave_credits
        WHERE user_id=:uid AND year=:year
        ORDER BY id DESC
        LIMIT 1
        """,
        {"uid": uid, "year": year},
    )

    if not rows:
        return {
            "username": username,
            "user_id": uid,
            "year": year,
            "annual_total": 0,
            "annual_used": 0,
            "remaining": 0,
            "note": "No leave_credits row found for this user/year.",
        }

    annual_total = int(rows[0]["annual_total"])
    annual_used = int(rows[0]["annual_used"])
    remaining = annual_total - annual_used

    return {
        "username": username,
        "user_id": uid,
        "year": year,
        "annual_total": annual_total,
        "annual_used": annual_used,
        "remaining": remaining,
    }


@app.post("/api/leave-used/{username}")
def set_leave_used(username: str, body: LeaveUsedUpdate):
    uid = resolve_user(username)
    year = datetime.now().year

    existing = run_select(
        "SELECT id FROM leave_credits WHERE user_id=:uid AND year=:year ORDER BY id DESC LIMIT 1",
        {"uid": uid, "year": year},
    )

    if not existing:
        run_write(
            """
            INSERT INTO leave_credits (user_id, year, annual_total, annual_used)
            VALUES (:uid, :year, :total, :used)
            """,
            {"uid": uid, "year": year, "total": 30, "used": body.annual_used},
        )
    else:
        run_write(
            """
            UPDATE leave_credits
            SET annual_used=:used
            WHERE id=:id
            """,
            {"used": body.annual_used, "id": existing[0]["id"]},
        )

    # audit log
    run_write(
        """
        INSERT INTO audit_log (user_id, action, details)
        VALUES (:uid, :action, :details::jsonb)
        """,
        {
            "uid": uid,
            "action": "leave_used_updated",
            "details": f'{{"annual_used": {int(body.annual_used)}, "year": {int(year)}}}',
        },
    )

    return {"ok": True, "username": username, "annual_used": body.annual_used}


# ============================================================
# NEW: Mock SAP Employee File APIs
# ============================================================

@app.get("/api/employees")
def list_employees(q: str | None = None) -> List[Dict[str, Any]]:
    """
    For the top search bar: list employees (optionally filtered).
    """
    if q:
        rows = run_select(
            """
            SELECT username, full_name, employment_title, org_unit, email
            FROM users
            WHERE lower(username) LIKE lower(:q)
               OR lower(full_name) LIKE lower(:q)
               OR lower(email) LIKE lower(:q)
            ORDER BY full_name
            LIMIT 20
            """,
            {"q": f"%{q}%"},
        )
    else:
        rows = run_select(
            """
            SELECT username, full_name, employment_title, org_unit, email
            FROM users
            ORDER BY full_name
            """,
            {},
        )
    return rows


@app.get("/api/employee/{username}")
def employee_summary(username: str) -> Dict[str, Any]:
    """
    Main payload for the Employee File page header + completeness ring.
    """
    uid = resolve_user(username)
    user = run_select("SELECT * FROM users WHERE id=:uid", {"uid": uid})[0]
    completeness = compute_profile_completeness(user)

    # Add "location" like your screenshot (we'll map address -> location)
    user_out = dict(user)
    user_out["location"] = user_out.get("address") or "—"
    user_out["local_time"] = datetime.now().strftime("%A, %I:%M:%S %p")

    return {
        "user": user_out,
        "profile_completeness": completeness,
        "as_of": datetime.now().strftime("%Y-%m-%d"),
    }


@app.get("/api/employee/{username}/employment")
def employee_employment(username: str) -> Dict[str, Any]:
    uid = resolve_user(username)
    u = run_select(
        """
        SELECT username, full_name, contract_type, start_date, employment_title, org_unit, address, direct_manager
        FROM users
        WHERE id=:uid
        """,
        {"uid": uid},
    )[0]
    return {"employment": u}


@app.get("/api/employee/{username}/compensation")
def employee_compensation(username: str) -> Dict[str, Any]:
    uid = resolve_user(username)
    u = run_select(
        """
        SELECT username, full_name, base_salary
        FROM users
        WHERE id=:uid
        """,
        {"uid": uid},
    )[0]
    return {"compensation": u}


@app.get("/api/employee/{username}/history")
def employee_history(username: str) -> Dict[str, Any]:
    uid = resolve_user(username)
    rows = run_select(
        """
        SELECT action, details, created_at
        FROM audit_log
        WHERE user_id=:uid
        ORDER BY created_at DESC
        LIMIT 50
        """,
        {"uid": uid},
    )
    return {"history": rows}


@app.get("/api/employee/{username}/leaves")
def employee_leaves(username: str) -> Dict[str, Any]:
    uid = resolve_user(username)
    rows = run_select(
        """
        SELECT id, start_date, end_date, days, reason, status, created_at
        FROM leaves
        WHERE user_id=:uid
        ORDER BY created_at DESC
        """,
        {"uid": uid},
    )
    return {"leaves": rows}


@app.post("/api/employee/{username}/leaves")
def create_leave_request(username: str, body: LeaveCreate) -> Dict[str, Any]:
    uid = resolve_user(username)

    run_write(
        """
        INSERT INTO leaves (user_id, start_date, end_date, days, reason, status)
        VALUES (:uid, :sd::date, :ed::date, :days, :reason, 'PENDING')
        """,
        {
            "uid": uid,
            "sd": body.start_date,
            "ed": body.end_date,
            "days": int(body.days),
            "reason": body.reason or "",
        },
    )

    run_write(
        """
        INSERT INTO audit_log (user_id, action, details)
        VALUES (:uid, :action, :details::jsonb)
        """,
        {
            "uid": uid,
            "action": "leave_requested",
            "details": f'{{"start_date":"{body.start_date}","end_date":"{body.end_date}","days":{int(body.days)},"reason":"{(body.reason or "").replace("\"","\\\"")}"}}',
        },
    )

    return {"ok": True}
