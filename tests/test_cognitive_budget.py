"""Tests for the γ + η = C cognitive budget system.

Validates the conservation law, measurement protocols, chart thickness
classification, alerting, task recommendations, and the Socratic Casting
Protocol described in docs/GAMMA_ETA_SPEC.md.
"""

import math
import pytest
from conservation_enforcer.cognitive_budget import (
    CognitiveBudget,
    ChartThickness,
    BudgetSnapshot,
    _estimate_tokens,
    THIN_THRESHOLD,
    THICK_THRESHOLD,
    ULTRA_THIN_THRESHOLD,
    ULTRA_THICK_THRESHOLD,
)


# ── 1. Capacity computation (C = W × H) ────────────────────────────────────

class TestCapacity:
    def test_capacity_is_context_times_heads(self):
        """C = context_window × attention_heads — the fundamental capacity formula."""
        budget = CognitiveBudget(context_window=8000, attention_heads=32)
        assert budget.capacity == 256_000  # 8000 × 32

    def test_capacity_with_head_saturation_factor(self):
        """GQA/MQA models have fewer effective heads — head_saturation_factor captures this."""
        budget = CognitiveBudget(
            context_window=8000,
            attention_heads=32,
            head_saturation_factor=0.5,  # only half the heads are effective
        )
        assert budget.capacity == 128_000  # 8000 × (32 × 0.5) = 8000 × 16

    def test_invalid_context_window_raises(self):
        with pytest.raises(ValueError, match="context_window"):
            CognitiveBudget(context_window=0, attention_heads=32)

    def test_invalid_attention_heads_raises(self):
        with pytest.raises(ValueError, match="attention_heads"):
            CognitiveBudget(context_window=8000, attention_heads=0)


# ── 2. Gamma accumulation ──────────────────────────────────────────────────

class TestGammaAccumulation:
    def test_gamma_starts_at_zero(self):
        budget = CognitiveBudget(context_window=8000, attention_heads=32)
        assert budget.gamma == 0

    def test_gamma_accumulates_from_all_components(self):
        budget = CognitiveBudget(context_window=8000, attention_heads=32)
        budget.add_system_prompt("You are a helpful assistant.")  # ~7 tokens
        budget.add_few_shot("Example input and output pair here.")  # ~7 tokens
        budget.add_context("Some retrieved context.")  # ~5 tokens
        budget.add_framework(100)  # explicit token count

        # γ should be sum of all components
        breakdown = budget.gamma_breakdown
        assert breakdown["system"] > 0
        assert breakdown["fewshot"] > 0
        assert breakdown["context"] > 0
        assert breakdown["framework"] == 100
        assert budget.gamma == sum(breakdown.values())

    def test_add_framework_negative_raises(self):
        budget = CognitiveBudget(context_window=8000, attention_heads=32)
        with pytest.raises(ValueError):
            budget.add_framework(-10)


# ── 3. Eta derivation and conservation law ──────────────────────────────────

class TestConservationLaw:
    def test_eta_equals_capacity_minus_gamma(self):
        """η = C − γ — the conservation law."""
        budget = CognitiveBudget(context_window=8000, attention_heads=32)
        budget.add_framework(50_000)
        assert budget.eta == 256_000 - 50_000

    def test_conservation_holds_after_adding_gamma(self):
        """γ + η = C must hold exactly at all times."""
        budget = CognitiveBudget(context_window=128_000, attention_heads=128)
        budget.add_system_prompt("A" * 1000)
        budget.add_few_shot("B" * 500)
        budget.add_context("C" * 2000)
        budget.add_framework(10_000)
        assert budget.conservation_holds is True
        assert budget.gamma + budget.eta == budget.capacity

    def test_conservation_holds_at_zero_gamma(self):
        budget = CognitiveBudget(context_window=8000, attention_heads=32)
        assert budget.conservation_holds is True
        assert budget.eta == budget.capacity

    def test_effective_eta_subtracts_reserved_output(self):
        budget = CognitiveBudget(
            context_window=8000,
            attention_heads=32,
            reserved_output_tokens=40_000,
        )
        budget.add_framework(50_000)
        # η = 256000 - 50000 = 206000
        # effective η = 206000 - 40000 = 166000
        assert budget.eta == 206_000
        assert budget.effective_eta == 166_000


# ── 4. Chart thickness classification ───────────────────────────────────────

