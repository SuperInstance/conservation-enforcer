"""Tests for new conservation policies: density, scope, decay."""

import pytest
from conservation_enforcer import (
    ConservationEnforcer,
    information_density_policy,
    scope_discipline_policy,
    budget_decay_policy,
    combined_policy,
)


class TestInformationDensityPolicy:
    def test_allows_high_density(self):
        """Output with many unique words should pass."""
        enforcer = ConservationEnforcer(information_density_policy(min_ratio=300))
        result = enforcer.enforce(
            "List colors",
            "red blue green yellow orange purple cyan magenta violet turquoise",
        )
        assert result.allowed is True

    def test_blocks_low_density(self):
        """Output with few unique words should be blocked."""
        enforcer = ConservationEnforcer(information_density_policy(min_ratio=500))
        result = enforcer.enforce(
            "Write a poem",
            "go go go go go go go go go go",
        )
        assert result.allowed is False
        assert "density" in result.violation.reason.lower()

    def test_boundary_case(self):
        """Exactly at threshold should pass (JLT is strict)."""
        enforcer = ConservationEnforcer(information_density_policy(min_ratio=500))
        # 1 unique out of 2 total = 500 per-mille, exactly at threshold
        result = enforcer.enforce("test", "hello world")
        assert result.allowed is True


class TestScopeDisciplinePolicy:
    def test_allows_on_topic(self):
        """Output sharing words with input should pass."""
        enforcer = ConservationEnforcer(scope_discipline_policy(min_overlap=50))
        result = enforcer.enforce(
            "Python programming language tutorial",
            "Python is a great programming language for beginners",
        )
        assert result.allowed is True

    def test_blocks_off_topic(self):
        """Output with no word overlap should be blocked."""
        enforcer = ConservationEnforcer(scope_discipline_policy(min_overlap=500))
        result = enforcer.enforce(
            "quantum physics particles energy",
            "banana apple orange grape melon fruit",
        )
        assert result.allowed is False
        assert "scope" in result.violation.reason.lower()

    def test_blocks_excessive_expansion(self):
        """Output that is 10x+ longer than input should be blocked."""
        enforcer = ConservationEnforcer(scope_discipline_policy(min_overlap=0))
        # input is very short, output is very long
        result = enforcer.enforce(
            "hi",
            "hello " * 100,  # 500 chars, input is 2 chars, ratio = 250x
        )
        assert result.allowed is False
        assert "scope" in result.violation.reason.lower()

    def test_allows_short_output_for_empty_input_check(self):
        """Empty input edge case — should not crash."""
        enforcer = ConservationEnforcer(scope_discipline_policy(min_overlap=0))
        result = enforcer.enforce("", "any output here")
        # empty input → skips the expansion check
        assert result.allowed is True


class TestBudgetDecayPolicy:
    def test_allows_with_sufficient_budget(self):
        """With plenty of budget, should allow."""
        enforcer = ConservationEnforcer(
            budget_decay_policy(decay_rate=10, min_threshold=5, max_calls=100),
            budget=1000,
        )
        result = enforcer.enforce("question", "answer response")
        assert result.allowed is True

    def test_blocks_when_budget_exhausted(self):
        """When budget decays below threshold, should block."""
        enforcer = ConservationEnforcer(
            budget_decay_policy(decay_rate=100, min_threshold=50, max_calls=100),
            budget=100,  # after one decay of 100, budget = 0 < 50
        )
        result = enforcer.enforce("question", "answer response")
        # budget was 100, decay 100 → 0, which is < 50
        assert result.allowed is False
        assert "budget" in result.violation.reason.lower() or "cooldown" in result.violation.reason.lower()

    def test_budget_decreases_across_calls(self):
        """Budget should decrease with each enforcement call."""
        enforcer = ConservationEnforcer(
            budget_decay_policy(decay_rate=50, min_threshold=5, max_calls=100),
            budget=500,
        )
        assert enforcer.remaining_budget == 500
        enforcer.enforce("q1", "response one here")
        assert enforcer.remaining_budget == 450  # 500 - 50
        enforcer.enforce("q2", "response two here")
        assert enforcer.remaining_budget == 400  # 450 - 50

    def test_blocks_when_max_calls_exceeded(self):
        """Should block when call count exceeds max_calls."""
        enforcer = ConservationEnforcer(
            budget_decay_policy(decay_rate=1, min_threshold=0, max_calls=3),
            budget=10000,
        )
        # First 3 calls should pass (call_count increments before VM runs)
        r1 = enforcer.enforce("q", "a response")
        r2 = enforcer.enforce("q", "a response")
        r3 = enforcer.enforce("q", "a response")
        # 4th call: call_count = 4 > max_calls = 3
        r4 = enforcer.enforce("q", "a response")
        # Note: _call_count in enforcer increments, but VM's _call_count also increments
        # At 4th call, VM call_count = 4 > 3 → blocked
        assert r4.allowed is False
        assert "budget" in r4.violation.reason.lower() or "cooldown" in r4.violation.reason.lower()


class TestCombinedWithNewPolicies:
    def test_combined_with_density(self):
        """Combined policy with density check enabled."""
        policy = combined_policy(
            max_tokens=10000,
            max_repetition=500,
            min_overlap=0,
            min_entropy=0,
            min_density=300,
        )
        enforcer = ConservationEnforcer(policy, budget=10000)

        # Low density output should be blocked
        result = enforcer.enforce(
            "Write something",
            "blah blah blah blah blah blah blah",
        )
        assert result.allowed is False

    def test_combined_without_density(self):
        """Combined policy without density check — density violations pass through.

        The same output is allowed when density is disabled and blocked when
        density is enabled above its unique-ratio, proving min_density=0 really
        disables the law (rather than just asserting cycles > 0, which would
        pass regardless of whether the density branch ran).
        """
        # unique ratio = 4 unique / 10 total = 400 per-mille
        output = "alpha beta gamma delta alpha beta gamma delta alpha beta"

        disabled = combined_policy(
            max_tokens=10000,
            max_repetition=500,
            min_overlap=0,
            min_entropy=0,
            min_density=0,  # disabled
        )
        r_off = ConservationEnforcer(disabled, budget=10000).enforce("Write something", output)
        assert r_off.allowed is True  # density law is a NOP

        enabled = combined_policy(
            max_tokens=10000,
            max_repetition=500,
            min_overlap=0,
            min_entropy=0,
            min_density=500,  # above the output's 400 per-mille ratio
        )
        r_on = ConservationEnforcer(enabled, budget=10000).enforce("Write something", output)
        assert r_on.allowed is False
        assert "density" in r_on.violation.reason.lower()

    def test_combined_with_decay(self):
        """Combined policy with budget decay enabled."""
        policy = combined_policy(
            max_tokens=10000,
            max_repetition=500,
            min_overlap=0,
            min_entropy=0,
            enable_decay=True,
            decay_rate=100,
        )
        enforcer = ConservationEnforcer(policy, budget=200)

        # First call should pass (budget 200 - 100 decay = 100 > threshold)
        r1 = enforcer.enforce("q", "a reasonable response here")
        # Second call: budget 100 - 100 = 0 < 10 threshold → blocked
        r2 = enforcer.enforce("q", "a reasonable response here")
        assert r2.allowed is False
        assert "budget" in r2.violation.reason.lower() or "cooldown" in r2.violation.reason.lower()
