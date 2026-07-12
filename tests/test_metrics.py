"""Tests for metrics collection."""

import json
import os
import tempfile
import pytest
from conservation_enforcer import MetricsCollector


class TestMetricsCollector:
    def test_initial_state(self):
        """New collector starts at zero."""
        m = MetricsCollector()
        snap = m.snapshot()
        assert snap.total_calls == 0
        assert snap.total_allowed == 0
        assert snap.total_blocked == 0
        assert snap.block_rate == 0.0

    def test_record_allowed(self):
        """Recording an allowed call."""
        m = MetricsCollector()
        m.record(allowed=True, cycles=10, budget_before=100, budget_after=90)
        snap = m.snapshot()
        assert snap.total_calls == 1
        assert snap.total_allowed == 1
        assert snap.total_blocked == 0
        assert snap.total_budget_consumed == 10

    def test_record_blocked(self):
        """Recording a blocked call with violation reason."""
        m = MetricsCollector()
        m.record(
            allowed=False,
            violation_reason="Length budget exceeded",
            cycles=5,
            budget_before=50,
            budget_after=50,
        )
        snap = m.snapshot()
        assert snap.total_calls == 1
        assert snap.total_blocked == 1
        assert snap.policy_triggers["Length budget exceeded"] == 1
        assert snap.total_budget_consumed == 0  # blocked, no budget consumed

    def test_multiple_records(self):
        """Multiple calls aggregate correctly."""
        m = MetricsCollector()
        m.record(allowed=True, cycles=10)
        m.record(allowed=False, violation_reason="Repetition", cycles=5)
        m.record(allowed=True, cycles=15)
        m.record(allowed=False, violation_reason="Entropy", cycles=8)

        snap = m.snapshot()
        assert snap.total_calls == 4
        assert snap.total_allowed == 2
        assert snap.total_blocked == 2
        assert snap.block_rate == 0.5
        assert snap.avg_cycles == 9.5
        assert snap.policy_triggers["Repetition"] == 1
        assert snap.policy_triggers["Entropy"] == 1

    def test_export_to_dict(self):
        """Export produces JSON-serializable dict."""
        m = MetricsCollector()
        m.record(allowed=True, cycles=10)
        m.record(allowed=False, violation_reason="Test", cycles=5)

        data = m.export()
        assert isinstance(data, dict)
        # Verify it's JSON-serializable
        json_str = json.dumps(data)
        assert json.loads(json_str)["total_calls"] == 2

    def test_export_to_file(self):
        """Export writes JSON file."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name

        try:
            m = MetricsCollector()
            m.record(allowed=True, cycles=10)
            m.export(path)

            with open(path) as f:
                data = json.load(f)
            assert data["total_calls"] == 1
            assert data["total_allowed"] == 1
        finally:
            os.unlink(path)

    def test_reset(self):
        """Reset clears all metrics."""
        m = MetricsCollector()
        m.record(allowed=True, cycles=10)
        m.record(allowed=False, violation_reason="Test", cycles=5)
        m.reset()

        snap = m.snapshot()
        assert snap.total_calls == 0
        assert snap.total_allowed == 0
        assert snap.total_blocked == 0
        assert len(snap.policy_triggers) == 0

    def test_budget_consumption_tracking(self):
        """Budget consumption is summed across calls."""
        m = MetricsCollector()
        m.record(allowed=True, budget_before=100, budget_after=80, cycles=5)
        m.record(allowed=True, budget_before=80, budget_after=30, cycles=5)
        m.record(allowed=True, budget_before=30, budget_after=10, cycles=5)

        snap = m.snapshot()
        assert snap.total_budget_consumed == 90  # 20 + 50 + 20
        assert snap.avg_budget_per_call == 30.0  # 90/3
