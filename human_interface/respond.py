from __future__ import annotations

import json

MUTATING_TOOLS = {"create_operation", "update_operation"}


def _format_action(entry: dict) -> str:
    args = ", ".join(f"{k}={v}" for k, v in entry["args"].items() if v is not None)
    return f"{entry['tool']}({args})"


def format_response(run_result: dict) -> str:
    log = run_result.get("tool_log") or []

    tool_errors = [
        e["result"].get("error", "unknown error") for e in log if not e["result"].get("ok")
    ]
    agent_errors: list[str] = []
    if run_result.get("llm_error"):
        agent_errors.append(run_result["llm_error"])
    if run_result.get("limit_exceeded"):
        agent_errors.append("tool-call iteration limit exceeded")

    mutating = [e for e in log if e["tool"] in MUTATING_TOOLS]
    action_entry = (mutating or log or [None])[-1]
    action = _format_action(action_entry) if action_entry else "-"

    ok_entries = [e for e in log if e["result"].get("ok")]
    data = json.dumps(ok_entries[-1]["result"]["data"], ensure_ascii=False) if ok_entries else "-"

    if agent_errors:
        status = "error"
        error_messages = tool_errors + agent_errors
    elif action_entry is not None and action_entry["result"].get("ok"):
        status = "success"
        error_messages = []
    elif log:
        status = "error"
        error_messages = tool_errors
    else:
        status = "error"
        error_messages = [run_result.get("final_text") or "no action performed"]

    errors = "; ".join(error_messages) if error_messages else "-"
    return f"Status: {status}\nAction: {action}\nData: {data}\nErrors: {errors}"
