"""CognitiveBudget — formal γ/η allocation from the Conservation Law of Intelligence.

The Conservation Law of Intelligence states:  γ + H = C

Where:
  γ (gamma) = allocated attention / committed cognitive capacity
  H (eta)   = entropy / unallocated potential / degrees of freedom
  C         = total cognitive capacity (constant for a given system)

This module provides the CognitiveBudget class that formalizes this
relationship in code, enabling conservation-enforcer policies to reason
about cognitive thickness and thinness.

A "thick" intelligence (γ/C > 0.7) is highly committed — most of its
capacity is allocated. It has strong patterns but low adaptability.

A "thin" intelligence (γ/C < 0.3) has most of its capacity unallocated.
It is highly adaptable but has weak committed patterns.

The sweet spot is typically in the middle — enough structure to be useful,
enough entropy to adapt.
"""

from __future__ import annotations

from dataclasses import dataclass


class BudgetExceededError(Exception):
    """Raised when spending exceeds the total cognitive capacity."""


@dataclass
class CognitiveBudget:
    """Formal cognitive budget tracking γ and η.

    Attributes:
        capacity: Total cognitive capacity C. Must be positive.
        allocated: Currently allocated attention γ. Must be 0 ≤ γ ≤ C.

    Properties:
        eta: Unallocated potential (C - γ).
        thickness_ratio: γ/C ratio in [0, 1].
    """

    capacity: float
    allocated: float = 0.0

    def __post_init__(self) -> None:
        if self.capacity <= 0:
            raise ValueError(f"capacity must be positive, got {self.capacity}")
        if self.allocated < 0:
            raise ValueError(f"allocated must be non-negative, got {self.allocated}")
        if self.allocated > self.capacity:
            raise ValueError(
                f"allocated ({self.allocated}) cannot exceed capacity ({self.capacity})"
            )

    @property
    def eta(self) -> float:
        """Unallocated cognitive potential: C - γ."""
        return self.capacity - self.allocated

    @property
    def gamma(self) -> float:
        """Alias for allocated (γ)."""
        return self.allocated

    @property
    def thickness_ratio(self) -> float:
        """γ/C ratio in [0, 1]. How committed the budget is."""
        return self.allocated / self.capacity

    def thickness(self) -> float:
        """Return the γ/C ratio — how thick the cognitive commitment is."""
        return self.thickness_ratio

    def is_thin(self) -> bool:
        """True when γ/C < 0.3 — mostly unallocated, highly adaptable."""
        return self.thickness_ratio < 0.3

    def is_thick(self) -> bool:
        """True when γ/C > 0.7 — mostly allocated, strongly committed."""
        return self.thickness_ratio > 0.7

    def is_balanced(self) -> bool:
        """True when 0.3 ≤ γ/C ≤ 0.7 — the adaptive middle zone."""
        return 0.3 <= self.thickness_ratio <= 0.7

    def spend(self, amount: float) -> None:
        """Allocate more cognitive capacity (increase γ).

        Args:
            amount: How much capacity to commit.

        Raises:
            BudgetExceededError: If γ would exceed C.
            ValueError: If amount is negative.
        """
        if amount < 0:
            raise ValueError(f"spend amount must be non-negative, got {amount}")
        new_allocated = self.allocated + amount
        if new_allocated > self.capacity:
            raise BudgetExceededError(
                f"Cannot spend {amount}: allocated would be {new_allocated} "
                f"which exceeds capacity {self.capacity} "
                f"(remaining η = {self.eta})"
            )
        self.allocated = new_allocated

    def release(self, amount: float) -> None:
        """Release allocated capacity back to entropy (decrease γ).

        Args:
            amount: How much capacity to release.

        Raises:
            ValueError: If amount exceeds current allocation or is negative.
        """
        if amount < 0:
            raise ValueError(f"release amount must be non-negative, got {amount}")
        if amount > self.allocated:
            raise ValueError(
                f"Cannot release {amount}: only {self.allocated} is allocated"
            )
        self.allocated -= amount

    def reset(self) -> None:
        """Reset allocation to zero — full entropy, no commitment."""
        self.allocated = 0.0

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "capacity": self.capacity,
            "allocated": self.allocated,
            "eta": self.eta,
            "thickness": self.thickness_ratio,
            "state": "thin" if self.is_thin() else ("thick" if self.is_thick() else "balanced"),
        }

    def __repr__(self) -> str:
        state = "thin" if self.is_thin() else ("thick" if self.is_thick() else "balanced")
        return (
            f"CognitiveBudget(C={self.capacity}, γ={self.allocated:.2f}, "
            f"η={self.eta:.2f}, thickness={self.thickness_ratio:.2%}, {state})"
        )
