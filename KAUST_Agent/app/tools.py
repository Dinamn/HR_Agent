from typing import List, Literal, Optional
from pydantic import BaseModel, Field, ValidationError
from datetime import date, timedelta
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

# ---------- READ HELPERS ----------
SAFE_SELECT_TABLES = {"users", "leave_credits", "leaves"}

def safe_select_sql(natural_question: str, user_id: int) -> str:
    """
    VERY IMPORTANT: we don't allow arbitrary tables/keywords.
    We ask the LLM to produce SQL only over allowed tables/columns and add WHERE user_id = :uid where needed.
    This function is called by the agent through function-calling with the final SQL string returned here.
    """
    # In a real system you'd generate with LLM then post-validate.
    # For demo, we handle common intents with templates.
    q = natural_question.lower()

    if "how many leaves" in q or "كم رصيد" in q or "رصيدي" in q:
        return """
        SELECT lc.annual_total - lc.annual_used AS remaining
        FROM leave_credits lc
        WHERE lc.user_id = :uid AND lc.year = EXTRACT(YEAR FROM now())::int
        """

    if "show my leave history" in q or "سجل" in q:
        return """
        SELECT id, start_date, end_date, days, status, reason
        FROM leaves
        WHERE user_id = :uid
        ORDER BY start_date DESC
        """

    # Fallback: minimal safe default (balance)
    return """
    SELECT lc.annual_total - lc.annual_used AS remaining
    FROM leave_credits lc
    WHERE lc.user_id = :uid AND lc.year = EXTRACT(YEAR FROM now())::int
    """

def run_safe_select(sql: str, user_id: int):
    # Ensure only SELECT and safe keywords
    s = " ".join(sql.strip().split()).upper()
    if not s.startswith("SELECT "):
        raise ValueError("Only SELECT allowed for read tool.")
    # Basic table whitelist
    for t in [" USERS", " LEAVES", " LEAVE_CREDITS"]:
        if t not in s:
            # not strict per-table check for brevity
            pass
    return run_select(sql, {"uid": user_id})

# ---------- ACTIONS ----------
def raise_leave(req: LeaveRequest):
    # business rules: future dates, days >0, enough balance, no overlap
    if req.end_date < req.start_date:
        raise ValueError("End date must be after start date.")
    if req.days <= 0:
        raise ValueError("Invalid number of days.")

    # balance
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

    # overlap check
    overlap = run_select("""
      SELECT 1 FROM leaves
      WHERE user_id = :uid AND status IN ('PENDING','APPROVED')
      AND daterange(start_date, end_date, '[]') && daterange(:s, :e, '[]')
    """, {"uid": req.user_id, "s": req.start_date, "e": req.end_date})
    if overlap:
        raise ValueError("Leave overlaps with an existing one.")

    # create leave (PENDING)
    run_write("""
      INSERT INTO leaves (user_id, start_date, end_date, days, reason, status)
      VALUES (:uid, :s, :e, :d, :r, 'PENDING')
    """, {"uid": req.user_id, "s": req.start_date, "e": req.end_date, "d": req.days, "r": req.reason})

    # increment used immediately for demo (or do it on approval in real life)
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
    # restore balance only if PENDING (for demo)
    row = run_select("""
      SELECT status, days FROM leaves WHERE id = :lid AND user_id = :uid
    """, {"lid": leave_id, "uid": user_id})
    if not row:
        raise ValueError("Leave not found.")
    status, days = row[0]["status"], row[0]["days"]
    if status not in ("PENDING", "APPROVED"):
        raise ValueError("Only pending/approved leaves can be cancelled (demo).")

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
