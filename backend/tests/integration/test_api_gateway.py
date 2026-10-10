import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.agent.orchestrator import AgentResult
from app.config import Settings
from app.main import create_app
from app.schemas.agent import AgentStep
from app.schemas.response import Recommendation, RetryRecommendationResponse

DATA = Path(__file__).resolve().parents[3] / "data" / "mock-transactions-set-1"


class FakeAgent:
    """Stands in for the LLM agent; counts how often it is called."""

    def __init__(self, steps=None, raises=False):
        self.calls = 0
        self.steps = steps or []
        self.raises = raises

    def decide(self, request):
        self.calls += 1
        if self.raises:
            raise RuntimeError("boom")
        response = RetryRecommendationResponse(
            transaction_id=request.transaction_id,
            recommendation=Recommendation.RETRY_NOW,
            confidence_score=0.9,
            explanation="fake agent says retry",
        )
        return AgentResult(response=response, steps=self.steps, loops_used=len(self.steps))


def make_client(agent=None, **settings_overrides):
    agent = agent or FakeAgent()
    settings = Settings(database_url="sqlite://", **settings_overrides)  # in-memory DB
    return TestClient(create_app(settings, agent)), agent


def base_request(**overrides):
    body = {
        "transaction_id": "TXN-1",
        "amount": 1500.5,
        "currency": "USD",
        "payment_rail": "RTGS",
        "failure_code": "NETWORK_TIMEOUT",
        "failure_reason": "Connection timed out during handshake",
        "ordering_customer": {
            "name": "Globex Manufacturing Ltd",
            "account_number": "DE02120300000000202051",
            "bic_code": "COBADEFFXXX",
        },
        "beneficiary": {"name": "Acme GmbH", "account_number": "DE89370400440532013000", "bic_code": "DEUTDEFF"},
        "timestamp": "2026-10-10T10:00:00Z",
        "retry_count": 1,
    }
    body.update(overrides)
    return body


def _retry_budget_pairs():
    pairs = []
    for pattern in ("c5-*.json", "e6-*.json"):
        for f in sorted(DATA.glob(pattern)):
            scenario = json.loads(f.read_text(encoding="utf-8"))
            for pair in scenario["api_requests"]:
                pairs.append(pytest.param(pair, id=f"{scenario['scenario_id']}-{pair.get('label', 'x')}"))
    assert pairs, f"No scenario files found in {DATA}"
    return pairs


# ---------- circuit breaker (dataset scenarios C5 and E6) ----------
@pytest.mark.parametrize("pair", _retry_budget_pairs())
def test_retry_budget_scenarios(pair):
    client, agent = make_client()
    r = client.post("/retry-decision", json=pair["request"])
    assert r.status_code == pair["expected_http_status"]
    if r.status_code == 429:
        body = r.json()
        assert body["recommendation"] == "DONT_RETRY"
        assert body["confidence_score"] == 1.0
        assert "Max retry limit reached" in body["explanation"]
        assert body["transaction_id"] == pair["request"]["transaction_id"]
        assert agent.calls == 0  # the LLM is never triggered
    else:
        assert agent.calls == 1


def test_max_retry_limit_is_configurable():
    client, agent = make_client(max_retry_count=5)
    r = client.post("/retry-decision", json=base_request(retry_count=3))
    assert r.status_code == 200 and agent.calls == 1


# ---------- kill switch ----------
def test_kill_switch_defaults_to_off():
    client, _ = make_client()
    assert client.get("/admin/kill-switch").json()["active"] is False


def test_kill_switch_routes_everything_to_no_recommendation():
    client, agent = make_client()
    r = client.post("/admin/kill-switch", json={"active": True, "updated_by": "tester"})
    assert r.json()["active"] is True and r.json()["updated_by"] == "tester"

    for retry_count in (1, 10):  # even a transaction past the retry limit
        res = client.post("/retry-decision", json=base_request(retry_count=retry_count))
        assert res.status_code == 200
        assert res.json()["recommendation"] == "NO_RECOMMENDATION"
    assert agent.calls == 0

    record = client.app.state.repo.get_by_transaction_id("TXN-1")[0]
    assert record.decision_source == "KILL_SWITCH" and record.no_rec_reason == "KILL_SWITCH_ACTIVE"


def test_kill_switch_off_resumes_decisions():
    client, agent = make_client()
    client.post("/admin/kill-switch", json={"active": True})
    client.post("/admin/kill-switch", json={"active": False})
    assert client.post("/retry-decision", json=base_request()).json()["recommendation"] == "RETRY_NOW"
    assert agent.calls == 1


# ---------- persistence ----------
def test_decision_and_steps_are_persisted():
    steps = [
        AgentStep(step=1, thought="check the bank", action="check_bank_status",
                  action_input={"bic_code": "DEUTDEFF"}, observation="ONLINE"),
        AgentStep(step=2, action="final_answer", observation="RETRY_NOW"),
    ]
    client, _ = make_client(agent=FakeAgent(steps=steps))
    client.post("/retry-decision", json=base_request())

    records = client.app.state.repo.get_by_transaction_id("TXN-1")
    assert len(records) == 1
    rec = records[0]
    assert rec.recommendation == "RETRY_NOW" and rec.http_status == 200
    assert rec.failure_category == "TECHNICAL" and rec.decision_source == "AGENT"
    assert rec.loops_used == 2
    assert [s.action for s in rec.steps] == ["check_bank_status", "final_answer"]
    assert json.loads(rec.steps[0].action_input_json) == {"bic_code": "DEUTDEFF"}


def test_circuit_breaker_decision_is_persisted():
    client, _ = make_client()
    client.post("/retry-decision", json=base_request(retry_count=3))
    rec = client.app.state.repo.get_by_transaction_id("TXN-1")[0]
    assert rec.decision_source == "CIRCUIT_BREAKER" and rec.http_status == 429


# ---------- resilience and validation ----------
def test_agent_crash_returns_no_recommendation():
    client, _ = make_client(agent=FakeAgent(raises=True))
    r = client.post("/retry-decision", json=base_request())
    assert r.status_code == 200 and r.json()["recommendation"] == "NO_RECOMMENDATION"
    rec = client.app.state.repo.get_by_transaction_id("TXN-1")[0]
    assert rec.no_rec_reason == "INTERNAL_ERROR" and rec.decision_source == "FALLBACK"


def test_placeholder_agent_gives_safe_default():
    client = TestClient(create_app(Settings(database_url="sqlite://")))  # default NotConfiguredAgent
    r = client.post("/retry-decision", json=base_request())
    assert r.status_code == 200 and r.json()["recommendation"] == "NO_RECOMMENDATION"


@pytest.mark.parametrize("bad", [
    {"amount": -5},
    {"currency": "usd"},
    {"payment_rail": "CARRIER_PIGEON"},
    {"retry_count": -1},
])
def test_invalid_payload_returns_400(bad):
    client, agent = make_client()
    r = client.post("/retry-decision", json=base_request(**bad))
    assert r.status_code == 400 and agent.calls == 0


def test_missing_field_returns_400():
    client, _ = make_client()
    body = base_request()
    del body["beneficiary"]
    assert client.post("/retry-decision", json=body).status_code == 400