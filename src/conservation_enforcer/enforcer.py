"""ConservationEnforcer — the main enforcement class.

Wraps any LLM call in a conservation-law check powered by FLUX bytecode.

Usage:
    from conservation_enforcer import ConservationEnforcer, length_budget_policy

    enforcer = ConservationEnforcer(length_budget_policy(max_tokens=500), budget=500)
    result = enforcer.enforce("What is AI?", llm_response)

    if result.allowed:
        return result.output
    else:
        return result.correction
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from .vm import VM


@dataclass
class Violation:
    reason: str
    code: int


@dataclass
class EnforcementResult:
    allowed: bool
    output: str
    violation: Optional[Violation] = None
    cycles: int = 0

    def __bool__(self) -> bool:
        return self.allowed


class ConservationEnforcer:
    """Enforce conservation laws on LLM outputs using FLUX bytecode.

    The bytecode policy is deterministic and auditable. It runs in a
    sandboxed VM and cannot be influenced by the LLM output it checks.

    Convention: R0 = 0 at HALT means ALLOW. R0 ≠ 0 means BLOCK.
    The policy sets R1 and calls SET_VIOLATION (syscall 8) to record the reason.
    """

    def __init__(
        self,
        policy_bytecode: bytes,
        budget: int = 1000,
        correction_template: str = (
            "⚠️ This response was blocked by a conservation law: {reason}. "
            "Please try again with a more conserved response."
        ),
        enable_audit: bool = False,
        audit_path: str = "audit.jsonl",
    ):
        self.vm = VM()
        self.policy = policy_bytecode
        self.budget = budget
        self._initial_budget = budget
        self.correction_template = correction_template
        self._call_count = 0
        self.enable_audit = enable_audit
        self.audit_path = audit_path

    @classmethod
    def from_policy_file(cls, path: str | Path, **kwargs) -> "ConservationEnforcer":
        """Load a policy from a binary file and create an enforcer."""
        path = Path(path)
        with open(path, "rb") as f:
            bytecode = f.read()
        return cls(bytecode, **kwargs)

    def save_policy(self, path: str | Path) -> None:
        """Save the current policy bytecode to a file."""
        with open(path, "wb") as f:
            f.write(self.policy)

    @property
    def call_count(self) -> int:
        return self._call_count

    @property
    def remaining_budget(self) -> int:
        return self.budget

    def replenish_budget(self, amount: int) -> None:
        """Replenish the conservation budget (e.g., after cooldown)."""
        if amount < 0:
            raise ValueError(f"replenish amount must be non-negative, got {amount}")
        self.budget += amount

    def reset_budget(self) -> None:
        """Reset budget to its initial value."""
        self.budget = self._initial_budget

    def enforce(self, input_text: str, output_text: str) -> EnforcementResult:
        """Check an LLM output against conservation laws."""
        self._call_count += 1

        self.vm.load_input(input_text)
        self.vm.load_output(output_text)
        self.vm.set_budget(self.budget)
        self.vm.increment_call_count()

        result_code = self.vm.run(self.policy)  # 0 = allow, non-zero = block

        # Sync budget back from VM (in case DECAY_BUDGET was called)
        self.budget = self.vm._budget

        if result_code == 0:
            result = EnforcementResult(
                allowed=True,
                output=output_text,
                cycles=self.vm.cycle_count,
            )
        else:
            violation = Violation(
                reason=self.vm.violation_reason or "Unknown conservation violation",
                code=result_code,
            )
            correction = self.correction_template.format(reason=violation.reason)
            result = EnforcementResult(
                allowed=False,
                output=correction,
                violation=violation,
                cycles=self.vm.cycle_count,
            )

        # Audit log
        if self.enable_audit:
            self._write_audit(input_text, output_text, result)

        return result

    def enforce_with_llm(
        self,
        input_text: str,
        llm_call: Callable[[str], str],
    ) -> EnforcementResult:
        """Call the LLM and enforce in one step."""
        output = llm_call(input_text)
        return self.enforce(input_text, output)

    def _write_audit(self, input_text: str, output_text: str, result: EnforcementResult) -> None:
        """Write an audit entry to the JSON Lines log."""
        from datetime import datetime, timezone
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "input_hash": hashlib.sha256(input_text.encode()).hexdigest()[:16],
            "output_hash": hashlib.sha256(output_text.encode()).hexdigest()[:16],
            "allowed": result.allowed,
            "violation": result.violation.reason if result.violation else None,
            "violation_code": result.violation.code if result.violation else 0,
            "cycles": result.cycles,
            "remaining_budget": self.budget,
            "call_count": self._call_count,
        }
        with open(self.audit_path, "a") as f:
            f.write(json.dumps(entry) + "\n")
