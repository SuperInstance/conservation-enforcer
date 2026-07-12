"""Metrics tracking for conservation enforcement.

Tracks cumulative enforcement statistics for dashboards and reporting:
    - Total enforcement calls
    - Blocked vs allowed calls
    - Budget consumed over time
    - Policy trigger counts (which conservation laws fire most?)
    - Average VM cycles per call

Export as JSON for integration with external dashboards (Grafana, Datadog, etc).

Usage:
    from conservation_enforcer.metrics import MetricsCollector

    metrics = MetricsCollector()

    # After each enforcement call:
    metrics.record(
        allowed=False,
        violation_reason="Length budget exceeded",
        cycles=42,
        budget_before=500,
        budget_after=450,
    )

    # Export for dashboarding:
    data = metrics.export()
    print(json.dumps(data, indent=2))
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class MetricsSnapshot:
    """Immutable point-in-time metrics snapshot."""
    total_calls: int = 0
    total_allowed: int = 0
    total_blocked: int = 0
    total_cycles: int = 0
    total_budget_consumed: int = 0
    policy_triggers: dict[str, int] = field(default_factory=dict)
    avg_cycles: float = 0.0
    block_rate: float = 0.0
    avg_budget_per_call: float = 0.0

    def to_dict(self) -> dict:
        return {
            "total_calls": self.total_calls,
            "total_allowed": self.total_allowed,
            "total_blocked": self.total_blocked,
            "total_cycles": self.total_cycles,
            "total_budget_consumed": self.total_budget_consumed,
            "policy_triggers": dict(self.policy_triggers),
            "avg_cycles": round(self.avg_cycles, 2),
            "block_rate": round(self.block_rate, 4),
            "avg_budget_per_call": round(self.avg_budget_per_call, 2),
        }


class MetricsCollector:
    """Collects enforcement metrics over the lifetime of an enforcer.

    Call `record()` after each enforcement decision, then `export()`
    to get a JSON-serializable summary for external dashboarding.
    """

    def __init__(self):
        self._total_calls = 0
        self._total_allowed = 0
        self._total_blocked = 0
        self._total_cycles = 0
        self._total_budget_consumed = 0
        self._policy_triggers: dict[str, int] = {}

    def record(
        self,
        allowed: bool,
        violation_reason: Optional[str] = None,
        cycles: int = 0,
        budget_before: int = 0,
        budget_after: int = 0,
    ) -> None:
        """Record a single enforcement decision."""
        self._total_calls += 1
        self._total_cycles += cycles
        self._total_budget_consumed += max(0, budget_before - budget_after)

        if allowed:
            self._total_allowed += 1
        else:
            self._total_blocked += 1
            if violation_reason:
                self._policy_triggers[violation_reason] = (
                    self._policy_triggers.get(violation_reason, 0) + 1
                )

    def snapshot(self) -> MetricsSnapshot:
        """Get a point-in-time snapshot of all metrics."""
        n = max(1, self._total_calls)
        return MetricsSnapshot(
            total_calls=self._total_calls,
            total_allowed=self._total_allowed,
            total_blocked=self._total_blocked,
            total_cycles=self._total_cycles,
            total_budget_consumed=self._total_budget_consumed,
            policy_triggers=dict(self._policy_triggers),
            avg_cycles=self._total_cycles / n,
            block_rate=self._total_blocked / n if self._total_calls > 0 else 0.0,
            avg_budget_per_call=self._total_budget_consumed / n if self._total_calls > 0 else 0.0,
        )

    def export(self, path: Optional[str] = None) -> dict:
        """Export metrics as JSON. Optionally write to file.

        Returns the JSON-serializable dict.
        """
        data = self.snapshot().to_dict()
        if path:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        return data

    def reset(self) -> None:
        """Reset all metrics to zero."""
        self._total_calls = 0
        self._total_allowed = 0
        self._total_blocked = 0
        self._total_cycles = 0
        self._total_budget_consumed = 0
        self._policy_triggers.clear()
