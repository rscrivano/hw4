"""Append-only audit trail of agent-loop activity -> output/audit_trail.json (Problem 12).

Every agent run adds entries; nothing is ever removed or rewritten:
  user_message  - who asked what (customer id only, never their email), page, source
  tool_call     - tool name, short arguments, short result
  end           - stop reason, model, number of model requests, tokens, duration
  error         - stop reason "error: ..." when the run failed
Also used by the hourly inventory check (event "inventory_check").

The file is one JSON array. Appends are serialized with a lock and written to a temp file that
atomically replaces the old one, so a crash mid-write can't leave a half-written file. If the file
is ever unreadable it is renamed aside (kept, not deleted) and a new array is started.
"""

from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path

AUDIT_PATH = Path(__file__).resolve().parent.parent / "output" / "audit_trail.json"
SHORT = 200  # max characters kept for args / results / messages
_lock = threading.Lock()


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def short(value, limit: int = SHORT) -> str:
    text = value if isinstance(value, str) else json.dumps(value, default=str, ensure_ascii=False)
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def append(entries: list[dict]) -> None:
    """Add entries to the end of the trail. Existing entries are always kept."""
    if not entries:
        return
    with _lock:
        AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
        records: list = []
        if AUDIT_PATH.exists():
            try:
                records = json.loads(AUDIT_PATH.read_text(encoding="utf-8") or "[]")
                if not isinstance(records, list):
                    raise ValueError("audit trail is not a JSON array")
            except (json.JSONDecodeError, ValueError):
                # Never wipe history: keep the unreadable file beside the new one.
                stamp = datetime.now().strftime("%Y%m%d%H%M%S")
                AUDIT_PATH.rename(AUDIT_PATH.with_name(f"audit_trail.corrupt-{stamp}.json"))
                records = []
        records.extend(entries)
        tmp = AUDIT_PATH.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(records, indent=1, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, AUDIT_PATH)


def count() -> int:
    try:
        return len(json.loads(AUDIT_PATH.read_text(encoding="utf-8")))
    except (FileNotFoundError, json.JSONDecodeError):
        return 0
