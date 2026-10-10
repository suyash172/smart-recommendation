import pytest

from app.services.circuit_breaker import is_retry_budget_exhausted


@pytest.mark.parametrize("count,limit,expected", [
    (0, 3, False), (2, 3, False), (3, 3, True), (5, 3, True), (10, 3, True), (3, 5, False),
])
def test_retry_budget(count, limit, expected):
    assert is_retry_budget_exhausted(count, limit) is expected