"""Tests for AI Visibility cost tracker."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from ai_visibility.cost_tracker import CostTracker


def test_initial_total_is_zero():
    ct = CostTracker()
    assert ct.total == 0.0


def test_add_positive_amount():
    ct = CostTracker()
    ct.add(0.42)
    ct.add(0.38)
    assert abs(ct.total - 0.80) < 0.001


def test_add_none_is_ignored():
    ct = CostTracker()
    ct.add(0.10)
    ct.add(None)
    assert abs(ct.total - 0.10) < 0.001


def test_add_zero_is_fine():
    ct = CostTracker()
    ct.add(0.0)
    assert ct.total == 0.0


def test_add_negative_is_ignored():
    ct = CostTracker()
    ct.add(0.50)
    ct.add(-0.10)
    assert abs(ct.total - 0.50) < 0.001


def test_add_non_numeric_string_is_ignored():
    ct = CostTracker()
    ct.add("not a number")
    assert ct.total == 0.0


def test_add_from_response_dict():
    ct = CostTracker()
    resp = {"status_code": 20000, "cost": 0.0031, "money_spent": 0.42}
    ct.add(resp.get("money_spent", 0))
    assert abs(ct.total - 0.42) < 0.001


def test_add_from_response_missing_key():
    ct = CostTracker()
    resp = {"status_code": 20000}
    ct.add(resp.get("money_spent"))
    assert ct.total == 0.0
