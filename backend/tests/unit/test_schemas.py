import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.schemas.request import RetryRecommendationRequest
from app.schemas.response import (
    Recommendation,
    RetryRecommendationResponse,
    dont_retry_max_retries,
    no_recommendation,
)

DATA = Path(__file__).resolve().parents[3] / "data" / "mock-transactions-set-1"


def _cases():
    files = sorted(DATA.glob("*.json"))
    assert files, f"No scenario files found in {DATA}"
    cases = []
    for f in files:
        scenario = json.loads(f.read_text(encoding="utf-8"))
        for i, pair in enumerate(scenario["api_requests"]):
            cases.append(pytest.param(pair, id=f"{scenario['scenario_id']}-{pair.get('label', i)}"))
    return cases


@pytest.mark.parametrize("pair", _cases())


def test_dataset_request_and_response_are_valid(pair):
    RetryRecommendationRequest.model_validate(pair["request"])
    RetryRecommendationResponse.model_validate(pair["expected_response"])


def _resp(**overrides):
    base = dict(transaction_id="T1", recommendation="RETRY_NOW", confidence_score=0.9, explanation="ok")
    base.update(overrides)
    return base


def test_retry_later_requires_timing():
    with pytest.raises(ValidationError):
        RetryRecommendationResponse(**_resp(recommendation="RETRY_LATER"))


def test_retry_after_update_requires_suggestions():
    with pytest.raises(ValidationError):
        RetryRecommendationResponse(**_resp(recommendation="RETRY_AFTER_UPDATE"))
    with pytest.raises(ValidationError):
        RetryRecommendationResponse(**_resp(recommendation="RETRY_AFTER_UPDATE", correction_suggestions=[]))


def test_timing_not_allowed_on_retry_now():
    with pytest.raises(ValidationError):
        RetryRecommendationResponse(**_resp(optimal_timing="2026-10-11T10:00:00Z"))


def test_confidence_out_of_range():
    with pytest.raises(ValidationError):
        RetryRecommendationResponse(**_resp(confidence_score=1.5))


def test_unknown_recommendation_rejected():
    with pytest.raises(ValidationError):
        RetryRecommendationResponse(**_resp(recommendation="MAYBE"))


def test_request_rejects_bad_input():
    good = json.loads(next(DATA.glob("e1-*.json")).read_text(encoding="utf-8"))["api_requests"][0]["request"]
    for field, value in [("amount", -5), ("currency", "usd"), ("payment_rail", "CARRIER_PIGEON")]:
        with pytest.raises(ValidationError):
            RetryRecommendationRequest.model_validate({**good, field: value})


def test_circuit_breaker_response_is_deterministic():
    r = dont_retry_max_retries("T1", 3, 3)
    assert r.recommendation == Recommendation.DONT_RETRY
    assert r.confidence_score == 1.0
    assert "Max retry limit reached" in r.explanation


def test_no_recommendation_response():
    r = no_recommendation("T1", "kill switch active")
    assert r.recommendation == Recommendation.NO_RECOMMENDATION
    assert r.confidence_score < 0.5
    assert "Unable to produce a recommendation" in r.explanation