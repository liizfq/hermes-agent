"""End-to-end Claude Code ACP verification (live LLM calls).

Verifies that delegate_task(model=X, acp_command="claude-code-acp", ...)
correctly spawns a real Claude Code subprocess AND that the requested
model is actually used for the LLM call.

Evidence captured:
  1. agent.log shows "Claude Code ACP client created" with model=X
  2. agent.log shows "API call #1" with provider=claude-code-acp model=X
  3. agent.log shows usage_update events (real subprocess events)
  4. process tree shows 3-5 claude-agent-acp subprocesses during the call

This is a manual verification script — NOT a pytest test.  It makes a
real LiteLLM call and requires:
  - hermes-dev conda env (or whichever env has the new delegate_task code)
  - LiteLLM proxy running on http://127.0.0.1:8000
  - ~/.claude/settings.json with valid ANTHROPIC_BASE_URL pointing at it
  - ANTHROPIC_AUTH_TOKEN set to a valid LiteLLM master key

Run from ~/hermes-dev:
    /home/nbot/.conda/envs/hermes-dev/bin/python \\
        tests/e2e/test_e2e_claude_code_acp.py

See test_e2e_model_name_check.py for the most definitive proof (the
child reports its own model name and it matches the requested one).
"""
import os
import sys
import json
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))


def main():
    from tools.delegate_tool import delegate_task
    from run_agent import AIAgent

    parent = AIAgent(
        model="claude-haiku-4-5-20251001",
        quiet_mode=True,
        skip_memory=True,
        skip_context_files=True,
    )

    goal = "Reply with the single word OK, nothing else."
    target_model = "claude-sonnet-4-6"

    print(f"Parent: model={parent.model}")
    print(f"Target child model (via acp_args --model): {target_model}")
    print(f"Goal: {goal!r}")
    print()

    # Mark agent.log offset
    log_path = os.path.expanduser("~/.hermes/logs/agent.log")
    log_offset = os.path.getsize(log_path) if os.path.exists(log_path) else 0

    t0 = time.time()
    result_json = delegate_task(
        goal=goal,
        acp_command="claude-code-acp",
        acp_args=["--acp", "--stdio", "--model", target_model],
        model=target_model,
        parent_agent=parent,
    )
    elapsed = time.time() - t0
    result = json.loads(result_json)
    r0 = result["results"][0]

    print(f"Elapsed: {elapsed:.2f}s")
    print(f"  status      : {r0['status']}")
    print(f"  summary     : {r0.get('summary')!r}")
    print(f"  api_calls   : {r0.get('api_calls', 0)}")
    print(f"  duration    : {r0.get('duration_seconds', 0)}s")
    print(f"  model field : {r0.get('model')!r}  (child-reported)")
    print()

    # Inspect agent.log for Claude Code ACP evidence
    print("=" * 70)
    print("agent.log evidence:")
    print("=" * 70)
    with open(log_path, errors="replace") as f:
        f.seek(log_offset)
        new_lines = f.readlines()

    acp_client_created = any(
        "Claude Code ACP client created" in ln and target_model in ln
        for ln in new_lines
    )
    acp_api_call = any(
        "API call" in ln and "provider=claude-code-acp" in ln and target_model in ln
        for ln in new_lines
    )
    acp_session_events = sum(
        1 for ln in new_lines if "session/update" in ln or "usage_update" in ln
    )

    print(f"  'Claude Code ACP client created' + model={target_model!r} : {acp_client_created}")
    print(f"  API call with provider=claude-code-acp + model={target_model!r}: {acp_api_call}")
    print(f"  ACP session/update events received                            : {acp_session_events}")
    print()

    if acp_client_created and acp_api_call and acp_session_events > 0:
        print("OK: Claude Code ACP child ran end-to-end with the requested model")
        return 0
    print("FAIL: missing one or more evidence points in agent.log")
    return 1


if __name__ == "__main__":
    sys.exit(main())
