# eval/run_with_langsmith.py
import os
import requests
from dotenv import load_dotenv
from langsmith.evaluation import evaluate

load_dotenv()

BACKEND = os.getenv("BACKEND_URL", "http://127.0.0.1:8000").rstrip("/")
DATASET = os.getenv("DATASET", "final-ds")              # set to your dataset name in LangSmith
RUN_NAME = os.getenv("RUN_NAME", "final-run-plz")      # will appear in Test Runs

def _extract_inputs(example):
    """Return {user, text, session} from either dict or Example object."""
    if hasattr(example, "inputs"):
        return example.inputs
    if isinstance(example, dict) and "inputs" in example:
        return example["inputs"]
    keys = {"user", "text", "session"}
    if isinstance(example, dict) and keys.issubset(example.keys()):
        return {k: example[k] for k in keys}
    raise ValueError("Could not extract inputs from example")

def call_backend(example, **kwargs):
    payload = _extract_inputs(example)
    r = requests.post(f"{BACKEND}/chat", json=payload, timeout=60)
    r.raise_for_status()
    return r.json().get("reply", "")

from metrics import (
    TaskCompletion,
    ToolSeqPrecision,   # sequence-aware precision
    ToolSeqRecall,      # sequence-aware recall
    ToolSeqF1,          # sequence-aware F1
    LatencyOnly,
)

if __name__ == "__main__":
    print(f"Backend: {BACKEND} | Dataset: {DATASET} | Run: {RUN_NAME}")
    evaluate(
        call_backend,
        data=DATASET,
        experiment_prefix=RUN_NAME,
        evaluators=[
            TaskCompletion(),
            ToolSeqPrecision(),
            ToolSeqRecall(),
            ToolSeqF1(),
            LatencyOnly(),
        ],
    )
