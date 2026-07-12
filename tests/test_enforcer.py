"""Tests for the ConservationEnforcer and policies."""

import pytest
from conservation_enforcer import (
    ConservationEnforcer,
    EnforcementResult,
    length_budget_policy,
    repetition_policy,
    category_policy,
    entropy_policy,
    combined_policy,
    assemble,
)


class TestLengthBudgetPolicy:
    def test_allows_short_output(self):
        enforcer = ConservationEnforcer(length_budget_policy(max_tokens=100), budget=100)
        result = enforcer.enforce("What is Python?", "Python is a programming language.")
        assert result.allowed is True

    def test_blocks_long_output(self):
        enforcer = ConservationEnforcer(length_budget_policy(max_tokens=5), budget=5)
        result = enforcer.enforce("Tell me everything", "word " * 100)
        assert result.allowed is False
        assert "Length budget exceeded" in result.violation.reason

    def test_correction_message(self):
        enforcer = ConservationEnforcer(
            length_budget_policy(max_tokens=3), budget=3,
            correction_template="🚫 Blocked: {reason}",
        )
        result = enforcer.enforce("Q", "This is a very long response that exceeds budget")
        assert not result.allowed
        assert "🚫 Blocked:" in result.output


class TestRepetitionPolicy:
    def test_allows_diverse_output(self):
        enforcer = ConservationEnforcer(repetition_policy(max_ratio=500))
        result = enforcer.enforce("Explain photosynthesis",
            "Plants convert sunlight into chemical energy through photosynthesis using chlorophyll and water.")
        assert result.allowed is True

    def test_blocks_repetitive_output(self):
        enforcer = ConservationEnforcer(repetition_policy(max_ratio=300))
        result = enforcer.enforce("Summarize", "the the the the the the the the the the")
        assert result.allowed is False
        assert "repetition" in result.violation.reason.lower()


class TestCategoryPolicy:
    def test_allows_on_topic(self):
        enforcer = ConservationEnforcer(category_policy(min_overlap=50))
        result = enforcer.enforce("Python programming language",
            "Python is a great programming language for beginners and experts alike")
        assert result.allowed is True

    def test_blocks_off_topic(self):
        enforcer = ConservationEnforcer(category_policy(min_overlap=900))
        result = enforcer.enforce("quantum physics particles",
            "banana apple orange grape melon")
        assert result.allowed is False
        assert "category" in result.violation.reason.lower()


class TestEntropyPolicy:
    def test_allows_high_entropy(self):
        enforcer = ConservationEnforcer(entropy_policy(min_entropy=1000))
        result = enforcer.enforce("List colors",
            "red blue green yellow orange purple cyan magenta")
        assert result.allowed is True

    def test_blocks_low_entropy(self):
        enforcer = ConservationEnforcer(entropy_policy(min_entropy=2500))
        result = enforcer.enforce("Write a poem",
            "go go go go go go go go go go")
        assert result.allowed is False
        assert "entropy" in result.violation.reason.lower()


class TestCombinedPolicy:
    def test_allows_compliant_output(self):
        enforcer = ConservationEnforcer(
            combined_policy(max_tokens=500, max_repetition=500, min_overlap=10, min_entropy=500),
            budget=500,
        )
        result = enforcer.enforce("What is machine learning?",
            "Machine learning is a subset of artificial intelligence that enables systems to learn from data.")
        assert result.allowed is True

    def test_blocks_on_length_violation(self):
        enforcer = ConservationEnforcer(combined_policy(max_tokens=3), budget=3)
        result = enforcer.enforce("Write a long essay about AI", "Artificial intelligence is " * 50)
        assert result.allowed is False
        assert "Length" in result.violation.reason

    def test_blocks_on_repetition_violation(self):
        enforcer = ConservationEnforcer(
            combined_policy(max_tokens=10000, max_repetition=200, min_overlap=0, min_entropy=0),
            budget=10000,
        )
        result = enforcer.enforce("Describe a sunset",
            "beautiful beautiful beautiful beautiful beautiful beautiful beautiful")
        assert result.allowed is False
        assert "repetition" in result.violation.reason.lower()


class TestEnforcementResult:
    def test_truthiness(self):
        assert bool(EnforcementResult(allowed=True, output="ok")) is True
        assert bool(EnforcementResult(allowed=False, output="blocked")) is False

    def test_cycles_recorded(self):
        enforcer = ConservationEnforcer(length_budget_policy(max_tokens=10000), budget=10000)
        result = enforcer.enforce("Hi", "Hello!")
        assert result.cycles > 0


class TestEnforceWithLLM:
    def test_wraps_llm_call(self):
        enforcer = ConservationEnforcer(length_budget_policy(max_tokens=100), budget=100)
        result = enforcer.enforce_with_llm("Hello", lambda p: f"Response to: {p}")
        assert result.allowed is True
        assert "Response to: Hello" in result.output


class TestCustomPolicy:
    def test_always_allow(self):
        code = assemble("MOVI R0, 0\nHALT")
        enforcer = ConservationEnforcer(code)
        result = enforcer.enforce("anything", "any response")
        assert result.allowed is True

    def test_always_block(self):
        code = assemble("""
            MOVI R1, 99
            MOVI R0, 8
            SYSCALL
            MOVI R0, 1
            HALT
        """)
        enforcer = ConservationEnforcer(code)
        result = enforcer.enforce("q", "a")
        assert result.allowed is False
        assert "Custom" in result.violation.reason

    def test_custom_correction_template(self):
        block_code = assemble("""
            MOVI R1, 99
            MOVI R0, 8
            SYSCALL
            MOVI R0, 1
            HALT
        """)
        enforcer = ConservationEnforcer(block_code, correction_template="🚫 {reason}")
        result = enforcer.enforce("q", "a")
        assert "🚫" in result.output
