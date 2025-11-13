# eval/metrics.py
from __future__ import annotations
from langsmith.evaluation import RunEvaluator, EvaluationResult
from langsmith.schemas import Run
from typing import List, Dict

# ----------------- helpers -----------------
def _out_text(run: Run) -> str:
    out = (run.outputs or {}).get("output")
    if out is None:
        out = (run.outputs or {}).get("result")
    return out or ""

def _md(example) -> Dict:
    # Works for Example object or plain dict
    return (example.get("metadata") if isinstance(example, dict) else getattr(example, "metadata", {})) or {}

def _norm(name: str) -> str:
    """
    Normalize tool names so expected names match traced names.
    Examples:
      'tools/ReadDB' -> 'readdb'
      'my.pkg.tools.GetLeaveBalance' -> 'getleavebalance'
    """
    if not name:
        return ""
    last = name.split("/")[-1].split(".")[-1]
    return last.strip().lower()

def _executed_tools_sequence(run: Run) -> List[str]:
    """
    Return executed tool names in chronological order, normalized.
    We sort child runs by start time and pick run_type == 'tool'.
    """
    kids = sorted(run.child_runs or [], key=lambda r: (r.start_time or r.end_time))
    seq = []
    for cr in kids:
        if cr.run_type == "tool":
            seq.append(_norm(cr.name or ""))
    return seq

def _lcs_len(a: List[str], b: List[str]) -> int:
    """
    Longest Common Subsequence length (order-sensitive overlap).
    """
    n, m = len(a), len(b)
    dp = [[0]*(m+1) for _ in range(n+1)]
    for i in range(n):
        ai = a[i]
        for j in range(m):
            if ai == b[j]:
                dp[i+1][j+1] = dp[i][j] + 1
            else:
                dp[i+1][j+1] = max(dp[i][j+1], dp[i+1][j])
    return dp[n][m]

def _seq_prf(pred_seq: List[str], gold_seq: List[str]):
    """
    Sequence-aware TP/FP/FN via LCS so order is required for a match.
    """
    tp = _lcs_len(pred_seq, gold_seq)
    fp = max(len(pred_seq) - tp, 0)
    fn = max(len(gold_seq) - tp, 0)

    # Precision / Recall / F1 with standard edge-case handling
    precision = tp / (tp + fp) if (tp + fp) else (1.0 if not pred_seq and not gold_seq else 0.0)
    recall    = tp / (tp + fn) if (tp + fn) else 1.0
    f1        = (2 * precision * recall) / (precision + recall) if (precision + recall) else 1.0
    return precision, recall, f1, tp, fp, fn

# ----------------- 1) Task Completion -----------------
class TaskCompletion(RunEvaluator):
    """
    Pass if final reply contains metadata.expected_reply_contains (case-insensitive).
    """
    def evaluate_run(self, run: Run, example, **kwargs) -> EvaluationResult:
        md = _md(example)
        expected = (md.get("expected_reply_contains") or "").strip()
        out = _out_text(run)
        if not expected:
            return EvaluationResult(key="task_completion", score=1.0, comment="no expected string provided")
        ok = expected.lower() in out.lower()
        return EvaluationResult(
            key="task_completion",
            score=1.0 if ok else 0.0,
            comment=f'expected contains "{expected}"'
        )

# ----------------- 2) Tool Correctness (sequence-aware PRF) -----------------
class ToolSeqPrecision(RunEvaluator):
    """Sequence-aware precision using LCS alignment."""
    def evaluate_run(self, run: Run, example, **kwargs) -> EvaluationResult:
        md = _md(example)
        gold_seq = [ _norm(x) for x in (md.get("expected_tool_names") or []) ]
        pred_seq = _executed_tools_sequence(run)
        p, r, f1, tp, fp, fn = _seq_prf(pred_seq, gold_seq)
        return EvaluationResult(
            key="tool_precision",
            score=p,
            scalar_metrics={"tp": tp, "fp": fp, "fn": fn, "pred_len": len(pred_seq), "gold_len": len(gold_seq)},
            comment=f"pred={pred_seq} gold={gold_seq}"
        )

class ToolSeqRecall(RunEvaluator):
    """Sequence-aware recall using LCS alignment."""
    def evaluate_run(self, run: Run, example, **kwargs) -> EvaluationResult:
        md = _md(example)
        gold_seq = [ _norm(x) for x in (md.get("expected_tool_names") or []) ]
        pred_seq = _executed_tools_sequence(run)
        p, r, f1, tp, fp, fn = _seq_prf(pred_seq, gold_seq)
        return EvaluationResult(
            key="tool_recall",
            score=r,
            scalar_metrics={"tp": tp, "fp": fp, "fn": fn, "pred_len": len(pred_seq), "gold_len": len(gold_seq)},
            comment=f"pred={pred_seq} gold={gold_seq}"
        )

class ToolSeqF1(RunEvaluator):
    """Sequence-aware F1 using LCS alignment (captures extra/missing and wrong order)."""
    def evaluate_run(self, run: Run, example, **kwargs) -> EvaluationResult:
        md = _md(example)
        gold_seq = [ _norm(x) for x in (md.get("expected_tool_names") or []) ]
        pred_seq = _executed_tools_sequence(run)
        p, r, f1, tp, fp, fn = _seq_prf(pred_seq, gold_seq)
        return EvaluationResult(
            key="tool_f1",
            score=f1,
            scalar_metrics={"precision": p, "recall": r, "tp": tp, "fp": fp, "fn": fn,
                            "pred_len": len(pred_seq), "gold_len": len(gold_seq)},
            comment=f"pred={pred_seq} gold={gold_seq}"
        )

# ----------------- 3) Latency -----------------
class LatencyOnly(RunEvaluator):
    """Record latency_ms as scalar (informational)."""
    def evaluate_run(self, run: Run, example, **kwargs) -> EvaluationResult:
        if run.end_time and run.start_time:
            latency_ms = (run.end_time - run.start_time).total_seconds() * 1000
        else:
            latency_ms = -1
        return EvaluationResult(
            key="latency",
            score=1.0,
            scalar_metrics={"latency_ms": latency_ms},
            comment=f"latency_ms={latency_ms}"
        )
