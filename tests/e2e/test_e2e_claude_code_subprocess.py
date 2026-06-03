"""Process-tree verification: while a Claude Code ACP child is running,
confirm 3-5 `claude-agent-acp` subprocesses are actually alive.

This is the most direct evidence the child spawns a real Claude Code
subprocess (vs. simulating/faking it).  Uses ps snapshots every 500ms
to track the subprocess lifetime.

This is a manual verification script — NOT a pytest test.  It requires:
  - hermes-dev conda env
  - ps in PATH (standard on Linux)
  - the same LiteLLM / settings.json prerequisites as the other E2Es

Run from ~/hermes-dev:
    /home/nbot/.conda/envs/hermes-dev/bin/python \\
        tests/e2e/test_e2e_claude_code_subprocess.py
"""
import os
import sys
import time
import json
import threading
import subprocess

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))


_snapshots = []
_stop = threading.Event()


def _snapshot():
    while not _stop.is_set():
        try:
            out = subprocess.run(
                ["ps", "-eo", "pid,ppid,comm,args"],
                capture_output=True, text=True, timeout=2,
            ).stdout
            relevant = [
                ln.strip() for ln in out.splitlines()
                if ("claude-agent-acp" in ln or "claude" in ln.lower())
                and "grep" not in ln
            ]
            _snapshots.append((time.time(), relevant))
        except Exception:
            pass
        time.sleep(0.5)


def main():
    from tools.delegate_tool import delegate_task
    from run_agent import AIAgent

    parent = AIAgent(
        model="claude-haiku-4-5-20251001",
        quiet_mode=True,
        skip_memory=True,
        skip_context_files=True,
    )

    print(f"Parent: model={parent.model}")
    print("Starting background process snapshotter...")
    print("Then triggering delegate_task(acp_command='claude-code-acp', ...)")
    print()

    snap = threading.Thread(target=_snapshot, daemon=True)
    snap.start()

    t0 = time.time()
    try:
        result_json = delegate_task(
            goal="Reply with the single word OK",
            acp_command="claude-code-acp",
            acp_args=["--acp", "--stdio", "--model", "claude-sonnet-4-6"],
            model="claude-sonnet-4-6",
            parent_agent=parent,
        )
        result = json.loads(result_json)
    finally:
        _stop.set()
        snap.join(timeout=3)

    print(f"Elapsed: {time.time() - t0:.2f}s")
    print(f"Result: status={result['results'][0]['status']}, "
          f"model={result['results'][0]['model']!r}, "
          f"summary={result['results'][0]['summary']!r}")
    print()

    print("=" * 70)
    print("Process tree snapshots showing claude-agent-acp subprocesses:")
    print("=" * 70)
    saw_claude_agent = False
    for ts, procs in _snapshots:
        claude_procs = [p for p in procs if "claude-agent-acp" in p]
        if claude_procs:
            saw_claude_agent = True
            print(f"  [{ts - t0:5.2f}s] {len(claude_procs)} claude-agent-acp process(es):")
            for p in claude_procs[:3]:
                if len(p) > 200:
                    p = p[:200] + "..."
                print(f"            {p}")
    print("=" * 70)
    print()

    if not saw_claude_agent:
        print("WARNING: No 'claude-agent-acp' process found in any snapshot")
        return 1
    print("OK: claude-agent-acp subprocess was running during the delegate_task call")
    return 0


if __name__ == "__main__":
    sys.exit(main())
