# tests/e2e/ — Live E2E Verification Scripts

These scripts make **real LLM calls** to verify the new
`delegate_task(model=X, acp_command="claude-code-acp", ...)` API
end-to-end.  They are **NOT** pytest tests — they require live
infrastructure and should be run manually.

## Prerequisites

- `hermes-dev` conda env (or whichever env has the new delegate_task code):
  `/home/nbot/.conda/envs/hermes-dev/bin/python`
- LiteLLM proxy running on `http://127.0.0.1:8000`
- `~/.claude/settings.json` with:
  ```json
  {
    "env": {
      "ANTHROPIC_BASE_URL": "http://127.0.0.1:8000",
      "ANTHROPIC_AUTH_TOKEN": "lzf593777"
    },
    "model": "claude-opus-4-7"
  }
  ```

## Scripts

### `test_e2e_claude_code_acp.py`

Verifies a `delegate_task(...acp_command="claude-code-acp"...)` call
actually creates a Claude Code ACP client and runs the LLM call with
the requested model.  Evidence collected from `~/.hermes/logs/agent.log`:
- `"Claude Code ACP client created"` with `model=<requested>`
- `"API call #1"` with `provider=claude-code-acp`
- `usage_update` events from the subprocess

### `test_e2e_claude_code_subprocess.py`

Process-tree verification: snapshots `ps` every 500ms during the call
and counts `claude-agent-acp` subprocesses.  Direct proof that the child
spawns a real Claude Code subprocess (not a simulation).

### `test_e2e_model_name_check.py` ⭐ (most definitive)

Asks the child Claude Code agent to report its own model name.  If
Claude Code uses the override model, it reports back exactly what we
asked for.  If it ignores the override and uses the settings.json
default (`claude-opus-4-7`), it reports that instead.

Verified result: each requested model is reported back correctly,
proving the override works for valid Claude aliases.  Invalid model
names fall back to the settings.json default (correct safety behavior).

## How to Run

```bash
cd /home/nbot/hermes-dev
/home/nbot/.conda/envs/hermes-dev/bin/python tests/e2e/test_e2e_claude_code_acp.py
/home/nbot/.conda/envs/hermes-dev/bin/python tests/e2e/test_e2e_claude_code_subprocess.py
/home/nbot/.conda/envs/hermes-dev/bin/python tests/e2e/test_e2e_model_name_check.py
```

Each takes ~10-30 seconds and makes 1-3 real LLM calls.

## CI

These scripts are intentionally **not** wired into CI.  They require
real LLM credentials and a live LiteLLM proxy.  The pytest unit +
plumbing E2E tests in `tests/tools/test_delegate.py` (168 passed)
cover the schema, model-flow, and priority-chain logic without needing
a live LLM.
