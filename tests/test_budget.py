"""Tests for the CognitiveBudget class."""

import pytest
from conservation_enforcer.budget import CognitiveBudget, BudgetExceededError


class TestCognitiveBudgetInit:
    def test_basic_creation(self):
        b = CognitiveBudget(capacity=100, allocated=30)
        assert b.capacity == 100
        assert b.allocated == 30

    def test_default_allocated_is_zero(self):
        b = CognitiveBudget(capacity=100)
        assert b.allocated == 0.0

    def test_zero_capacity_rejected(self):
        with pytest.raises(ValueError, match="capacity must be positive"):
            CognitiveBudget(capacity=0)

    def test_negative_capacity_rejected(self):
        with pytest.raises(ValueError, match="capacity must be positive"):
            CognitiveBudget(capacity=-10)

    def test_allocated_exceeds_capacity_rejected(self):
        with pytest.raises(ValueError, match="cannot exceed capacity"):
            CognitiveBudget(capacity=50, allocated=60)

    def test_negative_allocated_rejected(self):
        with pytest.raises(ValueError, match="non-negative"):
            CognitiveBudget(capacity=100, allocated=-5)


class TestCognitiveBudgetProperties:
    def test_eta_property(self):
        b = CognitiveBudget(capacity=100, allocated=30)
        assert b.eta == 70

    def test_gamma_alias(self):
        b = CognitiveBudget(capacity=100, allocated=42)
        assert b.gamma == 42

    def test_eta_full_when_nothing_allocated(self):
        b = CognitiveBudget(capacity=100)
        assert b.eta == 100

    def test_eta_zero_when_fully_allocated(self):
        b = CognitiveBudget(capacity=100, allocated=100)
        assert b.eta == 0

    def test_thickness_ratio(self):
        b = CognitiveBudget(capacity=100, allocated=30)
        assert b.thickness() == pytest.approx(0.3)

    def test_thickness_ratio_property(self):
        b = CognitiveBudget(capacity=200, allocated=80)
        assert b.thickness_ratio == pytest.approx(0.4)


class TestCognitiveBudgetStates:
    def test_is_thin(self):
        b = CognitiveBudget(capacity=100, allocated=20)
        assert b.is_thin() is True

    def test_is_not_thin_at_boundary(self):
        b = CognitiveBudget(capacity=100, allocated=30)
        assert b.is_thin() is False

    def test_is_thick(self):
        b = CognitiveBudget(capacity=100, allocated=80)
        assert b.is_thick() is True

    def test_is_not_thick_at_boundary(self):
        b = CognitiveBudget(capacity=100, allocated=70)
        assert b.is_thick() is False

    def test_is_balanced_in_middle(self):
        b = CognitiveBudget(capacity=100, allocated=50)
        assert b.is_balanced() is True

    def test_is_balanced_at_lower_boundary(self):
        b = CognitiveBudget(capacity=100, allocated=30)
        assert b.is_balanced() is True

    def test_is_balanced_at_upper_boundary(self):
        b = CognitiveBudget(capacity=100, allocated=70)
        assert b.is_balanced() is True


class TestCognitiveBudgetSpend:
    def test_spend_increases_allocated(self):
        b = CognitiveBudget(capacity=100, allocated=20)
        b.spend(30)
        assert b.allocated == 50

    def test_spend_decreases_eta(self):
        b = CognitiveBudget(capacity=100, allocated=20)
        b.spend(30)
        assert b.eta == 50

    def test_spend_exact_capacity(self):
        b = CognitiveBudget(capacity=100, allocated=80)
        b.spend(20)
        assert b.allocated == 100
        assert b.eta == 0

    def test_spend_exceeds_capacity_raises(self):
        b = CognitiveBudget(capacity=100, allocated=80)
        with pytest.raises(BudgetExceededError, match="exceeds capacity"):
            b.spend(30)

    def test_spend_negative_raises(self):
        b = CognitiveBudget(capacity=100)
        with pytest.raises(ValueError, match="non-negative"):
            b.spend(-10)

    def test_spend_makes_thin_thick(self):
        b = CognitiveBudget(capacity=100, allocated=20)
        assert b.is_thin()
        b.spend(60)
        assert b.is_thick()


class TestCognitiveBudgetRelease:
    def test_release_decreases_allocated(self):
        b = CognitiveBudget(capacity=100, allocated=50)
        b.release(20)
        assert b.allocated == 30

    def test_release_increases_eta(self):
        b = CognitiveBudget(capacity=100, allocated=50)
        b.release(20)
        assert b.eta == 70

    def test_release_to_zero(self):
        b = CognitiveBudget(capacity=100, allocated=50)
        b.release(50)
        assert b.allocated == 0
        assert b.eta == 100

    def test_release_more_than_allocated_raises(self):
        b = CognitiveBudget(capacity=100, allocated=30)
        with pytest.raises(ValueError, match="Cannot release"):
            b.release(40)

    def test_release_negative_raises(self):
        b = CognitiveBudget(capacity=100, allocated=50)
        with pytest.raises(ValueError, match="non-negative"):
            b.release(-10)


class TestCognitiveBudgetReset:
    def test_reset_sets_allocated_to_zero(self):
        b = CognitiveBudget(capacity=100, allocated=75)
        b.reset()
        assert b.allocated == 0
        assert b.eta == 100

    def test_reset_makes_thin(self):
        b = CognitiveBudget(capacity=100, allocated=90)
        assert b.is_thick()
        b.reset()
        assert b.is_thin()


class TestCognitiveBudgetSerialization:
    def test_to_dict(self):
        b = CognitiveBudget(capacity=100, allocated=25)
        d = b.to_dict()
        assert d["capacity"] == 100
        assert d["allocated"] == 25
        assert d["eta"] == 75
        assert d["thickness"] == pytest.approx(0.25)
        assert d["state"] == "thin"

    def test_to_dict_balanced(self):
        b = CognitiveBudget(capacity=100, allocated=50)
        d = b.to_dict()
        assert d["state"] == "balanced"

    def test_to_dict_thick(self):
        b = CognitiveBudget(capacity=100, allocated=85)
        d = b.to_dict()
        assert d["state"] == "thick"

    def test_repr_contains_key_values(self):
        b = CognitiveBudget(capacity=100, allocated=25)
        r = repr(b)
        assert "C=100" in r
        assert "γ=25.00" in r
        assert "η=75.00" in r
        assert "thin" in r
