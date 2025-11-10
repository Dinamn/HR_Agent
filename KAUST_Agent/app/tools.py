# app/tools.py
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from datetime import date
from .db import run_select, run_write

# ---------- SCHEMAS ----------
ALLOWED_PROFILE_FIELDS = {
    "address", "contact_phone", "email", "employment_title", "org_unit"
}

class LeaveRequest(BaseModel):
    user_id: int
    start_date: date
    end_date: date
    reason: Optional[str] = None

    @property
    def days(self) -> int:
        return (self.end_date - self.start_date).days + 1

class ProfileEdit(BaseModel):
    user_id: int
    field: str
    value: str

    def validate_field(self):
        if self.field not in ALLOWED_PROFILE_FIELDS:
            raise ValueError(f"Field '{self.field}' is not editable.")

# ---------- READ HELPERS (pure functions; no LLM here) ----------
def get_leave_balance_for(user_id: int) -> Dict[str, int]:
    rows = run_select("""
        SELECT lc.annual_total - lc.annual_used AS remaining
        FROM leave_credits lc
        WHERE lc.user_id = :uid AND lc.year = EXTRACT(YEAR FROM now())::int
    """, {"uid": user_id})
    return {"remaining": rows[0]["remaining"] if rows else 0}

def get_leave_history_for(user_id: int, limit: int = 20) -> Dict[str, List[Dict[str, Any]]]:
    lim = max(1, min(int(limit), 100))
    rows = run_select("""
        SELECT id, start_date, end_date, days, status, reason
        FROM leaves
        WHERE user_id = :uid
        ORDER BY start_date DESC
        LIMIT :lim
    """, {"uid": user_id, "lim": lim})
    return {"items": rows}

def get_pending_leaves_for(user_id: int) -> Dict[str, List[Dict[str, Any]]]:
    rows = run_select("""
        SELECT id, start_date, end_date, days, status, reason
        FROM leaves
        WHERE user_id = :uid AND status = 'PENDING'
        ORDER BY start_date DESC
    """, {"uid": user_id})
    return {"items": rows}

def get_profile_summary_for(user_id: int) -> Dict[str, Any]:
    rows = run_select("""
        SELECT id, username, full_name, address, contact_phone, email, employment_title, org_unit
        FROM users WHERE id = :uid
    """, {"uid": user_id})
    return rows[0] if rows else {}

# ---------- ACTIONS (your existing ones; kept, with tiny safety polish) ----------
def raise_leave(req: LeaveRequest):
    if req.end_date < req.start_date:
        raise ValueError("End date must be after start date.")
    if req.days <= 0:
        raise ValueError("Invalid number of days.")

    bal = run_select("""
      SELECT annual_total, annual_used
      FROM leave_credits
      WHERE user_id = :uid AND year = EXTRACT(YEAR FROM now())::int
    """, {"uid": req.user_id})
    if not bal:
        raise ValueError("No leave credit record found.")
    total, used = bal[0]["annual_total"], bal[0]["annual_used"]
    if used + req.days > total:
        raise ValueError("Not enough leave balance.")

    overlap = run_select("""
      SELECT 1 FROM leaves
      WHERE user_id = :uid AND status IN ('PENDING','APPROVED')
      AND daterange(start_date, end_date, '[]') && daterange(:s, :e, '[]')
    """, {"uid": req.user_id, "s": req.start_date, "e": req.end_date})
    if overlap:
        raise ValueError("Leave overlaps with an existing one.")

    run_write("""
      INSERT INTO leaves (user_id, start_date, end_date, days, reason, status)
      VALUES (:uid, :s, :e, :d, :r, 'PENDING')
    """, {"uid": req.user_id, "s": req.start_date, "e": req.end_date, "d": req.days, "r": req.reason})

    # For demo: deduct immediately; in real life do it on approval
    run_write("""
      UPDATE leave_credits
      SET annual_used = annual_used + :d
      WHERE user_id = :uid AND year = EXTRACT(YEAR FROM now())::int
    """, {"uid": req.user_id, "d": req.days})

    run_write("""
      INSERT INTO audit_log (user_id, action, details)
      VALUES (:uid, 'RAISE_LEAVE', jsonb_build_object('days', :d, 'start', :s, 'end', :e))
    """, {"uid": req.user_id, "d": req.days, "s": req.start_date, "e": req.end_date})

    return {"ok": True, "days": req.days}

def cancel_leave(user_id: int, leave_id: int):
    row = run_select("""
      SELECT status, days FROM leaves WHERE id = :lid AND user_id = :uid
    """, {"lid": leave_id, "uid": user_id})
    if not row:
        raise ValueError("Leave not found.")
    status, days = row[0]["status"], row[0]["days"]
    if status not in ("PENDING", "APPROVED"):
        raise ValueError("Only pending/approved leaves can be cancelled.")

    run_write("""
      UPDATE leaves SET status = 'CANCELLED' WHERE id = :lid AND user_id = :uid
    """, {"lid": leave_id, "uid": user_id})

    run_write("""
      UPDATE leave_credits
      SET annual_used = GREATEST(annual_used - :d, 0)
      WHERE user_id = :uid AND year = EXTRACT(YEAR FROM now())::int
    """, {"uid": user_id, "d": days})

    run_write("""
      INSERT INTO audit_log (user_id, action, details)
      VALUES (:uid, 'CANCEL_LEAVE', jsonb_build_object('leave_id', :lid))
    """, {"uid": user_id, "lid": leave_id})

    return {"ok": True}
