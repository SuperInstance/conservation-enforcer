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

from dataclasses import dataclass
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
    ):
        self.vm = VM()
        self.policy = policy_bytecode
        self.budget = budget
        self.correction_template = correction_template

    def enforce(self, input_text: str, output_text: str) -> EnforcementResult:
        """Check an LLM output against conservation laws."""
        self.vm.load_input(input_text)
        self.vm.load_output(output_text)
        self.vm.set_budget(self.budget)

        result_code = self.vm.run(self.policy)  # 0 = allow, non-zero = block

        if result_code == 0:
            return EnforcementResult(
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
            return EnforcementResult(
                allowed=False,
                output=correction,
                violation=violation,
                cycles=self.vm.cycle_count,
            )

    def enforce_with_llm(
        self,
        input_text: str,
        llm_call: Callable[[str], str],
    ) -> EnforcementResult:
        """Call the LLM and enforce in one step."""
        output = llm_call(input_text)
        return self.enforce(input_text, output)