class TestChartThickness:
    def test_ultra_thin_chart(self):
        """τ < 0.15 → ULTRA_THIN."""
        budget = CognitiveBudget(context_window=10_000, attention_heads=10)  # C = 100,000
        budget.add_framework(10_000)  # τ = 0.10
        assert budget.tau == pytest.approx(0.10, abs=1e-6)
        assert budget.chart_thickness == ChartThickness.ULTRA_THIN

    def test_thin_chart(self):
        """0.15 ≤ τ < 0.30 → THIN."""
        budget = CognitiveBudget(context_window=10_000, attention_heads=10)
        budget.add_framework(20_000)  # τ = 0.20
        assert budget.chart_thickness == ChartThickness.THIN

    def test_balanced_chart(self):
        """0.30 ≤ τ ≤ 0.70 → BALANCED."""
        budget = CognitiveBudget(context_window=10_000, attention_heads=10)
        budget.add_framework(50_000)  # τ = 0.50
        assert budget.chart_thickness == ChartThickness.BALANCED

    def test_thick_chart(self):
        """0.70 < τ ≤ 0.85 → THICK."""
        budget = CognitiveBudget(context_window=10_000, attention_heads=10)
        budget.add_framework(75_000)  # τ = 0.75
        assert budget.chart_thickness == ChartThickness.THICK

    def test_ultra_thick_chart(self):
        """τ > 0.85 → ULTRA_THICK."""
        budget = CognitiveBudget(context_window=10_000, attention_heads=10)
        budget.add_framework(90_000)  # τ = 0.90
        assert budget.chart_thickness == ChartThickness.ULTRA_THICK


# ── 5. Over-framework detection ─────────────────────────────────────────────

class TestOverFramework:
    def test_over_frameworked_when_tau_exceeds_070(self):
        budget = CognitiveBudget(context_window=10_000, attention_heads=10)
        budget.add_framework(75_000)  # τ = 0.75
        assert budget.is_over_frameworked is True

    def test_not_over_frameworked_when_tau_below_070(self):
        budget = CognitiveBudget(context_window=10_000, attention_heads=10)
        budget.add_framework(50_000)  # τ = 0.50
        assert budget.is_over_frameworked is False


# ── 6. Under-structure detection ────────────────────────────────────────────

class TestUnderStructured:
    def test_under_structured_when_tau_below_010(self):
        budget = CognitiveBudget(context_window=10_000, attention_heads=10)
        budget.add_framework(5_000)  # τ = 0.05
        assert budget.is_under_structured is True

    def test_not_under_structured_at_normal_tau(self):
        budget = CognitiveBudget(context_window=10_000, attention_heads=10)
        budget.add_framework(50_000)  # τ = 0.50
        assert budget.is_under_structured is False


# ── 7. Excess gamma computation ─────────────────────────────────────────────

class TestExcessGamma:
    def test_excess_gamma_when_over_frameworked(self):
        """Should report how many tokens to remove to reach τ = 0.70."""
        budget = CognitiveBudget(context_window=10_000, attention_heads=10)  # C = 100,000
        budget.add_framework(80_000)  # τ = 0.80
        target_gamma = int(0.70 * 100_000)  # 70,000
        assert budget.excess_gamma == 80_000 - target_gamma

    def test_excess_gamma_zero_when_within_threshold(self):
        budget = CognitiveBudget(context_window=10_000, attention_heads=10)
        budget.add_framework(50_000)  # τ = 0.50
        assert budget.excess_gamma == 0


# ── 8. Task-based recommendation ────────────────────────────────────────────

class TestTaskRecommendation:
    def test_thin_chart_optimal_for_discovery(self):
        budget = CognitiveBudget(context_window=10_000, attention_heads=10)
        budget.add_framework(20_000)  # τ = 0.20
        assert budget.classify_for_task("discovery") == "optimal"

    def test_thick_chart_suboptimal_for_discovery(self):
        budget = CognitiveBudget(context_window=10_000, attention_heads=10)
        budget.add_framework(80_000)  # τ = 0.80
        assert budget.classify_for_task("discovery") == "suboptimal"

    def test_thick_chart_optimal_for_synthesis(self):
        budget = CognitiveBudget(context_window=10_000, attention_heads=10)
        budget.add_framework(80_000)  # τ = 0.80
        assert budget.classify_for_task("synthesis") == "optimal"

    def test_balanced_optimal_for_balanced_task(self):
        budget = CognitiveBudget(context_window=10_000, attention_heads=10)
        budget.add_framework(50_000)  # τ = 0.50
        assert budget.classify_for_task("balanced") == "optimal"

    def test_unknown_task_returns_unknown(self):
        budget = CognitiveBudget(context_window=10_000, attention_heads=10)
        assert budget.classify_for_task("creative_writing") == "unknown_task"


# ── 9. Socratic Casting Protocol ────────────────────────────────────────────

class TestSocraticCasting:
    def test_casting_order_thin_before_thick(self):
        """The protocol mandates thin-chart models FIRST, thick-chart SECOND."""
        thick = CognitiveBudget(context_window=10_000, attention_heads=10)
        thick.add_framework(80_000)  # τ = 0.80 — thick

        thin = CognitiveBudget(context_window=10_000, attention_heads=10)
        thin.add_framework(15_000)  # τ = 0.15 — thin

        balanced = CognitiveBudget(context_window=10_000, attention_heads=10)
        balanced.add_framework(50_000)  # τ = 0.50

        order = CognitiveBudget.recommend_casting_order([thick, thin, balanced])
        # Should be: thin (idx 1) → balanced (idx 2) → thick (idx 0)
        assert order == [1, 2, 0]

    def test_casting_order_single_model(self):
        budget = CognitiveBudget(context_window=8000, attention_heads=32)
        order = CognitiveBudget.recommend_casting_order([budget])
        assert order == [0]

    def test_casting_order_empty_raises(self):
        with pytest.raises(ValueError, match="empty"):
            CognitiveBudget.recommend_casting_order([])

    def test_casting_order_already_sorted(self):
        """If already in thin→thick order, indices are identity."""
        budgets = []
        for tau_val in [0.10, 0.30, 0.50, 0.80]:
            b = CognitiveBudget(context_window=10_000, attention_heads=10)
            b.add_framework(int(tau_val * 100_000))
            budgets.append(b)
        order = CognitiveBudget.recommend_casting_order(budgets)
        assert order == [0, 1, 2, 3]


