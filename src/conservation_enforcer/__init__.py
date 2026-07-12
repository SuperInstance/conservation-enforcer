"""Conservation Enforcer — FLUX bytecode governance for LLM outputs.

Implements conservation-law enforcement on AI behavior using deterministic
FLUX bytecode programs as policy layers.

Architecture:
    User Request → LLM Call → [FLUX Conservation Validator] → Response
                                        ↓
                                  If violation: return correction
                                  If clean: return response

The FLUX bytecode acts as a deterministic, auditable policy layer.
You can't lie to bytecode — it doesn't have opinions, it just executes instructions.
"""

from .vm import VM, Op, Syscall, RegisterFile, Memory
from .assembler import assemble
from .enforcer import ConservationEnforcer, EnforcementResult, Violation
from .policies import (
    length_budget_policy,
    repetition_policy,
    category_policy,
    combined_policy,
    entropy_policy,
)

__version__ = "0.1.0"
__author__ = "SuperInstance"
__license__ = "MIT"

__all__ = [
    "VM",
    "Op",
    "Syscall",
    "RegisterFile",
    "Memory",
    "assemble",
    "ConservationEnforcer",
    "EnforcementResult",
    "Violation",
    "length_budget_policy",
    "repetition_policy",
    "category_policy",
    "combined_policy",
    "entropy_policy",
]
