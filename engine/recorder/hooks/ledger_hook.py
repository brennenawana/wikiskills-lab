#!/usr/bin/env python3
"""Claude Code hook -> action ledger.

Receives one hook event as JSON on stdin (PreToolUse, PostToolUse, Stop, ...)
and appends one scrubbed row to the actions ledger. Standard library only.

Install: see hooks/README.md. The ledger file path is the first argument;
if omitted, $WIKISKILLS_LEDGER_FILE; if that is unset, no row is written.

This script NEVER blocks or alters the observed agent: every failure path
exits 0 with no output. Observation must not change behavior.
"""

import datetime
import json
import os
import re
import sys

MAX_DETAIL = 600
SECRET_PATTERNS = [
    (re.compile(r"(?i)bearer\s+[A-Za-z0-9._~+/=\-]{8,}"), "Bearer [SCRUBBED]"),
    (re.compile(r"\bsk-[A-Za-z0-9_\-]{8,}"), "[SCRUBBED]"),
    (re.compile(r"\bghp_[A-Za-z0-9]{20,}"), "[SCRUBBED]"),
    (re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}"), "[SCRUBBED]"),
    (re.compile(r"\bxox[baprs]-[A-Za-z0-9\-]{10,}"), "[SCRUBBED]"),
    (re.compile(
        r'(?i)("(?:api[-_]?key|apikey|token|secret|password|authorization)"'
        r'\s*:\s*")[^"]{4,}(")'), r"\1[SCRUBBED]\2"),
]


def scrub(text):
    for pat, rep in SECRET_PATTERNS:
        text = pat.sub(rep, text)
    return text


def main():
    try:
        ledger = (sys.argv[1] if len(sys.argv) > 1
                  else os.environ.get("WIKISKILLS_LEDGER_FILE"))
        if not ledger:
            return
        event = json.load(sys.stdin)
        detail = event.get("tool_input")
        if detail is None:
            detail = event.get("tool_response")
        detail_text = scrub(json.dumps(detail, ensure_ascii=False))[:MAX_DETAIL] \
            if detail is not None else None
        row = {
            "v": 1,
            "ts": datetime.datetime.now(datetime.timezone.utc)
                  .isoformat(timespec="milliseconds"),
            "event": event.get("hook_event_name"),
            "session": event.get("session_id"),
            "tool": event.get("tool_name"),
            "detail": detail_text,
        }
        os.makedirs(os.path.dirname(os.path.abspath(ledger)), exist_ok=True)
        with open(ledger, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
            fh.flush()
            os.fsync(fh.fileno())
    except Exception:
        pass  # never block the observed agent
    finally:
        sys.exit(0)


if __name__ == "__main__":
    main()
