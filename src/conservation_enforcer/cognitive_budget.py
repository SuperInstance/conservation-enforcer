"""Cognitive Budget — γ + η = C enforcement for LLM systems.

Implements the cognitive budget conservation law described in
docs/GAMMA_ETA_SPEC.md. Every cognitive system operates under a finite
capacity C, split between:

    γ (gamma) — marked/committed capacity (system prompts, context, framework)
    η (eta)   — unmarked/available capacity (discovery space)

These satisfy the conservation law:  γ + η = C

This module provides measurement, tracking, and alerting so that prompt
construction, model casting, and FLUX policy enforcement can operate
with explicit awareness of the discovery/synthesis trade-off.

Usage:
    from conservation_enforcer.cognitive_budget import CognitiveBudget

    budget = CognitiveBudget(
        context_window=128_000,
        attention_heads=128,
    )
    budget.add_system_prompt("You are a helpful assistant.")
    budget.add_few_shot("Example: ...")

    if budget.is_over_frameworked:
        print(f"Reduce context by {budget.excess_gamma} tokens")

    print(budget.chart_thickness)   # ChartThickness.THIN
    print(f"τ = {budget.tau:.3f}") # γ/C ratio
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import Optional


# ── Token estimation ────────────────────────────────────────────────────────

# Rough token-to-character ratio for mixed English text. Real tokenizers
# vary, but this gives a stable approximation when a tokenizer is not
# available. Callers can override with pre-tokenized counts via
# ``add_framework``.
_CHARS_PER_TOKEN = 4.0


def _estimate_tokens(text: str) -> int:
    """Estimate token count from text length.

    Uses the standard ~4 chars/token heuristic. For precise measurement,
    pass explicit token counts to ``add_framework`` instead.
    """
    if not text:
        return 0
    return max(1, math.ceil(len(text) / _CHARS_PER_TOKEN))


# ── Chart Thickness Classification ───────────────────────────────────────────

class ChartThickness(Enum):
    """Classification of a model configuration by γ/C ratio.

    The thickness bands predict the discovery/synthesis trade-off:
    thinner charts favour discovery (higher η), thicker charts favour
    synthesis (higher γ).
    """

    ULTRA_THIN = "ultra_thin"      # τ < 0.15
    THIN = "thin"                  # 0.15 ≤ τ < 0.30
    BALANCED = "balanced"          # 0.30 ≤ τ ≤ 0.70
    THICK = "thick"                # 0.70 < τ ≤ 0.85
    ULTRA_THICK = "ultra_thick"    # τ > 0.85


# ── Thickness thresholds ────────────────────────────────────────────────────

THIN_THRESHOLD = 0.30        # τ below this = thin chart
THICK_THRESHOLD = 0.70       # τ above this = thick chart
ULTRA_THIN_THRESHOLD = 0.15  # τ below this = ultra-thin
ULTRA_THICK_THRESHOLD = 0.85 # τ above this = ultra-thick

# Default threshold for "over-frameworked" alert.
DEFAULT_OVER_FRAMEWORK_TAU = THICK_THRESHOLD  # 0.70

# Default threshold for "under-structured" alert.
DEFAULT_UNDER_STRUCTURE_TAU = 0.10


@dataclass
class BudgetSnapshot:
    """Immutable point-in-time snapshot of a cognitive budget."""

    capacity: int          # C
    gamma: int             # γ (marked)
    eta: int               # η (unmarked, before output reservation)
    tau: float             # γ/C ratio
    chart_thickness: ChartThickness
    reserved_output: int   # tokens reserved for generation
    effective_eta: int     # η − reserved_output
    is_over_frameworked: bool
    is_under_structured: bool

    def to_dict(self) -> dict:
        return {
            "capacity": self.capacity,
            "gamma": self.gamma,
            "eta": self.eta,
            "tau": round(self.tau, 6),
            "chart_thickness": self.chart_thickness.value,
            "reserved_output": self.reserved_output,
            "effective_eta": self.effective_eta,
            "is_over_frameworked": self.is_over_frameworked,
            "is_under_structured": self.is_under_structured,
        }


class CognitiveBudget:
    """Tracks the γ + η = C cognitive budget for an LLM inference.

    The conservation law γ + η = C is **exact and non-violable**. Every
    token of framework (system prompt, context, few-shot examples)
    increases γ and decreases η by exactly the same amount. This class
    measures that trade-off and provides alerts when the allocation
    becomes pathological for the intended task.

    Parameters
    ----------
    context_window:
        Maximum context window length in tokens (W).
    attention_heads:
        Number of effective attention heads (H).
    reserved_output_tokens:
        Tokens the model needs to reserve for generation. These are
        subtracted from η to give the *effective* discovery capacity.
    head_saturation_factor:
        Multiplier on attention heads to account for effective vs.
        nominal head count (GQA/MQA models have fewer effective heads).
        Defaults to 1.0 (no reduction).
    """

    def __init__(
        self,
        context_window: int,
        attention_heads: int,
        reserved_output_tokens: int = 0,
        head_saturation_factor: float = 1.0,
    ) -> None:
        if context_window <= 0:
            raise ValueError("context_window must be positive")
        if attention_heads <= 0:
            raise ValueError("attention_heads must be positive")
        if reserved_output_tokens < 0:
            raise ValueError("reserved_output_tokens must be non-negative")
        if head_saturation_factor <= 0 or head_saturation_factor > 1.0:
            raise ValueError("head_saturation_factor must be in (0, 1.0]")

        self._context_window = context_window
        self._attention_heads = attention_heads
        self._reserved_output = reserved_output_tokens
        self._head_factor = head_saturation_factor

        # γ components — tracked separately for analysis
        self._gamma_system: int = 0
        self._gamma_fewshot: int = 0
        self._gamma_context: int = 0
        self._gamma_framework: int = 0  # explicit token counts

    # ── Capacity (C) ───────────────────────────────────────────────────

    @property
    def capacity(self) -> int:
        """Total cognitive capacity C = context_window × effective_heads."""
        effective_heads = max(1, int(self._attention_heads * self._head_factor))
        return self._context_window * effective_heads

    # ── Gamma (γ) ──────────────────────────────────────────────────────

    @property
    def gamma(self) -> int:
        """Total marked capacity γ."""
        return (
            self._gamma_system
            + self._gamma_fewshot
            + self._gamma_context
            + self._gamma_framework
        )

    @property
    def gamma_breakdown(self) -> dict[str, int]:
        """Per-component γ breakdown."""
        return {
            "system": self._gamma_system,
            "fewshot": self._gamma_fewshot,
            "context": self._gamma_context,
            "framework": self._gamma_framework,
        }

    # ── Eta (η) ────────────────────────────────────────────────────────

    @property
    def eta(self) -> int:
        """Unmarked capacity η = C − γ.

        This is the raw discovery space before output reservation.
        """
        return max(0, self.capacity - self.gamma)

    @property
    def effective_eta(self) -> int:
        """Discovery capacity after reserving tokens for output generation."""
        return max(0, self.eta - self._reserved_output)

    # ── Conservation Check ─────────────────────────────────────────────

    @property
    def conservation_holds(self) -> bool:
        """Verify that γ + η = C exactly."""
        return self.gamma + self.eta == self.capacity

    # ── Chart Thickness (τ) ────────────────────────────────────────────

    @property
    def tau(self) -> float:
        """Chart thickness ratio τ = γ / C."""
        c = self.capacity
        if c == 0:
            return 0.0
        return self.gamma / c

    @property
    def chart_thickness(self) -> ChartThickness:
        """Classify the current configuration on the discovery/synthesis spectrum."""
        t = self.tau
        if t < ULTRA_THIN_THRESHOLD:
            return ChartThickness.ULTRA_THIN
        elif t < THIN_THRESHOLD:
            return ChartThickness.THIN
        elif t <= THICK_THRESHOLD:
            return ChartThickness.BALANCED
        elif t <= ULTRA_THICK_THRESHOLD:
            return ChartThickness.THICK
        else:
            return ChartThickness.ULTRA_THICK

    # ── Gamma accumulation ─────────────────────────────────────────────

    def add_system_prompt(self, text: str) -> int:
        """Add system prompt text to γ. Returns the token count added."""
        tokens = _estimate_tokens(text)
        self._gamma_system += tokens
        return tokens

    def add_few_shot(self, text: str) -> int:
        """Add few-shot exemplar text to γ. Returns the token count added."""
        tokens = _estimate_tokens(text)
        self._gamma_fewshot += tokens
        return tokens

    def add_context(self, text: str) -> int:
        """Add injected context (RAG, history, tool results) to γ.

        Returns the token count added.
        """
        tokens = _estimate_tokens(text)
        self._gamma_context += tokens
        return tokens

    def add_framework(self, token_count: int) -> int:
        """Add an explicit token count to γ (for pre-tokenized components).

        Use this when you have precise tokenizer counts and want to bypass
        the character-based estimation.
        """
        if token_count < 0:
            raise ValueError("token_count must be non-negative")
        self._gamma_framework += token_count
        return token_count

    # ── Reset ──────────────────────────────────────────────────────────

    def reset_gamma(self) -> None:
        """Reset all γ components to zero."""
        self._gamma_system = 0
        self._gamma_fewshot = 0
        self._gamma_context = 0
        self._gamma_framework = 0

    # ── Alerts ─────────────────────────────────────────────────────────

    @property
    def is_over_frameworked(self) -> bool:
        """True when τ exceeds the thick-chart threshold (too much γ)."""
        return self.tau > DEFAULT_OVER_FRAMEWORK_TAU

    @property
    def is_under_structured(self) -> bool:
        """True when τ is extremely low (too little γ for synthesis tasks)."""
        return self.tau < DEFAULT_UNDER_STRUCTURE_TAU

    @property
    def excess_gamma(self) -> int:
        """Token count to remove from γ to reach τ = 0.70.

        Returns 0 if already at or below the threshold.
        """
        target_gamma = int(DEFAULT_OVER_FRAMEWORK_TAU * self.capacity)
        if self.gamma <= target_gamma:
            return 0
        return self.gamma - target_gamma

    # ── Task-based recommendations ─────────────────────────────────────

    def classify_for_task(self, task: str) -> str:
        """Classify whether this budget is suited for the given task type.

        Parameters
        ----------
        task:
            One of: "discovery", "synthesis", "balanced".

        Returns
        -------
        One of: "optimal", "acceptable", "suboptimal".
        """
        task = task.lower().strip()
        t = self.tau

        if task == "discovery":
            if t < THIN_THRESHOLD:
                return "optimal"
            elif t <= 0.50:
                return "acceptable"
            else:
                return "suboptimal"
        elif task == "synthesis":
            if t > THICK_THRESHOLD:
                return "optimal"
            elif t >= 0.50:
                return "acceptable"
            else:
                return "suboptimal"
        elif task == "balanced":
            if 0.25 <= t <= 0.65:
                return "optimal"
            elif 0.15 <= t <= 0.75:
                return "acceptable"
            else:
                return "suboptimal"
        else:
            return "unknown_task"

    # ── Socratic Casting Protocol ──────────────────────────────────────

    @staticmethod
    def recommend_casting_order(
        budgets: list["CognitiveBudget"],
    ) -> list[int]:
        """Return indices in Socratic casting order (thin → thick).

        The Socratic Casting Protocol mandates casting thin-chart models
        FIRST for discovery, then thick-chart models SECOND for synthesis.
        Reversing this order contaminates the discovery space.

        Returns
        -------
        List of indices into ``budgets``, sorted from thinnest to thickest
        chart. This is the correct casting order.

        Raises
        ------
        ValueError if the list is empty.
        """
        if not budgets:
            raise ValueError("Cannot recommend casting order for empty list")
        indexed = list(enumerate(budgets))
        indexed.sort(key=lambda pair: pair[1].tau)
        return [idx for idx, _ in indexed]

    # ── Snapshot & Export ──────────────────────────────────────────────

    def snapshot(self) -> BudgetSnapshot:
        """Capture an immutable point-in-time snapshot of the budget."""
        return BudgetSnapshot(
            capacity=self.capacity,
            gamma=self.gamma,
            eta=self.eta,
            tau=self.tau,
            chart_thickness=self.chart_thickness,
            reserved_output=self._reserved_output,
            effective_eta=self.effective_eta,
            is_over_frameworked=self.is_over_frameworked,
            is_under_structured=self.is_under_structured,
        )

    def to_dict(self) -> dict:
        """Export budget state as a JSON-serializable dictionary."""
        snap = self.snapshot()
        d = snap.to_dict()
        d["gamma_breakdown"] = dict(self.gamma_breakdown)
        d["context_window"] = self._context_window
        d["attention_heads"] = self._attention_heads
        return d

    # ── Dunder methods ─────────────────────────────────────────────────

    def __repr__(self) -> str:
        return (
            f"CognitiveBudget(C={self.capacity}, γ={self.gamma}, "
            f"η={self.eta}, τ={self.tau:.4f}, "
            f"chart={self.chart_thickness.value})"
        )

    def __str__(self) -> str:
        return (
            f"Cognitive Budget\n"
            f"  Capacity C = {self.capacity:,}\n"
            f"  Marked  γ  = {self.gamma:,}  ({self.gamma_breakdown})\n"
            f"  Unmark  η  = {self.eta:,}\n"
            f"  Thick.  τ  = {self.tau:.4f}  ({self.chart_thickness.value})\n"
            f"  Reserved   = {self._reserved_output:,} output tokens\n"
            f"  Eff. η     = {self.effective_eta:,}"
        )
