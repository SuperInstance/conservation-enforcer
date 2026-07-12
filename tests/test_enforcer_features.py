"""Tests for new ConservationEnforcer features."""

import tempfile
import os
import pytest
from conservation_enforcer import (
    ConservationEnforcer,
    length_budget_policy,
    combined_policy,
    assemble,
)


class TestFromPolicyFile:
    def test_load_from_file(self):
        """from_policy_file creates enforcer from binary file."""
        policy = length_budget_policy(max_tokens=100)

        with tempfile.NamedTemporaryFile(suffix=".bin", delete=False) as f:
            f.write(policy)
            path = f.name

        try:
            enforcer = ConservationEnforcer.from_policy_file(path, budget=100)
            result = enforcer.enforce("question", "short answer")
            assert result.allowed is True
        finally:
            os.unlink(path)

    def test_save_policy(self):
        """save_policy writes bytecode to file."""
        enforcer = ConservationEnforcer(length_budget_policy(max_tokens=50), budget=50)

        with tempfile.NamedTemporaryFile(suffix=".bin", delete=False) as f:
            path = f.name

        try:
            enforcer.save_policy(path)
            # Reload and use
            enforcer2 = ConservationEnforcer.from_policy_file(path, budget=50)
            result = enforcer2.enforce("q", "short")
            assert result.allowed is True
        finally:
            os.unlink(path)


class TestBudgetTracking:
    def test_remaining_budget(self):
        """remaining_budget reflects current state."""
        enforcer = ConservationEnforcer(
            length_budget_policy(max_tokens=10000),
            budget=500,
        )
        assert enforcer.remaining_budget == 500

    def test_replenish_budget(self):
        """replenish_budget adds to current budget."""
        enforcer = ConservationEnforcer(
            length_budget_policy(max_tokens=10000),
            budget=100,
        )
        enforcer.replenish_budget(50)
        assert enforcer.remaining_budget == 150

    def test_reset_budget(self):
        """reset_budget restores initial budget."""
        enforcer = ConservationEnforcer(
            length_budget_policy(max_tokens=10000),
            budget=200,
        )
        enforcer.replenish_budget(100)
        assert enforcer.remaining_budget == 300
        enforcer.reset_budget()
        assert enforcer.remaining_budget == 200

    def test_budget_syncs_after_decay(self):
        """Budget syncs from VM after DECAY_BUDGET syscall."""
        from conservation_enforcer import budget_decay_policy

        enforcer = ConservationEnforcer(
            budget_decay_policy(decay_rate=50, min_threshold=5, max_calls=100),
            budget=500,
        )
        enforcer.enforce("q", "a response here")
        assert enforcer.remaining_budget == 450  # 500 - 50 decay


class TestCallCount:
    def test_call_count_increments(self):
        """call_count tracks enforcement calls."""
        from conservation_enforcer import length_budget_policy

        enforcer = ConservationEnforcer(
            length_budget_policy(max_tokens=10000),
            budget=10000,
        )
        assert enforcer.call_count == 0
        enforcer.enforce("q1", "response one")
        assert enforcer.call_count == 1
        enforcer.enforce("q2", "response two")
        assert enforcer.call_count == 2
