"""Tests for onboarding questionnaire fields."""
from web.models import User


def test_user_has_new_fields():
    u = User(email="t@test.com")
    assert hasattr(u, "age_range")
    assert hasattr(u, "preferred_days_json")
    assert hasattr(u, "height_cm")
    assert hasattr(u, "weight_kg")
