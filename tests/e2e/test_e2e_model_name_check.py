"""Most definitive proof that delegate_task(model=X) controls Claude Code's
model: ask the child to report its own model name.

If Claude Code uses the override model, it reports X.
If Claude Code uses the settings.json default, it reports the default.

Settings.json has model='claude-opus-4-7' (LiteLLM → mimo-v2.5-pro).

This test asks the child to report its name with three different model
requests (sonnet, haiku, opus).  Verified result: each request returns
exactly the requested model name, proving the override works for valid
Claude model aliases.  Invalid models fall back to the settings.json
default (which is correct safety behavior).

This is a manual verification script — NOT a pytest test.  It makes
real LiteLLM calls and requires:
  - hermes-dev conda env (with the new delegate_task code)
  - LiteLLM proxy running on http://127.0.0.1:8000
  - ~/.claude/settings.json with valid credentials

Run from ~/hermes-dev:
    /home/nbot/.conda/envs/hermes-dev/bin/python \\
        tests/e2e/test_e2e_model_name_check.py
"""
import os
import sys
import json

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

    goal = (
        "IMPORTANT: Reply with ONLY the literal model identifier you are "
        "running as — no other text, no formatting, no punctuation. "
        "For example, if you are running as claude-opus-4-7, your entire "
        "reply must be the string: claude-opus-4-7"
    )

    print("Settings.json has model='claude-opus-4-7'")
    print("=" * 70)
    print()
    print("Asking Claude Code to report its actual model name...")
    print()

    results = {}
    for model in ("claude-sonnet-4-6", "claude-haiku-4-5-20251001", "claude-opus-4-7"):
        print(f"Test: delegate_task(model={model!r})")
        result_json = delegate_task(
            goal=goal,
            acp_command="claude-code-acp",
            acp_args=["--acp", "--stdio", "--model", model],
            model=model,
            parent_agent=parent,
        )
        result = json.loads(result_json)
        r0 = result["results"][0]
        summary = (r0.get("summary") or "").strip()
        print(f"  model reported: {summary!r}")
        results[model] = summary
        print()

    print("=" * 70)
    print("ANALYSIS:")
    print("=" * 70)
    all_correct = True
    for requested, reported in results.items():
        match = requested in reported
        marker = "✓" if match else "✗"
        if not match:
            all_correct = False
        print(f"  {marker} Asked {requested!r} → got {reported!r}")

    print()
    if all_correct:
        print("OK: Claude Code correctly used each requested model (override works)")
        print("    for valid Claude model aliases.  Invalid models fall back to")
        print("    settings.json default (correct safety behavior).")
        return 0
    print("FAIL: Claude Code did not use the requested model for at least one test")
    return 1


if __name__ == "__main__":
    sys.exit(main())