# ── 10. Reset functionality ─────────────────────────────────────────────────

class TestReset:
    def test_reset_gamma_to_zero(self):
        budget = CognitiveBudget(context_window=10_000, attention_heads=10)
        budget.add_system_prompt("Important instructions here.")
        budget.add_few_shot("Example data.")
        budget.add_framework(5000)
        assert budget.gamma > 0

        budget.reset_gamma()
        assert budget.gamma == 0
        assert budget.eta == budget.capacity
        assert budget.tau == 0.0


# ── 11. Dictionary export ───────────────────────────────────────────────────

class TestExport:
    def test_to_dict_contains_all_fields(self):
        budget = CognitiveBudget(
            context_window=10_000,
            attention_heads=10,
            reserved_output_tokens=5000,
        )
        budget.add_system_prompt("Test prompt.")
        budget.add_framework(1000)

        d = budget.to_dict()
        assert "capacity" in d
        assert "gamma" in d
        assert "eta" in d
        assert "tau" in d
        assert "chart_thickness" in d
        assert "reserved_output" in d
        assert "effective_eta" in d
        assert "is_over_frameworked" in d
        assert "is_under_structured" in d
        assert "gamma_breakdown" in d
        assert "context_window" in d
        assert "attention_heads" in d

    def test_snapshot_is_immutable_dataclass(self):
        budget = CognitiveBudget(context_window=8000, attention_heads=32)
        budget.add_framework(100)
        snap = budget.snapshot()
        assert isinstance(snap, BudgetSnapshot)
        assert snap.capacity == 256_000
        assert snap.gamma == 100

    def test_repr_contains_key_values(self):
        budget = CognitiveBudget(context_window=8000, attention_heads=32)
        budget.add_framework(1000)
        r = repr(budget)
        assert "CognitiveBudget" in r
        assert "γ=" in r
        assert "η=" in r
        assert "τ=" in r


# ── 12. Token estimation ────────────────────────────────────────────────────

class TestTokenEstimation:
    def test_empty_string_zero_tokens(self):
        assert _estimate_tokens("") == 0

    def test_short_string_at_least_one_token(self):
        assert _estimate_tokens("hi") >= 1

    def test_long_string_uses_chars_per_token_ratio(self):
        text = "A" * 400  # 400 chars / 4 = 100 tokens
        assert _estimate_tokens(text) == 100

    def test_add_system_prompt_uses_estimation(self):
        budget = CognitiveBudget(context_window=8000, attention_heads=32)
        text = "A" * 100  # ~25 tokens
        tokens_added = budget.add_system_prompt(text)
        assert tokens_added == 25
        assert budget.gamma == 25


# ── 13. Realistic scenarios ─────────────────────────────────────────────────

class TestRealisticScenarios:
    def test_gpt4_with_moderate_context_is_thin(self):
        """GPT-4 has such large C that even 32K tokens of context is thin."""
        budget = CognitiveBudget(context_window=128_000, attention_heads=128)
        # C = 128000 × 128 = 16,384,000 — enormous capacity
        budget.add_framework(32_000)  # τ ≈ 0.002
        assert budget.chart_thickness == ChartThickness.ULTRA_THIN
        assert budget.tau < 0.01

    def test_gpt4_thick_prompt_to_be_thick_needs_massive_context(self):
        """To make GPT-4 'thick', you'd need an extraordinary amount of context."""
        budget = CognitiveBudget(context_window=128_000, attention_heads=128)
        budget.add_framework(12_000_000)  # τ ≈ 0.73
        assert budget.chart_thickness == ChartThickness.THICK
        assert budget.tau > THICK_THRESHOLD

    def test_small_model_thin_prompt_is_thin(self):
        """Simulate Ornith-35B with minimal prompt — the casting call winner."""
        budget = CognitiveBudget(context_window=4_000, attention_heads=32)
        budget.add_framework(500)  # minimal prompt
        assert budget.chart_thickness in (ChartThickness.ULTRA_THIN, ChartThickness.THIN)
        assert budget.tau < 0.30

    def test_conservation_invariant_never_violated_across_operations(self):
        """No matter what sequence of operations, γ + η = C always holds."""
        budget = CognitiveBudget(context_window=128_000, attention_heads=128)
        budget.add_system_prompt("System " * 100)
        budget.add_few_shot("Example " * 50)
        budget.add_context("Context " * 200)
        budget.add_framework(5000)
        budget.reset_gamma()
        budget.add_framework(999)
        assert budget.conservation_holds is True
