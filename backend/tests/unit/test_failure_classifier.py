import pytest

from app.schemas.agent import FailureCategory
from app.schemas.response import Recommendation
from app.services.failure_classifier import classify_failure


@pytest.mark.parametrize("code", ["NETWORK_TIMEOUT", "gateway_timeout", "PROCESSING_ERROR"])
def test_technical_codes(code):
    assert classify_failure(code) == FailureCategory.TECHNICAL


@pytest.mark.parametrize("code", ["NAME_MISMATCH", "INVALID_ACCOUNT", "INSUFFICIENT_FUNDS", "ACCOUNT_CLOSED"])
def test_structural_codes(code):
    assert classify_failure(code) == FailureCategory.STRUCTURAL


def test_unknown_code_uses_recommendation():
    assert classify_failure("WEIRD", Recommendation.RETRY_LATER) == FailureCategory.TECHNICAL
    assert classify_failure("WEIRD", Recommendation.RETRY_AFTER_UPDATE) == FailureCategory.STRUCTURAL