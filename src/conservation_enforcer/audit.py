"""Audit logging for conservation enforcement decisions.

Every enforcement call is logged as a JSON Lines entry with:
    - ISO timestamp
    - Input/output content hashes (privacy-preserving)
    - Policy decision (allow/block)
    - Violation reason and code
    - Conservation budget state
    - VM cycles consumed

This makes conservation enforcement fully auditable — you can prove
your AI behaves within its conservation laws by inspecting the log.

Usage:
    from conservation_enforcer.audit import AuditLog

    audit = AuditLog("enforcement_audit.jsonl")
    audit.log(
        input_text="user question",
        output_text="LLM response",
        allowed=False,
        violation_reason="Length budget exceeded",
        violation_code=1,
        cycles=42,
        remaining_budget=450,
        call_count=3,
    )
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


@dataclass
class AuditEntry:
    """A single audit log entry."""
    timestamp: str
    input_hash: str          # SHA-256 hash of input (first 16 hex chars)
    output_hash: str         # SHA-256 hash of output (first 16 hex chars)
    allowed: bool
    violation: Optional[str]
    violation_code: int
    cycles: int
    remaining_budget: int
    call_count: int

    def to_json(self) -> str:
        return json.dumps(asdict(self))


class AuditLog:
    """JSON Lines audit log for conservation enforcement decisions.

    Each call to `log()` appends one JSON object per line.
    The log is append-only and safe for concurrent single-process use.
    """

    def __init__(self, path: str | Path = "enforcement_audit.jsonl"):
        self.path = Path(path)
        # Ensure parent directory exists
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def log(
        self,
        input_text: str,
        output_text: str,
        allowed: bool,
        violation_reason: Optional[str] = None,
        violation_code: int = 0,
        cycles: int = 0,
        remaining_budget: int = 0,
        call_count: int = 0,
    ) -> AuditEntry:
        """Write an audit entry. Returns the created AuditEntry."""
        entry = AuditEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            input_hash=hashlib.sha256(input_text.encode()).hexdigest()[:16],
            output_hash=hashlib.sha256(output_text.encode()).hexdigest()[:16],
            allowed=allowed,
            violation=violation_reason,
            violation_code=violation_code,
            cycles=cycles,
            remaining_budget=remaining_budget,
            call_count=call_count,
        )
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(entry.to_json() + "\n")
        return entry

    def read_all(self) -> list[dict]:
        """Read all audit entries from the log."""
        if not self.path.exists():
            return []
        entries = []
        with open(self.path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    entries.append(json.loads(line))
        return entries

    def summary(self) -> dict:
        """Return summary statistics over all audit entries."""
        entries = self.read_all()
        if not entries:
            return {
                "total_calls": 0,
                "total_blocked": 0,
                "block_rate": 0.0,
                "total_cycles": 0,
                "avg_cycles": 0.0,
            }
        total = len(entries)
        blocked = sum(1 for e in entries if not e["allowed"])
        total_cycles = sum(e["cycles"] for e in entries)
        violations = {}
        for e in entries:
            if e["violation"]:
                violations[e["violation"]] = violations.get(e["violation"], 0) + 1

        return {
            "total_calls": total,
            "total_blocked": blocked,
            "block_rate": blocked / total if total > 0 else 0.0,
            "total_cycles": total_cycles,
            "avg_cycles": total_cycles / total if total > 0 else 0.0,
            "violation_breakdown": violations,
        }

    def clear(self) -> None:
        """Clear the audit log."""
        self.path.write_text("")
